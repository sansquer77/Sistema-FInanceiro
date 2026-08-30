from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import get_connection, initialize_database
from financeiro.portfolio import create_opening_position, get_portfolio, redeem_position


class PortfolioQuantityRedemptionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-redemptions.db"
        initialize_database()
        self.user = create_user("Alice", "alice@example.com", "correct-password")
        self.account = create_checking_account(self.user["id"], {
            "name": "Coinbase", "bank_name": "Coinbase", "account_type": "investment",
            "currency": "BRL", "initial_balance": "0,00",
        })

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def add_lot(self, acquisition_date: str, quantity: str, total_cost: str) -> None:
        create_opening_position(self.user["id"], {
            "account_id": self.account["id"], "asset_type": "stablecoin",
            "asset_identifier": "USDC", "asset_name": "USD Coin",
            "acquisition_date": acquisition_date, "quantity": quantity,
            "total_cost": total_cost,
        })

    def test_quantity_redemption_consumes_oldest_lot_and_credits_net_amount(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.39 — critérios 55-58
        self.add_lot("2026-01-10", "100", "500,00")
        self.add_lot("2026-02-10", "100", "600,00")

        result = redeem_position(self.user["id"], {
            "account_id": self.account["id"], "currency": "BRL",
            "asset_type": "stablecoin", "asset_identifier": "USDC", "asset_name": "USD Coin",
            "date": "2026-08-29", "quantity": "120", "unit_price": "5,50",
            "gross_amount": "660,00", "fees": "10,00", "amount": "650,00",
        })

        position = next(item for item in result["positions"] if item["asset_identifier"] == "USDC")
        self.assertEqual(position["quantity"], "80")
        self.assertEqual(position["total_cost"], "480.00")
        with get_connection() as conn:
            redemptions = conn.execute(
                "SELECT redeemed_quantity_micros, redeemed_cost_cents FROM investment_redemptions ORDER BY id"
            ).fetchall()
            transaction = conn.execute("SELECT amount_cents FROM transactions WHERE type = 'income'").fetchone()
            balance = conn.execute("SELECT current_balance_cents FROM checking_accounts WHERE id = ?", (self.account["id"],)).fetchone()[0]
        self.assertEqual([(row[0], row[1]) for row in redemptions], [(100_000_000, 50_000), (20_000_000, 12_000)])
        self.assertEqual(transaction[0], 65_000)
        self.assertEqual(balance, 65_000)


if __name__ == "__main__":
    unittest.main()
