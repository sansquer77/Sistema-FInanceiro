from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.categories import create_category
from financeiro.database import initialize_database
from financeiro.simulations import simulate_butterfly_effect
from financeiro.spending_limits import create_spending_limit
from financeiro.transactions import create_transaction


class ButterflyEffectSimulationTest(unittest.TestCase):
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

    def test_single_expense_reduces_account_balance_without_persisting(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        category = create_category(user["id"], "Serviços", "expense")

        response = simulate_butterfly_effect(user["id"], {
            "type": "expense",
            "amount": "250,00",
            "date": "2026-01-15",
            "description": "Despesa simulada",
            "account_id": str(account["id"]),
            "category_id": str(category["id"]),
            "series_kind": "single",
        })

        self.assertEqual(response["account_impact"]["projected_balance_cents"], 75000)
        self.assertEqual(response["account_impact"]["difference_cents"], -25000)
        self.assertEqual(len(response["virtual_items"]), 1)
        self.assertEqual(response["virtual_items"][0]["impact_cents"], -25000)

    def test_installment_series_creates_virtual_items_and_limit_impact(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        category = create_category(user["id"], "Supermercado", "expense")
        create_spending_limit(user["id"], {
            "month": "2026-01",
            "category_id": str(category["id"]),
            "limit_amount": "100,00",
        })
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Compra real",
            "amount": "100,00",
            "date": "2026-01-03",
            "account_id": str(account["id"]),
            "category": "Supermercado",
        })

        response = simulate_butterfly_effect(user["id"], {
            "type": "expense",
            "amount": "1200,00",
            "date": "2026-01-10",
            "description": "Parcelado",
            "account_id": str(account["id"]),
            "category_id": str(category["id"]),
            "series_kind": "installment",
            "installment_count": 12,
        })

        self.assertEqual(len(response["virtual_items"]), 12)
        self.assertEqual(response["virtual_items"][0]["impact_cents"], -10000)
        self.assertEqual(response["limit_impact"]["items"][0]["projected_spent_cents"], 20000)
        self.assertTrue(any("ultrapassado" in warning.lower() for warning in response["warnings"]))


if __name__ == "__main__":
    unittest.main()
