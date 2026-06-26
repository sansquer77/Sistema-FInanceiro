from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.credit_cards import (
    CreditCardError,
    create_credit_card,
    create_credit_card_transaction,
    pay_credit_card_invoice,
)
from financeiro.database import get_connection, initialize_database


class CreditCardPaymentAtomicityTest(unittest.TestCase):
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

    def test_invoice_payment_rolls_back_account_transaction_when_payment_insert_fails(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        card = create_credit_card(user["id"], {
            "name": "Cartao",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "2000,00",
            "closing_day": "28",
            "due_day": "10",
            "preferred_payment_account_id": str(account["id"]),
        })
        card_transaction = create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Compra",
            "amount": "100,00",
            "date": "2026-06-10",
            "invoice_month": "2026-06",
            "category": "Mercado",
        })

        with mock.patch(
            "financeiro.credit_cards.validate_preferred_payment_account",
            side_effect=CreditCardError("Falha simulada."),
        ):
            with self.assertRaises(CreditCardError):
                pay_credit_card_invoice(user["id"], {
                    "credit_card_id": str(card["id"]),
                    "invoice_month": card_transaction["invoice_month"],
                    "account_id": str(account["id"]),
                    "payment_date": "2026-06-20",
                })

        with get_connection() as conn:
            transaction_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            payment_count = conn.execute("SELECT COUNT(*) FROM credit_card_payments").fetchone()[0]
            account_row = conn.execute(
                "SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                (account["id"],),
            ).fetchone()

        self.assertEqual(transaction_count, 0)
        self.assertEqual(payment_count, 0)
        self.assertEqual(account_row["current_balance_cents"], 100000)


if __name__ == "__main__":
    unittest.main()
