from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
from unittest import mock

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import get_connection, initialize_database
from financeiro.portfolio_snapshots import list_snapshots, upsert_snapshots

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
        self.assertEqual(result["start_month"], "2026-01")
        for entry in result["series"]:
            self.assertIn("month", entry)
            self.assertIn("BRL_return_pct", entry)
            self.assertIn("cdi_return_pct", entry)
            self.assertIn("ipca_return_pct", entry)
        observed = [entry for entry in result["series"] if entry["month"] <= "2026-09"][-1]
        self.assertGreater(observed["cdi_return_pct"], 0)
        self.assertGreater(observed["ipca_return_pct"], 0)

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
        with self._mock_benchmarks(), mock.patch(
            "financeiro.portfolio.get_exchange_rate_to_brl", return_value=Decimal("5.400000")
        ):
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
            if entry["month"] <= "2026-09":
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

    def test_first_snapshot_does_not_treat_historical_stock_as_current_month_contribution(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira", "bank_name": "Banco", "account_type": "investment",
            "currency": "BRL", "initial_balance": "10000,00",
        })
        self._create_fixed_position(user["id"], account["id"], "CDB-HISTORICO", "1000,00")

        with self._mock_benchmarks():
            result = get_portfolio_returns(user["id"])

        with get_connection() as conn:
            september = list_snapshots(conn, user["id"], snapshot_month="2026-09")
        self.assertEqual(sum(row["contribution_cents"] for row in september), 0)
        september_return = next(row for row in result["series"] if row["month"] == "2026-09")
        self.assertGreater(september_return["BRL_return_pct"], -10)

    def test_snapshot_consolidates_multiple_lots_of_the_same_asset(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira", "bank_name": "Banco", "account_type": "investment",
            "currency": "BRL", "initial_balance": "10000,00",
        })
        self._create_fixed_position(user["id"], account["id"], "CDB-REPETIDO", "1000,00")
        self._create_fixed_position(user["id"], account["id"], "CDB-REPETIDO", "500,00")

        with self._mock_benchmarks():
            get_portfolio_returns(user["id"])

        with get_connection() as conn:
            rows = list_snapshots(conn, user["id"], snapshot_month="2026-09")
        repeated = [row for row in rows if row["asset_identifier"] == "CDB-REPETIDO"]
        self.assertEqual(len(repeated), 1)
        self.assertEqual(repeated[0]["cost_basis_cents"], 150_000)
        self.assertEqual(repeated[0]["quantity_micros"], 2_000_000)

    def test_persisted_snapshots_override_approximation_and_report_coverage(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira", "bank_name": "Banco", "account_type": "investment",
            "currency": "BRL", "initial_balance": "10000,00",
        })
        self._create_fixed_position(user["id"], account["id"], "CDB-TESTE", "1000,00")
        base = {
            "user_id": user["id"], "account_id": account["id"], "currency": "BRL",
            "asset_type": "fixed_income", "asset_identifier": "CDB-TESTE", "asset_name": "CDB-TESTE",
            "quantity_micros": 1_000_000, "unit_price_cents": 100_000,
            "cost_basis_cents": 100_000, "contribution_cents": 0, "redemption_cents": 0,
            "dividend_cents": 0, "quote_source": "CDI", "valuation_status": "observed",
        }
        with get_connection() as conn:
            upsert_snapshots(conn, [
                {**base, "snapshot_month": "2026-07", "as_of_date": "2026-07-31", "market_value_cents": 100_000},
                {**base, "snapshot_month": "2026-08", "as_of_date": "2026-08-31", "market_value_cents": 110_000},
            ])

        with self._mock_benchmarks():
            result = get_portfolio_returns(user["id"])

        august = next(entry for entry in result["series"] if entry["month"] == "2026-08")
        self.assertEqual(august["BRL_return_pct"], 10.0)
        self.assertEqual(result["snapshot_coverage"]["observed_months"], ["2026-07", "2026-08", "2026-09"])
        self.assertNotIn("2026-10", result["snapshot_coverage"]["approximate_months"])
        self.assertIn("2026-10", result["snapshot_coverage"]["future_months"])
        self.assertEqual(result["snapshot_coverage"]["coverage_percent"], 33.33)

    def test_approximate_snapshot_is_not_reported_as_observed(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira", "bank_name": "Banco", "account_type": "investment",
            "currency": "USD", "initial_balance": "1000,00",
        })
        create_opening_position(user["id"], {
            "account_id": str(account["id"]), "asset_type": "other", "asset_identifier": "USD-ASSET",
            "asset_name": "USD Asset", "acquisition_date": "2026-06-15", "quantity": "1",
            "unit_price": "100,00", "total_cost": "100,00", "exchange_rate": "5,00",
        })
        with get_connection() as conn:
            upsert_snapshots(conn, [{
                "user_id": user["id"], "snapshot_month": "2026-08", "as_of_date": "2026-08-31",
                "account_id": account["id"], "currency": "USD", "asset_type": "other",
                "asset_identifier": "USD-ASSET", "asset_name": "USD Asset", "market_value_cents": 10_000,
                "cost_basis_cents": 10_000, "quote_source": "current_value", "valuation_status": "approximate",
            }])
        with self._mock_benchmarks():
            result = get_portfolio_returns(user["id"])

        self.assertNotIn("2026-08", result["snapshot_coverage"]["observed_months"])
        self.assertIn("2026-08", result["snapshot_coverage"]["approximate_months"])

    def test_position_factors_are_cached_by_month_across_positions(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        def cdi_segments() -> set[tuple]:
            return {
                (str(call.args[1]), str(call.args[2]))
                for call in benchmark_mock.call_args_list
                if str(call.args[0]) == "CDI"
            }

        # Linha de base: uma posicao.
        with self._mock_benchmarks() as benchmark_mock:
            self._create_fixed_position(user["id"], account["id"], "CDB-A", "1000,00")
            result = get_portfolio_returns(user["id"])
        segments_one = cdi_segments()
        self.assertTrue(len(result["series"]) >= 1)

        # Segunda posicao com a mesma data de aquisicao: o cache mensal
        # compartilhado impede a duplicacao de fetches BCB por posicao.
        with self._mock_benchmarks() as benchmark_mock:
            self._create_fixed_position(user["id"], account["id"], "CDB-B", "500,00")
            result = get_portfolio_returns(user["id"])
        segments_two = cdi_segments()

        self.assertTrue(len(result["series"]) >= 1)
        self.assertEqual(segments_two, segments_one)


if __name__ == "__main__":
    unittest.main()
