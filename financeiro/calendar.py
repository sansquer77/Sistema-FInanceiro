from __future__ import annotations

from collections import defaultdict
from datetime import date
from http import HTTPStatus

from financeiro.database import get_connection, row_to_dict
from financeiro.portfolio_positions import load_open_fixed_income_maturities


class CalendarError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def get_cockpit_calendar(
    user_id: int,
    reference_date: date | None = None,
    portfolio_positions: list[dict] | None = None,
) -> dict:
    # spec: cockpit-calendario v0.9 — critérios 3, 4, 7, 8, 9, 10, 11, 12, 13, 14 e 15
    # (consolida contas a receber/pagar atrasadas e vencimentos de renda fixa
    #  em 30 e 60 dias a partir da data de referência do servidor)
    reference_date = reference_date or date.today()
    overdue_receivables = _fetch_overdue_transactions(user_id, reference_date, "income")
    overdue_payables = _fetch_overdue_transactions(user_id, reference_date, "expense")
    maturity_30_days, maturity_60_days = _fetch_fixed_income_maturities(
        user_id, reference_date, portfolio_positions=portfolio_positions
    )

    return {
        "reference_date": reference_date.isoformat(),
        "overdue_receivables": overdue_receivables,
        "overdue_payables": overdue_payables,
        "maturity_30_days": maturity_30_days,
        "maturity_60_days": maturity_60_days,
        "total_overdue_receivables_cents": sum(item["amount_cents"] for item in overdue_receivables),
        "total_overdue_payables_cents": sum(item["amount_cents"] for item in overdue_payables),
        "totals_by_currency": _build_totals_by_currency(
            overdue_receivables, overdue_payables, maturity_30_days, maturity_60_days
        ),
    }


def _fetch_overdue_transactions(user_id: int, reference_date: date, transaction_type: str) -> list[dict]:
    # spec: cockpit-calendario v0.9 — critérios 3 e 4 (receitas/despesas atrasadas)
    # (somente lançamentos de conta; data anterior à referência; não conciliados;
    #  transferências, investimentos e pagamentos de fatura excluídos)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                t.id,
                t.description,
                t.date,
                t.amount_cents,
                t.amount_brl_cents,
                a.id AS account_id,
                a.name AS account_name,
                a.currency AS account_currency,
                c.name AS category_name,
                sc.name AS subcategory_name
            FROM transactions t
            JOIN checking_accounts a
                ON a.id = t.account_id
                AND a.user_id = t.user_id
            LEFT JOIN categories c
                ON c.id = t.category_id
                AND c.user_id = t.user_id
            LEFT JOIN subcategories sc
                ON sc.id = t.subcategory_id
                AND sc.user_id = t.user_id
            LEFT JOIN credit_card_payments p
                ON p.transaction_id = t.id
                AND p.user_id = t.user_id
            WHERE t.user_id = ?
              AND t.type = ?
              AND t.date < ?
              AND (t.reconciled_at IS NULL OR t.reconciled_at = '')
              AND t.archived_at IS NULL
              AND p.id IS NULL
            ORDER BY t.date ASC, t.id ASC
            """,
            (user_id, transaction_type, reference_date.isoformat()),
        ).fetchall()
    return [_format_overdue_transaction(row_to_dict(row), reference_date) for row in rows]


def _format_overdue_transaction(row: dict, reference_date: date) -> dict:
    return {
        "id": row["id"],
        "description": row["description"],
        "date": row["date"],
        "amount_cents": row["amount_cents"],
        "currency": row["account_currency"] or "BRL",
        "account_id": row["account_id"],
        "account_name": row["account_name"],
        "days_overdue": (reference_date - date.fromisoformat(row["date"])).days,
        "category_name": row["category_name"] or "",
        "subcategory_name": row["subcategory_name"] or "",
    }


def _fetch_fixed_income_maturities(
    user_id: int,
    reference_date: date,
    portfolio_positions: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    # spec: cockpit-calendario v0.9 — critérios 7, 8, 9, 10, 11, 12, 13, 14 e 15
    # (somente posições abertas de renda fixa; exclui encerradas, poupança, ações,
    #  fundos, cripto, previdência e outros tipos; janelas de 30 e 60 dias sem sobreposição)
    if portfolio_positions is None:
        with get_connection() as conn:
            positions = load_open_fixed_income_maturities(conn, user_id)
    else:
        positions = portfolio_positions
    maturity_30_days: list[dict] = []
    maturity_60_days: list[dict] = []
    for position in positions:
        if position.get("asset_type") != "fixed_income":
            continue
        maturity_date = position.get("fixed_income_maturity_date")
        if not maturity_date:
            continue
        maturity = date.fromisoformat(str(maturity_date))
        days_to_maturity = (maturity - reference_date).days
        if days_to_maturity < 0:
            continue
        formatted = _format_maturity_position(position, maturity, days_to_maturity)
        if days_to_maturity <= 30:
            maturity_30_days.append(formatted)
        elif days_to_maturity <= 60:
            maturity_60_days.append(formatted)
    maturity_30_days.sort(key=lambda item: (item["days_to_maturity"], item["maturity_date"], item["position_id"]))
    maturity_60_days.sort(key=lambda item: (item["days_to_maturity"], item["maturity_date"], item["position_id"]))
    return maturity_30_days, maturity_60_days


def _format_maturity_position(position: dict, maturity_date: date, days_to_maturity: int) -> dict:
    return {
        "position_id": position.get("source_id") or position.get("id"),
        "source_type": position.get("source_type"),
        "asset_name": position.get("asset_name") or position.get("asset_identifier") or "",
        "asset_identifier": position.get("asset_identifier") or "",
        "maturity_date": maturity_date.isoformat(),
        "current_value_cents": int(position.get("current_value_cents") or 0),
        "currency": position.get("currency") or "BRL",
        "account_id": position.get("account_id"),
        "account_name": position.get("account_name") or "",
        "days_to_maturity": days_to_maturity,
    }


def _build_totals_by_currency(
    overdue_receivables: list[dict],
    overdue_payables: list[dict],
    maturity_30_days: list[dict],
    maturity_60_days: list[dict],
) -> list[dict]:
    # spec: cockpit-calendario v0.9 — seção "Dados" (totals_by_currency opcional)
    totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "overdue_receivables_cents": 0,
            "overdue_payables_cents": 0,
            "maturity_30_days_cents": 0,
            "maturity_60_days_cents": 0,
        }
    )
    for item in overdue_receivables:
        totals[item["currency"]]["overdue_receivables_cents"] += item["amount_cents"]
    for item in overdue_payables:
        totals[item["currency"]]["overdue_payables_cents"] += item["amount_cents"]
    for item in maturity_30_days:
        totals[item["currency"]]["maturity_30_days_cents"] += item["current_value_cents"]
    for item in maturity_60_days:
        totals[item["currency"]]["maturity_60_days_cents"] += item["current_value_cents"]
    return [
        {"currency": currency, **amounts}
        for currency, amounts in sorted(totals.items())
    ]
