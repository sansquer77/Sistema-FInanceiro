from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import initialize_database
from decimal import Decimal

from financeiro.portfolio import create_opening_position, get_portfolio_returns


class PortfolioReturnsTest(unittest.TestCase):
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

    def _mock_cdi(self) -> mock._patch:
        def side_effect(indexer, start_date, end_date, multiplier=None, force_refresh=False):
            if indexer != "CDI":
                return Decimal("1")
            days = max((end_date - start_date).days, 0)
            # Aproxima CDI a 12% a.a. para testes determinísticos
            rate = Decimal("0.12")
            multiplier_value = Decimal(multiplier) if multiplier else Decimal("1")
            return (Decimal("1") + rate * multiplier_value) ** (Decimal(days) / Decimal("365"))

        return mock.patch("financeiro.portfolio.fetch_accumulated_indexer_factor", side_effect=side_effect)

    def test_returns_series_is_empty_when_no_positions(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        result = get_portfolio_returns(user["id"])
        self.assertEqual(result["series"], [])
        self.assertIsNone(result["start_month"])
        self.assertFalse(result["has_historical_approximation"])

    def test_returns_contains_monthly_series_for_single_currency(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })
        with self._mock_cdi():
            create_opening_position(user["id"], {
                "account_id": str(account["id"]),
                "asset_type": "fixed_income",
                "asset_identifier": "CDB-TESTE",
                "asset_name": "CDB Teste",
                "acquisition_date": "2026-06-15",
                "quantity": "1",
                "unit_price": "1000,00",
                "total_cost": "1000,00",
                "fixed_income_mode": "post",
                "fixed_income_indexer": "CDI",
                "fixed_income_rate": "",
            })
            result = get_portfolio_returns(user["id"])

        self.assertTrue(len(result["series"]) >= 1)
        self.assertEqual(result["start_month"], "2026-06")
        currencies = {entry["currency"] for entry in result["series"]}
        self.assertEqual(currencies, {"BRL"})
        for entry in result["series"]:
            self.assertIn("portfolio_return_pct", entry)
            self.assertIn("cdi_return_pct", entry)

    def test_returns_separates_currencies(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        brl_account = create_checking_account(user["id"], {
            "name": "Carteira BRL",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })
        usd_account = create_checking_account(user["id"], {
            "name": "Carteira USD",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "USD",
            "initial_balance": "1000,00",
        })
        with self._mock_cdi():
            create_opening_position(user["id"], {
                "account_id": str(brl_account["id"]),
                "asset_type": "fixed_income",
                "asset_identifier": "CDB-BRL",
                "asset_name": "CDB BRL",
                "acquisition_date": "2026-06-15",
                "quantity": "1",
                "unit_price": "1000,00",
                "total_cost": "1000,00",
                "fixed_income_mode": "post",
                "fixed_income_indexer": "CDI",
                "fixed_income_rate": "",
            })
            create_opening_position(user["id"], {
                "account_id": str(usd_account["id"]),
                "asset_type": "other",
                "asset_identifier": "USD-ASSET",
                "asset_name": "USD Asset",
                "acquisition_date": "2026-06-15",
                "quantity": "1",
                "unit_price": "100,00",
                "total_cost": "100,00",
            })
            result = get_portfolio_returns(user["id"])

        currencies = {entry["currency"] for entry in result["series"]}
        self.assertEqual(currencies, {"BRL", "USD"})
        self.assertTrue(result["has_historical_approximation"])


if __name__ == "__main__":
    unittest.main()
