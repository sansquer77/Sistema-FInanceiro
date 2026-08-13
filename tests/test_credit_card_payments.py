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
    is_invoice_paid,
    list_credit_card_transactions,
    move_credit_card_transaction_invoice,
    pay_credit_card_invoice,
    update_credit_card_transaction,
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

    def test_recurring_card_transaction_use_average_persists_to_all_occurrences(self) -> None:
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
        self.assertTrue(all(row["use_average"] for row in recurring_rows))

    def test_recurring_card_transaction_use_average_auto_recalculates_future_on_edit(self) -> None:
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

        first = create_credit_card_transaction(user["id"], {
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

        update_credit_card_transaction(user["id"], str(first["id"]), {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-06-15",
            "invoice_month": "2026-06",
            "category": "Servicos",
            "subcategory": "Energia",
        })

        rows = sorted(
            list_credit_card_transactions(user["id"]),
            key=lambda row: row["date"],
        )
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertEqual(recurring_rows[0]["amount"], "999.00")
        self.assertEqual(recurring_rows[0]["date"], "2026-06-15")
        self.assertTrue(all(row["amount"] == "200.00" for row in recurring_rows[1:]))
        self.assertTrue(all(row["use_average"] for row in recurring_rows))


class CreditCardPartialPaymentTest(unittest.TestCase):
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

    def _create_user_account_card(self, invoice_amount: str = "100,00") -> tuple[dict, dict, dict, dict]:
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
            "amount": invoice_amount,
            "date": "2026-06-10",
            "invoice_month": "2026-06",
            "category": "Mercado",
        })
        return user, account, card, card_transaction

    def test_partial_payment_debits_paid_amount_and_carries_remainder_to_next_invoice(self) -> None:
        # spec: cartoes v2.10 — criterio 169
        user, account, card, card_transaction = self._create_user_account_card("100,00")
        result = pay_credit_card_invoice(user["id"], {
            "credit_card_id": str(card["id"]),
            "invoice_month": card_transaction["invoice_month"],
            "account_id": str(account["id"]),
            "payment_date": "2026-06-20",
            "amount": "40,00",
        })

        self.assertEqual(result["payment"]["amount"], "40.00")
        self.assertEqual(result["transaction"]["amount"], "40.00")
        carried = result["carried_transaction"]
        self.assertEqual(carried["amount"], "60.00")
        self.assertEqual(carried["description"], "Saldo da fatura 06/2026")
        self.assertEqual(carried["invoice_month"], "2026-07")

        with get_connection() as conn:
            account_row = conn.execute(
                "SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                (account["id"],),
            ).fetchone()
            payment_row = conn.execute(
                "SELECT amount_cents FROM credit_card_payments WHERE credit_card_id = ?",
                (card["id"],),
            ).fetchone()
            carried_row = conn.execute(
                """
                SELECT
                    credit_card_transactions.description,
                    credit_card_transactions.invoice_month,
                    categories.name AS category_name
                FROM credit_card_transactions
                JOIN categories ON categories.id = credit_card_transactions.category_id
                WHERE credit_card_transactions.id = ?
                """,
                (carried["id"],),
            ).fetchone()

        self.assertEqual(account_row["current_balance_cents"], 96000)
        self.assertEqual(payment_row["amount_cents"], 4000)
        self.assertEqual(carried_row["description"], "Saldo da fatura 06/2026")
        self.assertEqual(carried_row["invoice_month"], "2026-07")
        self.assertEqual(carried_row["category_name"], "Empréstimos")

        with get_connection() as conn:
            self.assertTrue(is_invoice_paid(conn, user["id"], card["id"], "2026-06"))
            self.assertFalse(is_invoice_paid(conn, user["id"], card["id"], "2026-07"))

    def test_partial_payment_rejects_amount_equal_or_greater_than_balance(self) -> None:
        # spec: cartoes v2.10 — criterio 170
        user, account, card, card_transaction = self._create_user_account_card("100,00")
        for amount in ("100,00", "150,00"):
            with self.assertRaises(CreditCardError) as context:
                pay_credit_card_invoice(user["id"], {
                    "credit_card_id": str(card["id"]),
                    "invoice_month": card_transaction["invoice_month"],
                    "account_id": str(account["id"]),
                    "payment_date": "2026-06-20",
                    "amount": amount,
                })
            self.assertEqual(
                context.exception.message,
                "O valor informado cobre toda a fatura; use o pagamento integral.",
            )
        with get_connection() as conn:
            payment_count = conn.execute("SELECT COUNT(*) FROM credit_card_payments").fetchone()[0]
            transaction_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        self.assertEqual(payment_count, 0)
        self.assertEqual(transaction_count, 0)

    def test_partial_payment_rejects_zero_or_negative_amount(self) -> None:
        # spec: cartoes v2.10 — criterio 170
        user, account, card, card_transaction = self._create_user_account_card("100,00")
        with self.assertRaises(CreditCardError) as context:
            pay_credit_card_invoice(user["id"], {
                "credit_card_id": str(card["id"]),
                "invoice_month": card_transaction["invoice_month"],
                "account_id": str(account["id"]),
                "payment_date": "2026-06-20",
                "amount": "0,00",
            })
        self.assertEqual(context.exception.message, "Informe um valor maior que zero.")

    def test_partial_payment_closes_invoice_like_full_payment(self) -> None:
        # spec: cartoes v2.10 — criterio 171
        user, account, card, card_transaction = self._create_user_account_card("100,00")
        pay_credit_card_invoice(user["id"], {
            "credit_card_id": str(card["id"]),
            "invoice_month": card_transaction["invoice_month"],
            "account_id": str(account["id"]),
            "payment_date": "2026-06-20",
            "amount": "40,00",
        })
        with self.assertRaises(CreditCardError) as context:
            update_credit_card_transaction(user["id"], str(card_transaction["id"]), {
                "credit_card_id": str(card["id"]),
                "type": "expense",
                "description": "Editada",
                "amount": "80,00",
                "date": "2026-06-10",
                "invoice_month": "2026-06",
                "category": "Mercado",
            })
        self.assertIn("fechada", context.exception.message)

    def test_partial_carried_transaction_lists_in_next_invoice_and_can_be_moved(self) -> None:
        # spec: cartoes v2.10 — criterio 172
        user, account, card, card_transaction = self._create_user_account_card("100,00")
        result = pay_credit_card_invoice(user["id"], {
            "credit_card_id": str(card["id"]),
            "invoice_month": card_transaction["invoice_month"],
            "account_id": str(account["id"]),
            "payment_date": "2026-06-20",
            "amount": "40,00",
        })
        carried = result["carried_transaction"]

        next_invoice_rows = list_credit_card_transactions(user["id"], invoice_month="2026-07")
        self.assertEqual(len(next_invoice_rows), 1)
        self.assertEqual(next_invoice_rows[0]["id"], carried["id"])
        self.assertEqual(next_invoice_rows[0]["amount"], "60.00")
        self.assertEqual(next_invoice_rows[0]["description"], "Saldo da fatura 06/2026")

        moved = move_credit_card_transaction_invoice(user["id"], str(carried["id"]), "next")
        self.assertEqual(moved["invoice_month"], "2026-08")
        self.assertEqual(len(list_credit_card_transactions(user["id"], invoice_month="2026-07")), 0)
        self.assertEqual(len(list_credit_card_transactions(user["id"], invoice_month="2026-08")), 1)

    def test_partial_payment_still_creates_flagged_account_transaction(self) -> None:
        # spec: cartoes v2.10 — criterios 9 e 169
        user, account, card, card_transaction = self._create_user_account_card("100,00")
        result = pay_credit_card_invoice(user["id"], {
            "credit_card_id": str(card["id"]),
            "invoice_month": card_transaction["invoice_month"],
            "account_id": str(account["id"]),
            "payment_date": "2026-06-20",
            "amount": "40,00",
        })
        payment_transaction = result["transaction"]
        self.assertTrue(payment_transaction["is_credit_card_payment"])
        listed = next(
            transaction
            for transaction in list_transactions(user["id"], month="2026-06")
            if transaction["id"] == payment_transaction["id"]
        )
        self.assertTrue(listed["is_credit_card_payment"])
        self.assertEqual(listed["amount"], "40.00")


if __name__ == "__main__":
    unittest.main()
