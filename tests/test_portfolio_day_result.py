from __future__ import annotations

import tempfile
import unittest
from datetime import date as real_date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from unittest import mock

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import initialize_database

from financeiro.portfolio import create_opening_position, get_portfolio


def _frozen_today(iso_date: str) -> mock._patch:
    fixed = real_date.fromisoformat(iso_date)

    class _FrozenDate(real_date):
        @classmethod
        def today(cls):
            return real_date(fixed.year, fixed.month, fixed.day)

    return mock.patch("financeiro.portfolio.date", _FrozenDate)


def _business_days(start: date, end: date) -> int:
    return sum(1 for offset in range((end - start).days + 1) if (start + timedelta(days=offset)).weekday() < 5)


def _indexer_factor_mock(indexer: str, start_date: real_date, end_date: real_date, multiplier=None, force_refresh=False) -> Decimal:
    if indexer == "TR" or start_date >= end_date:
        return Decimal("1")
    if indexer not in {"CDI", "SELIC", "IPCA", "IGP-M"}:
        return Decimal("1")
    rate = Decimal("0.12")
    multiplier_value = Decimal(multiplier) if multiplier else Decimal("1")
    return (Decimal("1") + rate * multiplier_value) ** (Decimal(_business_days(start_date, end_date)) / Decimal("252"))


def _indexer_rate_mock(indexer: str, force_refresh=False) -> Decimal:
    if indexer == "SELIC":
        return Decimal("0.15")
    return Decimal("0.12")


class PortfolioDayResultTest(unittest.TestCase):
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

    def _create_user_and_account(self) -> tuple[dict, int]:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Carteira",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })
        return user, account["id"]

    def _fixed_position(self, user_id: int, account_id: int, acquisition_date: str) -> None:
        create_opening_position(user_id, {
            "account_id": str(account_id),
            "asset_type": "fixed_income",
            "asset_identifier": "CDB-TESTE",
            "asset_name": "CDB Teste",
            "acquisition_date": acquisition_date,
            "quantity": "1",
            "unit_price": "1000,00",
            "total_cost": "1000,00",
            "fixed_income_mode": "post",
            "fixed_income_indexer": "CDI",
            "fixed_income_rate": "",
        })

    def _expected_fixed_value(self, cost_cents: int, acquisition: date, as_of: date) -> int:
        factor = _indexer_factor_mock("CDI", acquisition, as_of)
        return int((Decimal(cost_cents) * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def test_fixed_income_day_result_is_daily_accrual_on_business_day(self) -> None:
        user, account_id = self._create_user_and_account()
        with _frozen_today("2026-08-10"):
            self._fixed_position(user["id"], account_id, "2026-06-15")
            with mock.patch("financeiro.portfolio.fetch_accumulated_indexer_factor", side_effect=_indexer_factor_mock):
                portfolio = get_portfolio(user["id"])

        position = portfolio["positions"][0]
        expected_current = self._expected_fixed_value(100_000, real_date(2026, 6, 15), real_date(2026, 8, 10))
        expected_previous = self._expected_fixed_value(100_000, real_date(2026, 6, 15), real_date(2026, 8, 9))
        self.assertEqual(position["current_value_cents"], expected_current)
        self.assertEqual(position["day_result_cents"], expected_current - expected_previous)
        self.assertGreater(position["day_result_cents"], 0)
        self.assertEqual(position["day_result_brl_cents"], position["day_result_cents"])

    def test_indexer_position_has_zero_day_result_on_weekend(self) -> None:
        user, account_id = self._create_user_and_account()
        with _frozen_today("2026-08-08"):
            self._fixed_position(user["id"], account_id, "2026-06-15")
            with mock.patch("financeiro.portfolio.fetch_accumulated_indexer_factor", side_effect=_indexer_factor_mock):
                portfolio = get_portfolio(user["id"])

        position = portfolio["positions"][0]
        self.assertGreater(position["current_value_cents"], position["total_cost_cents"])
        self.assertEqual(position["day_result_cents"], 0)
        self.assertEqual(position["day_result_brl_cents"], 0)

    def test_fixed_income_day_result_is_zero_on_acquisition_date(self) -> None:
        user, account_id = self._create_user_and_account()
        with _frozen_today("2026-08-10"):
            self._fixed_position(user["id"], account_id, "2026-08-10")
            with mock.patch("financeiro.portfolio.fetch_accumulated_indexer_factor", side_effect=_indexer_factor_mock):
                portfolio = get_portfolio(user["id"])

        position = portfolio["positions"][0]
        self.assertEqual(position["current_value_cents"], position["total_cost_cents"])
        self.assertEqual(position["day_result_cents"], 0)

    def test_savings_day_result_concentrated_on_anniversary_credit(self) -> None:
        user, account_id = self._create_user_and_account()
        with _frozen_today("2026-08-05"):
            create_opening_position(user["id"], {
                "account_id": str(account_id),
                "asset_type": "savings",
                "asset_identifier": "POUPANCA",
                "asset_name": "Poupança",
                "acquisition_date": "2026-01-05",
                "total_cost": "10000,00",
            })
            with mock.patch("financeiro.portfolio.fetch_accumulated_indexer_factor", side_effect=_indexer_factor_mock), \
                 mock.patch("financeiro.portfolio.fetch_indexer_rate", side_effect=_indexer_rate_mock):
                portfolio = get_portfolio(user["id"])

        position = portfolio["positions"][0]
        current = int((Decimal("1000000") * (Decimal("1.005") ** 7)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        previous = int((Decimal("1000000") * (Decimal("1.005") ** 6)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        self.assertEqual(position["day_result_cents"], current - previous)
        self.assertGreater(position["day_result_cents"], 0)
        self.assertEqual(position["day_result_brl_cents"], position["day_result_cents"])

    def test_savings_day_result_is_zero_away_from_anniversary(self) -> None:
        user, account_id = self._create_user_and_account()
        with _frozen_today("2026-08-10"):
            create_opening_position(user["id"], {
                "account_id": str(account_id),
                "asset_type": "savings",
                "asset_identifier": "POUPANCA",
                "asset_name": "Poupança",
                "acquisition_date": "2026-01-05",
                "total_cost": "10000,00",
            })
            with mock.patch("financeiro.portfolio.fetch_accumulated_indexer_factor", side_effect=_indexer_factor_mock), \
                 mock.patch("financeiro.portfolio.fetch_indexer_rate", side_effect=_indexer_rate_mock):
                portfolio = get_portfolio(user["id"])

        position = portfolio["positions"][0]
        self.assertGreater(position["current_value_cents"], position["total_cost_cents"])
        self.assertEqual(position["day_result_cents"], 0)


if __name__ == "__main__":
    unittest.main()