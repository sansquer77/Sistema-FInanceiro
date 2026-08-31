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
    # spec: consultor/consultor v2.0 - criterio 30
    from financeiro.financial_health import calculate_financial_health_score

    positions = _load_portfolio_positions(user_id, portfolio_positions)
    score = calculate_financial_health_score(user_id, portfolio_positions=positions)
    return {
        "analysis_id": "analise_carteira",
        "portfolio": summarize_portfolio(positions),
        "allocation_goals": build_allocation_goals_context(user_id, positions),
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


# spec: consultor/consultor v2.0 — critérios 8 e 10
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

    calendar = get_cockpit_calendar(user_id, reference_date=reference_date, portfolio_positions=portfolio_positions)
    trends = calculate_trends(user_id, month)
    score = calculate_financial_health_score(user_id, month, portfolio_positions=portfolio_positions)
    maturity_assets = [
        *calendar.get("maturity_30_days", []),
        *calendar.get("maturity_60_days", []),
    ]
    return {
        "analysis_id": "destino_vencimentos",
        "reference_date": calendar.get("reference_date"),
        "maturity_assets": compact_maturities(maturity_assets),
        "market_data": market_data_context(maturity_assets),
        "cashflow_projection": {
            "month": trends["month"],
            "income_cents": int(trends.get("receitas_mes_cents") or 0),
            "expense_cents": int(trends.get("despesas_mes_cents") or 0),
            "balance_cents": int(trends.get("saldo_mes_cents") or 0),
            "confidence": trends.get("confianca"),
        },
        "score_pillars": {
            "reserve": int(score.get("pilar_reserva") or 0),
            "debt": int(score.get("pilar_endividamento") or 0),
            "eligible_reserve_cents": int(score.get("reserva_elegivel_cents") or 0),
            "debt_installments_month_cents": int(score.get("dividas_parcelas_mes_cents") or 0),
        },
    }


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
    # spec: consultor/consultor v2.0 — critério 39
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
            "current_value_cents": int(row.get("current_value_cents") or 0),
            "current_value_brl_cents": int(row.get("current_value_brl_cents") or row.get("current_value_cents") or 0),
            "quote_source": safe_quote_source(row.get("quote_source")),
            "quote_status": row.get("quote_status") or "",
            "quote_date": row.get("quote_date") or "",
            "maturity_date": row.get("maturity_date") or row.get("fixed_income_maturity_date") or "",
            "days_to_maturity": int(row.get("days_to_maturity") or 0),
        }
        for row in rows[:limit]
    ]
