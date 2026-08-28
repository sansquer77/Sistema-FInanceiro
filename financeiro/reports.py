from __future__ import annotations

from decimal import Decimal

from financeiro.credit_cards import list_credit_card_transactions
from financeiro.transactions import list_transactions


def build_tag_report(user_id: int, month: str | None = None) -> dict:
    # spec: relatorios/relatorios v2.16 — relatório de tags agrupado por tag com
    # Receitas, Despesas, Saldo e Investimentos, separados por moeda.
    transactions = list_transactions(user_id, month=month)
    card_transactions = list_credit_card_transactions(user_id, invoice_month=month)
    groups: dict[str, dict] = {}
    for transaction in transactions:
        if transaction.get("is_credit_card_payment"):
            continue
        _accumulate_tag_groups(groups, transaction, "account")
    for transaction in card_transactions:
        _accumulate_tag_groups(groups, transaction, "card")
    rows = sorted(
        groups.values(),
        key=lambda row: (
            -(row["expense_cents"] + row["investment_cents"]),
            row["tag"],
        ),
    )
    return {
        "month": month,
        "tags": [_serialize_tag_row(row) for row in rows],
    }


def _accumulate_tag_groups(
    groups: dict[str, dict],
    transaction: dict,
    source: str,
) -> None:
    report_type = _report_type_for(transaction)
    if not report_type:
        return
    tags = transaction.get("tags") or []
    if not tags:
        return
    amount_cents = int(Decimal(transaction.get("amount") or "0") * 100)
    currency = (
        transaction.get("currency")
        or transaction.get("card_currency")
        or transaction.get("account_currency")
        or "BRL"
    )
    for tag in tags:
        if tag not in groups:
            groups[tag] = {
                "tag": tag,
                "income_cents": 0,
                "expense_cents": 0,
                "investment_cents": 0,
                "income_by_currency": {},
                "expense_by_currency": {},
                "investment_by_currency": {},
                "count": 0,
            }
        group = groups[tag]
        group["count"] += 1
        if report_type == "income":
            group["income_cents"] += amount_cents
            group["income_by_currency"][currency] = group["income_by_currency"].get(currency, 0) + amount_cents
        elif report_type == "expense":
            group["expense_cents"] += amount_cents
            group["expense_by_currency"][currency] = group["expense_by_currency"].get(currency, 0) + amount_cents
        elif report_type == "investment":
            group["investment_cents"] += amount_cents
            group["investment_by_currency"][currency] = group["investment_by_currency"].get(currency, 0) + amount_cents


def _report_type_for(transaction: dict) -> str:
    tx_type = transaction.get("type")
    if tx_type == "income":
        return "income"
    if tx_type == "expense":
        return "expense"
    if tx_type == "investment":
        return "investment"
    return ""


def _serialize_tag_row(row: dict) -> dict:
    return {
        "tag": row["tag"],
        "count": row["count"],
        "income_cents": row["income_cents"],
        "expense_cents": row["expense_cents"],
        "investment_cents": row["investment_cents"],
        "balance_cents": row["income_cents"] - row["expense_cents"],
        "income_by_currency": row["income_by_currency"],
        "expense_by_currency": row["expense_by_currency"],
        "investment_by_currency": row["investment_by_currency"],
    }
