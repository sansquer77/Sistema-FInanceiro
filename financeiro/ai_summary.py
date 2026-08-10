from __future__ import annotations

import json
import os
import ssl
from urllib.parse import quote
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
    "Você escreve a síntese executiva integrada do módulo Tendências de um app financeiro pessoal. "
    "Produza 2 a 4 frases curtas, naturais e úteis, como uma leitura do mês feita pelo próprio sistema. "
    "Mantenha valores e fatos, não altere números, não invente dados e não dê recomendações personalizadas "
    "de investimento, crédito ou consumo. Destaque a causa provável apenas quando houver evidência local no "
    "payload; se a confiança for baixa, deixe claro que a leitura ainda é cautelosa. Não liste limites de "
    "orçamento, eventos pontuais ou antecipações de parcelas em detalhe; esses itens aparecem em cards "
    "separados abaixo do resumo."
)


def generate_ai_summary(user_id: int, trends_payload: dict) -> str | None:
    """
    spec: tendencias-saude-financeira v2.19 — critérios 12, 13, 14, 16 e 17
    Reescreve o resumo local com IA, usando payload minimizado, timeout curto e
    fallback imediato para None quando a IA estiver indisponível ou retornar conteúdo inválido.
    """
    settings = ai_settings_status(user_id)
    if not settings["enabled"] or not settings["configured"]:
        return None

    api_key = ""
    if settings["has_api_key"]:
        # spec: tendencias-saude-financeira v2.19 — critério 28
        # O segredo nunca deve transitar na API; aqui é usado apenas para a requisição externa.
        full = load_ai_settings(user_id)
        api_key = str(full.get("api_key") or "").strip()

    base_url = str(settings["base_url"] or "").rstrip("/")
    model = str(settings["model"] or "").strip()
    if not base_url or not model:
        return None

    minimized = minimize_trends_payload(trends_payload)
    request_payload = build_ai_request(settings, api_key, minimized)

    request = Request(
        request_payload["url"],
        data=json.dumps(request_payload["body"], ensure_ascii=False).encode("utf-8"),
        headers=request_payload["headers"],
        method="POST",
    )

    # spec: tendencias-saude-financeira v2.19 — critério 16
    # Nenhuma chamada de IA pode manter conexão SQLite aberta durante a requisição externa.
    # (a conexão já foi fechada antes de chamar esta função)
    timeout = int(settings.get("timeout_seconds") or SUMMARY_TIMEOUT_SECONDS)
    try:
        with urlopen(request, timeout=timeout, context=ai_ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    return extract_summary_text(payload, provider=str(settings.get("provider") or "custom"))


def ai_ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def build_ai_request(settings: dict, api_key: str, minimized_payload: dict) -> dict:
    provider = str(settings.get("provider") or "custom")
    base_url = str(settings.get("base_url") or "").rstrip("/")
    model = str(settings.get("model") or "").strip()
    temperature = float(settings.get("temperature") or DEFAULT_TEMPERATURE)
    max_tokens = int(settings.get("max_tokens") or MAX_SUMMARY_TOKENS)
    if provider == "google":
        # spec: tendencias-saude-financeira v2.19 — critérios 12, 24 e 32
        # Google/Gemini não usa o contrato OpenAI-compatible; usa generateContent.
        gemini_model = model.removeprefix("models/")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-goog-api-key"] = api_key
        return {
            "url": f"{base_url}/models/{quote(gemini_model, safe='')}:generateContent",
            "headers": headers,
            "body": {
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": json.dumps(minimized_payload, ensure_ascii=False)}],
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            },
        }
    if provider == "anthropic":
        # spec: tendencias-saude-financeira v2.19 — critérios 12, 24 e 32
        # Anthropic/Claude usa a Messages API nativa, não Chat Completions.
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if api_key:
            headers["x-api-key"] = api_key
        return {
            "url": f"{base_url}/messages",
            "headers": headers,
            "body": {
                "model": model,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": json.dumps(minimized_payload, ensure_ascii=False)},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        }

    headers = {"Content-Type": "application/json"}
    if settings["auth_type"] == "bearer" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return {
        "url": f"{base_url}/chat/completions",
        "headers": headers,
        "body": {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(minimized_payload, ensure_ascii=False)},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    }


def minimize_trends_payload(trends_payload: dict) -> dict:
    """
    Minimiza os dados enviados à IA: apenas resumo local, achados narrativos e
    contadores operacionais, sem valores brutos completos, histórico ou segredos.
    """
    findings = trends_payload.get("achados") or []
    narrative_finding_types = {"confianca", "receita", "despesa", "assinatura_servico"}
    minimized_findings = [
        {
            "tipo": f.get("tipo"),
            "titulo": f.get("titulo"),
            "descricao": f.get("descricao"),
        }
        for f in findings
        if f.get("tipo") in narrative_finding_types
    ]
    subscriptions = trends_payload.get("assinaturas_e_servicos") or []
    minimized_subscriptions = [
        {
            "subcategoria": s.get("subcategory_name"),
            "valor_cents": s.get("valor_cents"),
        }
        for s in subscriptions
    ]
    operational_context = summarize_operational_context(trends_payload)
    return {
        "month": trends_payload.get("month"),
        "confianca": trends_payload.get("confianca"),
        "resumo_local": trends_payload.get("resumo_local"),
        "receitas_mes_cents": trends_payload.get("receitas_mes_cents"),
        "despesas_mes_cents": trends_payload.get("despesas_mes_cents"),
        "saldo_mes_cents": trends_payload.get("saldo_mes_cents"),
        "achados": minimized_findings[:8],
        "assinaturas_e_servicos": minimized_subscriptions,
        "contexto_operacional": operational_context,
    }


def summarize_operational_context(trends_payload: dict) -> dict:
    findings = trends_payload.get("achados") or []
    counts = {
        "limites_em_cards": 0,
        "eventos_pontuais_em_cards": 0,
        "antecipacoes_em_cards": 0,
    }
    for finding in findings:
        finding_type = finding.get("tipo")
        if finding_type == "limite":
            counts["limites_em_cards"] += 1
        elif finding_type == "evento_pontual":
            counts["eventos_pontuais_em_cards"] += 1
        elif finding_type == "antecipacao_parcela":
            counts["antecipacoes_em_cards"] += 1
    counts["total_antecipado_cents"] = sum(
        int(item.get("valor_cents") or 0)
        for item in trends_payload.get("antecipacao_parcelas") or []
    )
    counts["quantidade_antecipacoes"] = len(trends_payload.get("antecipacao_parcelas") or [])
    return counts


def extract_summary_text(payload: dict, provider: str = "custom") -> str | None:
    if provider == "google":
        try:
            candidates = payload.get("candidates") or []
            parts = candidates[0].get("content", {}).get("parts") or []
            content = "\n".join(str(part.get("text") or "").strip() for part in parts if part.get("text"))
            return content.strip() or None
        except (AttributeError, TypeError, IndexError):
            return None
    if provider == "anthropic":
        try:
            parts = payload.get("content") or []
            content = "\n".join(str(part.get("text") or "").strip() for part in parts if part.get("type") == "text" and part.get("text"))
            return content.strip() or None
        except (AttributeError, TypeError):
            return None
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
