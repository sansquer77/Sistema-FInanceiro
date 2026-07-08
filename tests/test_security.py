from __future__ import annotations

from io import BytesIO
import sqlite3
import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path
from unittest import mock

import app
from financeiro import auth as auth_module
from financeiro import database
from financeiro.accounts import AccountError, create_checking_account, update_checking_account
from financeiro.auth import AuthError, create_user, login_user, request_password_reset
from financeiro.categories import ClassificationError, create_category, get_category_evolution, update_category
from financeiro.credit_cards import (
    CreditCardError,
    create_credit_card,
    create_credit_card_transaction,
    list_credit_card_invoice,
    update_credit_card,
    update_credit_card_transaction,
)
from financeiro.database import initialize_database
from financeiro.portfolio import PortfolioError, create_opening_position, update_opening_position
from financeiro.secure_config import email_config_status, save_email_config
from financeiro.spending_limits import SpendingLimitError, create_spending_limit, list_spending_limits, update_spending_limit
from financeiro.transactions import TransactionError, create_transaction, update_transaction


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


class BruteForceProtectionTest(IsolatedDatabaseTest):
    def test_login_uses_single_connection_on_success(self) -> None:
        create_user("Alice", "alice@example.com", "correct-password")

        with mock.patch("financeiro.auth.get_connection", wraps=auth_module.get_connection) as get_connection:
            login_user("alice@example.com", "correct-password", source_key="127.0.0.1")

        self.assertEqual(get_connection.call_count, 1)

    def test_login_uses_single_connection_on_invalid_password(self) -> None:
        create_user("Alice", "alice@example.com", "correct-password")

        with mock.patch("financeiro.auth.get_connection", wraps=auth_module.get_connection) as get_connection:
            with self.assertRaises(AuthError):
                login_user("alice@example.com", "wrong-password", source_key="127.0.0.1")

        self.assertEqual(get_connection.call_count, 1)

    def test_login_locks_after_repeated_failures(self) -> None:
        create_user("Alice", "alice@example.com", "correct-password")

        for _ in range(5):
            with self.assertRaises(AuthError) as failure:
                login_user("alice@example.com", "wrong-password", source_key="127.0.0.1")
            self.assertEqual(failure.exception.status, HTTPStatus.UNAUTHORIZED)

        with self.assertRaises(AuthError) as locked:
            login_user("alice@example.com", "correct-password", source_key="127.0.0.1")
        self.assertEqual(locked.exception.status, HTTPStatus.TOO_MANY_REQUESTS)

    def test_password_reset_request_is_rate_limited_without_revealing_email_existence(self) -> None:
        for _ in range(3):
            response = request_password_reset("missing@example.com", source_key="127.0.0.1")
            self.assertTrue(response["ok"])

        with self.assertRaises(AuthError) as locked:
            request_password_reset("missing@example.com", source_key="127.0.0.1")
        self.assertEqual(locked.exception.status, HTTPStatus.TOO_MANY_REQUESTS)

    def test_password_reset_email_failure_invalidates_created_token(self) -> None:
        create_user("Alice", "alice@example.com", "correct-password")

        with (
            mock.patch("financeiro.auth.send_password_reset_email", side_effect=RuntimeError("SMTP offline")),
            self.assertRaises(RuntimeError),
        ):
            request_password_reset("alice@example.com", source_key="127.0.0.1")

        with database.get_connection() as conn:
            reset = conn.execute("SELECT used_at FROM password_resets").fetchone()

        self.assertIsNotNone(reset["used_at"])

    def test_password_reset_uses_requested_users_email_config(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")

        with mock.patch("financeiro.auth.send_password_reset_email") as send_email:
            request_password_reset("alice@example.com", source_key="127.0.0.1")

        self.assertEqual(send_email.call_args.args[0], user["id"])
        self.assertEqual(send_email.call_args.args[1], "alice@example.com")


class IdorProtectionTest(IsolatedDatabaseTest):
    def test_account_update_requires_owner(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        attacker = create_user("Attacker", "attacker@example.com", "strong-password")
        account = create_checking_account(owner["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "100,00",
        })

        with self.assertRaises(AccountError) as denied:
            update_checking_account(attacker["id"], str(account["id"]), {
                "name": "Conta invadida",
                "bank_name": "Banco",
                "currency": "BRL",
                "initial_balance": "100,00",
            })
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_category_update_requires_owner(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        attacker = create_user("Attacker", "attacker@example.com", "strong-password")
        category = create_category(owner["id"], "Mercado", "expense")

        with self.assertRaises(ClassificationError) as denied:
            update_category(attacker["id"], str(category["id"]), "Outro nome")
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_credit_card_update_requires_owner(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        attacker = create_user("Attacker", "attacker@example.com", "strong-password")
        card = create_credit_card(owner["id"], {
            "name": "Cartao",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "1000,00",
            "closing_day": "10",
            "due_day": "20",
        })

        with self.assertRaises(CreditCardError) as denied:
            update_credit_card(attacker["id"], str(card["id"]), {
                "name": "Cartao alterado",
                "issuer": "Banco",
                "currency": "BRL",
                "limit": "1000,00",
                "closing_day": "10",
                "due_day": "20",
            })
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_credit_card_update_rejects_foreign_preferred_payment_account(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        other_user = create_user("Other", "other@example.com", "strong-password")
        foreign_account = create_checking_account(other_user["id"], {
            "name": "Conta de outro usuario",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "100,00",
        })
        card = create_credit_card(owner["id"], {
            "name": "Cartao",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "1000,00",
            "closing_day": "10",
            "due_day": "20",
        })

        with self.assertRaises(CreditCardError):
            update_credit_card(owner["id"], str(card["id"]), {
                "name": "Cartao",
                "issuer": "Banco",
                "currency": "BRL",
                "limit": "1000,00",
                "closing_day": "10",
                "due_day": "20",
                "preferred_payment_account_id": str(foreign_account["id"]),
            })

    def test_transaction_update_requires_owner(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        attacker = create_user("Attacker", "attacker@example.com", "strong-password")
        owner_account = create_checking_account(owner["id"], {
            "name": "Conta owner",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "100,00",
        })
        attacker_account = create_checking_account(attacker["id"], {
            "name": "Conta attacker",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "100,00",
        })
        transaction = create_transaction(owner["id"], transaction_payload(owner_account["id"]))

        with self.assertRaises(TransactionError) as denied:
            update_transaction(attacker["id"], str(transaction["id"]), transaction_payload(attacker_account["id"]))
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_transaction_create_rejects_foreign_account(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        other_user = create_user("Other", "other@example.com", "strong-password")
        foreign_account = create_checking_account(other_user["id"], {
            "name": "Conta de outro usuario",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "100,00",
        })

        with self.assertRaises(TransactionError) as denied:
            create_transaction(owner["id"], transaction_payload(foreign_account["id"]))
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_credit_card_transaction_update_requires_owner(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        attacker = create_user("Attacker", "attacker@example.com", "strong-password")
        owner_card = create_credit_card(owner["id"], credit_card_payload("Cartao owner"))
        attacker_card = create_credit_card(attacker["id"], credit_card_payload("Cartao attacker"))
        transaction = create_credit_card_transaction(owner["id"], card_transaction_payload(owner_card["id"]))

        with self.assertRaises(CreditCardError) as denied:
            update_credit_card_transaction(
                attacker["id"],
                str(transaction["id"]),
                card_transaction_payload(attacker_card["id"]),
            )
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_credit_card_invoice_rejects_foreign_card(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        attacker = create_user("Attacker", "attacker@example.com", "strong-password")
        owner_card = create_credit_card(owner["id"], credit_card_payload("Cartao owner"))

        with self.assertRaises(CreditCardError) as denied:
            list_credit_card_invoice(attacker["id"], str(owner_card["id"]), "2026-06")
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_spending_limit_update_requires_owner(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        attacker = create_user("Attacker", "attacker@example.com", "strong-password")
        owner_category = create_category(owner["id"], "Mercado", "expense")
        attacker_category = create_category(attacker["id"], "Mercado", "expense")
        limit = create_spending_limit(owner["id"], spending_limit_payload(owner_category["id"]))

        with self.assertRaises(SpendingLimitError) as denied:
            update_spending_limit(attacker["id"], str(limit["id"]), spending_limit_payload(attacker_category["id"]))
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_spending_limit_create_rejects_foreign_category(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        other_user = create_user("Other", "other@example.com", "strong-password")
        foreign_category = create_category(other_user["id"], "Mercado", "expense")

        with self.assertRaises(SpendingLimitError):
            create_spending_limit(owner["id"], spending_limit_payload(foreign_category["id"]))

    def test_spending_limits_are_recurring_from_start_month(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        category = create_category(user["id"], "Restaurantes", "expense")
        create_spending_limit(user["id"], spending_limit_payload(category["id"]))

        july_limits = list_spending_limits(user["id"], "2026-07")

        self.assertEqual(len(july_limits), 1)
        self.assertEqual(july_limits[0]["month"], "2026-06")
        self.assertEqual(july_limits[0]["limit_amount"], "500.00")

    def test_spending_limits_use_latest_definition_until_month(self) -> None:
        user = create_user("Alice", "alice@example.com", "strong-password")
        category = create_category(user["id"], "Restaurantes", "expense")
        create_spending_limit(user["id"], spending_limit_payload(category["id"]))
        create_spending_limit(user["id"], {
            "month": "2026-07",
            "category_id": str(category["id"]),
            "limit_amount": "750,00",
        })

        july_limits = list_spending_limits(user["id"], "2026-07")

        self.assertEqual(len(july_limits), 1)
        self.assertEqual(july_limits[0]["month"], "2026-07")
        self.assertEqual(july_limits[0]["limit_amount"], "750.00")

    def test_category_evolution_rejects_foreign_category(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        attacker = create_user("Attacker", "attacker@example.com", "strong-password")
        category = create_category(owner["id"], "Mercado", "expense")

        with self.assertRaises(ClassificationError) as denied:
            get_category_evolution(attacker["id"], category["id"])
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_portfolio_position_update_requires_owner(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        attacker = create_user("Attacker", "attacker@example.com", "strong-password")
        owner_account = create_checking_account(owner["id"], investment_account_payload("Investimentos owner"))
        attacker_account = create_checking_account(attacker["id"], investment_account_payload("Investimentos attacker"))
        create_opening_position(owner["id"], portfolio_position_payload(owner_account["id"]))

        with database.get_connection() as conn:
            position_id = conn.execute(
                "SELECT id FROM investment_opening_positions WHERE user_id = ?",
                (owner["id"],),
            ).fetchone()["id"]

        with self.assertRaises(PortfolioError) as denied:
            update_opening_position(attacker["id"], position_id, portfolio_position_payload(attacker_account["id"]))
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_portfolio_position_create_rejects_foreign_account(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        other_user = create_user("Other", "other@example.com", "strong-password")
        foreign_account = create_checking_account(other_user["id"], investment_account_payload("Investimentos outro"))

        with self.assertRaises(PortfolioError) as denied:
            create_opening_position(owner["id"], portfolio_position_payload(foreign_account["id"]))
        self.assertEqual(denied.exception.status, HTTPStatus.NOT_FOUND)

    def test_email_config_is_isolated_per_user(self) -> None:
        owner = create_user("Owner", "owner@example.com", "strong-password")
        other_user = create_user("Other", "other@example.com", "strong-password")

        save_email_config(owner["id"], email_config_payload("owner-smtp@example.com"))

        owner_status = email_config_status(owner["id"])
        other_status = email_config_status(other_user["id"])

        self.assertTrue(owner_status["configured"])
        self.assertEqual(owner_status["sender"], "owner-smtp@example.com")
        self.assertFalse(other_status["configured"])
        self.assertEqual(other_status["sender"], "")


class SessionCookieTest(unittest.TestCase):
    def test_session_cookie_is_httponly_samesite_and_not_secure_on_http(self) -> None:
        handler = object.__new__(app.AppHandler)
        with mock.patch.object(app, "PUBLIC_URL", "http://sistema-financeiro.localhost:8020"):
            cookie = handler.session_cookie("token")["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertNotIn("Secure", cookie)

    def test_session_cookie_adds_secure_on_https(self) -> None:
        handler = object.__new__(app.AppHandler)
        with mock.patch.object(app, "PUBLIC_URL", "https://financeiro.example.test"):
            cookie = handler.session_cookie("token")["Set-Cookie"]
        self.assertIn("Secure", cookie)


class RequestSourceProtectionTest(unittest.TestCase):
    def test_allowed_hosts_include_local_hosts_on_expected_port(self) -> None:
        with (
            mock.patch.object(app, "PORT", 8020),
            mock.patch.object(app, "PUBLIC_URL", "http://sistema-financeiro.localhost:8020"),
        ):
            self.assertIn("sistema-financeiro.localhost:8020", app.allowed_host_values())
            self.assertIn("127.0.0.1:8020", app.allowed_host_values())

    def test_public_https_url_with_port_is_allowed_as_host_and_origin(self) -> None:
        handler = object.__new__(app.AppHandler)
        with (
            mock.patch.object(app, "PORT", 8030),
            mock.patch.object(app, "PUBLIC_URL", "https://sistema-financeiro.net:8030"),
        ):
            self.assertTrue(handler.is_allowed_host("sistema-financeiro.net:8030"))
            self.assertTrue(handler.is_allowed_origin("https://sistema-financeiro.net:8030"))

    def test_disallows_unknown_origin(self) -> None:
        handler = object.__new__(app.AppHandler)
        with (
            mock.patch.object(app, "PORT", 8020),
            mock.patch.object(app, "PUBLIC_URL", "http://sistema-financeiro.localhost:8020"),
        ):
            self.assertTrue(handler.is_allowed_origin("http://sistema-financeiro.localhost:8020"))
            self.assertFalse(handler.is_allowed_origin("http://evil.example:8020"))

    def test_invalid_host_is_rejected_without_exception(self) -> None:
        handler = object.__new__(app.AppHandler)
        self.assertFalse(handler.is_allowed_host("sistema-financeiro.localhost:not-a-port"))


class JsonBodyLimitTest(unittest.TestCase):
    def test_read_json_rejects_invalid_content_length(self) -> None:
        handler = json_handler("invalid", b"")

        with self.assertRaises(app.ApiError) as error:
            handler.read_json()

        self.assertEqual(error.exception.status, HTTPStatus.BAD_REQUEST)

    def test_read_json_rejects_oversized_body_before_reading(self) -> None:
        handler = json_handler(str(app.MAX_JSON_BODY_BYTES + 1), b"")

        with self.assertRaises(app.ApiError) as error:
            handler.read_json()

        self.assertEqual(error.exception.status, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)

    def test_read_json_accepts_body_at_configured_limit(self) -> None:
        body = b'{"ok":true}'
        handler = json_handler(str(len(body)), body)

        self.assertEqual(handler.read_json(), {"ok": True})


class DatabaseBusyErrorTest(unittest.TestCase):
    def test_detects_sqlite_database_busy_errors(self) -> None:
        self.assertTrue(app.is_database_busy_error(sqlite3.OperationalError("database is locked")))
        self.assertTrue(app.is_database_busy_error(sqlite3.OperationalError("database table is locked")))
        self.assertTrue(app.is_database_busy_error(sqlite3.OperationalError("database is busy")))

    def test_ignores_other_operational_errors(self) -> None:
        self.assertFalse(app.is_database_busy_error(sqlite3.OperationalError("no such table: users")))
        self.assertFalse(app.is_database_busy_error(RuntimeError("database is locked")))


def credit_card_payload(name: str = "Cartao") -> dict:
    return {
        "name": name,
        "issuer": "Banco",
        "currency": "BRL",
        "limit": "1000,00",
        "closing_day": "10",
        "due_day": "20",
    }


def email_config_payload(sender: str) -> dict:
    return {
        "provider": "gmail",
        "sender": sender,
        "password": "app-password",
    }


def card_transaction_payload(card_id: int) -> dict:
    return {
        "credit_card_id": str(card_id),
        "type": "expense",
        "description": "Compra",
        "amount": "10,00",
        "date": "2026-06-15",
        "invoice_month": "2026-06",
        "category": "Mercado",
    }


def investment_account_payload(name: str) -> dict:
    return {
        "name": name,
        "bank_name": "Banco",
        "account_type": "investment",
        "currency": "BRL",
        "initial_balance": "1000,00",
    }


def portfolio_position_payload(account_id: int) -> dict:
    return {
        "account_id": str(account_id),
        "asset_type": "other",
        "asset_name": "Ativo teste",
        "acquisition_date": "2026-06-15",
        "quantity": "1",
        "unit_price": "100,00",
        "total_cost": "100,00",
    }


def spending_limit_payload(category_id: int) -> dict:
    return {
        "month": "2026-06",
        "category_id": str(category_id),
        "limit_amount": "500,00",
    }


def transaction_payload(account_id: int) -> dict:
    return {
        "type": "expense",
        "description": "Compra",
        "amount": "10,00",
        "date": "2026-06-15",
        "account_id": str(account_id),
        "category": "Mercado",
    }


def json_handler(content_length: str, body: bytes):
    handler = object.__new__(app.AppHandler)
    handler.headers = {"Content-Length": content_length}
    handler.rfile = BytesIO(body)
    return handler


if __name__ == "__main__":
    unittest.main()
