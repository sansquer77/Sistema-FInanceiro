from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from financeiro import database
from financeiro.secure_config import (
    SecureConfigError,
    ai_settings_status,
    load_ai_settings,
)

MAX_SUMMARY_TOKENS = 700
DEFAULT_TEMPERATURE = 0.2
SUMMARY_TIMEOUT_SECONDS = 15

SYSTEM_PROMPT = (
    "Você é um assistente conciso. Reescreva o resumo financeiro abaixo de forma natural, "
    "mantendo os valores e fatos. Não altere números, não invente dados, não dê recomendações "
    "personalizadas de investimento ou crédito. Use tom explicativo e não prescritivo."
)


def generate_ai_summary(user_id: int, trends_payload: dict) -> str | None:
    """
    spec: tendencias-saude-financeira v1.9 — critérios 12, 13, 14, 16 e 17
    Reescreve o resumo local com IA, usando payload minimizado, timeout curto e
    fallback imediato para None quando a IA estiver indisponível ou retornar conteúdo inválido.
    """
    settings = ai_settings_status(user_id)
    if not settings["enabled"] or not settings["configured"]:
        return None

    api_key = ""
    if settings["has_api_key"]:
        # spec: tendencias-saude-financeira v1.9 — critério 28
        # O segredo nunca deve transitar na API; aqui é usado apenas para a requisição externa.
        full = load_ai_settings(user_id)
        api_key = str(full.get("api_key") or "").strip()

    base_url = str(settings["base_url"] or "").rstrip("/")
    model = str(settings["model"] or "").strip()
    if not base_url or not model:
        return None

    url = f"{base_url}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings["auth_type"] == "bearer" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    minimized = minimize_trends_payload(trends_payload)
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(minimized, ensure_ascii=False)},
        ],
        "temperature": float(settings.get("temperature") or DEFAULT_TEMPERATURE),
        "max_tokens": int(settings.get("max_tokens") or MAX_SUMMARY_TOKENS),
    }

    request = Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    # spec: tendencias-saude-financeira v1.9 — critério 16
    # Nenhuma chamada de IA pode manter conexão SQLite aberta durante a requisição externa.
    # (a conexão já foi fechada antes de chamar esta função)
    timeout = int(settings.get("timeout_seconds") or SUMMARY_TIMEOUT_SECONDS)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    return extract_summary_text(payload)


def minimize_trends_payload(trends_payload: dict) -> dict:
    """
    Minimiza os dados enviados à IA: apenas resumo local, achados principais e
    assinaturas/eventos pontuais, sem valores brutos completos, histórico ou segredos.
    """
    findings = trends_payload.get("achados") or []
    minimized_findings = [
        {
            "tipo": f.get("tipo"),
            "titulo": f.get("titulo"),
            "descricao": f.get("descricao"),
        }
        for f in findings[:8]
    ]
    subscriptions = trends_payload.get("assinaturas_e_servicos") or []
    minimized_subscriptions = [
        {
            "subcategoria": s.get("subcategory_name"),
            "valor_cents": s.get("valor_cents"),
        }
        for s in subscriptions
    ]
    point_events = trends_payload.get("eventos_pontuais") or []
    minimized_events = [
        {
            "tipo": e.get("tipo"),
            "descricao": e.get("descricao"),
            "valor_cents": e.get("valor_cents"),
        }
        for e in point_events[:5]
    ]
    return {
        "month": trends_payload.get("month"),
        "confianca": trends_payload.get("confianca"),
        "resumo_local": trends_payload.get("resumo_local"),
        "receitas_mes_cents": trends_payload.get("receitas_mes_cents"),
        "despesas_mes_cents": trends_payload.get("despesas_mes_cents"),
        "saldo_mes_cents": trends_payload.get("saldo_mes_cents"),
        "achados": minimized_findings,
        "assinaturas_e_servicos": minimized_subscriptions,
        "eventos_pontuais": minimized_events,
    }


def extract_summary_text(payload: dict) -> str | None:
    try:
        choices = payload.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        content = str(message.get("content") or "").strip()
        return content or None
    except (AttributeError, TypeError, IndexError):
        return None


def ai_summary_enabled(user_id: int) -> bool:
    """Verifica se a configuração de IA permite reescrita automática."""
    try:
        settings = ai_settings_status(user_id)
        return bool(settings["enabled"] and settings["configured"])
    except SecureConfigError:
        return False
