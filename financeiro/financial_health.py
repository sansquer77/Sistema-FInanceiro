from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from http import HTTPStatus

from financeiro.database import get_connection, row_to_dict
from financeiro.portfolio import current_portfolio_positions
from financeiro.transactions import days_in_month

MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")

PILLAR_SAVINGS_MAX = 250
PILLAR_RESERVE_MAX = 250
PILLAR_DEBT_MAX = 200
PILLAR_LIMITS_MAX = 150
PILLAR_PORTFOLIO_CONCENTRATION_MAX = 150

PILLAR_DEFINITIONS = [
    ("poupanca", "Taxa de Poupança", PILLAR_SAVINGS_MAX, 25),
    ("reserva", "Reserva de Emergência", PILLAR_RESERVE_MAX, 25),
    ("endividamento", "Endividamento", PILLAR_DEBT_MAX, 20),
    ("limites", "Aderência aos Limites", PILLAR_LIMITS_MAX, 15),
    ("concentracao_portfolio", "Concentração da Carteira", PILLAR_PORTFOLIO_CONCENTRATION_MAX, 15),
]


class FinancialHealthError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def calculate_financial_health_score(user_id: int, month: object | None = None) -> dict:
    normalized_month = normalize_month(month)
    with get_connection() as conn:
        month_summary = fetch_month_summary(conn, user_id, normalized_month)
        average_expenses_cents = fetch_average_consumption_expenses(conn, user_id, normalized_month, months=3)
        debt_context = fetch_debt_context(conn, user_id, normalized_month)
        limits_context = fetch_limits_context(conn, user_id, normalized_month)
        recurring_income_context = fetch_recurring_income_reference(conn, user_id, normalized_month)
    portfolio_positions = current_portfolio_positions(user_id, force_refresh=False)
    eligible_reserve_cents = emergency_reserve_cents_from_positions(portfolio_positions)

    savings_pillar = calculate_savings_pillar(
        month_summary["income_cents"],
        month_summary["expense_cents"],
    )
    reserve_pillar = calculate_reserve_pillar(
        eligible_reserve_cents,
        average_expenses_cents,
    )
    debt_pillar = calculate_debt_pillar(
        debt_context["month_installments_cents"],
        month_summary["income_cents"],
    )
    limits_pillar = calculate_limits_pillar(
        limits_context["total_limits"],
        limits_context["within_limits"],
    )
    concentration_pillar = calculate_portfolio_concentration_pillar(portfolio_positions)
    paz_financeira = calculate_financial_peace(
        recurring_income_context,
        month_summary["income_cents"],
    )
    pillars = build_pillars([
        savings_pillar,
        reserve_pillar,
        debt_pillar,
        limits_pillar,
        concentration_pillar,
    ])
    total_score = sum(pillar["score"] for pillar in pillars)
    return {
        "month": normalized_month,
        "score_total": total_score,
        "nivel": score_level(total_score, 1000),
        "dados_insuficientes": month_summary["income_cents"] <= 0 and month_summary["expense_cents"] <= 0,
        "receitas_cents": month_summary["income_cents"],
        "despesas_consumo_cents": month_summary["expense_cents"],
        "pilar_poupanca": savings_pillar["score"],
        "pilar_reserva": reserve_pillar["score"],
        "pilar_endividamento": debt_pillar["score"],
        "pilar_limites": limits_pillar["score"],
        "pilar_concentracao_portfolio": concentration_pillar["score"],
        "reserva_elegivel_cents": eligible_reserve_cents,
        "meses_reserva": reserve_pillar["meses_reserva"],
        "maior_concentracao_portfolio_pct": concentration_pillar["maior_concentracao_pct"],
        "concentracao_poupanca_pct": concentration_pillar["concentracao_poupanca_pct"],
        "dividas_total_aberto_cents": debt_context["open_total_cents"],
        "dividas_parcelas_mes_cents": debt_context["month_installments_cents"],
        "comprometimento_divida_mes_pct": debt_pillar["comprometimento_pct"],
        "paz_financeira_base_receita_cents": paz_financeira["base_receita_cents"],
        "paz_financeira_confianca": paz_financeira["confianca"],
        "paz_financeira_meses_receita_recorrente": paz_financeira["meses_receita_recorrente"],
        "paz_independencia_cents": paz_financeira["independencia_mensal_cents"],
        "paz_reserva_estimada_cents": paz_financeira["reserva_estimada_cents"],
        "paz_recorrentes_saudaveis_cents": paz_financeira["recorrentes_saudaveis_cents"],
        "paz_lazer_saudavel_cents": paz_financeira["lazer_saudavel_cents"],
        "paz_financeira": paz_financeira,
        "pilares": pillars,
    }


def calculate_financial_health_score_history(user_id: int, months: object | None = None) -> list[dict]:
    # spec: score-saude-financeira v2.5 — critérios 15, 16 e 17
    raw_months = str(months or "").strip()
    if not raw_months:
        raise FinancialHealthError("O parametro months deve ser informado com valor entre 1 e 36.")
    try:
        months_count = int(raw_months)
    except (ValueError, TypeError):
        raise FinancialHealthError("O parametro months deve ser um numero inteiro entre 1 e 36.")
    if months_count < 1 or months_count > 36:
        raise FinancialHealthError("O parametro months deve estar entre 1 e 36.")
    reference_month = normalize_month()
    history = []
    for candidate_month in trailing_months(reference_month, months_count):
        entry = calculate_financial_health_score(user_id, candidate_month)
        history.append({
            "month": entry["month"],
            "score_total": entry["score_total"],
            "nivel": entry["nivel"],
            "dados_insuficientes": entry["dados_insuficientes"],
        })
    return history


def calculate_savings_pillar(income_cents: int, consumption_expenses_cents: int) -> dict:
    # spec: score-saude-financeira v2.5 — critérios 1 e 4
    if income_cents <= 0:
        return pillar_result(
            "poupanca",
            PILLAR_SAVINGS_MAX // 2,
            taxa_poupanca_pct=0.0,
            dados_insuficientes=True,
            mensagem="Sem receitas no mês para calcular a taxa de poupança; nota neutra aplicada.",
        )
    savings_cents = max(0, income_cents - max(0, consumption_expenses_cents))
    savings_rate = Decimal(savings_cents) / Decimal(income_cents)
    score = proportional_score(savings_rate, Decimal("0.30"), PILLAR_SAVINGS_MAX)
    return pillar_result(
        "poupanca",
        score,
        taxa_poupanca_pct=percent(savings_rate),
        mensagem="Taxa calculada por receitas menos despesas de consumo; aportes não entram como despesa.",
    )


def calculate_reserve_pillar(eligible_reserve_cents: int, average_monthly_expenses_cents: int) -> dict:
    # spec: score-saude-financeira v2.5 — critérios 2, 3 e 4
    if average_monthly_expenses_cents <= 0:
        return pillar_result(
            "reserva",
            PILLAR_RESERVE_MAX // 2,
            reserva_elegivel_cents=max(0, eligible_reserve_cents),
            meses_reserva=0.0,
            dados_insuficientes=True,
            mensagem="Sem média de despesas de consumo suficiente; nota neutra aplicada.",
        )
    months = Decimal(max(0, eligible_reserve_cents)) / Decimal(average_monthly_expenses_cents)
    score = proportional_score(months, Decimal("6"), PILLAR_RESERVE_MAX)
    return pillar_result(
        "reserva",
        score,
        reserva_elegivel_cents=max(0, eligible_reserve_cents),
        meses_reserva=decimal_number(months),
        mensagem="Considera apenas posições do Portfólio marcadas explicitamente como reserva.",
    )


def calculate_debt_pillar(month_installments_cents: int, income_cents: int) -> dict:
    # spec: score-saude-financeira v2.5 — critérios 4 e 7
    if income_cents <= 0:
        return pillar_result(
            "endividamento",
            PILLAR_DEBT_MAX // 2,
            comprometimento_pct=0.0,
            dados_insuficientes=True,
            mensagem="Sem receitas no mês para medir comprometimento de dívida; nota neutra aplicada.",
        )
    commitment = Decimal(max(0, month_installments_cents)) / Decimal(income_cents)
    if commitment <= Decimal("0.20"):
        score = PILLAR_DEBT_MAX
    elif commitment >= Decimal("0.60"):
        score = 0
    else:
        score = int((Decimal("0.60") - commitment) / Decimal("0.40") * PILLAR_DEBT_MAX)
    return pillar_result(
        "endividamento",
        clamp_score(score, PILLAR_DEBT_MAX),
        comprometimento_pct=percent(commitment),
        mensagem="Usa parcelas de dívidas do mês sobre receitas; o estoque total aberto é apenas contexto.",
    )


def calculate_limits_pillar(total_limits: int, within_limits: int) -> dict:
    # spec: score-saude-financeira v2.5 — critérios 5 e 6
    if total_limits <= 0:
        return pillar_result(
            "limites",
            0,
            total_limites=0,
            limites_dentro=0,
            dados_insuficientes=True,
            mensagem="Você ainda não cadastrou limites de gastos. Definir metas mensais por categoria ajuda a acompanhar e equilibrar seus gastos.",
        )
    adherence = Decimal(max(0, min(within_limits, total_limits))) / Decimal(total_limits)
    score = int((adherence * PILLAR_LIMITS_MAX).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return pillar_result(
        "limites",
        clamp_score(score, PILLAR_LIMITS_MAX),
        total_limites=total_limits,
        limites_dentro=within_limits,
        aderencia_pct=percent(adherence),
        mensagem="Percentual de limites cadastrados que ficaram dentro da meta no mês.",
    )


def calculate_portfolio_concentration_pillar(positions: list[dict]) -> dict:
    # spec: score-saude-financeira v2.5 — critérios 8, 9 e 10
    totals_by_class: dict[str, int] = {}
    totals_by_asset: dict[str, int] = {}
    total_cents = 0
    savings_cents = 0
    for position in positions:
        value_cents = portfolio_position_value_cents(position)
        if value_cents <= 0:
            continue
        total_cents += value_cents
        asset_type = str(position.get("asset_type") or "other")
        totals_by_class[asset_type] = totals_by_class.get(asset_type, 0) + value_cents
        asset_key = portfolio_asset_key(position)
        totals_by_asset[asset_key] = totals_by_asset.get(asset_key, 0) + value_cents
        if asset_type == "savings":
            savings_cents += value_cents
    if total_cents <= 0:
        return pillar_result(
            "concentracao_portfolio",
            PILLAR_PORTFOLIO_CONCENTRATION_MAX // 2,
            maior_concentracao_pct=0.0,
            concentracao_poupanca_pct=0.0,
            dados_insuficientes=True,
            mensagem="Sem carteira cadastrada suficiente; nota neutra aplicada.",
        )
    largest_class_cents = max(totals_by_class.values(), default=0)
    largest_asset_cents = max(totals_by_asset.values(), default=0)
    class_ratio = Decimal(largest_class_cents) / Decimal(total_cents)
    asset_ratio = Decimal(largest_asset_cents) / Decimal(total_cents)
    savings_ratio = Decimal(savings_cents) / Decimal(total_cents)
    score = PILLAR_PORTFOLIO_CONCENTRATION_MAX
    if class_ratio > Decimal("0.70"):
        excess = min(Decimal("0.30"), class_ratio - Decimal("0.70"))
        score -= int((excess / Decimal("0.30") * Decimal("60")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if asset_ratio > Decimal("0.60"):
        excess = min(Decimal("0.40"), asset_ratio - Decimal("0.60"))
        score -= int((excess / Decimal("0.40") * Decimal("40")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if savings_ratio > Decimal("0.25"):
        excess = min(Decimal("0.75"), savings_ratio - Decimal("0.25"))
        score -= int((excess / Decimal("0.75") * Decimal("40")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    message = "Carteira cadastrada sem concentração elevada pelos limites objetivos definidos."
    if class_ratio > Decimal("0.70") or asset_ratio > Decimal("0.60"):
        label, cents = largest_concentration_label(totals_by_class, totals_by_asset)
        message = f"Você tem alta concentração do portfólio em {label} ({percent(Decimal(cents) / Decimal(total_cents))}%)."
    if savings_ratio > Decimal("0.25"):
        message += f" Poupança representa {percent(savings_ratio)}% do portfólio; há alternativas que podem ser avaliadas conforme seu perfil."
    return pillar_result(
        "concentracao_portfolio",
        clamp_score(score, PILLAR_PORTFOLIO_CONCENTRATION_MAX),
        maior_concentracao_pct=percent(max(class_ratio, asset_ratio)),
        concentracao_poupanca_pct=percent(savings_ratio),
        mensagem=message,
    )


def calculate_financial_peace(recurring_income_reference: dict | int, month_income_cents: int) -> dict:
    # spec: score-saude-financeira v2.5 — critérios 11 e 12
    if isinstance(recurring_income_reference, dict):
        base = max(0, int(recurring_income_reference.get("average_cents") or 0))
        months_with_income = int(recurring_income_reference.get("months_with_income") or 0)
        window_months = int(recurring_income_reference.get("window_months") or 12)
    else:
        base = max(0, int(recurring_income_reference or 0))
        months_with_income = 12 if base > 0 else 0
        window_months = 12
    confidence = "alta" if months_with_income >= 12 else "intermediaria"
    notice = (
        "Base calculada pela média das receitas recorrentes mensais dos últimos 12 meses."
        if confidence == "alta"
        else f"Base calculada pela média de {months_with_income} mês(es) com receitas recorrentes nos últimos {window_months} meses."
    )
    if base <= 0:
        base = max(0, month_income_cents)
        confidence = "menor" if base > 0 else "indisponivel"
        notice = "Sem receitas recorrentes cadastradas; usa receitas do mês com menor confiança." if base > 0 else "Sem receitas para estimar Paz Financeira."
    message = (
        "Estimativas para nortear planejamento, baseadas em boas práticas gerais; "
        "não são regras fixas, metas ou recomendações personalizadas, sendo que a real necessidade "
        "varia conforme estilo de vida, localização e objetivos. Consulte um assessor para planejamento personalizado."
    )
    return {
        "base_receita_cents": base,
        "confianca": confidence,
        "meses_receita_recorrente": months_with_income,
        "janela_meses_receita_recorrente": window_months,
        "aviso": notice,
        "independencia_mensal_cents": base * 175,
        "independencia_mensal_legenda": "Patrimônio estimado (usando heurística de 175x sua receita mensal) para gerar renda passiva mensal equivalente à sua receita atual.",
        "reserva_estimada_cents": base * 6,
        "recorrentes_saudaveis_cents": multiply_cents(base, Decimal("0.5")),
        "lazer_saudavel_cents": multiply_cents(base, Decimal("0.3")),
        "mensagem": message,
    }


def build_pillars(results: list[dict]) -> list[dict]:
    by_id = {result["id"]: result for result in results}
    pillars = []
    for pillar_id, label, max_score, weight in PILLAR_DEFINITIONS:
        result = by_id[pillar_id]
        score = clamp_score(result["score"], max_score)
        pillars.append({
            **result,
            "id": pillar_id,
            "label": label,
            "score": score,
            "max_score": max_score,
            "percentual": percent(Decimal(score) / Decimal(max_score)) if max_score else 0.0,
            "peso_pct": weight,
            "nivel": score_level(score, max_score),
        })
    return pillars


def fetch_month_summary(conn, user_id: int, month: str) -> dict:
    start, end = month_bounds(month)
    account_rows = conn.execute(
        """
        SELECT transactions.type, COALESCE(SUM(transactions.amount_brl_cents), 0) AS total
        FROM transactions
        LEFT JOIN credit_card_payments
            ON credit_card_payments.transaction_id = transactions.id
            AND credit_card_payments.user_id = transactions.user_id
        WHERE transactions.user_id = ?
            AND transactions.archived_at IS NULL
            AND transactions.date BETWEEN ? AND ?
            AND credit_card_payments.id IS NULL
            AND transactions.type IN ('income', 'expense')
        GROUP BY transactions.type
        """,
        (user_id, start, end),
    ).fetchall()
    card_rows = conn.execute(
        """
        SELECT credit_card_transactions.type, COALESCE(SUM(credit_card_transactions.amount_cents), 0) AS total
        FROM credit_card_transactions
        WHERE credit_card_transactions.user_id = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.invoice_month = ?
            AND credit_card_transactions.type IN ('income', 'expense')
        GROUP BY credit_card_transactions.type
        """,
        (user_id, month),
    ).fetchall()
    totals = {"income_cents": 0, "expense_cents": 0}
    add_typed_rows(totals, account_rows)
    add_typed_rows(totals, card_rows)
    return totals


def fetch_average_consumption_expenses(conn, user_id: int, month: str, months: int = 3) -> int:
    if months <= 0:
        return 0
    total = 0
    for candidate_month in trailing_months(month, months):
        total += fetch_month_summary(conn, user_id, candidate_month)["expense_cents"]
    return int((Decimal(total) / Decimal(months)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fetch_emergency_reserve_cents(user_id: int) -> int:
    return emergency_reserve_cents_from_positions(current_portfolio_positions(user_id, force_refresh=False))


def emergency_reserve_cents_from_positions(positions: list[dict]) -> int:
    total = 0
    for position in positions:
        if not position.get("emergency_reserve_eligible"):
            continue
        total += portfolio_position_value_cents(position)
    return total


def fetch_debt_context(conn, user_id: int, month: str) -> dict:
    # spec: score-saude-financeira v2.5 — critério 6
    month_installments = conn.execute(
        """
        SELECT COALESCE(SUM(amount_cents), 0) AS total
        FROM credit_card_transactions
        WHERE user_id = ?
            AND archived_at IS NULL
            AND type = 'expense'
            AND series_kind = 'installment'
            AND invoice_month = ?
        """,
        (user_id, month),
    ).fetchone()["total"]
    open_total = conn.execute(
        """
        SELECT COALESCE(SUM(amount_cents), 0) AS total
        FROM credit_card_transactions
        WHERE user_id = ?
            AND archived_at IS NULL
            AND type = 'expense'
            AND series_kind = 'installment'
            AND invoice_month >= ?
        """,
        (user_id, month),
    ).fetchone()["total"]
    return {
        "month_installments_cents": int(month_installments or 0),
        "open_total_cents": int(open_total or 0),
    }


def fetch_limits_context(conn, user_id: int, month: str) -> dict:
    limits = fetch_effective_limits(conn, user_id, month)
    if not limits:
        return {"total_limits": 0, "within_limits": 0}
    expenses = fetch_expenses_by_limit_key(conn, user_id, month)
    within = 0
    for limit in limits:
        category_id = limit["category_id"]
        subcategory_id = limit["subcategory_id"]
        if subcategory_id:
            actual = expenses.get((category_id, subcategory_id), 0)
        else:
            actual = sum(value for (expense_category_id, _), value in expenses.items() if expense_category_id == category_id)
        if actual <= int(limit["limit_amount_cents"]):
            within += 1
    return {"total_limits": len(limits), "within_limits": within}


def fetch_effective_limits(conn, user_id: int, month: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT spending_limits.*
        FROM spending_limits
        JOIN categories
            ON categories.id = spending_limits.category_id
            AND categories.user_id = spending_limits.user_id
            AND categories.group_type = 'expense'
        WHERE spending_limits.user_id = ?
            AND spending_limits.month <= ?
            AND NOT EXISTS (
                SELECT 1
                FROM spending_limits newer_limits
                WHERE newer_limits.user_id = spending_limits.user_id
                    AND newer_limits.category_id = spending_limits.category_id
                    AND (
                        newer_limits.subcategory_id = spending_limits.subcategory_id
                        OR (
                            newer_limits.subcategory_id IS NULL
                            AND spending_limits.subcategory_id IS NULL
                        )
                    )
                    AND newer_limits.month <= ?
                    AND (
                        newer_limits.month > spending_limits.month
                        OR (
                            newer_limits.month = spending_limits.month
                            AND newer_limits.id > spending_limits.id
                        )
                    )
            )
        """,
        (user_id, month, month),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_expenses_by_limit_key(conn, user_id: int, month: str) -> dict[tuple[int, int | None], int]:
    start, end = month_bounds(month)
    expenses: dict[tuple[int, int | None], int] = {}
    account_rows = conn.execute(
        """
        SELECT transactions.category_id, transactions.subcategory_id, COALESCE(SUM(transactions.amount_brl_cents), 0) AS total
        FROM transactions
        LEFT JOIN credit_card_payments
            ON credit_card_payments.transaction_id = transactions.id
            AND credit_card_payments.user_id = transactions.user_id
        JOIN categories
            ON categories.id = transactions.category_id
            AND categories.user_id = transactions.user_id
            AND categories.group_type = 'expense'
        WHERE transactions.user_id = ?
            AND transactions.archived_at IS NULL
            AND transactions.date BETWEEN ? AND ?
            AND transactions.type = 'expense'
            AND credit_card_payments.id IS NULL
        GROUP BY transactions.category_id, transactions.subcategory_id
        """,
        (user_id, start, end),
    ).fetchall()
    card_rows = conn.execute(
        """
        SELECT credit_card_transactions.category_id, credit_card_transactions.subcategory_id,
            COALESCE(SUM(credit_card_transactions.amount_cents), 0) AS total
        FROM credit_card_transactions
        JOIN categories
            ON categories.id = credit_card_transactions.category_id
            AND categories.user_id = credit_card_transactions.user_id
            AND categories.group_type = 'expense'
        WHERE credit_card_transactions.user_id = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.invoice_month = ?
            AND credit_card_transactions.type = 'expense'
        GROUP BY credit_card_transactions.category_id, credit_card_transactions.subcategory_id
        """,
        (user_id, month),
    ).fetchall()
    for row in [*account_rows, *card_rows]:
        key = (int(row["category_id"]), int(row["subcategory_id"]) if row["subcategory_id"] else None)
        expenses[key] = expenses.get(key, 0) + int(row["total"] or 0)
    return expenses


def fetch_recurring_income_reference(conn, user_id: int, month: str, months: int = 12) -> dict:
    # spec: score-saude-financeira v2.5 — critérios 11 e 12
    months_list = trailing_months(month, months)
    first_month, last_month = months_list[0], months_list[-1]
    start, _ = month_bounds(first_month)
    _, end = month_bounds(last_month)
    rows = conn.execute(
        """
        SELECT substr(date, 1, 7) AS month, COALESCE(SUM(amount_brl_cents), 0) AS total
        FROM transactions
        WHERE user_id = ?
            AND archived_at IS NULL
            AND type = 'income'
            AND series_kind = 'recurring'
            AND date BETWEEN ? AND ?
        GROUP BY substr(date, 1, 7)
        """,
        (user_id, start, end),
    ).fetchall()
    totals_by_month = {row["month"]: int(row["total"] or 0) for row in rows}
    positive_totals = [totals_by_month.get(candidate_month, 0) for candidate_month in months_list if totals_by_month.get(candidate_month, 0) > 0]
    total = sum(positive_totals)
    months_with_income = len(positive_totals)
    average = int((Decimal(total) / Decimal(months_with_income)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if months_with_income else 0
    return {
        "average_cents": average,
        "months_with_income": months_with_income,
        "window_months": months,
        "total_cents": total,
    }


def add_typed_rows(totals: dict, rows) -> None:
    for row in rows:
        key = "income_cents" if row["type"] == "income" else "expense_cents"
        totals[key] += int(row["total"] or 0)


def pillar_result(pillar_id: str, score: int, **details) -> dict:
    return {
        "id": pillar_id,
        "score": int(score),
        **details,
    }


def proportional_score(value: Decimal, target: Decimal, max_score: int) -> int:
    if target <= 0:
        return max_score
    ratio = max(Decimal("0"), min(Decimal("1"), value / target))
    return clamp_score(int((ratio * max_score).quantize(Decimal("1"), rounding=ROUND_HALF_UP)), max_score)


def clamp_score(score: int, max_score: int) -> int:
    return max(0, min(int(score), int(max_score)))


def score_level(score: int, max_score: int) -> str:
    if max_score <= 0:
        return "atencao"
    normalized = Decimal(score) / Decimal(max_score) * Decimal("1000")
    if normalized < 400:
        return "critico"
    if normalized < 600:
        return "atencao"
    if normalized < 800:
        return "bom"
    return "excelente"


def percent(value: Decimal) -> float:
    return decimal_number(value * Decimal("100"))


def quantize_decimal(value: Decimal, pattern: str) -> Decimal:
    return value.quantize(Decimal(pattern), rounding=ROUND_HALF_UP)


def decimal_number(value: Decimal) -> float:
    return float(quantize_decimal(value, "0.01"))


def multiply_cents(cents: int, factor: Decimal) -> int:
    return int((Decimal(cents) * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def portfolio_position_value_cents(position: dict) -> int:
    for key in ("current_value_brl_cents", "total_cost_brl_cents", "invested_brl_cents"):
        value = position.get(key)
        if value is not None:
            return max(0, int(value or 0))
    for key in ("current_value_cents", "total_cost_cents", "invested_cents"):
        value = position.get(key)
        if value is not None:
            return max(0, int(value or 0))
    return 0


def portfolio_asset_key(position: dict) -> str:
    for key in ("asset_identifier", "asset_name", "cnpj"):
        value = str(position.get(key) or "").strip()
        if value:
            return value
    return str(position.get("asset_type") or "other")


def largest_concentration_label(totals_by_class: dict[str, int], totals_by_asset: dict[str, int]) -> tuple[str, int]:
    class_label, class_cents = max(totals_by_class.items(), key=lambda item: item[1])
    asset_label, asset_cents = max(totals_by_asset.items(), key=lambda item: item[1])
    return (asset_label, asset_cents) if asset_cents >= class_cents else (asset_type_label(class_label), class_cents)


def asset_type_label(asset_type: str) -> str:
    labels = {
        "stock": "Ações",
        "fund": "Fundos",
        "fixed_income": "Renda Fixa",
        "savings": "Poupança",
        "crypto": "Cripto",
        "private_pension": "Previdência Privada",
        "other": "Outros",
    }
    return labels.get(asset_type, asset_type or "Outros")


def month_bounds(month: str) -> tuple[str, str]:
    normalized = normalize_month(month)
    year, month_number = map(int, normalized.split("-"))
    return f"{normalized}-01", date(year, month_number, days_in_month(year, month_number)).isoformat()


def trailing_months(month: str, count: int) -> list[str]:
    year, month_number = map(int, normalize_month(month).split("-"))
    months = []
    for offset in range(count - 1, -1, -1):
        total_month = year * 12 + month_number - 1 - offset
        candidate_year, candidate_month_index = divmod(total_month, 12)
        months.append(f"{candidate_year:04d}-{candidate_month_index + 1:02d}")
    return months


def normalize_month(month: object | None = None) -> str:
    raw = str(month or date.today().strftime("%Y-%m")).strip()
    if not MONTH_PATTERN.fullmatch(raw):
        raise FinancialHealthError("Informe o mes no formato AAAA-MM.")
    year, month_number = map(int, raw.split("-"))
    if month_number < 1 or month_number > 12:
        raise FinancialHealthError("Informe um mes valido.")
    return f"{year:04d}-{month_number:02d}"
