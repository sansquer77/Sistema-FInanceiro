from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from financeiro.calendar_rules import add_months, month_end_date
from financeiro.database import get_connection


def build_currency_totals_for_user(user_id: int, month: str) -> list[dict]:
    """Build the Cockpit balance summary from bounded SQLite aggregates."""
    limit_date = month_end_date(month)
    # spec: relatorios/relatorios v2.23 — Cockpit não materializa históricos
    # detalhados para consolidar saldos e reservas de fatura por moeda.
    with get_connection() as conn:
        account_rows = conn.execute(
            """
            SELECT
                accounts.id,
                accounts.name,
                accounts.account_type,
                accounts.currency,
                accounts.initial_balance_cents + COALESCE(SUM(
                    CASE
                        WHEN transactions.account_id = accounts.id
                            AND transactions.type = 'income' THEN transactions.amount_cents
                        WHEN transactions.account_id = accounts.id
                            AND transactions.type IN ('expense', 'investment', 'transfer') THEN -transactions.amount_cents
                        WHEN transactions.destination_account_id = accounts.id
                            AND transactions.type = 'transfer'
                            THEN COALESCE(NULLIF(transactions.destination_amount_cents, 0), transactions.amount_cents)
                        ELSE 0
                    END
                ), 0) AS projected_cents,
                accounts.initial_balance_cents + COALESCE(SUM(
                    CASE
                        WHEN transactions.reconciled_at IS NULL THEN 0
                        WHEN transactions.account_id = accounts.id
                            AND transactions.type = 'income' THEN transactions.amount_cents
                        WHEN transactions.account_id = accounts.id
                            AND transactions.type IN ('expense', 'investment', 'transfer') THEN -transactions.amount_cents
                        WHEN transactions.destination_account_id = accounts.id
                            AND transactions.type = 'transfer'
                            THEN COALESCE(NULLIF(transactions.destination_amount_cents, 0), transactions.amount_cents)
                        ELSE 0
                    END
                ), 0) AS reconciled_cents
            FROM checking_accounts AS accounts
            LEFT JOIN transactions
                ON transactions.user_id = accounts.user_id
                AND transactions.archived_at IS NULL
                AND transactions.date <= ?
                AND (
                    transactions.account_id = accounts.id
                    OR transactions.destination_account_id = accounts.id
                )
            WHERE accounts.user_id = ? AND accounts.archived_at IS NULL
            GROUP BY accounts.id
            ORDER BY accounts.id
            """,
            (limit_date, user_id),
        ).fetchall()
        card_rows = conn.execute(
            """
            SELECT
                cards.id,
                cards.name,
                cards.issuer,
                cards.currency,
                COALESCE(SUM(
                    CASE card_transactions.type
                        WHEN 'expense' THEN card_transactions.amount_cents
                        WHEN 'income' THEN -card_transactions.amount_cents
                        ELSE 0
                    END
                ), 0) AS open_cents,
                COALESCE(SUM(
                    CASE
                        WHEN card_transactions.reconciled_at IS NULL THEN 0
                        WHEN card_transactions.type = 'expense' THEN card_transactions.amount_cents
                        WHEN card_transactions.type = 'income' THEN -card_transactions.amount_cents
                        ELSE 0
                    END
                ), 0) AS reconciled_cents,
                EXISTS (
                    SELECT 1
                    FROM credit_card_payments
                    WHERE credit_card_payments.user_id = cards.user_id
                        AND credit_card_payments.credit_card_id = cards.id
                        AND credit_card_payments.invoice_month = ?
                ) AS is_paid
            FROM credit_cards AS cards
            LEFT JOIN credit_card_transactions AS card_transactions
                ON card_transactions.user_id = cards.user_id
                AND card_transactions.credit_card_id = cards.id
                AND card_transactions.invoice_month = ?
                AND card_transactions.archived_at IS NULL
            WHERE cards.user_id = ? AND cards.archived_at IS NULL
            GROUP BY cards.id
            ORDER BY cards.id
            """,
            (month, month, user_id),
        ).fetchall()
        reservation_rows = conn.execute(
            """
            SELECT
                cards.id AS card_id,
                cards.preferred_payment_account_id AS account_id,
                card_transactions.invoice_month,
                cards.due_day,
                SUM(
                    CASE card_transactions.type
                        WHEN 'expense' THEN card_transactions.amount_cents
                        WHEN 'income' THEN -card_transactions.amount_cents
                        ELSE 0
                    END
                ) AS invoice_cents
            FROM credit_card_transactions AS card_transactions
            JOIN credit_cards AS cards
                ON cards.id = card_transactions.credit_card_id
                AND cards.user_id = card_transactions.user_id
                AND cards.archived_at IS NULL
            JOIN checking_accounts AS accounts
                ON accounts.id = cards.preferred_payment_account_id
                AND accounts.user_id = cards.user_id
                AND accounts.archived_at IS NULL
                AND accounts.currency = cards.currency
            WHERE card_transactions.user_id = ?
                AND card_transactions.archived_at IS NULL
                AND card_transactions.reconciled_at IS NOT NULL
                AND card_transactions.invoice_month <= ?
                AND NOT EXISTS (
                    SELECT 1
                    FROM credit_card_payments
                    WHERE credit_card_payments.user_id = card_transactions.user_id
                        AND credit_card_payments.credit_card_id = card_transactions.credit_card_id
                        AND credit_card_payments.invoice_month = card_transactions.invoice_month
                )
            GROUP BY cards.id, cards.preferred_payment_account_id, card_transactions.invoice_month
            """,
            (user_id, month),
        ).fetchall()

    reserved_by_account: dict[int, int] = {}
    reserved_by_card_month: dict[tuple[int, str], int] = {}
    for row in reservation_rows:
        invoice_month = str(row["invoice_month"])
        if card_invoice_date(invoice_month, row["due_day"]) > limit_date:
            continue
        reserved_cents = max(int(row["invoice_cents"] or 0), 0)
        account_id = int(row["account_id"])
        reserved_by_account[account_id] = reserved_by_account.get(account_id, 0) + reserved_cents
        reserved_by_card_month[(int(row["card_id"]), invoice_month)] = reserved_cents

    totals: dict[str, dict] = {}
    for account in account_rows:
        currency = normalized_currency(account["currency"])
        row = totals.setdefault(currency, {"currency": currency, "current_cents": 0, "accounts": [], "cards": []})
        projected_cents = int(account["projected_cents"] or 0) - reserved_by_account.get(int(account["id"]), 0)
        reconciled_cents = int(account["reconciled_cents"] or 0)
        row["current_cents"] += projected_cents
        row["accounts"].append({
            "id": account["id"], "name": account["name"], "type": account["account_type"],
            "amount": cents_to_value(projected_cents), "reconciled": cents_to_value(reconciled_cents),
        })
    for card in card_rows:
        currency = normalized_currency(card["currency"])
        row = totals.setdefault(currency, {"currency": currency, "current_cents": 0, "accounts": [], "cards": []})
        open_cents = int(card["open_cents"] or 0)
        reconciled_cents = int(card["reconciled_cents"] or 0)
        reserved_cents = reserved_by_card_month.get((int(card["id"]), month), 0)
        signed_cents = 0 if card["is_paid"] else -max(open_cents - reserved_cents, 0)
        row["current_cents"] += signed_cents
        row["cards"].append({
            "id": card["id"], "name": card["name"], "issuer": card["issuer"],
            "amount": cents_to_value(-max(open_cents, 0)),
            "reconciled": cents_to_value(-reconciled_cents),
        })
    return [
        {**row, "current": cents_to_value(row.pop("current_cents"))}
        for _, row in sorted(totals.items())
    ]


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
    # spec: lancamentos/lancamentos v3.35 — projeção limitada à conta selecionada
    # Mantém transferências recebidas; não recalcula outras contas a cada troca.
    if account_id is not None:
        transactions = [
            row for row in transactions
            if optional_int(row.get("account_id")) == account_id
            or optional_int(row.get("destination_account_id")) == account_id
        ]
        cards = [card for card in cards if optional_int(card.get("preferred_payment_account_id")) == account_id]
        card_ids = {int(card["id"]) for card in cards}
        card_transactions = [row for row in card_transactions if optional_int(row.get("credit_card_id")) in card_ids]
        card_payments = [row for row in card_payments if optional_int(row.get("credit_card_id")) in card_ids]
    dates = {str(transaction.get("date")) for transaction in transactions if transaction.get("date")}
    dates.add(date.today().isoformat())
    reference = date.fromisoformat(f"{month}-01")
    for offset in range(-1, 4):
        dates.add(month_end_date(add_months(reference, offset).strftime("%Y-%m")))

    # spec: lancamentos/lancamentos v3.35 — projeções preservam os saldos sem
    # reprocessar todo o histórico para cada data solicitada.
    ordered = sorted(transactions, key=lambda row: str(row.get("date") or ""))
    zero_accounts = [{**account, "initial_balance": 0} for account in selected_accounts]
    reconciled = account_totals_until(selected_accounts, [], "", reconciled_only=True)
    running = dict(reconciled)
    reservation_events = card_reservation_events(selected_accounts, cards, card_transactions, card_payments)
    reservations = {}
    transaction_index = reservation_index = 0
    balances = {}
    forecast_accounts: dict[str, bool] = {}
    for limit_date in sorted(dates):
        start = transaction_index
        while transaction_index < len(ordered) and str(ordered[transaction_index].get("date") or "") <= limit_date:
            transaction_index += 1
        batch = ordered[start:transaction_index]
        if batch:
            for target, only_reconciled in ((reconciled, True), (running, False)):
                for currency, delta in account_totals_until(zero_accounts, batch, limit_date, reconciled_only=only_reconciled).items():
                    target[currency] = target.get(currency, 0) + delta
        while reservation_index < len(reservation_events) and reservation_events[reservation_index][0] <= limit_date:
            _, owner, amount = reservation_events[reservation_index]
            reservations[owner] = reservations.get(owner, 0) + amount
            reservation_index += 1
        projected = dict(running)
        for account in selected_accounts:
            reserved = reservations.get(int(account["id"]), 0)
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


def card_reservation_events(accounts, cards, transactions, payments) -> list[tuple[str, int, int]]:
    """Aggregate reconciled, unpaid invoices once; reserve at their due date."""
    owners = {int(account["id"]): normalized_currency(account.get("currency")) for account in accounts}
    eligible = {
        int(card["id"]): card for card in cards
        if optional_int(card.get("preferred_payment_account_id")) in owners
        and normalized_currency(card.get("currency")) == owners[optional_int(card.get("preferred_payment_account_id"))]
    }
    paid = {(optional_int(row.get("credit_card_id")), row.get("invoice_month")) for row in payments}
    invoices = {}
    for row in transactions:
        key = (optional_int(row.get("credit_card_id")), str(row.get("invoice_month") or ""))
        if key[0] not in eligible or not key[1] or not row.get("reconciled_at") or key in paid:
            continue
        invoices[key] = invoices.get(key, 0) + card_transaction_delta_cents(row)
    return sorted(
        (card_invoice_date(month, eligible[card_id].get("due_day")),
         int(eligible[card_id]["preferred_payment_account_id"]), max(amount, 0))
        for (card_id, month), amount in invoices.items()
    )


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
