from __future__ import annotations

import unittest

from financeiro.balance_projections import build_balance_projection


class BalanceProjectionTest(unittest.TestCase):
    def test_paid_invoice_is_not_subtracted_twice(self) -> None:
        payload = build_balance_projection(
            accounts=[{"id": 1, "name": "Conta", "currency": "BRL", "account_type": "checking", "initial_balance": "1000.00"}],
            transactions=[{"account_id": 1, "type": "expense", "amount": "200.00", "date": "2026-08-10", "reconciled_at": "2026-08-10"}],
            cards=[{"id": 7, "name": "Cartão", "issuer": "Banco", "currency": "BRL", "due_day": 10, "preferred_payment_account_id": 1}],
            card_transactions=[{"credit_card_id": 7, "type": "expense", "amount": "200.00", "invoice_month": "2026-08", "reconciled_at": "2026-08-01"}],
            card_payments=[{"credit_card_id": 7, "invoice_month": "2026-08"}],
            month="2026-08",
        )
        brl = payload["currency_totals"][0]
        self.assertEqual(brl["current"], 800.0)
        self.assertEqual(brl["cards"][0]["amount"], -200.0)

    def test_open_invoice_is_reserved_from_preferred_account(self) -> None:
        payload = build_balance_projection(
            accounts=[{"id": 1, "name": "Conta", "currency": "BRL", "account_type": "checking", "initial_balance": "1000.00"}],
            transactions=[],
            cards=[{"id": 7, "name": "Cartão", "issuer": "Banco", "currency": "BRL", "due_day": 10, "preferred_payment_account_id": 1}],
            card_transactions=[{"credit_card_id": 7, "type": "expense", "amount": "200.00", "invoice_month": "2026-08", "reconciled_at": "2026-08-01"}],
            card_payments=[], month="2026-08", account_id=1,
        )
        month_end = payload["balances"]["2026-08-31"]
        self.assertEqual(month_end["reconciled"]["BRL"], 1000.0)
        self.assertEqual(month_end["projected"]["BRL"], 800.0)
        self.assertTrue(payload["preferred_card_forecasts"]["1:2026-08-31"])


if __name__ == "__main__":
    unittest.main()
