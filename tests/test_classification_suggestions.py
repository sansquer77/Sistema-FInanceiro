from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.auth import create_user
from financeiro.classification_suggestions import (
    get_classification_suggestion,
    normalize_description,
)
from financeiro.database import get_connection, initialize_database


class ClassificationSuggestionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"
        initialize_database()
        self.user = create_user("Alice", "alice@example.com", "correct-password")
        self.other_user = create_user("Bob", "bob@example.com", "correct-password")

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_normalization_preserves_numbers_and_ignores_accents_and_spacing(self) -> None:
        self.assertEqual(normalize_description("  VÁGA   55  "), "vaga 55")
        self.assertNotEqual(normalize_description("Vaga 55"), normalize_description("Vaga 56"))

    def test_exact_history_combines_account_and_card_transactions(self) -> None:
        category_id, subcategory_id, account_id, card_id = self.create_fixture(self.user["id"])
        self.insert_account_transaction(
            self.user["id"], account_id, category_id, subcategory_id, "Estacionamento"
        )
        self.insert_card_transaction(
            self.user["id"], card_id, category_id, subcategory_id, "ESTACIONÁMENTO"
        )

        result = get_classification_suggestion(self.user["id"], " estacionamento ", "expense")

        self.assertEqual(result["suggestion"]["category_name"], "Transporte MVP")
        self.assertEqual(result["suggestion"]["subcategory_name"], "Estacionamento MVP")
        self.assertEqual(result["suggestion"]["support"], 2)
        self.assertEqual(result["suggestion"]["confidence"], 1.0)

    def test_low_support_and_ambiguous_history_do_not_autofill(self) -> None:
        category_id, subcategory_id, account_id, _ = self.create_fixture(self.user["id"])
        self.insert_account_transaction(
            self.user["id"], account_id, category_id, subcategory_id, "Vaga 55"
        )
        self.assertIsNone(
            get_classification_suggestion(self.user["id"], "Vaga 55", "expense")["suggestion"]
        )

        other_category_id, other_subcategory_id = self.create_classification(
            self.user["id"], "Energia MVP", "Recarga MVP"
        )
        self.insert_account_transaction(
            self.user["id"], account_id, other_category_id, other_subcategory_id, "Vaga 55"
        )
        self.assertIsNone(
            get_classification_suggestion(self.user["id"], "Vaga 55", "expense")["suggestion"]
        )

    def test_history_is_isolated_by_user_and_group(self) -> None:
        category_id, subcategory_id, account_id, _ = self.create_fixture(self.user["id"])
        for _ in range(2):
            self.insert_account_transaction(
                self.user["id"], account_id, category_id, subcategory_id, "Vaga 55"
            )

        self.assertIsNotNone(
            get_classification_suggestion(self.user["id"], "Vaga 55", "expense")["suggestion"]
        )
        self.assertIsNone(
            get_classification_suggestion(self.other_user["id"], "Vaga 55", "expense")["suggestion"]
        )
        self.assertIsNone(
            get_classification_suggestion(self.user["id"], "Vaga 55", "income")["suggestion"]
        )

    def test_query_plan_uses_normalized_description_indexes(self) -> None:
        with get_connection() as conn:
            account_plan = conn.execute(
                """
                EXPLAIN QUERY PLAN
                SELECT category_id
                FROM transactions
                WHERE user_id = ? AND type = ? AND normalized_description = ?
                """,
                (self.user["id"], "expense", "vaga 55"),
            ).fetchall()
            card_plan = conn.execute(
                """
                EXPLAIN QUERY PLAN
                SELECT category_id
                FROM credit_card_transactions
                WHERE user_id = ? AND type = ? AND normalized_description = ?
                """,
                (self.user["id"], "expense", "vaga 55"),
            ).fetchall()
        self.assertIn("idx_transactions_user_type_normalized_description", " ".join(row["detail"] for row in account_plan))
        self.assertIn("idx_card_transactions_user_type_normalized_description", " ".join(row["detail"] for row in card_plan))

    def create_fixture(self, user_id: int) -> tuple[int, int, int, int]:
        category_id, subcategory_id = self.create_classification(
            user_id, "Transporte MVP", "Estacionamento MVP"
        )
        with get_connection() as conn:
            account_id = conn.execute(
                """
                INSERT INTO checking_accounts (
                    user_id, name, bank_name, account_type, currency,
                    initial_balance_cents, current_balance_cents
                ) VALUES (?, 'Conta MVP', 'Banco MVP', 'liquidity', 'BRL', 0, 0)
                """,
                (user_id,),
            ).lastrowid
            card_id = conn.execute(
                """
                INSERT INTO credit_cards (
                    user_id, name, issuer, currency, limit_cents, closing_day, due_day
                ) VALUES (?, 'Cartão MVP', 'Banco MVP', 'BRL', 100000, 10, 20)
                """,
                (user_id,),
            ).lastrowid
        return category_id, subcategory_id, account_id, card_id

    def create_classification(self, user_id: int, category: str, subcategory: str) -> tuple[int, int]:
        with get_connection() as conn:
            category_id = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, ?, 'expense')",
                (user_id, category),
            ).lastrowid
            subcategory_id = conn.execute(
                "INSERT INTO subcategories (user_id, category_id, name) VALUES (?, ?, ?)",
                (user_id, category_id, subcategory),
            ).lastrowid
        return category_id, subcategory_id

    def insert_account_transaction(
        self,
        user_id: int,
        account_id: int,
        category_id: int,
        subcategory_id: int,
        description: str,
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    date, account_id, category_id, subcategory_id
                ) VALUES (?, 'expense', ?, ?, 1000, '2026-07-23', ?, ?, ?)
                """,
                (
                    user_id,
                    description,
                    normalize_description(description),
                    account_id,
                    category_id,
                    subcategory_id,
                ),
            )

    def insert_card_transaction(
        self,
        user_id: int,
        card_id: int,
        category_id: int,
        subcategory_id: int,
        description: str,
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO credit_card_transactions (
                    user_id, credit_card_id, type, description, normalized_description,
                    amount_cents, date, invoice_month, category_id, subcategory_id
                ) VALUES (?, ?, 'expense', ?, ?, 1000, '2026-07-23', '2026-08', ?, ?)
                """,
                (
                    user_id,
                    card_id,
                    description,
                    normalize_description(description),
                    category_id,
                    subcategory_id,
                ),
            )


if __name__ == "__main__":
    unittest.main()
