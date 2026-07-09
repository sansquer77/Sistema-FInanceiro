from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import initialize_database
from financeiro.operation_logs import create_operation_log, get_operation_log, list_operation_logs
from financeiro.transactions import create_transaction


class OperationLogsTest(unittest.TestCase):
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

    def test_operation_log_is_isolated_by_user_and_filterable(self) -> None:
        owner = create_user("Alice", "alice@example.com", "correct-password")
        other = create_user("Bob", "bob@example.com", "correct-password")
        account = create_checking_account(owner["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "100,00",
        })
        transaction = create_transaction(owner["id"], {
            "type": "expense",
            "description": "Mercado",
            "amount": "25,00",
            "date": "2026-07-01",
            "account_id": str(account["id"]),
            "category": "Alimentacao",
        })
        create_operation_log(
            owner["id"],
            module="transactions",
            operation_type="create",
            entity_type="transaction",
            entity_id=transaction["id"],
            account_id=account["id"],
            description="Lancamento criado: Mercado",
            metadata={"password": "secret", "amount": transaction["amount"]},
        )
        create_operation_log(
            other["id"],
            module="transactions",
            operation_type="create",
            entity_type="transaction",
            description="Lancamento criado: Outro usuario",
        )

        response = list_operation_logs(owner["id"], {"module": "transactions", "q": "mercado"})

        self.assertEqual(len(response["logs"]), 1)
        log = response["logs"][0]
        self.assertEqual(log["user_id"], owner["id"])
        self.assertEqual(log["user_name"], "Alice")
        self.assertEqual(log["user_email"], "alice@example.com")
        self.assertEqual(log["account_id"], account["id"])
        self.assertEqual(log["account_name"], "Conta principal")
        self.assertEqual(log["metadata"]["amount"], transaction["amount"])
        self.assertNotIn("password", log["metadata"])

    def test_get_operation_log_requires_owner(self) -> None:
        owner = create_user("Alice", "alice@example.com", "correct-password")
        other = create_user("Bob", "bob@example.com", "correct-password")
        log = create_operation_log(
            owner["id"],
            module="accounts",
            operation_type="create",
            entity_type="account",
            description="Conta criada",
        )

        with self.assertRaises(Exception):
            get_operation_log(other["id"], log["id"])
