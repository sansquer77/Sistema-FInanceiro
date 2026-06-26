from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from financeiro import database
import financeiro.imports as imports_module
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import get_connection, initialize_database
from financeiro.imports import import_system_template


class SystemTemplateImportTest(unittest.TestCase):
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

    def test_import_uses_row_savepoints_and_keeps_partial_success_behavior(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        csv_bytes = "\n".join([
            "data;tipo;descricao;valor;categoria",
            "2026-06-01;expense;Linha 1;10,00;Mercado",
            "2026-06-02;expense;Linha 2;20,00;Mercado",
            "2026-06-03;expense;Linha 3;30,00;Mercado",
        ]).encode("utf-8")
        original_create = imports_module.create_transaction_with_conn
        call_count = 0

        def create_then_fail_second_row(conn, user_id, payload):
            nonlocal call_count
            call_count += 1
            created = original_create(conn, user_id, payload)
            if call_count == 2:
                raise RuntimeError("Falha simulada depois da insercao.")
            return created

        with mock.patch(
            "financeiro.imports.create_transaction_with_conn",
            side_effect=create_then_fail_second_row,
        ):
            result = import_system_template(user["id"], "account", account["id"], csv_bytes, "modelo.csv")

        with get_connection() as conn:
            transaction_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            balance = conn.execute(
                "SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                (account["id"],),
            ).fetchone()["current_balance_cents"]

        self.assertEqual(result["imported"], 2)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(transaction_count, 2)
        self.assertEqual(balance, 96000)


if __name__ == "__main__":
    unittest.main()
