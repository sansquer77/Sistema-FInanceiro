from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import get_connection, initialize_database
from financeiro.portfolio import create_opening_position, get_portfolio, redeem_position, update_position_value_override


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
        # spec: investimentos/investimentos-portfolio v2.63 — critérios 55-58
        self.add_lot("2026-01-10", "100", "500,00")
        self.add_lot("2026-02-10", "100", "600,00")

        result = redeem_position(self.user["id"], {
            "account_id": self.account["id"], "currency": "BRL",
            "asset_type": "stablecoin", "asset_identifier": "USDC", "asset_name": "USD Coin",
            "date": "2026-08-29", "quantity": "120", "unit_price": "5,50",
            "gross_amount": "660,00", "fees": "10,00", "amount": "650,00",
        })

        position = next(item for item in result["positions"] if item["asset_identifier"] == "USDC")
        self.assertEqual(position["quantity"], "80.00000000")
        self.assertEqual(position["total_cost"], "480.00")
        history = result["redemption_history"][0]
        self.assertEqual(history["redeemed_quantity"], "120.00000000")
        self.assertEqual(history["gross_value"], "660.00")
        self.assertEqual(history["fees"], "10.00")
        self.assertEqual(history["net_value"], "650.00")
        self.assertEqual(history["redeemed_cost"], "620.00")
        self.assertEqual(history["realized_result"], "30.00")
        self.assertEqual(history["remaining_quantity"], "80.00000000")
        self.assertEqual(history["remaining_cost"], "480.00")
        with get_connection() as conn:
            redemptions = conn.execute(
                "SELECT redeemed_quantity_micros, redeemed_cost_cents FROM investment_redemptions ORDER BY id"
            ).fetchall()
            transaction = conn.execute("SELECT amount_cents FROM transactions WHERE type = 'income'").fetchone()
            balance = conn.execute("SELECT current_balance_cents FROM checking_accounts WHERE id = ?", (self.account["id"],)).fetchone()[0]
        self.assertEqual([(row[0], row[1]) for row in redemptions], [(10_000_000_000, 50_000), (2_000_000_000, 12_000)])
        self.assertEqual(transaction[0], 65_000)
        self.assertEqual(balance, 65_000)

    def test_eth_redemption_preserves_eight_decimals_and_manual_value_residual(self) -> None:
        create_opening_position(self.user["id"], {
            "account_id": self.account["id"], "asset_type": "crypto",
            "asset_identifier": "ETH", "asset_name": "Ethereum",
            "acquisition_date": "2026-06-20", "quantity": "0,02865320",
            "total_cost": "309,53",
        })
        update_position_value_override(self.user["id"], {
            "account_id": self.account["id"], "asset_type": "crypto",
            "asset_identifier": "ETH", "asset_name": "Ethereum",
            "current_value": "364,30", "quote_date": "2026-09-11",
        })
        portfolio = get_portfolio(self.user["id"])
        eth = next(item for item in portfolio["positions"] if item["asset_identifier"] == "ETH")

        self.assertEqual(eth["quantity"], "0.02865320")
        self.assertEqual(eth["redemption_quantity"], "0.0286532")
        with get_connection() as conn:
            stored_quantity = conn.execute(
                "SELECT quantity_micros FROM investment_opening_positions WHERE asset_identifier = 'ETH'"
            ).fetchone()[0]
        self.assertEqual(stored_quantity, 2_865_320)

        result = redeem_position(self.user["id"], {
            "account_id": self.account["id"], "currency": "BRL",
            "asset_type": "crypto", "asset_identifier": "ETH", "asset_name": "Ethereum",
            "date": "2026-09-11", "quantity": "0,02864854",
            "gross_amount": "364,24", "amount": "364,24", "fees": "0,00",
        })

        remaining = next(item for item in result["positions"] if item["asset_identifier"] == "ETH")
        self.assertEqual(remaining["quantity"], "0.00000466")
        self.assertEqual(remaining["current_value"], "0.06")
        self.assertEqual(result["redemption_history"][0]["redeemed_quantity"], "0.02864854")
        self.assertEqual(result["redemption_history"][0]["remaining_quantity"], "0.00000466")
        with get_connection() as conn:
            redeemed_quantity = conn.execute(
                "SELECT redeemed_quantity_micros FROM investment_redemptions"
            ).fetchone()[0]
            manual_value = conn.execute(
                "SELECT current_value_cents FROM investment_value_overrides WHERE user_id = ?",
                (self.user["id"],),
            ).fetchone()[0]
            credited_amount = conn.execute(
                "SELECT amount_cents FROM transactions WHERE type = 'income'"
            ).fetchone()[0]
        self.assertEqual(redeemed_quantity, 2_864_854)
        self.assertEqual(manual_value, 6)
        self.assertEqual(credited_amount, 36_424)

    def test_manual_value_uses_gross_redemption_while_account_receives_net(self) -> None:
        self.add_lot("2026-01-10", "100", "500,00")
        update_position_value_override(self.user["id"], {
            "account_id": self.account["id"], "asset_type": "stablecoin",
            "asset_identifier": "USDC", "asset_name": "USD Coin",
            "current_value": "660,00", "quote_date": "2026-09-11",
        })

        result = redeem_position(self.user["id"], {
            "account_id": self.account["id"], "currency": "BRL",
            "asset_type": "stablecoin", "asset_identifier": "USDC", "asset_name": "USD Coin",
            "date": "2026-09-11", "quantity": "50", "gross_amount": "330,00",
            "fees": "10,00", "amount": "320,00",
        })

        position = next(item for item in result["positions"] if item["asset_identifier"] == "USDC")
        self.assertEqual(position["current_value"], "330.00")
        with get_connection() as conn:
            manual_value = conn.execute(
                "SELECT current_value_cents FROM investment_value_overrides WHERE user_id = ?",
                (self.user["id"],),
            ).fetchone()[0]
            balance = conn.execute(
                "SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                (self.account["id"],),
            ).fetchone()[0]
        self.assertEqual(manual_value, 33_000)
        self.assertEqual(balance, 32_000)


if __name__ == "__main__":
    unittest.main()
