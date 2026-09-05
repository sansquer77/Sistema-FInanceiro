from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.classification_suggestions import normalize_description
from financeiro.global_search import GlobalSearchError, search_global


class GlobalSearchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.old_paths = database.DATA_DIR, database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test.db"
        database.initialize_database()
        self.user = create_user("Alice", "alice@example.com", "correct-password")
        self.other = create_user("Bob", "bob@example.com", "correct-password")
        self.account = create_checking_account(self.user["id"], {
            "name": "Conta", "bank_name": "Banco", "currency": "BRL", "initial_balance": "0,00",
        })
        self.other_account = create_checking_account(self.other["id"], {
            "name": "Outra", "bank_name": "Banco", "currency": "BRL", "initial_balance": "0,00",
        })

    def tearDown(self) -> None:
        database.DATA_DIR, database.DB_PATH = self.old_paths
        self.tempdir.cleanup()

    def insert_transaction(self, user_id: int, account_id: int, description: str, date: str) -> None:
        with database.get_connection() as conn:
            conn.execute(
                """INSERT INTO transactions
                   (user_id, type, description, normalized_description, amount_cents, date, account_id)
                   VALUES (?, 'expense', ?, ?, 1000, ?, ?)""",
                (user_id, description, normalize_description(description), date, account_id),
            )

    def test_search_finds_old_competences_and_isolates_user(self) -> None:
        self.insert_transaction(self.user["id"], self.account["id"], "Aluguel apartamento antigo", "2024-01-10")
        self.insert_transaction(self.other["id"], self.other_account["id"], "Aluguel secreto", "2025-01-10")

        response = search_global(self.user["id"], "aluguel")

        self.assertEqual([row["title"] for row in response["results"]], ["Aluguel apartamento antigo"])
        self.assertEqual(response["results"][0]["month"], "2024-01")

    def test_search_is_limited_paginated_and_treats_wildcards_literally(self) -> None:
        for index in range(4):
            self.insert_transaction(self.user["id"], self.account["id"], f"Assinatura {index}", f"2026-0{index + 1}-10")

        first = search_global(self.user["id"], "assinatura", limit=2)
        second = search_global(self.user["id"], "assinatura", limit=2, offset=2)

        self.assertTrue(first["has_more"])
        self.assertEqual(len(first["results"]), 2)
        self.assertEqual(len(second["results"]), 2)
        self.assertEqual(search_global(self.user["id"], "%%")["results"], [])

    def test_short_or_oversized_queries_are_rejected(self) -> None:
        for query in ("a", "x" * 101):
            with self.assertRaises(GlobalSearchError):
                search_global(self.user["id"], query)
