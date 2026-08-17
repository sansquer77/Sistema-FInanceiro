from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import financeiro.transactions as transactions_module
from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import initialize_database
from financeiro.transactions import create_transaction, list_transactions, update_transaction


class TransactionSeriesUpdateTest(unittest.TestCase):
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

    def test_future_series_update_reuses_invariant_lookups(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        first = create_transaction(user["id"], {
            "type": "expense",
            "description": "Assinatura",
            "amount": "10,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "tags": "Recorrente",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "recurrence_count": "5",
        })

        with (
            mock.patch(
                "financeiro.transactions.get_active_account",
                wraps=transactions_module.get_active_account,
            ) as get_active_account,
            mock.patch(
                "financeiro.transactions.resolve_transaction_category",
                wraps=transactions_module.resolve_transaction_category,
            ) as resolve_transaction_category,
            mock.patch(
                "financeiro.transactions.get_or_create_tag",
                wraps=transactions_module.get_or_create_tag,
            ) as get_or_create_tag,
        ):
            update_transaction(user["id"], str(first["id"]), {
                "type": "expense",
                "description": "Assinatura atualizada",
                "amount": "20,00",
                "date": "2026-01-12",
                "account_id": str(account["id"]),
                "category": "Servicos",
                "tags": "Recorrente",
                "apply_to_future": "true",
            })

        transactions = list_transactions(user["id"], account_id=account["id"])

        self.assertEqual(len(transactions), 5)
        self.assertTrue(all(row["amount"] == "20.00" for row in transactions))
        self.assertLessEqual(get_active_account.call_count, 2)
        self.assertLessEqual(resolve_transaction_category.call_count, 2)
        self.assertLessEqual(get_or_create_tag.call_count, 2)

    def test_installment_transaction_splits_total_amount_across_installments(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        create_transaction(user["id"], {
            "type": "expense",
            "description": "Compra parcelada",
            "amount": "500,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Compras",
            "series_kind": "installment",
            "installment_count": "5",
        })

        rows = sorted(list_transactions(user["id"], account_id=account["id"]), key=lambda row: row["installment_index"])

        self.assertEqual([row["amount"] for row in rows], ["100.00", "100.00", "100.00", "100.00", "100.00"])
        self.assertEqual([row["description"] for row in rows], [
            "Compra parcelada (1/5)",
            "Compra parcelada (2/5)",
            "Compra parcelada (3/5)",
            "Compra parcelada (4/5)",
            "Compra parcelada (5/5)",
        ])

    def test_single_transaction_can_be_edited_to_installment_series(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        transaction = create_transaction(user["id"], {
            "type": "expense",
            "description": "Compra",
            "amount": "300,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Compras",
        })

        updated = update_transaction(user["id"], str(transaction["id"]), {
            "type": "expense",
            "description": "Compra parcelada",
            "amount": "300,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Compras",
            "series_kind": "installment",
            "installment_count": "3",
        })

        rows = sorted(list_transactions(user["id"], account_id=account["id"]), key=lambda row: row["installment_index"])
        self.assertEqual(updated["series_kind"], "installment")
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["amount"] for row in rows], ["100.00", "100.00", "100.00"])
        self.assertEqual([row["description"] for row in rows], [
            "Compra parcelada (1/3)",
            "Compra parcelada (2/3)",
            "Compra parcelada (3/3)",
        ])
        self.assertEqual(len({row["series_id"] for row in rows}), 1)

    def test_single_transaction_can_be_edited_to_recurring_series(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        transaction = create_transaction(user["id"], {
            "type": "expense",
            "description": "Assinatura",
            "amount": "30,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
        })

        update_transaction(user["id"], str(transaction["id"]), {
            "type": "expense",
            "description": "Assinatura",
            "amount": "30,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "recurrence_count": "4",
        })

        rows = sorted(list_transactions(user["id"], account_id=account["id"]), key=lambda row: row["date"])
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["series_kind"] == "recurring" for row in rows))
        self.assertEqual([row["date"] for row in rows], [
            "2026-01-10",
            "2026-02-10",
            "2026-03-10",
            "2026-04-10",
        ])

    def test_recurring_transaction_keeps_full_amount_on_each_occurrence(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        create_transaction(user["id"], {
            "type": "expense",
            "description": "Assinatura recorrente",
            "amount": "500,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "recurrence_count": "5",
        })

        rows = list_transactions(user["id"], account_id=account["id"])

        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["amount"] == "500.00" for row in rows))

    def test_recurring_transaction_uses_default_120_occurrences(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })

        create_transaction(user["id"], {
            "type": "expense",
            "description": "Assinatura recorrente",
            "amount": "500,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
        })

        rows = list_transactions(user["id"], account_id=account["id"])

        self.assertEqual(len(rows), 120)
        self.assertTrue(all(row["amount"] == "500.00" for row in rows))

    def test_recurring_transaction_with_average_uses_historical_average(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        for amount, date_value in [("100,00", "2025-10-10"), ("200,00", "2025-11-10"), ("300,00", "2025-12-10")]:
            create_transaction(user["id"], {
                "type": "expense",
                "description": "Conta de luz",
                "amount": amount,
                "date": date_value,
                "account_id": str(account["id"]),
                "category": "Servicos",
                "subcategory": "Energia",
            })

        create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        rows = list_transactions(user["id"], account_id=account["id"])
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertTrue(all(row["amount"] == "200.00" for row in recurring_rows))

    def test_recurring_transaction_average_ignores_different_category_or_subcategory(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "300,00",
            "date": "2025-12-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
        })
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "900,00",
            "date": "2025-12-11",
            "account_id": str(account["id"]),
            "category": "Outros",
            "subcategory": "Energia",
        })
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "900,00",
            "date": "2025-12-12",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Outros",
        })

        create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        rows = list_transactions(user["id"], account_id=account["id"])
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertTrue(all(row["amount"] == "300.00" for row in recurring_rows))

    def test_recurring_transaction_with_average_falls_back_to_form_value_without_history(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        create_transaction(user["id"], {
            "type": "expense",
            "description": "Nova assinatura",
            "amount": "150,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        rows = list_transactions(user["id"], account_id=account["id"])

        self.assertEqual(len(rows), 120)
        self.assertTrue(all(row["amount"] == "150.00" for row in rows))

    def test_recurring_transaction_use_average_persists_to_all_occurrences(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        rows = list_transactions(user["id"], account_id=account["id"])
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertTrue(all(row["use_average"] for row in recurring_rows))

    def test_recurring_transaction_use_average_recalculates_future_on_edit_with_future_scope(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        for amount, date_value in [("100,00", "2025-10-10"), ("200,00", "2025-11-10"), ("300,00", "2025-12-10")]:
            create_transaction(user["id"], {
                "type": "expense",
                "description": "Conta de luz",
                "amount": amount,
                "date": date_value,
                "account_id": str(account["id"]),
                "category": "Servicos",
                "subcategory": "Energia",
            })

        first = create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        update_transaction(user["id"], str(first["id"]), {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-01-15",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "apply_to_future": "true",
        })

        rows = sorted(
            list_transactions(user["id"], account_id=account["id"]),
            key=lambda row: row["date"],
        )
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertEqual(recurring_rows[0]["amount"], "999.00")
        self.assertEqual(recurring_rows[0]["date"], "2026-01-15")
        self.assertTrue(all(row["amount"] == "200.00" for row in recurring_rows[1:]))
        self.assertTrue(all(row["use_average"] for row in recurring_rows))

    def test_recurring_transaction_use_average_unchanged_edit_does_not_cascade(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        first = create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        update_transaction(user["id"], str(first["id"]), {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "777,00",
            "date": "2026-01-15",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
        })

        rows = sorted(
            list_transactions(user["id"], account_id=account["id"]),
            key=lambda row: row["date"],
        )
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertEqual(recurring_rows[0]["amount"], "777.00")
        self.assertEqual(recurring_rows[0]["date"], "2026-01-15")
        self.assertTrue(all(row["amount"] == "999.00" for row in recurring_rows[1:]))
        self.assertTrue(all(row["use_average"] for row in recurring_rows))

    def test_recurring_transaction_use_average_ignores_future_occurrences_when_recalculating(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        first = create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "123,00",
            "date": "2026-08-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        rows = sorted(
            list_transactions(user["id"], account_id=account["id"]),
            key=lambda row: row["date"],
        )
        september = next(row for row in rows if row["series_kind"] == "recurring" and row["date"] == "2026-09-10")

        update_transaction(user["id"], str(september["id"]), {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "159,00",
            "date": "2026-09-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "apply_to_future": "true",
        })

        rows = sorted(
            list_transactions(user["id"], account_id=account["id"]),
            key=lambda row: row["date"],
        )
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertEqual(recurring_rows[0]["amount"], "123.00")
        self.assertEqual(recurring_rows[1]["amount"], "159.00")
        self.assertTrue(all(row["amount"] == "141.00" for row in recurring_rows[2:]))

    def test_recurring_transaction_use_average_activated_on_edit_recalculates_future(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        for amount, date_value in [("100,00", "2025-10-10"), ("200,00", "2025-11-10"), ("300,00", "2025-12-10")]:
            create_transaction(user["id"], {
                "type": "expense",
                "description": "Conta de luz",
                "amount": amount,
                "date": date_value,
                "account_id": str(account["id"]),
                "category": "Servicos",
                "subcategory": "Energia",
            })

        first = create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
        })

        update_transaction(user["id"], str(first["id"]), {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-01-15",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "use_average": "true",
        })

        rows = sorted(
            list_transactions(user["id"], account_id=account["id"]),
            key=lambda row: row["date"],
        )
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertEqual(recurring_rows[0]["amount"], "999.00")
        self.assertEqual(recurring_rows[0]["date"], "2026-01-15")
        self.assertTrue(all(row["amount"] == "200.00" for row in recurring_rows[1:]))
        self.assertTrue(all(row["use_average"] for row in recurring_rows))

    def test_recurring_transaction_use_average_deactivated_on_edit_keeps_value(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "10000,00",
        })

        for amount, date_value in [("100,00", "2025-10-10"), ("200,00", "2025-11-10"), ("300,00", "2025-12-10")]:
            create_transaction(user["id"], {
                "type": "expense",
                "description": "Conta de luz",
                "amount": amount,
                "date": date_value,
                "account_id": str(account["id"]),
                "category": "Servicos",
                "subcategory": "Energia",
            })

        first = create_transaction(user["id"], {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "999,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "series_kind": "recurring",
            "recurrence_frequency": "monthly",
            "use_average": "true",
        })

        update_transaction(user["id"], str(first["id"]), {
            "type": "expense",
            "description": "Conta de luz",
            "amount": "777,00",
            "date": "2026-01-15",
            "account_id": str(account["id"]),
            "category": "Servicos",
            "subcategory": "Energia",
            "use_average": "0",
            "apply_to_future": "true",
        })

        rows = sorted(
            list_transactions(user["id"], account_id=account["id"]),
            key=lambda row: row["date"],
        )
        recurring_rows = [row for row in rows if row["series_kind"] == "recurring"]

        self.assertEqual(len(recurring_rows), 120)
        self.assertEqual(recurring_rows[0]["amount"], "777.00")
        self.assertTrue(all(row["amount"] == "777.00" for row in recurring_rows[1:]))
        self.assertTrue(all(not row["use_average"] for row in recurring_rows))


if __name__ == "__main__":
    unittest.main()
