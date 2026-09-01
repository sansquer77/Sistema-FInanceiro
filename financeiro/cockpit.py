from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from financeiro.money import cents_to_decimal, decimal_to_cents


def cockpit_payload(transactions: list[dict]) -> dict:
    totals_cents = {"income": 0, "expense": 0, "investment": 0}
    category_rows = {"income": {}, "expense": {}, "investment": {}}
    planning = {"income": {}, "expense": {}, "investment": {}}
    for transaction in transactions:
        if is_credit_card_payment_transaction(transaction):
            continue
        report_type = cockpit_transaction_type(transaction)
        if not report_type:
            continue
        amount_cents = money_value_to_cents(transaction.get("amount_brl") or transaction.get("amount") or 0)
        totals_cents[report_type] += amount_cents
        label = cockpit_category_label(transaction)
        add_cockpit_group(category_rows[report_type], label, amount_cents)
        if transaction.get("series_kind") == "recurring" or (report_type == "investment" and transaction.get("series_kind") != "single"):
            currency = cockpit_transaction_currency(transaction)
            add_cockpit_group(planning[report_type], label, money_value_to_cents(transaction.get("amount") or 0), currency)
    income_cents = totals_cents["income"]
    savings_rate = float(Decimal(totals_cents["investment"]) / Decimal(income_cents)) if income_cents > 0 else 0.0
    return {
        "month_totals": {key: cents_to_value(value) for key, value in totals_cents.items()} | {"savings_rate": savings_rate},
        "top_income": ranked_cockpit_rows(category_rows["income"], 3),
        "top_expenses": ranked_cockpit_rows(category_rows["expense"], 5),
        "planning": {key: ranked_cockpit_rows(planning[key]) for key in ("income", "investment", "expense")},
    }


def cents_to_value(cents: int) -> float:
    return float(cents_to_decimal(cents))


def money_value_to_cents(value: object) -> int:
    try:
        decimal = Decimal(str(value or "0").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return 0
    return decimal_to_cents(decimal)


def is_credit_card_payment_transaction(transaction: dict) -> bool:
    # spec: relatorios/relatorios v2.20 — critério 6
    return bool(transaction.get("is_credit_card_payment"))


def cockpit_transaction_type(transaction: dict) -> str:
    if transaction.get("type") == "income":
        return "income"
    if transaction.get("type") == "expense":
        return "expense"
    if transaction.get("type") == "investment" or transaction.get("investment_operation"):
        return "investment"
    return ""


def cockpit_category_label(transaction: dict) -> str:
    category = transaction.get("category_name") or "Sem categoria"
    subcategory = transaction.get("subcategory_name") or ""
    return f"{category} / {subcategory}" if subcategory else category


def cockpit_transaction_currency(transaction: dict) -> str:
    return str(transaction.get("account_currency") or transaction.get("card_currency") or "BRL").upper()


def add_cockpit_group(groups: dict, label: str, amount_cents: int, currency: str | None = None) -> None:
    key = (currency, label) if currency else label
    row = groups.setdefault(key, {"label": label, "total_cents": 0, "count": 0})
    if currency:
        row["currency"] = currency
    row["total_cents"] += amount_cents
    row["count"] += 1


def _cockpit_row_public(row: dict) -> dict:
    result = {"label": row["label"], "total": cents_to_value(row["total_cents"]), "count": row["count"]}
    if "currency" in row:
        result["currency"] = row["currency"]
    return result


def ranked_cockpit_rows(groups: dict, limit: int | None = None) -> list[dict]:
    rows = sorted(groups.values(), key=lambda row: (row.get("currency", ""), -row["total_cents"], row["label"]))
    if limit and len(rows) > limit:
        visible = [_cockpit_row_public(row) for row in rows[:limit]]
        remainder = rows[limit:]
        total_cents = sum(row["total_cents"] for row in remainder)
        if total_cents > 0:
            visible.append({"label": "Outros", "total": cents_to_value(total_cents), "count": sum(row["count"] for row in remainder), "items": [_cockpit_row_public(row) for row in remainder]})
        return visible
    return [_cockpit_row_public(row) for row in rows]
