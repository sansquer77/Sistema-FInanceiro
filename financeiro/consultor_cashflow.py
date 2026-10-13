from __future__ import annotations

from datetime import date, timedelta

from financeiro.balance_projections import card_invoice_date
from financeiro.database import get_connection


def build_maturity_cashflow_context(user_id: int, reference_date: date) -> dict:
    """Projeção curta a partir de saldos efetivos e compromissos explicitamente registrados."""
    # spec: consultor/consultor v2.14 — critérios 42, 43 e 45
    from financeiro.consultor_context import format_currency_minor_units

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
