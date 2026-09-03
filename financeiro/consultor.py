from __future__ import annotations

import re
import unicodedata
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


REFUSAL_MESSAGE = (
    "Nao posso apresentar recomendacao direta de compra ou venda de ativos especificos. "
    "Esta analise deve permanecer educacional e informativa."
)
FORBIDDEN_OUTPUT_PATTERNS = (
    r"\b(compre|comprar|compraria|compra)\b.*\b(acao|acoes|ativo|ticker|fundo|etf|fii|cripto|bitcoin|cdb|lci|lca|tesouro)\b",
    r"\b(venda|vender|venderia|liquide|liquidar)\b.*\b(acao|acoes|ativo|ticker|fundo|etf|fii|cripto|bitcoin|cdb|lci|lca|tesouro)\b",
    r"\brecomendo\s+(comprar|vender|aplicar|investir)\b",
    r"\b(retorno|rentabilidade)\s+(garantido|garantida|garantidos|garantidas)\b",
    r"\b(sem risco|risco zero)\b",
)
_FORBIDDEN_NEGATION_WINDOW = (
    r"\b(nao|nunca|sem|evite|evitar|evitando|desaconselho|desaconselha|desaconselhar|apenas|somente)"
    r"|deixe\s+de|deixa\s+de|deixar\s+de"
)
CONSULTOR_MAX_TOKENS = 900
CONSULTOR_MIN_TIMEOUT_SECONDS = 20
CONSULTOR_DAILY_QUOTA = history_store.CONSULTOR_DAILY_QUOTA
CONSULTOR_FAILURE_COOLDOWN_SECONDS = history_store.CONSULTOR_FAILURE_COOLDOWN_SECONDS
DEFAULT_TEMPERATURE = provider_adapter.DEFAULT_TEMPERATURE


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
    # spec: consultor/consultor v2.0 - criterios 7, 8, 10, 13, 34 e 38
    normalized_user_id = int(user_id)
    normalized_analysis_id = validate_analysis_id(analysis_id)
    current_time = now or datetime.now()
    consultor_settings = get_consultor_settings(normalized_user_id)
    if not consultor_settings["available"]:
        raise ConsultorError("O Consultor nao esta disponivel. Verifique as Preferencias.")
    assert_not_in_failure_cooldown(normalized_user_id, normalized_analysis_id, current_time)
    assert_daily_quota_available(normalized_user_id, current_time.date())

    ai_settings = load_ai_settings(normalized_user_id)
    max_tokens = normalize_consultor_max_tokens(ai_settings.get("max_tokens"))
    timeout_seconds = normalize_consultor_timeout(ai_settings.get("timeout_seconds"))
    normalized_period = validate_period_window(period_window, analysis_id=normalized_analysis_id)
    context = build_analysis_context(
        normalized_user_id,
        normalized_analysis_id,
        month=month,
        period_window=normalized_period,
        reference_date=reference_date,
        investor_profile=consultor_settings["investor_profile"],
        portfolio_positions=portfolio_positions,
    )
    system_prompt = build_system_prompt(
        normalized_analysis_id,
        investor_profile=consultor_settings["investor_profile"],
        period_window=normalized_period,
    )
    messages = build_ai_messages(system_prompt, context)
    client = ai_client or call_consultor_ai_provider
    try:
        output = client(
            ai_settings,
            messages,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        text = str(output or "").strip()
        if not text:
            raise ConsultorError("O Consultor esta indisponivel no momento.")
        text = postprocess_consultor_output(text)
    except ConsultorError as exc:
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
    }


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
    # spec: consultor/consultor v2.0 - criterios 11, 12, 14 e 15
    text = str(output or "").strip()
    if not text:
        raise ConsultorError("O Consultor esta indisponivel no momento.")
    normalized = normalize_text(text)
    if contains_forbidden_recommendation(normalized):
        return refusal_response()
    missing_sections = [section for section in RESPONSE_SECTIONS if not has_section(text, section)]
    missing_without_disclaimer = [section for section in missing_sections if section != "Disclaimer"]
    if missing_without_disclaimer:
        raise ConsultorError("O Consultor esta indisponivel no momento.")
    if "Disclaimer" in missing_sections or normalize_text(DISCLAIMER) not in normalized:
        text = append_consultor_disclaimer(text)
    return text


def has_section(text: str, section: str) -> bool:
    # spec: consultor/consultor v2.0 - cabeçalhos com acentos normalizados
    normalized_text = normalize_text(text)
    escaped = re.escape(section)
    return bool(re.search(
        rf"(^|\n)\s*(?:[-*]\s+)?(?:#{{1,6}}\s*)?(\*\*)?{escaped}(\*\*)?\s*:?",
        normalized_text,
        flags=re.IGNORECASE,
    ))


def contains_forbidden_recommendation(normalized_text: str) -> bool:
    # spec: consultor/consultor v2.0 - correcao de falso positivo
    # Frases defensivas da IA ("nao constitui recomendacao de compra de acoes",
    # "sem recomendar compra de fundos", "evite comprar por impulso") casavam os
    # padroes vedados; o match so vale se nao houver negacao/ressalva na janela anterior.
    # O padrao "recomendo <verbo>" usa janela curta para nao engolir idiomas
    # afirmativos como "sem duvida, recomendo comprar".
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        window = 10 if pattern.startswith(r"\brecomendo") else 60
        for match in re.finditer(pattern, normalized_text):
            before = normalized_text[max(0, match.start() - window):match.start()]
            if re.search(_FORBIDDEN_NEGATION_WINDOW, before):
                continue
            return True
    return False


def has_risk_level(normalized_text: str) -> bool:
    return bool(re.search(r"\brisco\s+(baixo|medio|alto)\b", normalized_text))


def append_consultor_disclaimer(text: str) -> str:
    return f"{text.rstrip()}\n\nDisclaimer\n{DISCLAIMER}"


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
    # spec: consultor/consultor v2.0 - criterios 7, 10, 27, 30, 34 e 38
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
        # spec: consultor/consultor v2.0 — critério 10
        context = build_score_evolution_context(user_id, period_window=normalized_period or "6m", portfolio_positions=portfolio_positions)
    elif normalized_analysis_id == "sustentabilidade_padrao_vida":
        context = build_lifestyle_context(user_id, month=month, portfolio_positions=portfolio_positions)
    elif normalized_analysis_id == "destino_vencimentos":
        context = build_maturities_context(user_id, month=month, reference_date=reference_date, portfolio_positions=portfolio_positions)
    else:
        raise ConsultorError("Analise do Consultor invalida.")
    # spec: consultor/consultor v2.0 - criterios 38 e 39
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
