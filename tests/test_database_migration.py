from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

from financeiro import database


class DatabaseV2MigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "finance.db"

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_new_database_starts_at_v2_schema_version(self) -> None:
        database.initialize_database()

        self.assertTrue(database.DB_PATH.exists())
        self.assertEqual(self.schema_version(database.DB_PATH), database.V2_SCHEMA_VERSION)
        self.assertFalse(self.backup_path.exists())

    def test_reopening_v2_database_skips_schema_compatibility(self) -> None:
        database.initialize_database()

        with mock.patch.object(database, "_initialize_schema") as initialize_schema:
            database.initialize_database()

        initialize_schema.assert_not_called()
        self.assertFalse(self.backup_path.exists())

    def test_schema_version_is_read_from_path_with_spaces(self) -> None:
        spaced_dir = database.DATA_DIR / "Sistema Financeiro v2"
        spaced_dir.mkdir()
        spaced_db = spaced_dir / "finance.db"
        with closing(sqlite3.connect(spaced_db)) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA user_version = 0")
            conn.commit()

        self.assertEqual(database._read_schema_version(spaced_db), 0)

    def test_legacy_database_is_preserved_and_promoted_under_stable_name(self) -> None:
        self.create_legacy_database()

        database.initialize_database()

        self.assertTrue(database.DB_PATH.exists())
        self.assertTrue(self.backup_path.exists())
        self.assertEqual(self.schema_version(database.DB_PATH), database.V2_SCHEMA_VERSION)
        self.assertEqual(self.schema_version(self.backup_path), 0)
        with closing(sqlite3.connect(database.DB_PATH)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
            self.assertEqual(
                conn.execute("SELECT payload_enc FROM secure_configs").fetchone()[0],
                '{"ciphertext":"segredo-criptografado"}',
            )

    def test_reopening_migrated_database_does_not_replace_backup(self) -> None:
        self.create_legacy_database()
        database.initialize_database()
        original_backup = self.backup_path.read_bytes()

        database.initialize_database()

        self.assertEqual(self.backup_path.read_bytes(), original_backup)

    def test_existing_backup_blocks_legacy_migration_without_overwrite(self) -> None:
        self.create_legacy_database()
        self.backup_path.write_bytes(b"backup-existente")

        with self.assertRaises(database.DatabaseMigrationError):
            database.initialize_database()

        self.assertEqual(self.schema_version(database.DB_PATH), 0)
        self.assertEqual(self.backup_path.read_bytes(), b"backup-existente")

    def test_unknown_schema_version_is_rejected_without_changes(self) -> None:
        database.initialize_database()
        with closing(sqlite3.connect(database.DB_PATH)) as conn:
            conn.execute("PRAGMA user_version = 30000")
            conn.commit()

        with self.assertRaises(database.DatabaseMigrationError):
            database.initialize_database()

        self.assertEqual(self.schema_version(database.DB_PATH), 30000)
        self.assertFalse(self.backup_path.exists())

    def test_validation_failure_keeps_legacy_database_in_place(self) -> None:
        self.create_legacy_database()

        with mock.patch.object(
            database,
            "_validate_database",
            side_effect=database.DatabaseMigrationError("falha simulada"),
        ):
            with self.assertRaises(database.DatabaseMigrationError):
                database.initialize_database()

        self.assertEqual(self.schema_version(database.DB_PATH), 0)
        self.assertFalse(self.backup_path.exists())
        self.assertFalse((database.DATA_DIR / database.MIGRATION_WORK_NAME).exists())
        self.assertFalse((database.DATA_DIR / database.MIGRATION_CANDIDATE_NAME).exists())

    def test_second_promotion_failure_restores_legacy_name(self) -> None:
        self.create_legacy_database()
        real_replace = database.os.replace
        calls = 0

        def fail_candidate_promotion(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("falha simulada")
            return real_replace(source, destination)

        with mock.patch.object(database.os, "replace", side_effect=fail_candidate_promotion):
            with self.assertRaises(database.DatabaseMigrationError):
                database.initialize_database()

        self.assertTrue(database.DB_PATH.exists())
        self.assertEqual(self.schema_version(database.DB_PATH), 0)
        self.assertFalse(self.backup_path.exists())

    @property
    def backup_path(self) -> Path:
        return database.DATA_DIR / database.LEGACY_BACKUP_NAME

    def create_legacy_database(self) -> None:
        database._initialize_schema(database.DB_PATH)
        with closing(sqlite3.connect(database.DB_PATH)) as conn:
            user_id = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES ('Ana', 'ana@example.com', 'hash')"
            ).lastrowid
            conn.execute(
                """
                INSERT INTO secure_configs (user_id, config_type, payload_enc)
                VALUES (?, 'ai', ?)
                """,
                (user_id, '{"ciphertext":"segredo-criptografado"}'),
            )
            conn.execute("PRAGMA user_version = 0")
            conn.commit()

    @staticmethod
    def schema_version(path: Path) -> int:
        with closing(sqlite3.connect(path)) as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
