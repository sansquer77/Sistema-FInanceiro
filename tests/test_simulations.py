from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.categories import create_category
from financeiro.credit_cards import create_credit_card, create_credit_card_transaction, set_credit_card_transaction_reconciled
from financeiro.database import initialize_database
from financeiro.simulations import SimulationError, simulate_butterfly_effect
from financeiro.spending_limits import create_spending_limit
from financeiro.transactions import create_transaction, set_transaction_reconciled


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
        with database.get_connection() as conn:
            transaction_count = conn.execute("SELECT COUNT(*) AS total FROM transactions").fetchone()["total"]
            account_row = conn.execute(
                "SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                (account["id"],),
            ).fetchone()
        self.assertEqual(transaction_count, 0)
        self.assertEqual(account_row["current_balance_cents"], 100000)

    def test_single_expense_accepts_minimal_uncategorized_payload(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        response = simulate_butterfly_effect(user["id"], {
            "type": "expense",
            "amount": "250,00",
            "date": "2026-01-15",
            "account_id": str(account["id"]),
            "series_kind": "single",
        })

        self.assertEqual(response["scenario"]["description"], "Despesa simulada")
        self.assertIsNone(response["scenario"]["category_id"])
        self.assertEqual(response["account_impact"]["projected_balance_cents"], 75000)
        self.assertEqual(response["limit_impact"]["items"], [])

    def test_simulation_uses_reconciled_balance_as_of_selected_date(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        income_category = create_category(user["id"], "Salário", "income")
        income_transaction = create_transaction(user["id"], {
            "type": "income",
            "description": "Salário",
            "amount": "100,00",
            "date": "2026-01-03",
            "account_id": str(account["id"]),
            "category": "Salário",
        })
        set_transaction_reconciled(user["id"], str(income_transaction["id"]), True)
        expense_category = create_category(user["id"], "Moradia", "expense")
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Despesa não conciliada",
            "amount": "50,00",
            "date": "2026-01-04",
            "account_id": str(account["id"]),
            "category": "Moradia",
        })

        response = simulate_butterfly_effect(user["id"], {
            "type": "expense",
            "amount": "250,00",
            "date": "2026-01-15",
            "description": "Despesa simulada",
            "account_id": str(account["id"]),
            "category_id": "1",
            "series_kind": "single",
        })

        self.assertEqual(response["account_impact"]["current_balance_cents"], 110000)
        self.assertEqual(response["account_impact"]["projected_balance_cents"], 80000)

    def test_chart_series_tracks_monthly_projected_balance(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        response = simulate_butterfly_effect(user["id"], {
            "type": "income",
            "amount": "2000,00",
            "date": "2026-01-15",
            "description": "Receita simulada",
            "account_id": str(account["id"]),
            "series_kind": "installment",
            "installment_count": 3,
        })

        self.assertEqual(response["account_impact"]["current_balance_cents"], 100000)
        self.assertEqual(response["account_impact"]["projected_balance_cents"], 166667)
        self.assertEqual(response["account_impact"]["simulated_month_total_cents"], 66667)
        self.assertEqual(
            [entry["projected_balance_cents"] for entry in response["chart_series"]],
            [166667, 233334, 300000, 300000, 300000],
        )

    def test_chart_series_keeps_previous_real_movements_in_base_balance(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        create_transaction(user["id"], {
            "type": "income",
            "description": "Receita anterior",
            "amount": "500,00",
            "date": "2025-12-20",
            "account_id": str(account["id"]),
            "category": "Salário",
        })

        response = simulate_butterfly_effect(user["id"], {
            "type": "income",
            "amount": "100,00",
            "date": "2026-01-15",
            "description": "Receita simulada",
            "account_id": str(account["id"]),
            "series_kind": "single",
        })

        self.assertEqual(response["chart_series"][0]["real_balance_cents"], 150000)
        self.assertEqual(response["chart_series"][0]["projected_balance_cents"], 160000)

    def test_chart_series_uses_account_forecast_with_reconciled_card_invoice(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        card = create_credit_card(user["id"], {
            "name": "Cartao principal",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "5000,00",
            "closing_day": "25",
            "due_day": "10",
            "preferred_payment_account_id": str(account["id"]),
        })
        card_transaction = create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Fatura conciliada",
            "amount": "300,00",
            "date": "2026-01-05",
            "invoice_month": "2026-01",
            "category": "Cartao",
        })
        set_credit_card_transaction_reconciled(user["id"], str(card_transaction["id"]), True)

        response = simulate_butterfly_effect(user["id"], {
            "type": "income",
            "amount": "200,00",
            "date": "2026-01-15",
            "description": "Receita simulada",
            "account_id": str(account["id"]),
            "series_kind": "single",
        })

        self.assertEqual(response["chart_series"][0]["real_balance_cents"], 70000)
        self.assertEqual(response["chart_series"][0]["projected_balance_cents"], 90000)

    def test_recurring_income_adds_full_amount_to_each_projected_month(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "18747,04",
        })

        response = simulate_butterfly_effect(user["id"], {
            "type": "income",
            "amount": "2000,00",
            "date": "2026-07-05",
            "description": "Receita extra",
            "account_id": str(account["id"]),
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "recurrence_count": 3,
        })

        self.assertEqual(response["account_impact"]["current_balance_cents"], 1874704)
        self.assertEqual(response["account_impact"]["projected_balance_cents"], 2074704)
        self.assertEqual(response["account_impact"]["simulated_month_total_cents"], 200000)
        self.assertEqual([item["impact_cents"] for item in response["virtual_items"]], [200000, 200000, 200000])
        self.assertEqual(
            [entry["projected_balance_cents"] for entry in response["chart_series"]],
            [2074704, 2274704, 2474704, 2474704, 2474704],
        )

    def test_recurring_simulation_uses_default_120_occurrences(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        response = simulate_butterfly_effect(user["id"], {
            "type": "income",
            "amount": "100,00",
            "date": "2026-01-15",
            "description": "Receita recorrente",
            "account_id": str(account["id"]),
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
        })

        self.assertEqual(response["scenario"]["recurrence_count"], 120)
        self.assertEqual(len(response["virtual_items"]), 120)
        self.assertTrue(all(item["impact_cents"] == 10000 for item in response["virtual_items"]))

    def test_rejects_non_monthly_recurrence_until_supported(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        with self.assertRaises(SimulationError):
            simulate_butterfly_effect(user["id"], {
                "type": "income",
                "amount": "100,00",
                "date": "2026-01-15",
                "description": "Receita trimestral",
                "account_id": str(account["id"]),
                "series_kind": "recurring",
                "recurrence_frequency": "quarterly",
                "recurrence_count": 3,
            })

    def test_month_impact_counts_inbound_transfer_for_destination_account(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        origin = create_checking_account(user["id"], {
            "name": "Origem",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        destination = create_checking_account(user["id"], {
            "name": "Destino",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "500,00",
        })
        transfer = create_transaction(user["id"], {
            "type": "transfer",
            "description": "Transferência",
            "amount": "200,00",
            "date": "2026-01-05",
            "account_id": str(origin["id"]),
            "destination_account_id": str(destination["id"]),
        })
        set_transaction_reconciled(user["id"], str(transfer["id"]), True)

        response = simulate_butterfly_effect(user["id"], {
            "type": "income",
            "amount": "100,00",
            "date": "2026-01-15",
            "description": "Receita simulada",
            "account_id": str(destination["id"]),
            "series_kind": "single",
        })

        self.assertEqual(response["month_impact"]["real_total_cents"], 20000)
        self.assertEqual(response["month_impact"]["projected_total_cents"], 30000)
        self.assertEqual(response["chart_series"][0]["real_balance_cents"], 70000)
        self.assertEqual(response["chart_series"][0]["projected_balance_cents"], 80000)

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

    def test_project_month_card_ignores_occurrences_of_later_months(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        response = simulate_butterfly_effect(user["id"], {
            "type": "income",
            "amount": "100,00",
            "date": "2026-01-15",
            "description": "Receita recorrente",
            "account_id": str(account["id"]),
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "recurrence_count": 120,
        })

        self.assertEqual(response["account_impact"]["projected_balance_cents"], 110000)
        self.assertEqual(response["account_impact"]["simulated_month_total_cents"], 10000)
        self.assertEqual(response["chart_series"][1]["projected_balance_cents"], 120000)

    def test_daily_projection_covers_today_and_next_fourteen_days(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        today = date.today()
        scenario_date = today + timedelta(days=10)
        response = simulate_butterfly_effect(user["id"], {
            "type": "expense",
            "amount": "200,00",
            "date": scenario_date.isoformat(),
            "account_id": str(account["id"]),
            "series_kind": "single",
        })

        projection = response["daily_projection"]
        self.assertEqual(len(projection), 15)
        self.assertEqual(projection[0]["date"], today.isoformat())
        self.assertEqual(projection[14]["date"], (today + timedelta(days=14)).isoformat())
        self.assertEqual(response["weekly_projection"], projection)
        self.assertIn("forecast_balance_cents", projection[0])
        self.assertIn("simulated_balance_cents", projection[0])
        self.assertIn("difference_cents", projection[0])

    def test_daily_projection_applies_single_impact_on_exact_date(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        today = date.today()
        scenario_date = today + timedelta(days=10)
        response = simulate_butterfly_effect(user["id"], {
            "type": "expense",
            "amount": "200,00",
            "date": scenario_date.isoformat(),
            "account_id": str(account["id"]),
            "series_kind": "single",
        })

        projection = response["daily_projection"]
        for index in range(10):
            self.assertEqual(projection[index]["difference_cents"], 0)
        for index in range(10, 15):
            self.assertEqual(projection[index]["forecast_balance_cents"], 100000)
            self.assertEqual(projection[index]["simulated_balance_cents"], 80000)
            self.assertEqual(projection[index]["difference_cents"], -20000)

    def test_distant_scenario_centers_daily_window_on_scenario_date(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        scenario_date = date.today() + timedelta(days=30)
        response = simulate_butterfly_effect(user["id"], {
            "type": "expense",
            "amount": "200,00",
            "date": scenario_date.isoformat(),
            "account_id": str(account["id"]),
            "series_kind": "single",
        })

        projection = response["daily_projection"]
        self.assertEqual(projection[0]["date"], (scenario_date - timedelta(days=7)).isoformat())
        self.assertEqual(projection[7]["date"], scenario_date.isoformat())
        self.assertEqual(projection[14]["date"], (scenario_date + timedelta(days=7)).isoformat())
        self.assertEqual(projection[6]["difference_cents"], 0)
        self.assertEqual(projection[7]["difference_cents"], -20000)

    def test_daily_projection_summary_identifies_caused_negative_balance(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "100,00",
        })
        scenario_date = date.today() + timedelta(days=3)

        response = simulate_butterfly_effect(user["id"], {
            "type": "expense",
            "amount": "150,00",
            "date": scenario_date.isoformat(),
            "account_id": str(account["id"]),
            "series_kind": "single",
        })

        summary = response["daily_projection_summary"]
        self.assertEqual(summary["effect"], "causes_negative")
        self.assertIsNone(summary["forecast_first_negative_date"])
        self.assertEqual(summary["simulated_first_negative_date"], scenario_date.isoformat())

    def test_daily_projection_summary_identifies_avoided_negative_balance(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "100,00",
        })
        category = create_category(user["id"], "Contas", "expense")
        risk_date = date.today() + timedelta(days=5)
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta futura",
            "amount": "150,00",
            "date": risk_date.isoformat(),
            "account_id": str(account["id"]),
            "category": "Contas",
            "category_id": str(category["id"]),
        })

        response = simulate_butterfly_effect(user["id"], {
            "type": "income",
            "amount": "100,00",
            "date": risk_date.isoformat(),
            "account_id": str(account["id"]),
            "series_kind": "single",
        })

        summary = response["daily_projection_summary"]
        self.assertEqual(summary["effect"], "avoids_negative")
        self.assertEqual(summary["forecast_first_negative_date"], risk_date.isoformat())
        self.assertIsNone(summary["simulated_first_negative_date"])


if __name__ == "__main__":
    unittest.main()
