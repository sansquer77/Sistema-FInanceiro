from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.auth import create_user
from financeiro.categories import create_tag, delete_tag, list_tags, update_tag
from financeiro.database import initialize_database


class CategorySqlTest(unittest.TestCase):
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

    def test_tag_crud_uses_explicit_allowed_sql_paths(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")

        tag = create_tag(user["id"], "Revisar")
        updated = update_tag(user["id"], str(tag["id"]), "Conferido")
        delete_tag(user["id"], str(tag["id"]))

        self.assertEqual(updated["name"], "Conferido")
        self.assertEqual(list_tags(user["id"]), [])


if __name__ == "__main__":
    unittest.main()
