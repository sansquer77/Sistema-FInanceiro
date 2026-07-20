from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import get_connection, initialize_database
from financeiro.portfolio import close_position, create_opening_position


class PortfolioClosingCreditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"
        initialize_database()

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def create_position(self) -> tuple[dict, dict]:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        create_opening_position(user["id"], {
            "account_id": str(account["id"]),
            "asset_type": "other",
            "asset_identifier": "CDB-TESTE",
            "asset_name": "CDB Teste",
            "acquisition_date": "2026-01-10",
            "quantity": "1",
            "unit_price": "100,00",
            "total_cost": "100,00",
        })
        return user, account

    def test_close_position_without_credit_does_not_create_income_transaction(self) -> None:
        user, account = self.create_position()

        close_position(user["id"], {
            "account_id": str(account["id"]),
            "currency": "BRL",
            "asset_type": "other",
            "asset_identifier": "CDB-TESTE",
            "asset_name": "CDB Teste",
            "closing_value": "123,45",
            "date": "2026-07-20",
        })

        with get_connection() as conn:
            transaction_count = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
                (user["id"],),
            ).fetchone()[0]
            balance = conn.execute(
                "SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                (account["id"],),
            ).fetchone()[0]

        self.assertEqual(transaction_count, 0)
        self.assertEqual(balance, 100000)

    def test_close_position_with_credit_creates_income_transaction_and_updates_balance(self) -> None:
        user, account = self.create_position()

        close_position(user["id"], {
            "account_id": str(account["id"]),
            "currency": "BRL",
            "asset_type": "other",
            "asset_identifier": "CDB-TESTE",
            "asset_name": "CDB Teste",
            "closing_value": "123,45",
            "date": "2026-07-20",
            "register_credit": "true",
        })

        with get_connection() as conn:
            transaction = conn.execute(
                """
                SELECT type, description, amount_cents, account_id
                FROM transactions
                WHERE user_id = ?
                """,
                (user["id"],),
            ).fetchone()
            balance = conn.execute(
                "SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                (account["id"],),
            ).fetchone()[0]

        self.assertEqual(transaction["type"], "income")
        self.assertEqual(transaction["description"], "Encerramento - CDB Teste")
        self.assertEqual(transaction["amount_cents"], 12345)
        self.assertEqual(transaction["account_id"], account["id"])
        self.assertEqual(balance, 112345)


if __name__ == "__main__":
    unittest.main()
