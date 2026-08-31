from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from financeiro.calendar_rules import add_months, month_end_date


def build_balance_projection(
    *,
    accounts: list[dict],
    transactions: list[dict],
    cards: list[dict],
    card_transactions: list[dict],
    card_payments: list[dict],
    month: str,
    account_id: int | None = None,
) -> dict:
    selected_accounts = [account for account in accounts if account_id is None or int(account["id"]) == account_id]
    dates = {str(transaction.get("date")) for transaction in transactions if transaction.get("date")}
    dates.add(date.today().isoformat())
    reference = date.fromisoformat(f"{month}-01")
    for offset in range(-1, 4):
        dates.add(month_end_date(add_months(reference, offset).strftime("%Y-%m")))

    balances = {}
    forecast_accounts: dict[str, bool] = {}
    for limit_date in sorted(dates):
        reconciled = account_totals_until(selected_accounts, transactions, limit_date, reconciled_only=True)
        projected = account_totals_until(selected_accounts, transactions, limit_date, reconciled_only=False)
        for account in selected_accounts:
            reserved = preferred_card_forecast_for_account(
                account, cards, card_transactions, card_payments, limit_date
            )
            currency = normalized_currency(account.get("currency"))
            projected[currency] = projected.get(currency, 0) - reserved
            if reserved > 0:
                forecast_accounts[f"{account['id']}:{limit_date}"] = True
        balances[limit_date] = {
            "reconciled": public_money_map(reconciled),
            "projected": public_money_map(projected),
        }

    return {
        "balances": balances,
        "preferred_card_forecasts": forecast_accounts,
        "currency_totals": currency_totals(
            accounts, transactions, cards, card_transactions, card_payments, month
        ) if account_id is None else [],
    }


def account_totals_until(accounts: list[dict], transactions: list[dict], limit_date: str, *, reconciled_only: bool) -> dict[str, int]:
    account_ids = {int(account["id"]) for account in accounts}
    totals: dict[str, int] = {}
    account_currencies = {int(account["id"]): normalized_currency(account.get("currency")) for account in accounts}
    for account in accounts:
        currency = normalized_currency(account.get("currency"))
        totals[currency] = totals.get(currency, 0) + money_to_cents(account.get("initial_balance"))
    for transaction in transactions:
        if str(transaction.get("date") or "") > limit_date or (reconciled_only and not transaction.get("reconciled_at")):
            continue
        source_id = optional_int(transaction.get("account_id"))
        destination_id = optional_int(transaction.get("destination_account_id"))
        if source_id in account_ids:
            currency = account_currencies[source_id]
            totals[currency] = totals.get(currency, 0) + transaction_source_delta_cents(transaction)
        if transaction.get("type") == "transfer" and destination_id in account_ids:
            currency = account_currencies[destination_id]
            totals[currency] = totals.get(currency, 0) + money_to_cents(
                transaction.get("destination_amount") or transaction.get("amount")
            )
    return totals


def currency_totals(accounts, transactions, cards, card_transactions, card_payments, month: str) -> list[dict]:
    limit_date = month_end_date(month)
    rows: dict[str, dict] = {}
    for account in accounts:
        currency = normalized_currency(account.get("currency"))
        row = rows.setdefault(currency, {"currency": currency, "current_cents": 0, "accounts": [], "cards": []})
        reconciled = account_balance_cents(account, transactions, limit_date, True)
        reserved = preferred_card_forecast_for_account(account, cards, card_transactions, card_payments, limit_date)
        projected = account_balance_cents(account, transactions, limit_date, False) - reserved
        row["current_cents"] += projected
        row["accounts"].append({
            "id": account["id"], "name": account.get("name"), "type": account.get("account_type"),
            "amount": cents_to_value(projected), "reconciled": cents_to_value(reconciled),
        })
    for card in cards:
        currency = normalized_currency(card.get("currency"))
        row = rows.setdefault(currency, {"currency": currency, "current_cents": 0, "accounts": [], "cards": []})
        open_cents = card_invoice_balance_cents(card["id"], month, card_transactions, reconciled_only=False)
        reconciled_cents = card_invoice_balance_cents(card["id"], month, card_transactions, reconciled_only=True)
        reserved = preferred_card_forecast_amount(card, card_transactions, card_payments, limit_date)
        signed = 0 if is_invoice_paid(card["id"], month, card_payments) else -max(open_cents - reserved, 0)
        row["current_cents"] += signed
        row["cards"].append({
            "id": card["id"], "name": card.get("name"), "issuer": card.get("issuer"),
            "amount": cents_to_value(-max(open_cents, 0)), "reconciled": cents_to_value(-reconciled_cents),
        })
    return [{**row, "current": cents_to_value(row.pop("current_cents"))} for _, row in sorted(rows.items())]


def account_balance_cents(account: dict, transactions: list[dict], limit_date: str, reconciled_only: bool) -> int:
    return account_totals_until([account], transactions, limit_date, reconciled_only=reconciled_only).get(normalized_currency(account.get("currency")), 0)


def preferred_card_forecast_for_account(account, cards, card_transactions, card_payments, limit_date: str) -> int:
    return sum(
        preferred_card_forecast_amount(card, card_transactions, card_payments, limit_date)
        for card in cards
        if optional_int(card.get("preferred_payment_account_id")) == int(account["id"])
        and normalized_currency(card.get("currency")) == normalized_currency(account.get("currency"))
    )


def preferred_card_forecast_amount(card, card_transactions, card_payments, limit_date: str) -> int:
    if not card.get("preferred_payment_account_id"):
        return 0
    invoices: dict[str, int] = {}
    for transaction in card_transactions:
        invoice_month = str(transaction.get("invoice_month") or "")
        if optional_int(transaction.get("credit_card_id")) != int(card["id"]) or not transaction.get("reconciled_at") or not invoice_month:
            continue
        if card_invoice_date(invoice_month, card.get("due_day")) > limit_date or is_invoice_paid(card["id"], invoice_month, card_payments):
            continue
        invoices[invoice_month] = invoices.get(invoice_month, 0) + card_transaction_delta_cents(transaction)
    return sum(max(amount, 0) for amount in invoices.values())


def card_invoice_balance_cents(card_id, invoice_month, transactions, *, reconciled_only: bool) -> int:
    return sum(
        card_transaction_delta_cents(transaction)
        for transaction in transactions
        if optional_int(transaction.get("credit_card_id")) == int(card_id)
        and transaction.get("invoice_month") == invoice_month
        and (not reconciled_only or transaction.get("reconciled_at"))
    )


def card_transaction_delta_cents(transaction: dict) -> int:
    amount = money_to_cents(transaction.get("amount"))
    return -amount if transaction.get("type") == "income" else amount if transaction.get("type") == "expense" else 0


def transaction_source_delta_cents(transaction: dict) -> int:
    amount = money_to_cents(transaction.get("amount"))
    return amount if transaction.get("type") == "income" else -amount


def is_invoice_paid(card_id, invoice_month, payments) -> bool:
    return any(optional_int(payment.get("credit_card_id")) == int(card_id) and payment.get("invoice_month") == invoice_month for payment in payments)


def card_invoice_date(invoice_month: str, due_day: object) -> str:
    year, month = (int(part) for part in invoice_month.split("-", 1))
    last_day = date(year + (month // 12), month % 12 + 1, 1).toordinal() - date(year, month, 1).toordinal()
    return f"{year:04d}-{month:02d}-{min(max(int(due_day or 1), 1), last_day):02d}"


def money_to_cents(value: object) -> int:
    try:
        return int((Decimal(str(value or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except InvalidOperation:
        return 0


def cents_to_value(value: int) -> float:
    return float(Decimal(value) / Decimal(100))


def public_money_map(values: dict[str, int]) -> dict[str, float]:
    return {currency: cents_to_value(amount) for currency, amount in sorted(values.items())}


def normalized_currency(value: object) -> str:
    return str(value or "BRL").upper()


def optional_int(value: object) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
