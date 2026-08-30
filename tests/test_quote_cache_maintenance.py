from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from financeiro import database


class QuoteCacheMaintenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "finance.db"
        database.initialize_database()
        self.now = datetime(2026, 8, 30, 12, 0, 0)

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_prunes_only_entries_older_than_stale_retention(self) -> None:
        self.insert_cache("bcb:old", self.now - timedelta(days=31), self.now - timedelta(days=40))
        self.insert_cache("bcb:recent-stale", self.now - timedelta(days=29), self.now - timedelta(days=30))
        self.insert_cache("bcb:valid", self.now + timedelta(hours=1), self.now)

        result = database.maintain_quote_cache(now=self.now)

        self.assertEqual(result["deleted"], 1)
        self.assertEqual(self.keys(), {"bcb:recent-stale", "bcb:valid"})

    def test_provider_limit_preserves_valid_and_most_recent_entries(self) -> None:
        for index in range(5):
            self.insert_cache(
                f"bcb:{index}",
                self.now - timedelta(days=1),
                self.now - timedelta(hours=index),
            )
        self.insert_cache("bcb:valid", self.now + timedelta(days=1), self.now - timedelta(days=10))

        with mock.patch.object(database, "QUOTE_CACHE_MAX_ENTRIES_PER_PROVIDER", 3):
            result = database.maintain_quote_cache(now=self.now)

        self.assertEqual(result["deleted"], 3)
        self.assertEqual(self.keys(), {"bcb:valid", "bcb:0", "bcb:1"})

    def test_total_limit_is_applied_across_providers(self) -> None:
        for index, provider in enumerate(("bcb", "yahoo", "coingecko", "maisretorno")):
            self.insert_cache(
                f"{provider}:{index}",
                self.now - timedelta(days=1),
                self.now - timedelta(hours=index),
            )

        with mock.patch.object(database, "QUOTE_CACHE_MAX_ENTRIES", 3):
            result = database.maintain_quote_cache(now=self.now)

        self.assertEqual(result["deleted"], 1)
        self.assertEqual(len(self.keys()), 3)
        self.assertNotIn("maisretorno:3", self.keys())

    def test_vacuum_runs_only_when_configured_thresholds_are_met(self) -> None:
        self.insert_cache("bcb:old", self.now - timedelta(days=31), self.now - timedelta(days=40), "x" * 20000)

        with (
            mock.patch.object(database, "QUOTE_CACHE_VACUUM_MIN_FREE_BYTES", 0),
            mock.patch.object(database, "QUOTE_CACHE_VACUUM_MIN_FREE_RATIO", 0),
        ):
            result = database.maintain_quote_cache(now=self.now)

        self.assertTrue(result["vacuumed"])
        self.assertEqual(self.keys(), set())

    def test_database_error_during_cache_maintenance_is_non_blocking(self) -> None:
        with mock.patch.object(database, "get_connection", side_effect=sqlite3.OperationalError("falha")):
            result = database.maintain_quote_cache(now=self.now)

        self.assertEqual(result["deleted"], 0)
        self.assertFalse(result["vacuumed"])

    def insert_cache(self, key: str, expires_at: datetime, updated_at: datetime, payload: str = "{}") -> None:
        with closing(sqlite3.connect(database.DB_PATH)) as conn:
            conn.execute(
                """
                INSERT INTO quote_cache (cache_key, payload_json, expires_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, payload, expires_at.isoformat(), updated_at.isoformat()),
            )
            conn.commit()

    def keys(self) -> set[str]:
        with closing(sqlite3.connect(database.DB_PATH)) as conn:
            return {row[0] for row in conn.execute("SELECT cache_key FROM quote_cache")}


if __name__ == "__main__":
    unittest.main()
