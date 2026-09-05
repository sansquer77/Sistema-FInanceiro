from __future__ import annotations

from financeiro.accounts import cents_to_money
from financeiro.calendar_rules import shift_month


def load_invoice_history(conn, user_id: int, card_id: int, month: str) -> list[dict]:
    months = [shift_month(month, offset) for offset in range(-2, 3)]
    rows = conn.execute(
        """
        SELECT
            invoice_month,
            SUM(CASE WHEN type = 'expense' THEN amount_cents ELSE -amount_cents END) AS total_cents
        FROM credit_card_transactions
        WHERE user_id = ?
            AND credit_card_id = ?
            AND invoice_month BETWEEN ? AND ?
            AND archived_at IS NULL
        GROUP BY invoice_month
        """,
        (user_id, card_id, months[0], months[-1]),
    ).fetchall()
    totals = {row["invoice_month"]: int(row["total_cents"] or 0) for row in rows}
    return [
        {
            "month": invoice_month,
            "amount": cents_to_money(totals.get(invoice_month, 0)),
            "amount_cents": totals.get(invoice_month, 0),
        }
        for invoice_month in months
    ]


def format_card_payment(payment: dict, currency: str) -> dict:
    payment["amount"] = cents_to_money(payment.pop("amount_cents"))
    payment["card_currency"] = currency
    return payment
