from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import AppHandler
from financeiro import database
from financeiro.accounts import create_checking_account, list_checking_accounts
from financeiro.auth import create_user
from financeiro.balance_projections import build_balance_projection, build_currency_totals_for_user
from financeiro.credit_cards import (
    create_credit_card,
    list_credit_card_payments,
    list_credit_card_transactions,
)
from financeiro.transactions import list_transactions


class CockpitCurrencyTotalsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"
        database.initialize_database()
        self.user = create_user("Alice", "alice@example.com", "correct-password")
        self.account = create_checking_account(self.user["id"], {
            "name": "Conta", "bank_name": "Banco", "currency": "BRL", "initial_balance": "1000,00",
        })
        self.card = create_credit_card(self.user["id"], {
            "name": "Cartão", "issuer": "Banco", "currency": "BRL", "limit": "5000,00",
            "closing_day": "20", "due_day": "10", "preferred_payment_account_id": str(self.account["id"]),
        })

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_sql_aggregates_match_existing_projection_contract(self) -> None:
        with database.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, amount_cents, date, account_id, reconciled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (self.user["id"], "income", "Receita", 10000, "2026-08-01", self.account["id"], "2026-08-01"),
                    (self.user["id"], "expense", "Despesa prevista", 5000, "2026-08-02", self.account["id"], None),
                ],
            )
            conn.executemany(
                """
                INSERT INTO credit_card_transactions (
                    user_id, credit_card_id, type, description, amount_cents, date, invoice_month, reconciled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (self.user["id"], self.card["id"], "expense", "Fatura atual", 20000,
                     "2026-08-01", "2026-08", "2026-08-01"),
                    (self.user["id"], self.card["id"], "expense", "Fatura anterior", 3000,
                     "2026-07-01", "2026-07", "2026-07-01"),
                ],
            )

        expected = build_balance_projection(
            accounts=list_checking_accounts(self.user["id"]),
            transactions=list_transactions(self.user["id"]),
            cards=[self.card],
            card_transactions=list_credit_card_transactions(self.user["id"]),
            card_payments=list_credit_card_payments(self.user["id"]),
            month="2026-08",
        )["currency_totals"]

        self.assertEqual(build_currency_totals_for_user(self.user["id"], "2026-08"), expected)

    def test_cockpit_handler_does_not_call_detailed_history_readers(self) -> None:
        handler = mock.Mock()
        handler.path = "/api/cockpit?month=2026-08"
        handler.require_user.return_value = {"id": self.user["id"]}
        currency_totals = [{"currency": "BRL", "current": 1000.0, "accounts": [], "cards": []}]
        with (
            mock.patch("app.build_cockpit_summary", return_value={"month_totals": {}}),
            mock.patch("app.build_currency_totals_for_user", return_value=currency_totals) as aggregate,
            mock.patch("app.get_open_debts", return_value={"groups": []}),
            mock.patch("app.list_transactions", side_effect=AssertionError("histórico de contas")),
            mock.patch("app.list_credit_card_transactions", side_effect=AssertionError("histórico de cartões")),
            mock.patch("app.list_credit_card_payments", side_effect=AssertionError("histórico de pagamentos")),
        ):
            AppHandler.handle_cockpit(handler)

        aggregate.assert_called_once_with(self.user["id"], "2026-08")
        self.assertEqual(handler.send_json.call_args.args[0]["currency_totals"], currency_totals)


if __name__ == "__main__":
    unittest.main()
