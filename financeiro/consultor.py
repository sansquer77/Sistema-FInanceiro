from __future__ import annotations

import re
import unicodedata
import logging
from datetime import date, datetime
from financeiro.ai_endpoint_security import ai_urlopen

# Reexports preservam os imports públicos; a montagem central continua nesta fachada.
from financeiro.consultor_context import (
    MARKET_DATA_SOURCES,
    build_ralos_context,
    build_subscriptions_context,
    build_allocation_context,
    build_currency_exposure_context,
    build_portfolio_analysis_context,
    build_allocation_goals_context,
    build_score_context,
    build_score_evolution_context,
    _compact_pillars,
    build_lifestyle_context,
    build_maturities_context,
    build_financial_commitments_context,
    _load_portfolio_positions,
    money_context,
    summarize_portfolio,
    group_positions_by,
    compact_positions,
    market_data_context,
    cents_to_reais,
    format_brl_cents,
    add_money_displays,
    safe_quote_source,
    compact_budget_alerts,
    compact_point_events,
    compact_acceleration,
    normalize_subscriptions_payload,
    amount_from_row,
    compact_named_amounts,
    compact_maturities,
)
from financeiro.consultor_cashflow import build_maturity_cashflow_context
from financeiro import consultor_history as history_store
from financeiro import consultor_provider as provider_adapter
from financeiro.ai_summary import ai_ssl_context, extract_summary_text
from financeiro.secure_config import load_ai_settings
from financeiro.consultor_catalog import (
    DISCLAIMER,
    RESPONSE_SECTIONS,
    INVESTOR_PROFILES,
    PERIOD_WINDOWS,
    SCORE_EVOLUTION_WINDOWS,
    AnalysisCard,
    ANALYSIS_CATALOG,
    CATALOG_BY_ID,
    list_analysis_cards,
    validate_investor_profile,
    validate_analysis_id,
    validate_period_window,
    _period_label,
    build_system_prompt,
    standard_response_skeleton,
)
from financeiro.consultor_settings import (
    COMPLEMENTARY_PROFILE_SCHEMA_VERSION,
    COMPLEMENTARY_PROFILE_FIELDS,
    COMPLEMENTARY_PROFILE_ENUMS,
    DEFAULT_SETTINGS,
    get_consultor_settings,
    consultor_blocked_reason,
    save_consultor_settings,
    sync_consultor_with_ai_settings,
    get_complementary_profile,
    save_complementary_profile,
    delete_complementary_profile,
    normalize_complementary_profile,
    normalize_optional_int,
    normalize_profile_enum,
)
from financeiro.consultor_errors import ConsultorError
from financeiro.ai_execution import get_ai_execution_settings


REFUSAL_MESSAGE = (
    "Nao posso recomendar a venda ou o resgate de investimentos, nem garantir "
    "retornos ou ausencia de risco. Esta analise deve permanecer educacional e informativa."
)
_FORBIDDEN_SALE_ACTION = r"(?:venda|vender|venderia|liquide|liquidar|resgate|resgatar|desfaca|desfazer)"
# Portfolio context omits position names and tickers, so explicit investment sales fail closed.
_FORBIDDEN_TICKER_SALE_PATTERN = (
    r"\b(?i:" + _FORBIDDEN_SALE_ACTION + r")"
    + r"\s+(?:(?:o|a|os|as|um|uma|de|do|da|das|dos|seu|sua|seus|suas)\s+)?"
    + r"[A-Z]{2,6}\d{0,2}\b"
)
FORBIDDEN_OUTPUT_PATTERNS = (
    r"\b" + _FORBIDDEN_SALE_ACTION + r"\b.*\b(acao|acoes|ativo|ativos|ticker|fundo|fundos|etf|etfs|fii|fiis|cripto|bitcoin|cdb|lci|lca|tesouro|investimento|investimentos|posicao|posicoes|carteira)\b",
    r"\b(recomendo|sugiro|indico|aconselho|deveria|deve|vale a pena|considere)\b.{0,60}\b" + _FORBIDDEN_SALE_ACTION + r"\b",
    r"\b(retorno|rentabilidade)\s+(garantido|garantida|garantidos|garantidas)\b",
    r"\b(sem risco|risco zero)\b",
)
_FORBIDDEN_NEGATION_WINDOW = (
    r"\b(nao|nunca|sem|evite|evitar|evitando|desaconselho|desaconselha|desaconselhar)"
    r"|deixe\s+de|deixa\s+de|deixar\s+de"
)
CONSULTOR_MAX_TOKENS = 900
ANALISE_CARTEIRA_MAX_TOKENS = 2500
CONSULTOR_MIN_TIMEOUT_SECONDS = 20
CONSULTOR_DAILY_QUOTA = history_store.CONSULTOR_DAILY_QUOTA
CONSULTOR_FAILURE_COOLDOWN_SECONDS = history_store.CONSULTOR_FAILURE_COOLDOWN_SECONDS
DEFAULT_TEMPERATURE = provider_adapter.DEFAULT_TEMPERATURE
LOGGER = logging.getLogger(__name__)


def execute_consultor_analysis(
    user_id: int,
    analysis_id: object,
    *,
    month: object | None = None,
    period_window: object | None = None,
    reference_date: date | None = None,
    ai_client=None,
    now: datetime | None = None,
    portfolio_positions: list[dict] | None = None,
) -> dict:
    # spec: consultor/consultor v2.16 - critérios 40 a 43, 64 a 68
    normalized_user_id = int(user_id)
    normalized_analysis_id = validate_analysis_id(analysis_id)
    current_time = now or datetime.now()
    consultor_settings = get_consultor_settings(normalized_user_id)
    if not consultor_settings["available"]:
        raise ConsultorError("O Consultor nao esta disponivel. Verifique as Preferencias.")
    normalized_period = validate_period_window(period_window, analysis_id=normalized_analysis_id)
    if "remota" not in get_ai_execution_settings(normalized_user_id)["order"]:
        raise ConsultorError("A política atual não permite IA remota para o Consultor.")
    assert_not_in_failure_cooldown(normalized_user_id, normalized_analysis_id, current_time)
    assert_daily_quota_available(normalized_user_id, current_time.date())

    ai_settings = load_ai_settings(normalized_user_id)
    max_tokens = normalize_consultor_max_tokens(ai_settings.get("max_tokens"))
    if normalized_analysis_id == "analise_carteira":
        max_tokens = max(max_tokens, ANALISE_CARTEIRA_MAX_TOKENS)
    timeout_seconds = normalize_consultor_timeout(ai_settings.get("timeout_seconds"))
    macro_research = (
        collect_portfolio_macro_research(ai_settings, timeout_seconds=timeout_seconds)
        if normalized_analysis_id == "analise_carteira"
        else None
    )
    context = build_analysis_context(
        normalized_user_id,
        normalized_analysis_id,
        month=month,
        period_window=normalized_period,
        reference_date=reference_date,
        investor_profile=consultor_settings["investor_profile"],
        portfolio_positions=portfolio_positions,
    )
    if macro_research is not None:
        context["macro_research"] = macro_research
    system_prompt = build_system_prompt(
        normalized_analysis_id,
        investor_profile=consultor_settings["investor_profile"],
        period_window=normalized_period,
    )
    messages = build_ai_messages(system_prompt, context)
    client = ai_client or call_consultor_ai_provider
    failure_stage = "provider_request"
    try:
        output = client(
            ai_settings,
            messages,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        failure_stage = "output_validation"
        text = str(output or "").strip()
        if not text:
            raise ConsultorError("O Consultor esta indisponivel no momento.")
        text = postprocess_consultor_output(text)
    except ConsultorError as exc:
        root_cause = exc
        provider_error_reason = ""
        provider_diagnostics = {}
        while root_cause.__cause__ is not None and root_cause.__cause__ is not root_cause:
            cause = root_cause.__cause__
            provider_error_reason = provider_error_reason or str(getattr(cause, "reason", "") or "")
            if not provider_diagnostics:
                cause_diagnostics = getattr(cause, "diagnostics", None)
                if isinstance(cause_diagnostics, dict):
                    provider_diagnostics = cause_diagnostics
            root_cause = root_cause.__cause__
        provider_error_reason = provider_adapter.safe_provider_error_reason(
            provider_error_reason or getattr(root_cause, "reason", "")
        )
        if not provider_diagnostics:
            root_diagnostics = getattr(root_cause, "diagnostics", None)
            if isinstance(root_diagnostics, dict):
                provider_diagnostics = root_diagnostics
        http_status = getattr(root_cause, "code", None)
        LOGGER.warning(
            "consultor analysis failed provider=%s model=%s base_url=%s stage=%s error_type=%s "
            "provider_error_reason=%s provider_diagnostics=%s http_status=%s",
            str(ai_settings.get("provider") or "custom"),
            str(ai_settings.get("model") or ""),
            str(ai_settings.get("base_url") or ""),
            failure_stage,
            type(root_cause).__name__,
            provider_error_reason,
            provider_adapter.format_safe_provider_diagnostics(provider_diagnostics),
            http_status if isinstance(http_status, int) else "",
        )
        register_failure_cooldown(normalized_user_id, normalized_analysis_id, current_time)
        raise ConsultorError("O Consultor esta indisponivel no momento.") from exc
    execution = persist_consultor_analysis(
        normalized_user_id,
        normalized_analysis_id,
        normalized_period,
        text,
        current_time,
    )
    clear_failure_cooldown(normalized_user_id, normalized_analysis_id)
    return {
        "analysis_execution_id": execution["id"],
        "analysis_id": normalized_analysis_id,
        "period_window": normalized_period,
        "output": text,
        "created_at": execution["created_at"],
        "context": context,
        "provider": ai_settings.get("provider") or "custom",
        "model": ai_settings.get("model") or "",
        "max_tokens": max_tokens,
        "timeout_seconds": timeout_seconds,
        "macro_research": context.get("macro_research"),
    }


def prepare_local_analysis(user_id: int, analysis_id: object, *, period_window: object | None = None,
                           portfolio_positions: list[dict] | None = None) -> dict:
    """Monta no backend o único prompt/contexto que o worker local pode receber."""
    settings = get_consultor_settings(int(user_id))
    if not settings["consultor_enabled"]:
        raise ConsultorError("O Consultor nao esta disponivel. Verifique as Preferencias.")
    execution_settings = get_ai_execution_settings(int(user_id))
    if "local" not in execution_settings["order"]:
        raise ConsultorError("A política atual não permite IA local para o Consultor.")
    normalized_id = validate_analysis_id(analysis_id)
    normalized_period = validate_period_window(period_window, analysis_id=normalized_id)
    macro_research = None
    if normalized_id == "analise_carteira":
        macro_research = {"status": "unavailable", "summary": "", "sources": []}
        if "remota" in execution_settings["order"]:
            remote_settings = load_ai_settings(int(user_id))
            macro_research = collect_portfolio_macro_research(
                remote_settings,
                timeout_seconds=normalize_consultor_timeout(remote_settings.get("timeout_seconds")),
            )
    context = build_analysis_context(int(user_id), normalized_id, period_window=normalized_period,
        investor_profile=settings["investor_profile"], portfolio_positions=portfolio_positions)
    if macro_research is not None:
        context["macro_research"] = macro_research
    return {
        "analysis_id": normalized_id,
        "period_window": normalized_period,
        "messages": build_ai_messages(build_system_prompt(normalized_id, investor_profile=settings["investor_profile"], period_window=normalized_period), context),
        "max_tokens": 900,
        "temperature": 0.2,
        "macro_research": macro_research,
    }


# spec: consultor/consultor v2.16 — critérios 64 a 68
def collect_portfolio_macro_research(ai_settings: dict, *, timeout_seconds: int) -> dict:
    try:
        research = provider_adapter.call_consultor_market_research(
            ai_settings,
            timeout_seconds=min(int(timeout_seconds), 30),
            opener=ai_urlopen,
            ssl_context_factory=ai_ssl_context,
        )
    except provider_adapter.ConsultorProviderError as exc:
        LOGGER.warning(
            "consultor macro research unavailable provider=%s error_type=%s provider_error_reason=%s "
            "provider_diagnostics=%s",
            str(ai_settings.get("provider") or "custom"),
            type(exc).__name__,
            provider_adapter.safe_provider_error_reason(exc.reason),
            provider_adapter.format_safe_provider_diagnostics(exc),
        )
        research = None
    if research:
        return research
    return {"status": "unavailable", "summary": "", "sources": []}


def complete_local_analysis(user_id: int, analysis_id: object, output: object, *, period_window: object | None = None,
                            now: datetime | None = None) -> dict:
    current_time = now or datetime.now()
    normalized_id = validate_analysis_id(analysis_id)
    normalized_period = validate_period_window(period_window, analysis_id=normalized_id)
    assert_daily_quota_available(int(user_id), current_time.date())
    text = postprocess_consultor_output(output)
    execution = persist_consultor_analysis(int(user_id), normalized_id, normalized_period, text, current_time)
    clear_failure_cooldown(int(user_id), normalized_id)
    return {"analysis_execution_id": execution["id"], "analysis_id": normalized_id,
            "period_window": normalized_period, "output": text, "created_at": execution["created_at"],
            "provider": "webllm", "model": "Qwen2.5-3B-Instruct-q4f16_1-MLC"}


def assert_daily_quota_available(user_id: int, current_date: date) -> None:
    if history_store.daily_quota_exceeded(user_id, current_date):
        raise ConsultorError("Limite diario do Consultor atingido. Tente novamente amanha.")


def consultor_daily_usage(user_id: int, current_date: date) -> int:
    return history_store.daily_usage(user_id, current_date)


def persist_consultor_analysis(
    user_id: int,
    analysis_id: str,
    period_window: str | None,
    output: str,
    current_time: datetime,
) -> dict:
    return history_store.persist_analysis(user_id, analysis_id, period_window, output, current_time)


def list_consultor_history(user_id: int, *, limit: int = 50) -> list[dict]:
    return history_store.list_history(user_id, limit=limit)


def assert_not_in_failure_cooldown(user_id: int, analysis_id: str, current_time: datetime) -> None:
    remaining = failure_cooldown_remaining(user_id, analysis_id, current_time)
    if remaining > 0:
        raise ConsultorError(
            f"O Consultor esta indisponivel no momento. Tente novamente em {remaining} segundos."
        )


def register_failure_cooldown(user_id: int, analysis_id: str, current_time: datetime) -> None:
    history_store.register_failure_cooldown(user_id, analysis_id, current_time)


def clear_failure_cooldown(user_id: int, analysis_id: str) -> None:
    history_store.clear_failure_cooldown(user_id, analysis_id)


def failure_cooldown_remaining(user_id: int, analysis_id: str, current_time: datetime) -> int:
    return history_store.failure_cooldown_remaining(user_id, analysis_id, current_time)


def postprocess_consultor_output(output: object) -> str:
    # spec: consultor/consultor v2.15 - critérios 62 e 63
    text = str(output or "").strip()
    if not text:
        raise ConsultorError("O Consultor esta indisponivel no momento.")
    text = remove_internal_cent_summary_lines(text)
    normalized = normalize_text(text)
    if contains_forbidden_recommendation(normalized, original_text=text):
        return refusal_response()
    missing_sections = [section for section in RESPONSE_SECTIONS if not has_section(text, section)]
    missing_without_disclaimer = [section for section in missing_sections if section != "Disclaimer"]
    if missing_without_disclaimer:
        LOGGER.warning(
            "consultor output validation failed missing_sections=%s output_prefix=%s",
            ",".join(missing_without_disclaimer),
            text[:800].replace("\n", " "),
        )
        raise ConsultorError("O Consultor esta indisponivel no momento.")
    return replace_consultor_disclaimer(text)


def has_section(text: str, section: str) -> bool:
    # spec: consultor/consultor v2.14 - cabeçalhos com acentos normalizados
    normalized_text = normalize_text(text)
    escaped = re.escape(section)
    return bool(re.search(
        rf"(^|\n)\s*(?:[-*]\s+)?(?:#{{1,6}}\s*)?(\*\*)?{escaped}(\*\*)?\s*:?",
        normalized_text,
        flags=re.IGNORECASE,
    ))


def contains_forbidden_recommendation(normalized_text: str, *, original_text: str | None = None) -> bool:
    # spec: consultor/consultor v2.14 - bloqueia indicacoes de venda, nao de compra
    # Frases preventivas sobre venda continuam permitidas quando a negacao vem antes do verbo.
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        for match in re.finditer(pattern, normalized_text):
            action_match = re.search(r"\b" + _FORBIDDEN_SALE_ACTION + r"\b", match.group())
            action_start = match.start() + action_match.start() if action_match else match.start()
            before = normalized_text[max(0, action_start - 60):action_start]
            before = re.split(r"[.!?;,\n]", before)[-1]
            if re.search(_FORBIDDEN_NEGATION_WINDOW, before):
                continue
            LOGGER.warning(
                "consultor forbidden recommendation detected pattern=%s match=%s",
                pattern,
                match.group()[:200],
            )
            return True
    if original_text:
        for match in re.finditer(_FORBIDDEN_TICKER_SALE_PATTERN, original_text):
            before = normalize_text(original_text[max(0, match.start() - 60):match.start()])
            before = re.split(r"[.!?;,\n]", before)[-1]
            if not re.search(_FORBIDDEN_NEGATION_WINDOW, before):
                LOGGER.warning(
                    "consultor forbidden ticker sale detected match=%s",
                    match.group()[:200],
                )
                return True
    return False


def has_risk_level(normalized_text: str) -> bool:
    return bool(re.search(r"\brisco\s+(baixo|medio|alto)\b", normalized_text))


def append_consultor_disclaimer(text: str) -> str:
    return f"{text.rstrip()}\n\nDisclaimer\n{DISCLAIMER}"


def remove_internal_cent_summary_lines(text: str) -> str:
    filtered_lines = []
    for line in text.splitlines():
        label = normalize_text(line).lstrip(" -*#").replace("*", "").strip()
        if re.match(r"total\s+(?:em|in)\s+(?:cents|centavos)\b", label):
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines).strip()


def replace_consultor_disclaimer(text: str) -> str:
    lines = text.rstrip().splitlines()
    disclaimer_start = next(
        (index for index, line in enumerate(lines) if has_section(line, "Disclaimer")),
        None,
    )
    if disclaimer_start is not None:
        prefix = "\n".join(lines[:disclaimer_start]).rstrip()
        heading = lines[disclaimer_start].strip()
        if prefix:
            return f"{prefix}\n\n{heading}\n{DISCLAIMER}"
        return f"{heading}\n{DISCLAIMER}"
    return append_consultor_disclaimer(text)


def refusal_response() -> str:
    return (
        f"Resumo\n{REFUSAL_MESSAGE}\n\n"
        "Analise de Dados\nA resposta original foi bloqueada por violar as limitacoes obrigatorias "
        "do Consultor.\n\n"
        "Pontos de Atencao (Riscos)\nRisco Alto: a saida continha recomendacao direta ou afirmacao "
        "vedada sobre ativo especifico.\n\n"
        "Plano de Acao (Educacional)\nUse o Consultor para avaliar fatos, riscos e alternativas gerais, "
        "mantendo a decisao final fora do app.\n\n"
        f"Disclaimer\n{DISCLAIMER}"
    )


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = "".join(char for char in text if not unicodedata.combining(char))
    return ascii_text.lower()


def normalize_consultor_max_tokens(value: object) -> int:
    try:
        configured = int(value if value not in (None, "") else 700)
    except (TypeError, ValueError):
        configured = 700
    return max(1, min(configured, CONSULTOR_MAX_TOKENS))


def normalize_consultor_timeout(value: object) -> int:
    try:
        configured = int(value if value not in (None, "") else CONSULTOR_MIN_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        configured = CONSULTOR_MIN_TIMEOUT_SECONDS
    return max(CONSULTOR_MIN_TIMEOUT_SECONDS, configured)


def build_ai_messages(system_prompt: str, context: dict) -> list[dict]:
    return provider_adapter.build_ai_messages(system_prompt, context)


def call_consultor_ai_provider(
    ai_settings: dict,
    messages: list[dict],
    *,
    max_tokens: int,
    timeout_seconds: int,
) -> str:
    # Dependências tardias preservam os pontos de mock públicos da fachada.
    try:
        return provider_adapter.call_consultor_ai_provider(
            ai_settings, messages, max_tokens=max_tokens, timeout_seconds=timeout_seconds,
            opener=ai_urlopen, ssl_context_factory=ai_ssl_context,
            text_extractor=extract_summary_text, request_builder=build_consultor_ai_request,
        )
    except provider_adapter.ConsultorProviderError as exc:
        raise ConsultorError("O Consultor esta indisponivel no momento.") from exc


def build_consultor_ai_request(ai_settings: dict, messages: list[dict], *, max_tokens: int) -> dict:
    try:
        return provider_adapter.build_consultor_ai_request(ai_settings, messages, max_tokens=max_tokens)
    except provider_adapter.ConsultorProviderError as exc:
        raise ConsultorError("O Consultor esta indisponivel no momento.") from exc


def build_analysis_context(
    user_id: int,
    analysis_id: object,
    *,
    month: object | None = None,
    period_window: object | None = None,
    reference_date: date | None = None,
    investor_profile: object | None = None,
    portfolio_positions: list[dict] | None = None,
) -> dict:
    # spec: consultor/consultor v2.14 - criterios 7, 10, 27, 30, 34 e 38
    normalized_analysis_id = validate_analysis_id(analysis_id)
    normalized_period = validate_period_window(period_window, analysis_id=normalized_analysis_id)
    # Otimização: calcula o portfólio uma única vez e repassa aos cards que o consomem,
    # evitando recalcular posições/cotações múltiplas vezes na mesma análise.
    if portfolio_positions is None and normalized_analysis_id in {
        "alocacao_perfil",
        "exposicao_cambial",
        "analise_carteira",
        "score_saude_financeira",
        "evolucao_score_tempo",
        "sustentabilidade_padrao_vida",
        "destino_vencimentos",
    }:
        from financeiro.portfolio import current_portfolio_positions
        portfolio_positions = current_portfolio_positions(user_id, force_refresh=False)
    if normalized_analysis_id == "ralos_financeiros":
        context = build_ralos_context(user_id, month=month, period_window=normalized_period or "3m")
    elif normalized_analysis_id == "assinaturas_recorrencias":
        context = build_subscriptions_context(user_id, month=month)
    elif normalized_analysis_id == "alocacao_perfil":
        context = build_allocation_context(user_id, portfolio_positions=portfolio_positions)
    elif normalized_analysis_id == "exposicao_cambial":
        context = build_currency_exposure_context(user_id, portfolio_positions=portfolio_positions)
    elif normalized_analysis_id == "analise_carteira":
        context = build_portfolio_analysis_context(user_id, portfolio_positions=portfolio_positions)
    elif normalized_analysis_id == "score_saude_financeira":
        context = build_score_context(user_id, month=month, portfolio_positions=portfolio_positions)
    elif normalized_analysis_id == "evolucao_score_tempo":
        # spec: consultor/consultor v2.14 — critério 10
        context = build_score_evolution_context(user_id, period_window=normalized_period or "6m", portfolio_positions=portfolio_positions)
    elif normalized_analysis_id == "sustentabilidade_padrao_vida":
        context = build_lifestyle_context(user_id, month=month, portfolio_positions=portfolio_positions)
    elif normalized_analysis_id == "destino_vencimentos":
        from financeiro.calendar import get_cockpit_calendar

        positions = _load_portfolio_positions(user_id, portfolio_positions)
        calendar = get_cockpit_calendar(user_id, reference_date=reference_date, portfolio_positions=positions)
        reference_date_value = date.fromisoformat(calendar.get("reference_date") or date.today().isoformat())
        cashflow = build_maturity_cashflow_context(user_id, reference_date_value)
        context = build_maturities_context(
            user_id,
            month=month,
            reference_date=reference_date,
            portfolio_positions=portfolio_positions,
            maturity_cashflow=cashflow,
        )
    else:
        raise ConsultorError("Analise do Consultor invalida.")
    # spec: consultor/consultor v2.14 - criterios 38 e 39
    # Todos os cards recebem perfil de investidor e Perfil Complementar (quando preenchido)
    # para contextualizar a analise - nunca dados de outro usuario.
    if investor_profile is None:
        investor_profile = get_consultor_settings(int(user_id))["investor_profile"]
    complementary = get_complementary_profile(int(user_id))
    context["investor_profile"] = INVESTOR_PROFILES[validate_investor_profile(investor_profile)]["label"]
    context["complementary_profile"] = complementary["profile"] if complementary["configured"] else {}
    return add_money_displays(context)


def delete_consultor_history(user_id: int) -> int:
    return history_store.delete_history(user_id)
