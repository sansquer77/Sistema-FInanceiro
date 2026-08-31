from __future__ import annotations

import unittest

from financeiro.balance_projections import build_balance_projection


class BalanceProjectionTest(unittest.TestCase):
    def test_incremental_projection_matches_reference_for_every_date(self) -> None:
        from datetime import date, timedelta
        from financeiro.balance_projections import account_totals_until, preferred_card_forecast_for_account, public_money_map
        accounts = [{"id": 1, "currency": "BRL", "initial_balance": "123.45"},
                    {"id": 2, "currency": "USD", "initial_balance": "-10.01"}]
        transactions = [
            {"account_id": 1 + index % 2, "destination_account_id": 2 - index % 2,
             "amount": "3.17", "destination_amount": "0.61", "type": ["income", "expense", "transfer", "investment"][index % 4],
             "date": (date(2026, 1, 1) + timedelta(days=index * 3)).isoformat(),
             "reconciled_at": "yes" if index % 3 else None}
            for index in range(120)
        ]
        cards = [{"id": 7, "currency": "BRL", "due_day": 31, "preferred_payment_account_id": 1},
                 {"id": 8, "currency": "USD", "due_day": 10, "preferred_payment_account_id": 2},
                 {"id": 9, "currency": "USD", "due_day": 10, "preferred_payment_account_id": 1}]
        charges = [{"credit_card_id": card_id, "invoice_month": f"2026-{month:02d}",
                    "amount": "10.19" if month % 2 else "30.01", "type": kind, "reconciled_at": "yes"}
                   for card_id in (7, 8, 9) for month in range(1, 13) for kind in ("expense", "income", "expense")]
        charges += [{"credit_card_id": 7, "invoice_month": "2026-02", "amount": "1000", "type": "income", "reconciled_at": "yes"},
                    {"credit_card_id": 7, "invoice_month": "2026-03", "amount": "1000", "type": "expense"}]
        payments = [{"credit_card_id": 7, "invoice_month": "2026-01"}]
        for selected in (None, 1, 2):
            payload = build_balance_projection(accounts=accounts, transactions=transactions[::-1], cards=cards,
                card_transactions=charges, card_payments=payments, month="2026-08", account_id=selected)
            owners = [account for account in accounts if selected is None or account["id"] == selected]
            flags = {}
            for day, balances in payload["balances"].items():
                reconciled = account_totals_until(owners, transactions, day, reconciled_only=True)
                projected = account_totals_until(owners, transactions, day, reconciled_only=False)
                for account in owners:
                    reserved = preferred_card_forecast_for_account(account, cards, charges, payments, day)
                    projected[account["currency"]] -= reserved
                    if reserved:
                        flags[f"{account['id']}:{day}"] = True
                self.assertEqual(balances, {"reconciled": public_money_map(reconciled), "projected": public_money_map(projected)})
            self.assertEqual(payload["preferred_card_forecasts"], flags)

    def test_projection_scans_history_at_most_twice_and_invoices_once(self) -> None:
        from datetime import date, timedelta
        from unittest.mock import patch
        from financeiro.balance_projections import account_totals_until, card_transaction_delta_cents
        transactions = [{"account_id": 1, "type": "income", "amount": "1.01",
                         "date": (date(2020, 1, 1) + timedelta(days=index)).isoformat()} for index in range(2000)]
        charges = [{"credit_card_id": 7, "invoice_month": "2026-08", "type": "expense", "amount": "0.01", "reconciled_at": "yes"}] * 2000
        with patch("financeiro.balance_projections.account_totals_until", wraps=account_totals_until) as totals, \
             patch("financeiro.balance_projections.card_transaction_delta_cents", wraps=card_transaction_delta_cents) as delta:
            build_balance_projection(accounts=[{"id": 1}], transactions=transactions,
                cards=[{"id": 7, "preferred_payment_account_id": 1}], card_transactions=charges,
                card_payments=[], month="2026-08", account_id=1)
        self.assertLessEqual(sum(len(call.args[1]) for call in totals.call_args_list), 2 * len(transactions))
        self.assertEqual(delta.call_count, len(charges))

    def test_selected_account_keeps_incoming_transfers_and_ignores_other_accounts(self) -> None:
        payload = build_balance_projection(
            accounts=[{"id": 1, "currency": "BRL", "initial_balance": "1000"},
                      {"id": 2, "currency": "BRL", "initial_balance": "200"}],
            transactions=[
                {"account_id": 2, "destination_account_id": 1, "type": "transfer",
                 "amount": "50", "destination_amount": "50", "date": "2026-08-01", "reconciled_at": "yes"},
                {"account_id": 1, "type": "expense", "amount": "20",
                 "date": "2026-08-01", "reconciled_at": "yes"},
                {"account_id": 2, "type": "expense", "amount": "99",
                 "date": "2026-08-02", "reconciled_at": "yes"},
            ],
            cards=[{"id": 7, "preferred_payment_account_id": 2, "currency": "BRL", "due_day": 10}],
            card_transactions=[{"credit_card_id": 7, "type": "expense", "amount": "500",
                                "invoice_month": "2026-08", "reconciled_at": "yes"}],
            card_payments=[], month="2026-08", account_id=1,
        )
        self.assertEqual(payload["balances"]["2026-08-31"]["projected"]["BRL"], 1030)
        self.assertEqual(payload["balances"]["2026-08-31"]["reconciled"]["BRL"], 1030)
        self.assertNotIn("2026-08-02", payload["balances"])
        self.assertEqual(payload["currency_totals"], [])

    def test_selected_account_does_not_scan_unrelated_history_for_each_date(self) -> None:
        from unittest.mock import patch
        from financeiro.balance_projections import account_totals_until
        unrelated = [{"account_id": 2, "type": "expense", "amount": "1", "date": "2026-01-01"}] * 5000
        with patch("financeiro.balance_projections.account_totals_until", wraps=account_totals_until) as totals:
            build_balance_projection(
                accounts=[{"id": 1, "currency": "BRL", "initial_balance": "1000"}],
                transactions=unrelated, cards=[], card_transactions=[], card_payments=[],
                month="2026-08", account_id=1,
            )
        self.assertTrue(totals.called)
        self.assertTrue(all(call.args[1] == [] for call in totals.call_args_list))

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
