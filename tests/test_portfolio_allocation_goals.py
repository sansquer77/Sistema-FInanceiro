from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.auth import create_user
from financeiro.database import initialize_database
from financeiro.portfolio import PortfolioError, get_allocation_goals, save_allocation_goals


class PortfolioAllocationGoalsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-allocation-goals.db"
        initialize_database()
        self.user = create_user("Alice", "alice@example.com", "correct-password")

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_saves_goals_that_total_one_hundred_percent(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.52 — critérios 62-66
        result = save_allocation_goals(self.user["id"], {"goals": [
            {"asset_type": "fixed_income", "target_percent": "60"},
            {"asset_type": "stock", "target_percent": "30"},
            {"asset_type": "stablecoin", "target_percent": "10"},
        ]})
        goals = {goal["asset_type"]: goal["target_percent"] for goal in result["allocation_goals"]}
        self.assertEqual(goals["fixed_income"], "60")
        self.assertEqual(goals["stock"], "30")
        self.assertEqual(goals["stablecoin"], "10")
        self.assertEqual(len(get_allocation_goals(self.user["id"])), 9)

    def test_saves_separate_usd_variable_income_goal(self) -> None:
        result = save_allocation_goals(self.user["id"], {"goals": [
            {"asset_type": "fixed_income", "target_percent": "50"},
            {"asset_type": "stock", "target_percent": "20"},
            {"asset_type": "stock_usd", "target_percent": "20"},
            {"asset_type": "stablecoin", "target_percent": "10"},
        ]})
        goals = {goal["asset_type"]: goal for goal in result["allocation_goals"]}
        self.assertEqual(goals["stock"]["label"], "Renda variável")
        self.assertEqual(goals["stock_usd"]["label"], "Renda variável - USD")
        self.assertEqual(goals["stock_usd"]["target_percent"], "20")

    def test_rejects_goal_total_different_from_one_hundred_percent(self) -> None:
        with self.assertRaisesRegex(PortfolioError, "exatamente 100%"):
            save_allocation_goals(self.user["id"], {"goals": [
                {"asset_type": "stock", "target_percent": "80"},
            ]})


if __name__ == "__main__":
    unittest.main()
