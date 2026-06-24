from __future__ import annotations

import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path
from unittest import mock

import app
from financeiro import database
from financeiro.accounts import AccountError, create_checking_account, update_checking_account
from financeiro.auth import AuthError, create_user, login_user, request_password_reset
from financeiro.categories import ClassificationError, create_category, update_category
from financeiro.credit_cards import CreditCardError, create_credit_card, update_credit_card
from financeiro.database import initialize_database


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


if __name__ == "__main__":
    unittest.main()
