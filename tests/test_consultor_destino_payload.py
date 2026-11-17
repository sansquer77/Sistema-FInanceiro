from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.consultor_cashflow import (
    MAX_OPEN_INVOICES,
    MAX_TIMELINE_EVENTS_PER_CURRENCY,
    build_maturity_cashflow_context,
)
from financeiro.consultor_catalog import build_system_prompt
from financeiro.consultor_provider import build_ai_messages
from financeiro.credit_cards import create_credit_card, create_credit_card_transaction
from financeiro.database import initialize_database
from financeiro.transactions import create_transaction

REFERENCE = date(2026, 10, 31)


class DestinoVencimentosPayloadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-destino.db"
        initialize_database()
        self.user = create_user("Ana", "ana@example.com", "correct-password")

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def add_future_expenses(self, count: int) -> None:
        account = create_checking_account(self.user["id"], {
            "name": "Conta Liquidez", "bank_name": "Banco", "account_type": "liquidity",
            "currency": "BRL", "initial_balance": "50000,00",
        })
        for index in range(count):
            create_transaction(self.user["id"], {
                "type": "expense", "description": f"Despesa futura {index}", "amount": "100,00",
                "date": (date(2026, 11, 1) + timedelta(days=index)).isoformat(), "account_id": str(account["id"]),
                "category": "Outros",
            })

    def add_open_invoices(self, cards: int, months: list[str]) -> None:
        for index in range(cards):
            card = create_credit_card(self.user["id"], {
                "name": f"Cartao {index}", "issuer": "Banco", "currency": "BRL",
                "limit": "5000,00", "closing_day": "5", "due_day": "10",
            })
            for invoice_month in months:
                create_credit_card_transaction(self.user["id"], {
                    "credit_card_id": str(card["id"]), "type": "expense",
                    "description": f"Compra {invoice_month}", "amount": "80,00",
                    "date": f"{invoice_month}-01", "invoice_month": invoice_month,
                    "category": "Outros",
                })

    def test_timeline_is_capped_and_keeps_final_balance(self) -> None:
        self.add_future_expenses(MAX_TIMELINE_EVENTS_PER_CURRENCY + 4)

        cashflow = build_maturity_cashflow_context(self.user["id"], REFERENCE)
        timeline = next(item for item in cashflow["timeline_by_currency"] if item["currency"] == "BRL")

        self.assertEqual(len(timeline["events"]), MAX_TIMELINE_EVENTS_PER_CURRENCY)
        self.assertEqual(timeline["omitted_events"], 4)
        self.assertEqual(
            timeline["projected_balance_at_horizon_minor_units"],
            timeline["opening_balance_minor_units"] - (MAX_TIMELINE_EVENTS_PER_CURRENCY + 4) * 10_000,
        )

    def test_forecast_months_are_capped_and_empty_months_are_not_sent(self) -> None:
        account = create_checking_account(self.user["id"], {
            "name": "Conta Meses", "bank_name": "Banco", "account_type": "liquidity",
            "currency": "BRL", "initial_balance": "10000,00",
        })
        for dated in ("2026-11-05", "2026-12-05", "2027-01-05"):
            create_transaction(self.user["id"], {
                "type": "expense", "description": "Mensal", "amount": "100,00",
                "date": dated, "account_id": str(account["id"]), "category": "Outros",
            })

        cashflow = build_maturity_cashflow_context(self.user["id"], REFERENCE)
        months = [item["month"] for item in cashflow["months_by_currency"] if item["currency"] == "BRL"]

        self.assertEqual(months, ["2026-10", "2026-11", "2026-12"])
        self.assertEqual(cashflow["omitted_months"], 1)
        self.assertNotIn("opening_balance_minor_units", cashflow["months_by_currency"][1])

    def test_timeline_without_excess_omits_nothing(self) -> None:
        self.add_future_expenses(3)

        cashflow = build_maturity_cashflow_context(self.user["id"], REFERENCE)
        timeline = next(item for item in cashflow["timeline_by_currency"] if item["currency"] == "BRL")

        self.assertEqual(len(timeline["events"]), 3)
        self.assertEqual(timeline["omitted_events"], 0)
        self.assertEqual(cashflow["omitted_open_card_invoices"], 0)

    def test_open_invoices_are_capped_to_nearest_due_dates(self) -> None:
        self.add_open_invoices(cards=3, months=["2026-11", "2026-12", "2027-01"])

        cashflow = build_maturity_cashflow_context(self.user["id"], REFERENCE)
        shown = cashflow["open_card_invoices"]

        self.assertEqual(len(shown), MAX_OPEN_INVOICES)
        self.assertEqual(cashflow["omitted_open_card_invoices"], 9 - MAX_OPEN_INVOICES)
        due_dates = [item["due_date"] for item in shown]
        self.assertEqual(due_dates, sorted(due_dates))

    def test_prompt_payload_stays_under_local_budget_with_extensive_data(self) -> None:
        from unittest import mock

        self.add_future_expenses(40)
        self.add_open_invoices(cards=3, months=["2026-11", "2026-12", "2027-01"])

        calendar = {"reference_date": REFERENCE.isoformat(), "maturity_30_days": [], "maturity_60_days": []}
        with mock.patch("financeiro.calendar.get_cockpit_calendar", return_value=calendar):
            from financeiro.consultor import build_analysis_context

            context = build_analysis_context(
                self.user["id"], "destino_vencimentos", reference_date=REFERENCE,
                investor_profile="moderado", portfolio_positions=[],
            )
        messages = build_ai_messages(build_system_prompt("destino_vencimentos", investor_profile="moderado"), context)
        payload = messages[1]["content"]

        self.assertLessEqual(len(payload), 8_000, f"payload com {len(payload)} caracteres")
        self.assertIn("omitted_events", payload)
        self.assertIn("omitted_open_card_invoices", payload)


if __name__ == "__main__":
    unittest.main()
