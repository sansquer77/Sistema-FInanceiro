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
    list_credit_card_transactions,
    pay_credit_card_invoice,
)
from financeiro.categories import get_category_evolution
from financeiro.database import get_connection, initialize_database
from financeiro.transactions import list_transactions


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

    def test_invoice_payment_is_flagged_and_excluded_from_category_evolution(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        card = create_credit_card(user["id"], {
            "name": "The One",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "2000,00",
            "closing_day": "28",
            "due_day": "10",
            "preferred_payment_account_id": str(account["id"]),
        })
        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Lavagem",
            "amount": "100,00",
            "date": "2026-07-10",
            "invoice_month": "2026-07",
            "category": "Transporte",
            "subcategory": "Lavagem e cuidados com o carro",
        })

        payment_result = pay_credit_card_invoice(user["id"], {
            "credit_card_id": str(card["id"]),
            "invoice_month": "2026-07",
            "account_id": str(account["id"]),
            "payment_date": "2026-07-20",
        })

        payment_transaction = payment_result["transaction"]
        self.assertTrue(payment_transaction["is_credit_card_payment"])

        listed_payment = next(
            transaction
            for transaction in list_transactions(user["id"], month="2026-07")
            if transaction["id"] == payment_transaction["id"]
        )
        self.assertTrue(listed_payment["is_credit_card_payment"])

        with get_connection() as conn:
            account_row = conn.execute(
                "SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                (account["id"],),
            ).fetchone()
            payment_category = conn.execute(
                """
                SELECT id
                FROM categories
                WHERE user_id = ? AND name = 'Serviços Financeiros e Impostos'
                """,
                (user["id"],),
            ).fetchone()

        self.assertEqual(account_row["current_balance_cents"], 90000)
        evolution = get_category_evolution(user["id"], payment_category["id"], period="all")
        self.assertEqual(evolution, [])

    def test_installment_card_transaction_splits_total_amount_across_installments(self) -> None:
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

        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Compra parcelada",
            "amount": "500,00",
            "date": "2026-06-10",
            "invoice_month": "2026-06",
            "category": "Compras",
            "series_kind": "installment",
            "installment_count": "5",
        })

        rows = sorted(list_credit_card_transactions(user["id"]), key=lambda row: row["installment_index"])

        self.assertEqual([row["amount"] for row in rows], ["100.00", "100.00", "100.00", "100.00", "100.00"])
        self.assertEqual([row["installment_index"] for row in rows], [1, 2, 3, 4, 5])

    def test_recurring_card_transaction_keeps_full_amount_on_each_occurrence(self) -> None:
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

        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Assinatura recorrente",
            "amount": "500,00",
            "date": "2026-06-10",
            "invoice_month": "2026-06",
            "category": "Servicos",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "installment_count": "5",
        })

        rows = list_credit_card_transactions(user["id"])

        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["amount"] == "500.00" for row in rows))

    def test_card_transactions_can_be_filtered_by_invoice_month(self) -> None:
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

        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Compra Junho",
            "amount": "100,00",
            "date": "2026-06-10",
            "invoice_month": "2026-06",
            "category": "Compras",
        })
        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Compra Julho",
            "amount": "200,00",
            "date": "2026-07-10",
            "invoice_month": "2026-07",
            "category": "Compras",
        })

        all_rows = list_credit_card_transactions(user["id"])
        june_rows = list_credit_card_transactions(user["id"], invoice_month="2026-06")

        self.assertEqual(len(all_rows), 2)
        self.assertEqual(len(june_rows), 1)
        self.assertEqual(june_rows[0]["description"], "Compra Junho")
        self.assertEqual(june_rows[0]["invoice_month"], "2026-06")

    def test_card_transaction_before_closing_uses_next_invoice_when_calculated_invoice_is_paid(self) -> None:
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
        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Compra antiga",
            "amount": "100,00",
            "date": "2026-07-10",
            "invoice_month": "2026-07",
            "category": "Compras",
        })
        pay_credit_card_invoice(user["id"], {
            "credit_card_id": str(card["id"]),
            "invoice_month": "2026-07",
            "account_id": str(account["id"]),
            "payment_date": "2026-07-20",
        })

        transaction = create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Compra depois do pagamento",
            "amount": "50,00",
            "date": "2026-07-15",
            "invoice_month": "2026-07",
            "category": "Compras",
        })

        self.assertEqual(transaction["invoice_month"], "2026-08")

    def test_recurring_card_transaction_uses_default_120_occurrences(self) -> None:
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
            "limit": "20000,00",
            "closing_day": "28",
            "due_day": "10",
            "preferred_payment_account_id": str(account["id"]),
        })

        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Assinatura recorrente",
            "amount": "500,00",
            "date": "2026-06-10",
            "invoice_month": "2026-06",
            "category": "Servicos",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
        })

        rows = list_credit_card_transactions(user["id"])

        self.assertEqual(len(rows), 120)
        self.assertTrue(all(row["amount"] == "500.00" for row in rows))

    def test_recurring_card_transaction_with_average_uses_historical_average(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })
        card = create_credit_card(user["id"], {
            "name": "Cartao",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "20000,00",
            "closing_day": "28",
            "due_day": "10",
            "preferred_payment_account_id": str(account["id"]),
        })

        for amount, date_value in [("100,00", "2025-10-10"), ("200,00", "2025-11-10"), ("300,00", "2025-12-10")]:
            create_credit_card_transaction(user["id"], {
                "credit_card_id": str(card["id"]),
                "type": "expense",
                "description": "Conta de luz",
                "amount": amount,
                "date": date_value,
                "invoice_month": date_value[:7],
                "category": "Servicos",
                "subcategory": "Energia",
            })

        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-06-10",
            "invoice_month": "2026-06",
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        rows = list_credit_card_transactions(user["id"])
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertTrue(all(row["amount"] == "200.00" for row in recurring_rows))

    def test_recurring_card_transaction_average_ignores_different_category_or_subcategory(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })
        card = create_credit_card(user["id"], {
            "name": "Cartao",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "20000,00",
            "closing_day": "28",
            "due_day": "10",
            "preferred_payment_account_id": str(account["id"]),
        })

        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Conta de luz",
            "amount": "300,00",
            "date": "2025-12-10",
            "invoice_month": "2025-12",
            "category": "Servicos",
            "subcategory": "Energia",
        })
        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Conta de luz",
            "amount": "900,00",
            "date": "2025-12-11",
            "invoice_month": "2025-12",
            "category": "Outros",
            "subcategory": "Energia",
        })
        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Conta de luz",
            "amount": "900,00",
            "date": "2025-12-12",
            "invoice_month": "2025-12",
            "category": "Servicos",
            "subcategory": "Outros",
        })

        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-06-10",
            "invoice_month": "2026-06",
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        rows = list_credit_card_transactions(user["id"])
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertTrue(all(row["amount"] == "300.00" for row in recurring_rows))


if __name__ == "__main__":
    unittest.main()
