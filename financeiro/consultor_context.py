"""Contextos minimizados do Consultor; sem configuração, histórico ou transporte de IA."""
from __future__ import annotations

from datetime import date


MARKET_DATA_SOURCES = (
    "Yahoo Finance",
    "CoinGecko",
    "PTAX do Banco Central",
    "Banco Central SGS",
    "Mais Retorno",
    "Valor manual informado no Portfolio",
)


def build_ralos_context(user_id: int, *, month: object | None, period_window: str) -> dict:
    from financeiro.trends import calculate_trends

    trends = calculate_trends(user_id, month)
    return {
        "analysis_id": "ralos_financeiros",
        "period_window": period_window,
        "month": trends["month"],
        "confidence": trends["confianca"],
        "summary": money_context(trends),
        "comparison": {
            "income_base_cents": int(trends.get("receitas_base_comparacao_cents") or 0),
            "expense_base_cents": int(trends.get("despesas_base_comparacao_cents") or 0),
        },
        "budget_alerts": compact_budget_alerts(trends.get("orcamento_realizado") or []),
        "point_events": compact_point_events(trends.get("eventos_pontuais") or []),
        "installment_acceleration": compact_acceleration(trends.get("antecipacao_parcelas") or {}),
    }


def build_subscriptions_context(user_id: int, *, month: object | None) -> dict:
    from financeiro.trends import calculate_trends

    trends = calculate_trends(user_id, month)
    subscriptions = normalize_subscriptions_payload(trends.get("assinaturas_e_servicos"))
    return {
        "analysis_id": "assinaturas_recorrencias",
        "month": trends["month"],
        "confidence": trends["confianca"],
        "total_cents": subscriptions["total_cents"],
        "annualized_cents": subscriptions["total_cents"] * 12,
        "items": compact_named_amounts(subscriptions["items"]),
    }


def build_allocation_context(user_id: int, *, portfolio_positions: list[dict] | None = None) -> dict:
    positions = _load_portfolio_positions(user_id, portfolio_positions)
    return {
        "analysis_id": "alocacao_perfil",
        "portfolio": summarize_portfolio(positions),
        "allocation_goals": build_allocation_goals_context(user_id, positions),
        "financial_commitments": build_financial_commitments_context(user_id, positions),
        "market_data": market_data_context(positions),
    }


def build_currency_exposure_context(user_id: int, *, portfolio_positions: list[dict] | None = None) -> dict:
    positions = _load_portfolio_positions(user_id, portfolio_positions)
    return {
        "analysis_id": "exposicao_cambial",
        "portfolio": {
            "total_brl_cents": sum(int(position.get("current_value_brl_cents") or 0) for position in positions),
            "by_currency": group_positions_by(positions, "currency"),
            "by_market": group_positions_by(positions, "market_label"),
        },
        "market_data": market_data_context(positions),
    }


def build_portfolio_analysis_context(user_id: int, *, portfolio_positions: list[dict] | None = None) -> dict:
    # spec: consultor/consultor v2.1 - criterio 30
    from financeiro.financial_health import calculate_financial_health_score

    positions = _load_portfolio_positions(user_id, portfolio_positions)
    score = calculate_financial_health_score(user_id, portfolio_positions=positions)
    return {
        "analysis_id": "analise_carteira",
        "portfolio": summarize_portfolio(positions),
        "allocation_goals": build_allocation_goals_context(user_id, positions),
        "financial_commitments": build_financial_commitments_context(user_id, positions),
        "by_currency": group_positions_by(positions, "currency"),
        "by_market": group_positions_by(positions, "market_label"),
        "score": {
            "month": score["month"],
            "reserve_months": score.get("meses_reserva") or 0,
            "reserve_pillar": int(score.get("pilar_reserva") or 0),
            "eligible_reserve_cents": int(score.get("reserva_elegivel_cents") or 0),
            "debt_pillar": int(score.get("pilar_endividamento") or 0),
        },
        "market_data": market_data_context(positions),
    }


def build_financial_commitments_context(
    user_id: int, positions: list[dict], *, goals: list[dict] | None = None
) -> dict:
    """Agrega objetivos e dívidas sem expor nomes, IDs ou compensar moedas."""
    # spec: consultor/consultor v2.1 — critérios 40 e 41
    from financeiro.financial_goals import list_financial_goals
    from financeiro.loans import list_loans

    if goals is None:
        goals = list_financial_goals(user_id)
    goals = [goal for goal in goals if goal.get("status") in {"active", "paused"}]
    reserved_by_type: dict[str, int] = {}
    from financeiro.financial_goals import investment_asset_identity
    reserved_identities = {
        investment_asset_identity(source)
        for goal in goals for source in goal.get("funding_sources", [])
    }
    for position in positions:
        if investment_asset_identity(position) in reserved_identities:
            key = str(position.get("asset_type") or "other")
            reserved_by_type[key] = reserved_by_type.get(key, 0) + int(position.get("current_value_brl_cents") or 0)
    from decimal import Decimal, ROUND_HALF_UP
    goals_context = {
        "count": len(goals),
        "target_brl_cents": sum(int(goal.get("target_amount_cents") or 0) for goal in goals),
        "reserved_brl_cents": sum(int(goal.get("reserved_balance_cents") or 0) for goal in goals),
        "remaining_brl_cents": sum(
            max(
                0,
                int((Decimal(int(goal.get("target_amount_cents") or 0) * (10000 + int(goal.get("safety_margin_bps") or 0))) / Decimal(10000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                - int(goal.get("reserved_balance_cents") or 0),
            )
            for goal in goals
        ),
        "linked_investments_brl_cents": sum(int(goal.get("linked_reserved_balance_cents") or 0) for goal in goals),
        "linked_investments_by_asset_type_brl_cents": [
            {"asset_type": key, "current_value_brl_cents": value}
            for key, value in sorted(reserved_by_type.items())
        ],
    }
    reserve_positions = [position for position in positions if position.get("emergency_reserve_eligible")]
    goals_context["emergency_reserve_investments_brl_cents"] = sum(
        int(position.get("current_value_brl_cents") or 0) for position in reserve_positions
    )

    by_currency: dict[str, dict] = {}
    for loan in list_loans(user_id):
        currency = str(loan.get("currency") or "BRL").upper()
        row = by_currency.setdefault(currency, {
            "currency": currency, "count": 0, "remaining_commitment_minor_units": 0,
            "monthly_installments_minor_units": 0, "loans_without_rate": 0,
        })
        row["count"] += 1
        row["remaining_commitment_minor_units"] += int(loan.get("remaining_commitment_cents") or 0)
        row["monthly_installments_minor_units"] += int(loan.get("installment_cents") or 0)
        row["loans_without_rate"] += int(loan.get("monthly_rate_micros") is None)
    for row in by_currency.values():
        row["remaining_commitment_display"] = format_currency_minor_units(
            row["remaining_commitment_minor_units"], row["currency"]
        )
        row["monthly_installments_display"] = format_currency_minor_units(
            row["monthly_installments_minor_units"], row["currency"]
        )
    return {"goals": goals_context, "loans_by_currency": list(by_currency.values())}


def build_allocation_goals_context(user_id: int, positions: list[dict]) -> list[dict]:
    from financeiro.portfolio import allocation_goal_key, get_allocation_goals

    total_cents = sum(int(position.get("current_value_brl_cents") or 0) for position in positions)
    current_by_type: dict[str, int] = {}
    for position in positions:
        asset_type = allocation_goal_key(position)
        current_by_type[asset_type] = current_by_type.get(asset_type, 0) + int(position.get("current_value_brl_cents") or 0)
    context = []
    for goal in get_allocation_goals(user_id):
        target_percent = float(goal.get("target_percent") or 0)
        current_cents = current_by_type.get(goal["asset_type"], 0)
        current_percent = (current_cents * 100 / total_cents) if total_cents > 0 else 0.0
        if target_percent <= 0 and current_cents <= 0:
            continue
        context.append({
            "asset_type": goal["asset_type"],
            "label": goal["label"],
            "target_percent": round(target_percent, 4),
            "current_percent": round(current_percent, 4),
            "deviation_percentage_points": round(current_percent - target_percent, 4),
            "current_value_brl_cents": current_cents,
            "target_defined_by_user": True,
        })
    return context


def build_score_context(
    user_id: int,
    *,
    month: object | None,
    portfolio_positions: list[dict] | None = None,
) -> dict:
    from financeiro.financial_health import calculate_financial_health_score

    score = calculate_financial_health_score(user_id, month, portfolio_positions=portfolio_positions)
    return {
        "analysis_id": "score_saude_financeira",
        "month": score["month"],
        "score_total": int(score.get("score_total") or 0),
        "level": score.get("nivel"),
        "insufficient_data": bool(score.get("dados_insuficientes")),
        "pillars": score.get("pilares") or [],
    }


# spec: consultor/consultor v2.1 — critérios 8 e 10
def build_score_evolution_context(
    user_id: int,
    *,
    period_window: str,
    portfolio_positions: list[dict] | None = None,
) -> dict:
    from financeiro.financial_health import calculate_financial_health_score
    from financeiro.financial_health import trailing_months
    from financeiro.portfolio import current_portfolio_positions

    # Otimização: calcula o portfólio uma única vez e reutiliza para todos os
    # meses da série, evitando recalcular posições/cotações 6-12 vezes.
    if portfolio_positions is None:
        portfolio_positions = current_portfolio_positions(user_id, force_refresh=False)
    reference_month = calculate_financial_health_score(
        user_id, portfolio_positions=portfolio_positions
    )["month"]
    months = trailing_months(reference_month, 12 if period_window == "12m" else 6)
    series = []
    for month in months:
        score = calculate_financial_health_score(
            user_id, month, portfolio_positions=portfolio_positions
        )
        series.append({
            "month": month,
            "score_total": int(score.get("score_total") or 0),
            "level": score.get("nivel"),
            "insufficient_data": bool(score.get("dados_insuficientes")),
            "pillars": _compact_pillars(score.get("pilares") or []),
        })
    return {
        "analysis_id": "evolucao_score_tempo",
        "period_window": period_window,
        "reference_month": reference_month,
        "series": series,
    }


def _compact_pillars(pillars: list[dict]) -> list[dict]:
    return [
        {
            "id": pillar.get("id"),
            "label": pillar.get("label"),
            "score": int(pillar.get("score") or 0),
            "max_score": int(pillar.get("max_score") or 0),
            "percentual": pillar.get("percentual"),
            "nivel": pillar.get("nivel"),
        }
        for pillar in pillars
    ]


def build_lifestyle_context(
    user_id: int,
    *,
    month: object | None,
    portfolio_positions: list[dict] | None = None,
) -> dict:
    from financeiro.financial_health import calculate_financial_health_score

    score = calculate_financial_health_score(user_id, month, portfolio_positions=portfolio_positions)
    return {
        "analysis_id": "sustentabilidade_padrao_vida",
        "month": score["month"],
        "income_cents": int(score.get("receitas_cents") or 0),
        "consumption_expenses_cents": int(score.get("despesas_consumo_cents") or 0),
        "financial_peace": score.get("paz_financeira") or {},
    }


def build_maturities_context(
    user_id: int,
    *,
    month: object | None,
    reference_date: date | None,
    portfolio_positions: list[dict] | None = None,
) -> dict:
    from financeiro.calendar import get_cockpit_calendar
    from financeiro.trends import calculate_trends
    from financeiro.financial_health import calculate_financial_health_score

    positions = _load_portfolio_positions(user_id, portfolio_positions)
    calendar = get_cockpit_calendar(user_id, reference_date=reference_date, portfolio_positions=positions)
    trends = calculate_trends(user_id, month)
    score = calculate_financial_health_score(user_id, month, portfolio_positions=positions)
    maturity_assets = [
        *calendar.get("maturity_30_days", []),
        *calendar.get("maturity_60_days", []),
    ]
    from financeiro.financial_goals import list_financial_goals
    goals = list_financial_goals(user_id)
    commitment_context = build_financial_commitments_context(user_id, positions, goals=goals)
    cashflow = build_maturity_cashflow_context(user_id, date.fromisoformat(calendar.get("reference_date") or date.today().isoformat()))
    reserved_identities = _goal_reserved_investment_identities(user_id, goals=goals)
    for asset in maturity_assets:
        # spec: consultor/consultor v2.1 — critério 40
        from financeiro.financial_goals import investment_asset_identity
        position = next((item for item in positions
                         if str(item.get("source_id") or item.get("id")) == str(asset.get("position_id"))), None)
        asset["reserved_for_objective"] = bool(position and investment_asset_identity(position) in reserved_identities)
        if position:
            asset["asset_type"] = position.get("asset_type")
            asset["current_value_brl_cents"] = int(position.get("current_value_brl_cents") or 0)
            asset["quote_source"] = position.get("quote_source") or ""
            asset["quote_status"] = position.get("quote_status") or ""
            asset["quote_date"] = position.get("quote_date") or ""
            asset["emergency_reserve_eligible"] = bool(position.get("emergency_reserve_eligible"))
    return {
        "analysis_id": "destino_vencimentos",
        "reference_date": calendar.get("reference_date"),
        "maturity_assets": compact_maturities(maturity_assets),
        "market_data": market_data_context(maturity_assets),
        "cashflow_projection": {
            "month": trends["month"],
            "confidence": trends.get("confianca"),
            **cashflow,
        },
        "financial_commitments": commitment_context,
        "score_pillars": {
            "reserve": int(score.get("pilar_reserva") or 0),
            "debt": int(score.get("pilar_endividamento") or 0),
            "eligible_reserve_cents": int(score.get("reserva_elegivel_cents") or 0),
            "debt_installments_month_cents": int(score.get("dividas_parcelas_mes_cents") or 0),
        },
    }


def build_maturity_cashflow_context(user_id: int, reference_date: date) -> dict:
    """Projeção curta a partir de saldos efetivos e compromissos explicitamente registrados."""
    # spec: consultor/consultor v2.1 — critérios 42, 43 e 45
    from datetime import timedelta
    from financeiro.balance_projections import card_invoice_date
    from financeiro.database import get_connection

    horizon = reference_date + timedelta(days=90)
    with get_connection() as conn:
        balance_rows = conn.execute(
            """SELECT account_balances.currency, account_balances.account_type,
                      SUM(account_balances.balance_cents) AS balance_cents
               FROM (
                 SELECT a.id, a.currency, a.account_type, a.initial_balance_cents + COALESCE(SUM(
                      CASE WHEN t.account_id=a.id AND t.type='income' THEN t.amount_cents
                           WHEN t.account_id=a.id AND t.type IN ('expense','investment','transfer') THEN -t.amount_cents
                           WHEN t.destination_account_id=a.id AND t.type='transfer'
                             THEN COALESCE(NULLIF(t.destination_amount_cents,0),t.amount_cents)
                           ELSE 0 END),0) AS balance_cents
               FROM checking_accounts a
               LEFT JOIN transactions t ON t.user_id=a.user_id AND t.archived_at IS NULL
                 AND t.date<=? AND (t.account_id=a.id OR t.destination_account_id=a.id)
                 WHERE a.user_id=? AND a.archived_at IS NULL GROUP BY a.id
               ) account_balances GROUP BY account_balances.currency, account_balances.account_type""",
            (reference_date.isoformat(), user_id),
        ).fetchall()
        planned_rows = conn.execute(
            """SELECT planned.currency, planned.date, planned.type, SUM(planned.amount_cents) AS amount_cents
               FROM (
                 SELECT a.currency, t.date, t.type, t.amount_cents
                 FROM transactions t JOIN checking_accounts a ON a.id=t.account_id AND a.user_id=t.user_id
                 WHERE t.user_id=? AND t.archived_at IS NULL AND a.archived_at IS NULL
                   AND a.account_type IN ('liquidity','wallet') AND t.type IN ('income','expense')
                   AND t.date>? AND t.date<=?
                   AND NOT EXISTS (SELECT 1 FROM credit_card_payments p
                                   WHERE p.user_id=t.user_id AND p.transaction_id=t.id)
                 UNION ALL
                 SELECT a.currency, t.date, 'expense', t.amount_cents
                 FROM transactions t JOIN checking_accounts a ON a.id=t.account_id AND a.user_id=t.user_id
                 WHERE t.user_id=? AND t.archived_at IS NULL AND a.archived_at IS NULL
                   AND a.account_type IN ('liquidity','wallet') AND t.type='transfer'
                   AND t.date>? AND t.date<=?
                 UNION ALL
                 SELECT a.currency, t.date, 'income', COALESCE(NULLIF(t.destination_amount_cents,0),t.amount_cents)
                 FROM transactions t JOIN checking_accounts a ON a.id=t.destination_account_id AND a.user_id=t.user_id
                 WHERE t.user_id=? AND t.archived_at IS NULL AND a.archived_at IS NULL
                   AND a.account_type IN ('liquidity','wallet') AND t.type='transfer'
                   AND t.date>? AND t.date<=?
               ) planned GROUP BY planned.currency, planned.date, planned.type
               ORDER BY planned.date, planned.currency""",
            (user_id, reference_date.isoformat(), horizon.isoformat(),
             user_id, reference_date.isoformat(), horizon.isoformat(),
             user_id, reference_date.isoformat(), horizon.isoformat()),
        ).fetchall()
        invoice_rows = conn.execute(
            """SELECT cards.currency, cards.due_day, card_transactions.invoice_month,
                      SUM(CASE card_transactions.type WHEN 'expense' THEN card_transactions.amount_cents
                               WHEN 'income' THEN -card_transactions.amount_cents ELSE 0 END) AS amount_cents
               FROM credit_card_transactions card_transactions
               JOIN credit_cards cards ON cards.id=card_transactions.credit_card_id AND cards.user_id=card_transactions.user_id
               WHERE card_transactions.user_id=? AND card_transactions.archived_at IS NULL
                 AND cards.archived_at IS NULL
                 AND NOT EXISTS (SELECT 1 FROM credit_card_payments p
                                 WHERE p.user_id=cards.user_id AND p.credit_card_id=cards.id
                                   AND p.invoice_month=card_transactions.invoice_month)
               GROUP BY cards.id, card_transactions.invoice_month
               HAVING amount_cents > 0 ORDER BY card_transactions.invoice_month, cards.currency""",
            (user_id,),
        ).fetchall()

    balances: dict[str, int] = {}
    investment_balances: dict[str, int] = {}
    for row in balance_rows:
        currency = str(row["currency"] or "BRL").upper()
        target = investment_balances if row["account_type"] == "investment" else balances
        target[currency] = target.get(currency, 0) + int(row["balance_cents"] or 0)
    events: dict[tuple[str, str], dict[str, int]] = {}
    dated_events: dict[tuple[str, str], dict[str, int]] = {}
    for raw in planned_rows:
        currency, month = str(raw["currency"] or "BRL").upper(), str(raw["date"])[:7]
        event = events.setdefault((currency, month), {"planned_income_minor_units": 0, "planned_expense_minor_units": 0, "open_card_invoices_minor_units": 0})
        key = "planned_income_minor_units" if raw["type"] == "income" else "planned_expense_minor_units"
        event[key] += int(raw["amount_cents"] or 0)
        dated = dated_events.setdefault((currency, str(raw["date"])), {"planned_income_minor_units": 0, "planned_expense_minor_units": 0, "open_card_invoices_minor_units": 0})
        dated[key] += int(raw["amount_cents"] or 0)

    invoices = []
    for raw in invoice_rows:
        due_date = card_invoice_date(str(raw["invoice_month"]), raw["due_day"])
        if due_date > horizon.isoformat():
            continue
        currency = str(raw["currency"] or "BRL").upper()
        amount = int(raw["amount_cents"] or 0)
        month = max(due_date[:7], reference_date.strftime("%Y-%m"))
        event = events.setdefault((currency, month), {"planned_income_minor_units": 0, "planned_expense_minor_units": 0, "open_card_invoices_minor_units": 0})
        event["open_card_invoices_minor_units"] += amount
        event_date = due_date if due_date >= reference_date.isoformat() else reference_date.isoformat()
        dated = dated_events.setdefault((currency, event_date), {"planned_income_minor_units": 0, "planned_expense_minor_units": 0, "open_card_invoices_minor_units": 0})
        dated["open_card_invoices_minor_units"] += amount
        invoices.append({
            "due_date": due_date, "invoice_month": str(raw["invoice_month"]), "currency": currency,
            "amount_minor_units": amount,
            "amount_display": format_currency_minor_units(amount, currency),
            "overdue": due_date < reference_date.isoformat(),
        })

    currencies = sorted(set(balances) | {currency for currency, _ in events})
    forecast = []
    for currency in currencies:
        running = balances.get(currency, 0)
        month = reference_date.strftime("%Y-%m")
        last_month = horizon.strftime("%Y-%m")
        while month <= last_month:
            event = events.get((currency, month), {})
            running += int(event.get("planned_income_minor_units") or 0)
            running -= int(event.get("planned_expense_minor_units") or 0)
            running -= int(event.get("open_card_invoices_minor_units") or 0)
            forecast.append({
                "currency": currency, "month": month,
                "opening_balance_minor_units": balances.get(currency, 0) if month == reference_date.strftime("%Y-%m") else None,
                "planned_income_minor_units": int(event.get("planned_income_minor_units") or 0),
                "planned_income_display": format_currency_minor_units(int(event.get("planned_income_minor_units") or 0), currency),
                "planned_expense_minor_units": int(event.get("planned_expense_minor_units") or 0),
                "planned_expense_display": format_currency_minor_units(int(event.get("planned_expense_minor_units") or 0), currency),
                "open_card_invoices_minor_units": int(event.get("open_card_invoices_minor_units") or 0),
                "open_card_invoices_display": format_currency_minor_units(int(event.get("open_card_invoices_minor_units") or 0), currency),
                "projected_balance_after_recorded_bills_minor_units": running,
                "projected_balance_display": format_currency_minor_units(running, currency),
            })
            year, number = int(month[:4]), int(month[5:7])
            month = f"{year + (number == 12):04d}-{(number % 12) + 1:02d}"

    timelines = []
    for currency in sorted(set(balances) | {key[0] for key in dated_events}):
        running = balances.get(currency, 0)
        cash_events = []
        for (_, event_date), event in sorted(
            (item for item in dated_events.items() if item[0][0] == currency), key=lambda item: item[0][1]
        ):
            income = int(event.get("planned_income_minor_units") or 0)
            expense = int(event.get("planned_expense_minor_units") or 0)
            invoices_due = int(event.get("open_card_invoices_minor_units") or 0)
            running += income - expense - invoices_due
            cash_events.append({
                "date": event_date,
                "planned_income_minor_units": income,
                "planned_income_display": format_currency_minor_units(income, currency),
                "planned_expense_minor_units": expense,
                "planned_expense_display": format_currency_minor_units(expense, currency),
                "open_card_invoices_minor_units": invoices_due,
                "open_card_invoices_display": format_currency_minor_units(invoices_due, currency),
                "projected_balance_after_recorded_bills_minor_units": running,
                "projected_balance_display": format_currency_minor_units(running, currency),
            })
        timelines.append({
            "currency": currency,
            "opening_balance_minor_units": balances.get(currency, 0),
            "opening_balance_display": format_currency_minor_units(balances.get(currency, 0), currency),
            "events": cash_events,
        })

    return {
        "horizon_days": 90,
        "scope_note": "Inclui apenas lançamentos futuros já cadastrados, saldos atuais e faturas ainda abertas; parcelas mensais de empréstimos são informadas separadamente e só entram na projeção quando houver lançamento futuro cadastrado; não estima renda/despesa variável futura nem garante disponibilidade de recursos.",
        "current_liquid_balances_by_currency": [
            {"currency": currency, "amount_minor_units": amount,
             "amount_display": format_currency_minor_units(amount, currency)}
            for currency, amount in sorted(balances.items())
        ],
        "investment_account_balances_by_currency": [
            {"currency": currency, "amount_minor_units": amount,
             "amount_display": format_currency_minor_units(amount, currency)}
            for currency, amount in sorted(investment_balances.items())
        ],
        "months_by_currency": forecast,
        "timeline_by_currency": timelines,
        "open_card_invoices": invoices,
    }


def _goal_reserved_investment_identities(user_id: int, *, goals: list[dict] | None = None) -> set[tuple]:
    from financeiro.financial_goals import investment_asset_identity, list_financial_goals

    if goals is None:
        goals = list_financial_goals(user_id)
    return {
        investment_asset_identity(source)
        for goal in goals
        if goal.get("status") in {"active", "paused"}
        for source in goal.get("funding_sources", [])
    }


def format_currency_minor_units(value: object, currency: str) -> str:
    amount = cents_to_reais(value)
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    symbol = {"BRL": "R$", "USD": "US$", "EUR": "€", "GBP": "£"}.get(currency.upper(), currency.upper())
    return f"{symbol} {formatted}"


def _load_portfolio_positions(user_id: int, portfolio_positions: list[dict] | None = None) -> list[dict]:
    if portfolio_positions is not None:
        return portfolio_positions
    from financeiro.portfolio import current_portfolio_positions

    return current_portfolio_positions(user_id, force_refresh=False)


def money_context(trends: dict) -> dict:
    return {
        "income_cents": int(trends.get("receitas_mes_cents") or 0),
        "expense_cents": int(trends.get("despesas_mes_cents") or 0),
        "balance_cents": int(trends.get("saldo_mes_cents") or 0),
        "available_history_months": int(trends.get("historico_meses_disponiveis") or 0),
    }


def summarize_portfolio(positions: list[dict]) -> dict:
    total_brl_cents = sum(int(position.get("current_value_brl_cents") or 0) for position in positions)
    return {
        "currency_unit_note": "Valores com sufixo _cents estao em centavos de BRL; valores _brl ja estao em reais.",
        "total_brl_cents": total_brl_cents,
        "total_brl": cents_to_reais(total_brl_cents),
        "total_display": format_brl_cents(total_brl_cents),
        "position_count": len(positions),
        "by_asset_type": group_positions_by(positions, "asset_type_label"),
        "positions": compact_positions(positions),
    }


def group_positions_by(positions: list[dict], key: str) -> list[dict]:
    totals: dict[str, dict] = {}
    for position in positions:
        label = str(position.get(key) or "Nao informado")
        row = totals.setdefault(label, {
            "label": label,
            "current_value_brl_cents": 0,
            "current_value_brl": 0.0,
            "current_value_display": "",
            "position_count": 0,
        })
        row["current_value_brl_cents"] += int(position.get("current_value_brl_cents") or 0)
        row["current_value_brl"] = cents_to_reais(row["current_value_brl_cents"])
        row["current_value_display"] = format_brl_cents(row["current_value_brl_cents"])
        row["position_count"] += 1
    return sorted(totals.values(), key=lambda row: row["current_value_brl_cents"], reverse=True)


def compact_positions(positions: list[dict], *, limit: int = 12) -> list[dict]:
    sorted_positions = sorted(
        positions,
        key=lambda position: int(position.get("current_value_brl_cents") or 0),
        reverse=True,
    )
    return [
        {
            "asset_type": position.get("asset_type"),
            "asset_type_label": position.get("asset_type_label"),
            "currency": position.get("currency"),
            "current_value_brl_cents": int(position.get("current_value_brl_cents") or 0),
            "current_value_brl": cents_to_reais(position.get("current_value_brl_cents")),
            "current_value_display": format_brl_cents(position.get("current_value_brl_cents")),
            "total_cost_brl_cents": int(position.get("total_cost_brl_cents") or 0),
            "total_cost_brl": cents_to_reais(position.get("total_cost_brl_cents")),
            "total_cost_display": format_brl_cents(position.get("total_cost_brl_cents")),
            "quote_source": safe_quote_source(position.get("quote_source")),
            "quote_status": position.get("quote_status") or "",
            "quote_date": position.get("quote_date") or "",
            "emergency_reserve_eligible": bool(position.get("emergency_reserve_eligible")),
            "fixed_income_maturity_date": position.get("fixed_income_maturity_date") or "",
        }
        for position in sorted_positions[:limit]
    ]


def market_data_context(rows: list[dict]) -> dict:
    sources = sorted({
        source for source in (safe_quote_source(row.get("quote_source")) for row in rows)
        if source
    })
    return {
        "uses_portfolio_quotes": True,
        "uses_quote_cache": True,
        "allowed_sources": list(MARKET_DATA_SOURCES),
        "observed_sources": sources,
    }


def cents_to_reais(value: object) -> float:
    return round(int(value or 0) / 100, 2)


def format_brl_cents(value: object) -> str:
    amount = cents_to_reais(value)
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def add_money_displays(value):
    """Adiciona a todo campo *_cents seu equivalente *_display, inclusive aninhado."""
    # spec: consultor/consultor v2.1 — critério 39
    if isinstance(value, list):
        return [add_money_displays(item) for item in value]
    if not isinstance(value, dict):
        return value
    enriched = {key: add_money_displays(item) for key, item in value.items()}
    for key, item in value.items():
        if key.endswith("_cents"):
            enriched[f"{key[:-6]}_display"] = format_brl_cents(item)
    return enriched


def safe_quote_source(value: object) -> str:
    source = str(value or "").strip()
    if not source:
        return ""
    if source.startswith("Valor atual informado manualmente"):
        return "Valor manual informado no Portfolio"
    return source


def compact_budget_alerts(rows: list[dict], *, limit: int = 8) -> list[dict]:
    return [
        {
            "category": row.get("category_name") or row.get("category") or "",
            "subcategory": row.get("subcategory_name") or row.get("subcategory") or "",
            "limit_cents": int(row.get("limit_cents") or 0),
            "actual_cents": int(row.get("actual_cents") or row.get("spent_cents") or 0),
            "usage_pct": row.get("usage_pct"),
        }
        for row in rows[:limit]
    ]


def compact_point_events(rows: list[dict], *, limit: int = 8) -> list[dict]:
    return [
        {
            "kind": row.get("kind") or row.get("type") or "",
            "category": row.get("category_name") or row.get("category") or "",
            "subcategory": row.get("subcategory_name") or row.get("subcategory") or "",
            "amount_cents": int(row.get("amount_cents") or row.get("total_cents") or 0),
            "count": int(row.get("count") or row.get("transaction_count") or 0),
        }
        for row in rows[:limit]
    ]


def compact_acceleration(payload: object) -> dict:
    if isinstance(payload, list):
        return {
            "total_cents": sum(amount_from_row(item) for item in payload),
            "count": len(payload),
        }
    if not isinstance(payload, dict):
        return {"total_cents": 0, "count": 0}
    return {
        "total_cents": int(payload.get("total_cents") or 0),
        "count": int(payload.get("count") or payload.get("parcel_count") or 0),
    }


def normalize_subscriptions_payload(payload: object) -> dict:
    if isinstance(payload, list):
        items = payload
        total_cents = sum(amount_from_row(item) for item in items)
        return {"total_cents": total_cents, "items": items}
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("itens") or []
        total_cents = int(payload.get("total_cents") or 0)
        if total_cents <= 0:
            total_cents = sum(amount_from_row(item) for item in items)
        return {"total_cents": total_cents, "items": items}
    return {"total_cents": 0, "items": []}


def amount_from_row(row: dict) -> int:
    return int(row.get("amount_cents") or row.get("total_cents") or row.get("valor_cents") or 0)


def compact_named_amounts(rows: list[dict], *, limit: int = 12) -> list[dict]:
    return [
        {
            "name": row.get("name") or row.get("label") or row.get("subcategory_name") or row.get("description") or "",
            "amount_cents": amount_from_row(row),
            "count": int(row.get("count") or row.get("transaction_count") or 0),
        }
        for row in rows[:limit]
    ]


def compact_maturities(rows: list[dict], *, limit: int = 12) -> list[dict]:
    return [
        {
            "asset_type": row.get("asset_type"),
            "currency": row.get("currency"),
            "current_value_minor_units": int(row.get("current_value_cents") or 0),
            "current_value_display": format_currency_minor_units(
                row.get("current_value_cents") or 0, str(row.get("currency") or "BRL")
            ),
            "current_value_brl_cents": int(row.get("current_value_brl_cents") or row.get("current_value_cents") or 0),
            "quote_source": safe_quote_source(row.get("quote_source")),
            "quote_status": row.get("quote_status") or "",
            "quote_date": row.get("quote_date") or "",
            "maturity_date": row.get("maturity_date") or row.get("fixed_income_maturity_date") or "",
            "days_to_maturity": int(row.get("days_to_maturity") or 0),
            "reserved_for_objective": bool(row.get("reserved_for_objective")),
            "reserved_for_emergency": bool(row.get("emergency_reserve_eligible")),
        }
        for row in rows[:limit]
    ]
