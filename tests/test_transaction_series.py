from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import financeiro.transactions as transactions_module
from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import initialize_database
from financeiro.transactions import create_transaction, list_transactions, update_transaction


class TransactionSeriesUpdateTest(unittest.TestCase):
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

    def test_future_series_update_reuses_invariant_lookups(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        first = create_transaction(user["id"], {
            "type": "expense",
            "description": "Assinatura",
            "amount": "10,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "tags": "Recorrente",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "recurrence_count": "5",
        })

        with (
            mock.patch(
                "financeiro.transactions.get_active_account",
                wraps=transactions_module.get_active_account,
            ) as get_active_account,
            mock.patch(
                "financeiro.transactions.resolve_transaction_category",
                wraps=transactions_module.resolve_transaction_category,
            ) as resolve_transaction_category,
            mock.patch(
                "financeiro.transactions.get_or_create_tag",
                wraps=transactions_module.get_or_create_tag,
            ) as get_or_create_tag,
        ):
            update_transaction(user["id"], str(first["id"]), {
                "type": "expense",
                "description": "Assinatura atualizada",
                "amount": "20,00",
                "date": "2026-01-12",
                "account_id": str(account["id"]),
                "category": "Servicos",
                "tags": "Recorrente",
                "apply_to_future": "true",
            })

        transactions = list_transactions(user["id"], account_id=account["id"])

        self.assertEqual(len(transactions), 5)
        self.assertTrue(all(row["amount"] == "20.00" for row in transactions))
        self.assertLessEqual(get_active_account.call_count, 2)
        self.assertLessEqual(resolve_transaction_category.call_count, 2)
        self.assertLessEqual(get_or_create_tag.call_count, 2)


if __name__ == "__main__":
    unittest.main()
