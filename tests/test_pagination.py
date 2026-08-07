from __future__ import annotations

import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app
from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.credit_cards import create_credit_card, create_credit_card_transaction
from financeiro.database import initialize_database
from financeiro.transactions import create_transaction, list_transactions


class ListPaginationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-pagination.db"
        initialize_database()

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def _handler(self, path: str, user: dict | None = None) -> app.AppHandler:
        handler = object.__new__(app.AppHandler)
        handler.headers = {
            "Host": "sistema-financeiro.localhost:8020",
            "Origin": "http://sistema-financeiro.localhost:8020",
        }
        handler.path = path
        handler.send_json = mock.Mock()
        return handler

    def _context(self, user: dict | None = None):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(app, "PORT", 8020))
        stack.enter_context(mock.patch.object(app, "PUBLIC_URL", "http://sistema-financeiro.localhost:8020"))
        if user is None:
            stack.enter_context(mock.patch.object(app.AppHandler, "get_cookie", return_value=None))
        else:
            stack.enter_context(mock.patch.object(app.AppHandler, "require_user", return_value=user))
        return stack

    def _account(self, user_id: int) -> dict:
        return create_checking_account(user_id, {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })

    def _transaction(self, user_id: int, account_id: int, index: int) -> dict:
        return create_transaction(user_id, {
            "account_id": str(account_id),
            "type": "expense",
            "description": f"Despesa {index:03d}",
            "amount": "10,00",
            "date": f"2026-01-{index % 28 + 1:02d}",
            "category": "Mercado",
        })

    def _card(self, user_id: int, account_id: int) -> dict:
        return create_credit_card(user_id, {
            "name": "Cartao",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "2000,00",
            "closing_day": "28",
            "due_day": "10",
            "preferred_payment_account_id": str(account_id),
        })

    def test_transactions_endpoint_paginates_with_has_more(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = self._account(user["id"])
        for index in range(1, 6):
            self._transaction(user["id"], account["id"], index)

        with self._context(user):
            handler = self._handler("/api/transactions?limit=2&offset=0")
            handler.handle_list_transactions()
            payload = handler.send_json.call_args[0][0]

        self.assertEqual(len(payload["transactions"]), 2)
        self.assertTrue(payload["has_more"])
        self.assertEqual(payload["limit"], 2)
        self.assertEqual(payload["offset"], 0)

        with self._context(user):
            handler = self._handler("/api/transactions?limit=2&offset=4")
            handler.handle_list_transactions()
            payload = handler.send_json.call_args[0][0]

        self.assertEqual(len(payload["transactions"]), 1)
        self.assertFalse(payload["has_more"])

    def test_transactions_endpoint_keeps_month_and_account_filters(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = self._account(user["id"])
        for index in range(1, 6):
            self._transaction(user["id"], account["id"], index)

        with self._context(user):
            handler = self._handler("/api/transactions?month=2026-01&limit=3")
            handler.handle_list_transactions()
            payload = handler.send_json.call_args[0][0]

        self.assertEqual(len(payload["transactions"]), 3)
        self.assertTrue(payload["has_more"])

    def test_month_account_slice_keeps_history_for_cumulative_balance(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = self._account(user["id"])
        create_transaction(user["id"], {
            "account_id": str(account["id"]),
            "type": "income",
            "description": "Salario de dezembro",
            "amount": "4200,00",
            "date": "2025-12-05",
            "category": "Salario",
        })
        create_transaction(user["id"], {
            "account_id": str(account["id"]),
            "type": "expense",
            "description": "Gasto de janeiro",
            "amount": "200,00",
            "date": "2026-01-10",
            "category": "Mercado",
        })

        rows = list_transactions(user["id"], month="2026-01", account_id=account["id"])
        self.assertEqual(len(rows), 2)
        self.assertIn("2025-12-05", [row["date"] for row in rows])

    def test_transactions_endpoint_clamps_oversized_limit(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = self._account(user["id"])
        self._transaction(user["id"], account["id"], 1)

        with self._context(user):
            handler = self._handler("/api/transactions?limit=999999")
            handler.handle_list_transactions()
            payload = handler.send_json.call_args[0][0]

        self.assertLessEqual(payload["limit"], 5000)

    def test_credit_card_transactions_endpoint_paginates(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = self._account(user["id"])
        card = self._card(user["id"], account["id"])
        for index in range(1, 6):
            create_credit_card_transaction(user["id"], {
                "credit_card_id": str(card["id"]),
                "type": "expense",
                "description": f"Compra {index:03d}",
                "amount": "10,00",
                "date": f"2026-01-{index:02d}",
                "invoice_month": "2026-01",
                "category": "Mercado",
            })

        with self._context(user):
            handler = self._handler("/api/credit-card-transactions?limit=2")
            handler.handle_list_credit_card_transactions()
            payload = handler.send_json.call_args[0][0]

        self.assertEqual(len(payload["transactions"]), 2)
        self.assertTrue(payload["has_more"])

    def test_credit_card_payments_endpoint_paginates(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = self._account(user["id"])
        card = self._card(user["id"], account["id"])
        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Compra",
            "amount": "100,00",
            "date": "2026-01-10",
            "invoice_month": "2026-01",
            "category": "Mercado",
        })
        from financeiro.credit_cards import pay_credit_card_invoice
        pay_credit_card_invoice(user["id"], {
            "credit_card_id": str(card["id"]),
            "invoice_month": "2026-01",
            "account_id": str(account["id"]),
            "payment_date": "2026-01-20",
        })

        with self._context(user):
            handler = self._handler("/api/credit-card-payments?limit=1")
            handler.handle_list_credit_card_payments()
            payload = handler.send_json.call_args[0][0]

        self.assertEqual(len(payload["payments"]), 1)
        self.assertFalse(payload["has_more"])

    def test_transactions_list_function_bounds_without_breaking_internal_callers(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = self._account(user["id"])
        for index in range(1, 6):
            self._transaction(user["id"], account["id"], index)

        all_rows = list_transactions(user["id"])
        self.assertEqual(len(all_rows), 5)

        page = list_transactions(user["id"], limit=2, offset=0)
        self.assertEqual(len(page), 2)


if __name__ == "__main__":
    unittest.main()
