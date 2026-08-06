from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from http import HTTPStatus
from pathlib import Path
from unittest import mock

import app
from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_session, create_user
from financeiro.database import initialize_database
from financeiro.calendar import get_cockpit_calendar
from financeiro.portfolio import create_opening_position


class IsolatedDatabaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"
        initialize_database()
        self.seed_patch = mock.patch("financeiro.categories.seed_default_categories", lambda conn, user_id: None)
        self.seed_patch.start()

    def tearDown(self) -> None:
        self.seed_patch.stop()
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()


class CalendarCoreTest(IsolatedDatabaseTest):
    def test_overdue_receivable_is_listed(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        self.create_transaction(user["id"], account["id"], "income", "Receita atrasada", "100,00", date.today() - timedelta(days=5))

        payload = get_cockpit_calendar(user["id"], reference_date=date.today())

        self.assertEqual(len(payload["overdue_receivables"]), 1)
        self.assertEqual(payload["overdue_receivables"][0]["description"], "Receita atrasada")
        self.assertEqual(payload["overdue_receivables"][0]["amount_cents"], 10000)
        self.assertEqual(payload["overdue_receivables"][0]["days_overdue"], 5)
        self.assertEqual(payload["total_overdue_receivables_cents"], 10000)
        self.assertEqual(payload["total_overdue_payables_cents"], 0)

    def test_overdue_payable_is_listed(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        self.create_transaction(user["id"], account["id"], "expense", "Despesa atrasada", "50,00", date.today() - timedelta(days=3))

        payload = get_cockpit_calendar(user["id"], reference_date=date.today())

        self.assertEqual(len(payload["overdue_payables"]), 1)
        self.assertEqual(payload["overdue_payables"][0]["description"], "Despesa atrasada")
        self.assertEqual(payload["overdue_payables"][0]["amount_cents"], 5000)
        self.assertEqual(payload["overdue_payables"][0]["days_overdue"], 3)
        self.assertEqual(payload["total_overdue_payables_cents"], 5000)
        self.assertEqual(payload["total_overdue_receivables_cents"], 0)

    def test_reconciled_transaction_is_excluded(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        transaction = self.create_transaction(user["id"], account["id"], "income", "Receita conciliada", "100,00", date.today() - timedelta(days=1))
        with database.get_connection() as conn:
            conn.execute(
                "UPDATE transactions SET reconciled_at = CURRENT_TIMESTAMP WHERE id = ?",
                (transaction["id"],),
            )

        payload = get_cockpit_calendar(user["id"], reference_date=date.today())

        self.assertEqual(payload["overdue_receivables"], [])
        self.assertEqual(payload["overdue_payables"], [])

    def test_credit_card_payment_is_excluded_from_payables(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        from financeiro.credit_cards import create_credit_card
        from financeiro.transactions import create_transaction as core_create_transaction
        card = create_credit_card(user["id"], {
            "name": "Cartão",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "1000,00",
            "closing_day": "10",
            "due_day": "20",
        })
        payment_transaction = core_create_transaction(user["id"], {
            "type": "expense",
            "description": "Pagamento de fatura",
            "amount": "100,00",
            "date": (date.today() - timedelta(days=2)).isoformat(),
            "account_id": str(account["id"]),
            "category": "Serviços Financeiros",
        })
        with database.get_connection() as conn:
            conn.execute(
                "INSERT INTO credit_card_payments (user_id, credit_card_id, invoice_month, account_id, transaction_id, payment_date, amount_cents) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user["id"], card["id"], "2026-07", account["id"], payment_transaction["id"], (date.today() - timedelta(days=2)).isoformat(), 10000),
            )

        payload = get_cockpit_calendar(user["id"], reference_date=date.today())

        self.assertEqual(payload["overdue_payables"], [])

    def test_transfer_and_investment_are_excluded_from_overdue(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        source_account = create_checking_account(user["id"], {
            "name": "Conta origem",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        destination_account = create_checking_account(user["id"], {
            "name": "Conta destino",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        self.create_transaction(
            user["id"], source_account["id"], "transfer", "Transferência", "100,00",
            date.today() - timedelta(days=1),
            destination_account_id=destination_account["id"],
        )
        self.create_transaction(user["id"], source_account["id"], "investment", "Investimento", "100,00", date.today() - timedelta(days=1))

        payload = get_cockpit_calendar(user["id"], reference_date=date.today())

        self.assertEqual(payload["overdue_receivables"], [])
        self.assertEqual(payload["overdue_payables"], [])

    def test_fixed_income_maturity_windows(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        account = create_checking_account(user["id"], {
            "name": "Investimentos",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        today = date.today()
        self.create_fixed_income_position(user["id"], account["id"], "CDB 30 dias", today + timedelta(days=15))
        self.create_fixed_income_position(user["id"], account["id"], "CDB 31 dias", today + timedelta(days=31))
        self.create_fixed_income_position(user["id"], account["id"], "CDB 60 dias", today + timedelta(days=60))
        self.create_fixed_income_position(user["id"], account["id"], "CDB 61 dias", today + timedelta(days=61))

        with mock.patch("financeiro.portfolio.read_json_url", side_effect=RuntimeError("offline")):
            payload = get_cockpit_calendar(user["id"], reference_date=today)

        self.assertEqual(len(payload["maturity_30_days"]), 1)
        self.assertEqual(payload["maturity_30_days"][0]["asset_name"], "CDB 30 dias")
        self.assertEqual(payload["maturity_30_days"][0]["days_to_maturity"], 15)

        self.assertEqual(len(payload["maturity_60_days"]), 2)
        names = [item["asset_name"] for item in payload["maturity_60_days"]]
        self.assertEqual(names, ["CDB 31 dias", "CDB 60 dias"])
        self.assertEqual(payload["maturity_60_days"][0]["days_to_maturity"], 31)
        self.assertEqual(payload["maturity_60_days"][1]["days_to_maturity"], 60)

    def test_non_fixed_income_positions_are_excluded(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        account = create_checking_account(user["id"], {
            "name": "Investimentos",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        today = date.today()
        self.create_fixed_income_position(user["id"], account["id"], "Ação", today + timedelta(days=15), asset_type="stock")
        self.create_fixed_income_position(user["id"], account["id"], "Cripto", today + timedelta(days=15), asset_type="crypto")
        self.create_fixed_income_position(user["id"], account["id"], "Poupança", today + timedelta(days=15), asset_type="savings")
        self.create_fixed_income_position(user["id"], account["id"], "Previdência", today + timedelta(days=15), asset_type="private_pension")

        with mock.patch("financeiro.portfolio.read_json_url", side_effect=RuntimeError("offline")):
            payload = get_cockpit_calendar(user["id"], reference_date=today)

        self.assertEqual(payload["maturity_30_days"], [])
        self.assertEqual(payload["maturity_60_days"], [])

    def test_closed_position_is_excluded(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        account = create_checking_account(user["id"], {
            "name": "Investimentos",
            "bank_name": "Banco",
            "account_type": "investment",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        today = date.today()
        self.create_fixed_income_position(user["id"], account["id"], "CDB fechado", today + timedelta(days=15))
        with database.get_connection() as conn:
            position_id = conn.execute(
                "SELECT id FROM investment_opening_positions WHERE user_id = ?",
                (user["id"],),
            ).fetchone()["id"]
            conn.execute(
                "INSERT INTO investment_closed_positions (user_id, account_id, currency, asset_type, asset_identifier, asset_name, cnpj, fixed_income_indexer, fixed_income_maturity_date, closed_at, source_count, quantity_micros, total_cost_cents, total_cost_brl_cents, closing_value_cents, closing_value_brl_cents, result_brl_cents, result_percent_micros) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user["id"], account["id"], "BRL", "fixed_income", "", "CDB fechado", "", "", (today + timedelta(days=15)).isoformat(), today.isoformat(), 1, 0, 10000, 10000, 10000, 10000, 0, 0),
            )

        with mock.patch("financeiro.portfolio.read_json_url", side_effect=RuntimeError("offline")):
            payload = get_cockpit_calendar(user["id"], reference_date=today)

        self.assertEqual(payload["maturity_30_days"], [])

    def test_empty_state_returns_zero_totals(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })

        payload = get_cockpit_calendar(user["id"], reference_date=date.today())

        self.assertEqual(payload["overdue_receivables"], [])
        self.assertEqual(payload["overdue_payables"], [])
        self.assertEqual(payload["maturity_30_days"], [])
        self.assertEqual(payload["maturity_60_days"], [])
        self.assertEqual(payload["total_overdue_receivables_cents"], 0)
        self.assertEqual(payload["total_overdue_payables_cents"], 0)
        self.assertEqual(payload["totals_by_currency"], [])

    def test_overdue_items_sorted_oldest_first(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        today = date.today()
        self.create_transaction(user["id"], account["id"], "expense", "Mais recente", "10,00", today - timedelta(days=1))
        self.create_transaction(user["id"], account["id"], "expense", "Mais antiga", "20,00", today - timedelta(days=10))

        payload = get_cockpit_calendar(user["id"], reference_date=today)

        self.assertEqual([item["description"] for item in payload["overdue_payables"]], ["Mais antiga", "Mais recente"])

    def test_totals_by_currency_groups_by_currency(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        brl_account = create_checking_account(user["id"], {
            "name": "Conta BRL",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        usd_account = create_checking_account(user["id"], {
            "name": "Conta USD",
            "bank_name": "Banco",
            "currency": "USD",
            "initial_balance": "0,00",
        })
        today = date.today()
        self.create_transaction(user["id"], brl_account["id"], "expense", "BRL", "100,00", today - timedelta(days=1))
        self.create_transaction(user["id"], usd_account["id"], "expense", "USD", "50,00", today - timedelta(days=1), exchange_rate_to_brl="5,00")

        payload = get_cockpit_calendar(user["id"], reference_date=today)

        by_currency = {item["currency"]: item for item in payload["totals_by_currency"]}
        self.assertEqual(by_currency["BRL"]["overdue_payables_cents"], 10000)
        self.assertEqual(by_currency["USD"]["overdue_payables_cents"], 5000)

    def create_transaction(
        self,
        user_id: int,
        account_id: int,
        transaction_type: str,
        description: str,
        amount: str,
        transaction_date: date,
        *,
        destination_account_id: int | None = None,
        exchange_rate_to_brl: str | None = None,
    ) -> dict:
        from financeiro.transactions import create_transaction as core_create_transaction
        payload: dict = {
            "type": transaction_type,
            "description": description,
            "amount": amount,
            "date": transaction_date.isoformat(),
            "account_id": str(account_id),
            "category": "Outros" if transaction_type == "expense" else "Receitas",
        }
        if destination_account_id is not None:
            payload["destination_account_id"] = str(destination_account_id)
        if exchange_rate_to_brl is not None:
            payload["exchange_rate_to_brl"] = exchange_rate_to_brl
        return core_create_transaction(user_id, payload)

    def create_fixed_income_position(self, user_id: int, account_id: int, name: str, maturity_date: date, asset_type: str = "fixed_income") -> dict:
        return create_opening_position(user_id, {
            "account_id": str(account_id),
            "asset_type": asset_type,
            "asset_name": name,
            "acquisition_date": (maturity_date - timedelta(days=90)).isoformat(),
            "quantity": "1",
            "unit_price": "1000,00",
            "total_cost": "1000,00",
            "fixed_income_mode": "pre",
            "fixed_income_rate": "10,00",
            "fixed_income_maturity_date": maturity_date.isoformat(),
        })


class CalendarRouteTest(IsolatedDatabaseTest):
    def test_route_requires_authentication(self) -> None:
        handler = object.__new__(app.AppHandler)
        handler.headers = {"Host": "sistema-financeiro.localhost:8020"}
        handler.path = "/api/cockpit/calendar"
        handler.send_json = mock.Mock()
        with (
            mock.patch.object(app, "PORT", 8020),
            mock.patch.object(app, "PUBLIC_URL", "http://sistema-financeiro.localhost:8020"),
            mock.patch.object(app.AppHandler, "get_cookie", return_value=None),
        ):
            with self.assertRaises(app.ApiError) as error:
                handler.handle_cockpit_calendar()
        self.assertEqual(error.exception.status, HTTPStatus.UNAUTHORIZED)

    def test_route_rejects_unknown_origin(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        handler = object.__new__(app.AppHandler)
        handler.headers = {
            "Host": "sistema-financeiro.localhost:8020",
            "Origin": "http://evil.example:8020",
        }
        handler.path = "/api/cockpit/calendar"
        handler.send_json = mock.Mock()
        with (
            mock.patch.object(app, "PORT", 8020),
            mock.patch.object(app, "PUBLIC_URL", "http://sistema-financeiro.localhost:8020"),
            mock.patch.object(app.AppHandler, "require_user", return_value=user),
        ):
            self.assertFalse(handler.handle_cockpit_calendar())
        handler.send_json.assert_called_once_with(
            {"error": "Origem da requisicao nao permitida."}, HTTPStatus.FORBIDDEN
        )

    def test_route_returns_payload_for_allowed_origin(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        handler = object.__new__(app.AppHandler)
        handler.headers = {
            "Host": "sistema-financeiro.localhost:8020",
            "Origin": "http://sistema-financeiro.localhost:8020",
        }
        handler.path = "/api/cockpit/calendar"
        handler.send_json = mock.Mock()
        with (
            mock.patch.object(app, "PORT", 8020),
            mock.patch.object(app, "PUBLIC_URL", "http://sistema-financeiro.localhost:8020"),
            mock.patch.object(app.AppHandler, "require_user", return_value=user),
        ):
            handler.handle_cockpit_calendar()
        handler.send_json.assert_called_once()
        payload = handler.send_json.call_args.args[0]
        self.assertIn("reference_date", payload)
        self.assertIn("overdue_receivables", payload)
        self.assertIn("overdue_payables", payload)
        self.assertIn("maturity_30_days", payload)
        self.assertIn("maturity_60_days", payload)


if __name__ == "__main__":
    unittest.main()
