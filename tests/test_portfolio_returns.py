from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
from unittest import mock

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import initialize_database

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

    def _mock_benchmarks(self) -> mock._patch:
        def side_effect(indexer, start_date, end_date, multiplier=None, force_refresh=False):
            days = max((end_date - start_date).days, 0)
            rate = Decimal("0.1200")
            if indexer == "CDI":
                rate = Decimal("0.12")
            elif indexer == "IPCA":
                rate = Decimal("0.05")
            else:
                return Decimal("1")
            multiplier_value = Decimal(multiplier) if multiplier else Decimal("1")
            return (Decimal("1") + rate * multiplier_value) ** (Decimal(days) / Decimal("365"))

        return mock.patch("financeiro.portfolio.fetch_accumulated_indexer_factor", side_effect=side_effect)

    def _create_fixed_position(self, user_id, account_id, name, cost, mode="post", indexer="CDI"):
        create_opening_position(user_id, {
            "account_id": str(account_id),
            "asset_type": "fixed_income",
            "asset_identifier": name,
            "asset_name": name,
            "acquisition_date": "2026-06-15",
            "quantity": "1",
            "unit_price": cost,
            "total_cost": cost,
            "fixed_income_mode": mode,
            "fixed_income_indexer": indexer,
            "fixed_income_rate": "",
        })

    def test_returns_series_is_empty_when_no_positions(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        result = get_portfolio_returns(user["id"])
        self.assertEqual(result["series"], [])
        self.assertIsNone(result["start_month"])
        self.assertFalse(result["has_historical_approximation"])

    def test_returns_monthly_series_per_currency_with_benchmarks(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })
        with self._mock_benchmarks():
            self._create_fixed_position(user["id"], account["id"], "CDB-TESTE", "1000,00")
            result = get_portfolio_returns(user["id"])

        self.assertTrue(len(result["series"]) >= 1)
        self.assertEqual(result["start_month"], "2026-06")
        for entry in result["series"]:
            self.assertIn("month", entry)
            self.assertIn("BRL_return_pct", entry)
            self.assertIn("cdi_return_pct", entry)
            self.assertIn("ipca_return_pct", entry)
        self.assertGreater(result["series"][-1]["cdi_return_pct"], 0)
        self.assertGreater(result["series"][-1]["ipca_return_pct"], 0)

    def test_series_has_brl_and_usd_lines_when_both_currencies(self) -> None:
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
        with self._mock_benchmarks():
            self._create_fixed_position(user["id"], brl_account["id"], "CDB-BRL", "1000,00")
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

        # Um registro por mês, com retornos por moeda e benchmarks
        for entry in result["series"]:
            self.assertIn("BRL_return_pct", entry)
            self.assertIn("USD_return_pct", entry)
            self.assertGreater(entry["cdi_return_pct"], 0)
            self.assertGreater(entry["ipca_return_pct"], 0)
        months = [entry["month"] for entry in result["series"]]
        self.assertEqual(len(set(months)), len(months))
        self.assertTrue(result["has_historical_approximation"])

    def test_first_month_is_baseline_per_currency(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })
        with self._mock_benchmarks():
            self._create_fixed_position(user["id"], account["id"], "CDB-TESTE", "1000,00")
            result = get_portfolio_returns(user["id"])

        self.assertEqual(result["series"][0]["BRL_return_pct"], 0.0)
        self.assertTrue(len(result["series"]) >= 1)


if __name__ == "__main__":
    unittest.main()