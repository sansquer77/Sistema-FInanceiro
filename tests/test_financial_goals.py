from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from financeiro import database
from financeiro.auth import create_user
from financeiro.accounts import create_checking_account
from financeiro.database import get_connection, initialize_database
from financeiro.financial_goals import (
    FinancialGoalError,
    archive_financial_goal,
    create_financial_goal,
    create_goal_movement,
    emergency_reserve_summary,
    link_goal_funding_source,
    list_financial_goals,
    list_goal_funding_sources,
    list_goal_movements,
    unlink_goal_funding_source,
    update_financial_goal,
)
from financeiro.portfolio import PortfolioError, update_opening_position


class FinancialGoalsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"
        initialize_database()
        self.user = create_user("Alice", "alice@example.com", "correct-password")

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_schema_is_idempotent(self) -> None:
        initialize_database()
        with get_connection() as conn:
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'financial_goal%'"
                ).fetchall()
            }
        self.assertEqual(
            tables,
            {"financial_goals", "financial_goal_movements", "financial_goal_funding_sources"},
        )

    def test_goal_tracks_manual_contributions_without_financial_transaction(self) -> None:
        goal = self.create_goal()
        movement = create_goal_movement(self.user["id"], goal["id"], {
            "movement_type": "contribution",
            "amount": "3000,00",
            "movement_date": "2026-09-23",
        })
        goals = list_financial_goals(self.user["id"])

        self.assertEqual(movement["amount"], "3000.00")
        self.assertEqual(goals[0]["reserved_balance"], "3000.00")
        self.assertEqual(goals[0]["remaining_amount"], "9000.00")
        self.assertEqual(goals[0]["progress_percentage"], 25.0)
        with get_connection() as conn:
            transaction_count = conn.execute(
                "SELECT COUNT(*) AS total FROM transactions WHERE user_id = ?",
                (self.user["id"],),
            ).fetchone()["total"]
        self.assertEqual(transaction_count, 0)

    def test_withdrawal_cannot_exceed_reserved_balance(self) -> None:
        goal = self.create_goal()
        create_goal_movement(self.user["id"], goal["id"], {
            "movement_type": "contribution", "amount": "100,00", "movement_date": "2026-09-23",
        })
        with self.assertRaises(FinancialGoalError):
            create_goal_movement(self.user["id"], goal["id"], {
                "movement_type": "withdrawal", "amount": "100,01", "movement_date": "2026-09-23",
            })

    def test_adjustment_is_an_auditable_delta(self) -> None:
        goal = self.create_goal()
        create_goal_movement(self.user["id"], goal["id"], {
            "movement_type": "contribution", "amount": "100,00", "movement_date": "2026-09-23",
        })
        create_goal_movement(self.user["id"], goal["id"], {
            "movement_type": "adjustment", "amount": "250,00", "movement_date": "2026-09-24",
        })
        movements = list_goal_movements(self.user["id"], goal["id"])
        refreshed = list_financial_goals(self.user["id"])[0]

        self.assertEqual(len(movements), 2)
        self.assertEqual(movements[0]["signed_amount"], "150.00")
        self.assertEqual(refreshed["reserved_balance"], "250.00")

    def test_goals_are_isolated_by_user(self) -> None:
        goal = self.create_goal()
        other = create_user("Bob", "bob@example.com", "correct-password")
        self.assertEqual(list_financial_goals(other["id"]), [])
        with self.assertRaises(FinancialGoalError):
            update_financial_goal(other["id"], goal["id"], self.goal_payload())

    def test_archiving_hides_goal_and_preserves_history(self) -> None:
        goal = self.create_goal()
        create_goal_movement(self.user["id"], goal["id"], {
            "movement_type": "contribution", "amount": "100,00", "movement_date": "2026-09-23",
        })
        archive_financial_goal(self.user["id"], goal["id"])

        self.assertEqual(list_financial_goals(self.user["id"]), [])
        archived = list_financial_goals(self.user["id"], include_archived=True)
        self.assertEqual(archived[0]["reserved_balance"], "100.00")

    def test_emergency_reserve_lists_only_explicit_components(self) -> None:
        summary = emergency_reserve_summary(self.user["id"], positions=[
            {
                "asset_name": "Poupanca",
                "asset_type": "savings",
                "asset_type_label": "Poupanca",
                "account_name": "Banco",
                "currency": "BRL",
                "current_value_cents": 500_000,
                "current_value_brl_cents": 500_000,
                "emergency_reserve_eligible": True,
                "quote_source": "Curva local",
            },
            {
                "asset_name": "ETF",
                "asset_type": "stock",
                "current_value_cents": 900_000,
                "current_value_brl_cents": 900_000,
                "emergency_reserve_eligible": False,
            },
        ])

        self.assertEqual(summary["total_brl"], "5000.00")
        self.assertEqual(len(summary["components"]), 1)
        self.assertEqual(summary["components"][0]["asset_name"], "Poupanca")

    def test_projection_compares_conservative_and_yield_scenarios(self) -> None:
        goal = create_financial_goal(self.user["id"], {
            **self.goal_payload(),
            "yield_mode": "custom_annual_rate",
            "yield_percentage": "12,00",
        })
        create_goal_movement(self.user["id"], goal["id"], {
            "movement_type": "contribution", "amount": "3000,00", "movement_date": "2026-09-23",
        })
        projection = list_financial_goals(self.user["id"])[0]["projection"]

        self.assertEqual(projection["conservative"]["reserved"], "3000.00")
        self.assertGreater(float(projection["with_yield"]["projected_yield"]), 0)
        self.assertLess(
            float(projection["with_yield"]["future_contributions"]),
            float(projection["conservative"]["future_contributions"]),
        )

    def test_cdi_projection_exposes_reference_and_does_not_change_balance(self) -> None:
        create_financial_goal(self.user["id"], {
            **self.goal_payload(), "yield_mode": "cdi_percentage", "yield_percentage": "100",
        })
        goal = list_financial_goals(self.user["id"])[0]

        self.assertEqual(goal["reserved_balance"], "0.00")
        self.assertEqual(goal["projection"]["rate_label"], "100% do CDI")
        self.assertRegex(goal["projection"]["reference_date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_funding_source_is_exclusive_between_active_goals(self) -> None:
        source_id, _ = self.create_investment_source()
        first_goal = self.create_goal()
        second_goal = create_financial_goal(self.user["id"], {
            **self.goal_payload(), "name": "IPVA",
        })

        source = link_goal_funding_source(self.user["id"], first_goal["id"], {
            "source_type": "investment_opening", "source_id": source_id,
        })

        self.assertEqual(source["label"], "Poupança Objetivos")
        refreshed = next(goal for goal in list_financial_goals(self.user["id"]) if goal["id"] == first_goal["id"])
        self.assertEqual(refreshed["coverage_status"], "linked")
        with self.assertRaisesRegex(FinancialGoalError, "ja esta vinculado"):
            link_goal_funding_source(self.user["id"], second_goal["id"], {
                "source_type": "investment_opening", "source_id": source_id,
            })

    def test_only_investments_can_be_linked_to_a_goal(self) -> None:
        with self.assertRaisesRegex(FinancialGoalError, "Tipo de origem de recurso invalido"):
            link_goal_funding_source(self.user["id"], self.create_goal()["id"], {
                "source_type": "checking_account", "source_id": 1,
            })

    def test_linked_asset_balance_includes_all_matching_lots_and_manual_balance(self) -> None:
        source_id, payload = self.create_investment_source()
        second_source_id = self.insert_matching_opening_position(payload)
        goal = self.create_goal()
        portfolio_positions = [
            {
                "account_id": payload["account_id"], "currency": "BRL", "asset_type": "savings",
                "asset_identifier": "POUPANCA", "asset_name": "Poupança Objetivos", "cnpj": "",
                "fixed_income_indexer": "", "fixed_income_maturity_date": "",
                "current_value_brl_cents": 125_000,
            },
            {
                "account_id": payload["account_id"], "currency": "BRL", "asset_type": "savings",
                "asset_identifier": "POUPANCA", "asset_name": "Poupança Objetivos", "cnpj": "",
                "fixed_income_indexer": "", "fixed_income_maturity_date": "",
                "current_value_brl_cents": 75_000,
            },
        ]

        with patch("financeiro.portfolio.current_portfolio_positions", return_value=portfolio_positions):
            linked = link_goal_funding_source(self.user["id"], goal["id"], {
                "source_type": "investment_opening", "source_id": second_source_id,
            })
            create_goal_movement(self.user["id"], goal["id"], {
                "movement_type": "contribution", "amount": "50,00", "movement_date": "2026-09-23",
            })
            current = next(item for item in list_financial_goals(self.user["id"]) if item["id"] == goal["id"])

        self.assertEqual(linked["source_id"], source_id)
        self.assertEqual(linked["current_value_brl"], "2000.00")
        self.assertEqual(current["manual_reserved_balance"], "50.00")
        self.assertEqual(current["linked_reserved_balance"], "2000.00")
        self.assertEqual(current["reserved_balance"], "2050.00")

        with self.assertRaisesRegex(FinancialGoalError, "ja esta vinculado"):
            link_goal_funding_source(self.user["id"], self.create_goal()["id"], {
                "source_type": "investment_opening", "source_id": source_id,
            })

    def test_tesouro_prefixado_links_all_lots_despite_different_purchase_rates(self) -> None:
        account = create_checking_account(self.user["id"], {
            "name": "Carteira Tesouro", "bank_name": "Tesouro Direto", "account_type": "investment",
            "currency": "BRL", "initial_balance": "0,00",
        })
        source_ids = []
        with get_connection() as conn:
            for index, rate in enumerate((100_000, 125_000)):
                cursor = conn.execute(
                    """
                    INSERT INTO investment_opening_positions (
                        user_id, account_id, asset_type, asset_identifier, asset_name, cnpj,
                        acquisition_date, quantity_micros, unit_price_cents, total_cost_cents,
                        fixed_income_mode, fixed_income_indexer, fixed_income_rate_micros,
                        fixed_income_maturity_date
                    ) VALUES (?, ?, 'fixed_income', 'TESOURO_PREFIXADO_2027', 'Tesouro Prefixado 2027', '',
                        ?, 1000000, 100000, 100000, 'fixed_rate', 'PREFIXADO', ?, '2027-01-01')
                    """,
                    (self.user["id"], account["id"], f"2026-0{index + 1}-10", rate),
                )
                source_ids.append(int(cursor.lastrowid))
        goal = self.create_goal()
        current_positions = [
            {
                "account_id": account["id"], "currency": "BRL", "asset_type": "fixed_income",
                "asset_identifier": "TESOURO_PREFIXADO_2027", "asset_name": "Tesouro Prefixado 2027",
                "cnpj": "", "fixed_income_indexer": "PREFIXADO", "fixed_income_maturity_date": "2027-01-01",
                "fixed_income_rate": str(rate), "current_value_brl_cents": value,
            }
            for rate, value in (("10.0", 150_000), ("12.5", 250_000))
        ]

        with patch("financeiro.portfolio.current_portfolio_positions", return_value=current_positions):
            source = link_goal_funding_source(self.user["id"], goal["id"], {
                "source_type": "investment_opening", "source_id": source_ids[1],
            })
            current = next(item for item in list_financial_goals(self.user["id"]) if item["id"] == goal["id"])

        self.assertEqual(source["source_id"], source_ids[0])
        self.assertEqual(source["label"], "Tesouro Prefixado 2027")
        self.assertEqual(current["linked_reserved_balance"], "4000.00")

    def test_emergency_reserve_source_cannot_be_linked_to_goal(self) -> None:
        source_id, _ = self.create_investment_source(emergency=True)
        with self.assertRaisesRegex(FinancialGoalError, "Reserva de Emergencia"):
            link_goal_funding_source(self.user["id"], self.create_goal()["id"], {
                "source_type": "investment_opening", "source_id": source_id,
            })

    def test_emergency_mark_on_any_lot_blocks_the_consolidated_asset(self) -> None:
        source_id, payload = self.create_investment_source()
        self.insert_matching_opening_position(payload, emergency=True)

        with self.assertRaisesRegex(FinancialGoalError, "Reserva de Emergencia"):
            link_goal_funding_source(self.user["id"], self.create_goal()["id"], {
                "source_type": "investment_opening", "source_id": source_id,
            })

    def test_linked_source_cannot_later_become_emergency_reserve(self) -> None:
        source_id, payload = self.create_investment_source()
        goal = self.create_goal()
        link_goal_funding_source(self.user["id"], goal["id"], {
            "source_type": "investment_opening", "source_id": source_id,
        })

        with self.assertRaisesRegex(PortfolioError, "vinculado ao objetivo"):
            update_opening_position(self.user["id"], source_id, {
                **payload, "emergency_reserve_eligible": True,
            })

    def test_unlink_preserves_balance_and_releases_source(self) -> None:
        source_id, payload = self.create_investment_source()
        goal = self.create_goal()
        create_goal_movement(self.user["id"], goal["id"], {
            "movement_type": "contribution", "amount": "100,00", "movement_date": "2026-09-23",
        })
        link = link_goal_funding_source(self.user["id"], goal["id"], {
            "source_type": "investment_opening", "source_id": source_id,
        })

        unlink_goal_funding_source(self.user["id"], goal["id"], link["id"])
        with patch("financeiro.portfolio.get_portfolio", return_value={"positions": []}):
            update_opening_position(self.user["id"], source_id, {
                **payload, "emergency_reserve_eligible": True,
            })

        self.assertEqual(list_goal_funding_sources(self.user["id"], goal["id"]), [])
        self.assertEqual(list_financial_goals(self.user["id"])[0]["reserved_balance"], "100.00")

    def create_goal(self) -> dict:
        return create_financial_goal(self.user["id"], self.goal_payload())

    def create_investment_source(self, emergency: bool = False) -> tuple[int, dict]:
        account = create_checking_account(self.user["id"], {
            "name": "Carteira", "bank_name": "Banco", "account_type": "investment",
            "currency": "BRL", "initial_balance": "1000,00",
        })
        payload = {
            "account_id": account["id"],
            "asset_type": "savings",
            "asset_identifier": "POUPANCA",
            "asset_name": "Poupança Objetivos",
            "acquisition_date": "2026-01-10",
            "quantity": "1",
            "unit_price": "1000,00",
            "total_cost": "1000,00",
            "emergency_reserve_eligible": emergency,
        }
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO investment_opening_positions (
                    user_id, account_id, asset_type, asset_identifier, asset_name, acquisition_date,
                    quantity_micros, unit_price_cents, total_cost_cents, emergency_reserve_eligible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.user["id"], account["id"], payload["asset_type"], payload["asset_identifier"],
                    payload["asset_name"], payload["acquisition_date"], 1_000_000, 100_000,
                    100_000, 1 if emergency else 0,
                ),
            )
            source_id = cursor.lastrowid
        return source_id, payload

    def insert_matching_opening_position(self, payload: dict, emergency: bool = False) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO investment_opening_positions (
                    user_id, account_id, asset_type, asset_identifier, asset_name, acquisition_date,
                    quantity_micros, unit_price_cents, total_cost_cents, emergency_reserve_eligible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.user["id"], payload["account_id"], payload["asset_type"], payload["asset_identifier"],
                    payload["asset_name"], payload["acquisition_date"], 500_000, 100_000, 50_000,
                    1 if emergency else 0,
                ),
            )
            return int(cursor.lastrowid)

    @staticmethod
    def goal_payload() -> dict:
        return {
            "name": "Viagem",
            "objective_type": "target",
            "target_amount": "12000,00",
            "start_date": "2026-09-01",
            "target_date": "2027-08-01",
            "yield_mode": "none",
            "tax_treatment": "conservative",
        }


if __name__ == "__main__":
    unittest.main()
