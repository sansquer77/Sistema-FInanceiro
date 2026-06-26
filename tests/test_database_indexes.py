from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.database import get_connection, initialize_database


class DatabaseIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_initialize_database_creates_high_volume_navigation_indexes(self) -> None:
        initialize_database()

        with get_connection() as conn:
            transaction_indexes = index_names(conn, "transactions")
            card_transaction_indexes = index_names(conn, "credit_card_transactions")
            card_payment_indexes = index_names(conn, "credit_card_payments")

        self.assertIn("idx_transactions_user_account_date", transaction_indexes)
        self.assertIn("idx_transactions_user_destination_date", transaction_indexes)
        self.assertIn("idx_transactions_user_series_date", transaction_indexes)
        self.assertIn("idx_credit_card_transactions_user_card_invoice_date", card_transaction_indexes)
        self.assertIn("idx_credit_card_transactions_user_invoice_date", card_transaction_indexes)
        self.assertIn("idx_credit_card_transactions_user_series_invoice_date", card_transaction_indexes)
        self.assertIn("idx_credit_card_payments_user_card_invoice", card_payment_indexes)
        self.assertIn("idx_credit_card_payments_user_date", card_payment_indexes)

    def test_get_connection_closes_after_context_exit(self) -> None:
        initialize_database()

        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()

        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1").fetchone()


def index_names(conn, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA index_list({table_name})")}


if __name__ == "__main__":
    unittest.main()
