from __future__ import annotations

from datetime import date, timedelta
import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account, list_checking_accounts
from financeiro.auth import create_user
from financeiro.database import get_connection, initialize_database
from financeiro.transactions import create_transaction


class AccountBalanceListingTest(unittest.TestCase):
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

    def test_list_accounts_recalculates_foreign_currency_destination_balance(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        brl_account = create_checking_account(user["id"], {
            "name": "Conta BRL",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        usd_account = create_checking_account(user["id"], {
            "name": "Conta USD",
            "bank_name": "Corretora",
            "currency": "USD",
            "initial_balance": "0,00",
        })
        create_transaction(user["id"], {
            "type": "transfer",
            "description": "Cambio",
            "amount": "156,26",
            "destination_amount": "33,93",
            "transfer_exchange_rate": "0,217126",
            "date": "2026-07-15",
            "account_id": str(brl_account["id"]),
            "destination_account_id": str(usd_account["id"]),
        })

        with get_connection() as conn:
            conn.execute(
                """
                UPDATE checking_accounts
                SET current_balance_cents = ?
                WHERE id = ?
                """,
                (15626, usd_account["id"]),
            )

        accounts = list_checking_accounts(user["id"])
        listed_usd_account = next(account for account in accounts if account["id"] == usd_account["id"])

        self.assertEqual(listed_usd_account["currency"], "USD")
        self.assertEqual(listed_usd_account["current_balance"], "33.93")

    def test_list_accounts_ignores_future_transactions_in_current_balance(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta USD",
            "bank_name": "Corretora",
            "currency": "USD",
            "initial_balance": "2,26",
        })
        create_transaction(user["id"], {
            "type": "income",
            "description": "Dividendos",
            "amount": "31,67",
            "date": date.today().isoformat(),
            "account_id": str(account["id"]),
            "category": "Rendimentos",
        })
        create_transaction(user["id"], {
            "type": "income",
            "description": "Dividendos futuros",
            "amount": "122,33",
            "date": (date.today() + timedelta(days=30)).isoformat(),
            "account_id": str(account["id"]),
            "category": "Rendimentos",
        })

        accounts = list_checking_accounts(user["id"])
        listed_account = next(entry for entry in accounts if entry["id"] == account["id"])

        self.assertEqual(listed_account["stored_current_balance"], "156.26")
        self.assertEqual(listed_account["current_balance"], "33.93")

    def test_transfer_updates_destination_account_balance(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        source = create_checking_account(user["id"], {
            "name": "Origem",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "500,00",
        })
        destination = create_checking_account(user["id"], {
            "name": "Destino",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10,00",
        })

        create_transaction(user["id"], {
            "type": "transfer",
            "description": "Transferencia",
            "amount": "125,50",
            "date": date.today().isoformat(),
            "account_id": str(source["id"]),
            "destination_account_id": str(destination["id"]),
        })

        accounts = {account["id"]: account for account in list_checking_accounts(user["id"])}

        self.assertEqual(accounts[source["id"]]["current_balance"], "374.50")
        self.assertEqual(accounts[destination["id"]]["current_balance"], "135.50")


if __name__ == "__main__":
    unittest.main()
