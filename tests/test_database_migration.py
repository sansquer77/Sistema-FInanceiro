from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

from financeiro import database
from financeiro import database_migrations


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
        self.assertEqual(self.schema_version(database.DB_PATH), database.SCHEMA_VERSION)
        self.assertFalse(self.backup_path.exists())
        with database.get_connection() as conn:
            migrations = conn.execute(
                "SELECT version, name FROM schema_migrations ORDER BY version"
            ).fetchall()
        self.assertEqual(
            [(database.BASELINE_SCHEMA_VERSION, "v2_baseline"), (database.SCHEMA_VERSION, "sqlite_operational_hardening")],
            [(row["version"], row["name"]) for row in migrations],
        )

    def test_baseline_database_advances_through_incremental_migration(self) -> None:
        database.initialize_database()
        with database.get_connection() as conn:
            conn.execute("DROP TABLE schema_migrations")
            conn.execute(f"PRAGMA user_version = {database.BASELINE_SCHEMA_VERSION}")
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES ('Ana', 'ana@example.com', 'hash')"
            )

        database.initialize_database()

        self.assertEqual(self.schema_version(database.DB_PATH), database.SCHEMA_VERSION)
        with database.get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
            versions = [
                row["version"]
                for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")
            ]
        self.assertEqual(
            versions,
            [database.BASELINE_SCHEMA_VERSION, database.SCHEMA_VERSION],
        )

    def test_incremental_migration_rolls_back_version_and_history_on_failure(self) -> None:
        database.initialize_database()
        with database.get_connection() as conn:
            conn.execute("DROP TABLE schema_migrations")
            conn.execute(f"PRAGMA user_version = {database.BASELINE_SCHEMA_VERSION}")

        def fail_migration(conn):
            conn.execute("CREATE TABLE should_rollback (id INTEGER PRIMARY KEY)")
            raise sqlite3.DatabaseError("falha simulada")

        with mock.patch.dict(
            database_migrations.INCREMENTAL_MIGRATIONS,
            {database.SCHEMA_VERSION: ("failing", fail_migration)},
            clear=True,
        ):
            with self.assertRaises(sqlite3.DatabaseError):
                database.initialize_database()

        self.assertEqual(self.schema_version(database.DB_PATH), database.BASELINE_SCHEMA_VERSION)
        with closing(sqlite3.connect(database.DB_PATH)) as conn:
            self.assertIsNone(
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'should_rollback'"
                ).fetchone()
            )

    def test_reopening_v2_database_skips_schema_compatibility(self) -> None:
        database.initialize_database()

        with mock.patch.object(database, "create_database") as create_database:
            database.initialize_database()

        create_database.assert_not_called()
        self.assertFalse(self.backup_path.exists())

    def test_schema_version_is_read_from_path_with_spaces(self) -> None:
        spaced_dir = database.DATA_DIR / "Sistema Financeiro v2"
        spaced_dir.mkdir()
        spaced_db = spaced_dir / "finance.db"
        with closing(sqlite3.connect(spaced_db)) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA user_version = 0")
            conn.commit()

        self.assertEqual(database_migrations.read_schema_version(spaced_db), 0)

    def test_connection_policy_uses_wal_full_durability_and_foreign_keys(self) -> None:
        database.initialize_database()

        with database.get_connection() as conn:
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
            self.assertEqual(conn.execute("PRAGMA synchronous").fetchone()[0], 2)
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(
                conn.execute("PRAGMA busy_timeout").fetchone()[0],
                database.SQLITE_BUSY_TIMEOUT_MS,
            )

    def test_startup_optimizer_creates_query_planner_statistics(self) -> None:
        database.initialize_database()

        with database.get_connection() as conn:
            self.assertIsNotNone(
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_stat1'"
                ).fetchone()
            )

    def test_wal_keeps_reads_available_during_a_short_write(self) -> None:
        database.initialize_database()

        with database.get_connection() as writer, database.get_connection() as reader:
            database.begin_immediate(writer)
            writer.execute(
                "INSERT INTO users (name, email, password_hash) VALUES ('Ana', 'ana@example.com', 'hash')"
            )
            self.assertEqual(reader.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)
            writer.commit()
            self.assertEqual(reader.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)

    def test_legacy_database_is_preserved_and_promoted_under_stable_name(self) -> None:
        self.create_legacy_database()

        database.initialize_database()

        self.assertTrue(database.DB_PATH.exists())
        self.assertTrue(self.backup_path.exists())
        self.assertEqual(self.schema_version(database.DB_PATH), database.SCHEMA_VERSION)
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
            database_migrations,
            "_validate_database",
            side_effect=database_migrations.DatabaseMigrationError("falha simulada"),
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

    def test_genuine_legacy_database_migrates_with_compatibility(self) -> None:
        self.create_genuine_legacy_database()

        database.initialize_database()

        self.assertTrue(database.DB_PATH.exists())
        self.assertTrue(self.backup_path.exists())
        self.assertEqual(self.schema_version(database.DB_PATH), database.SCHEMA_VERSION)

        with closing(sqlite3.connect(database.DB_PATH)) as conn:
            # sessions.token foi migrado para sessions.token_hash
            columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
            self.assertIn("token_hash", columns)
            self.assertNotIn("token", columns)
            self.assertEqual(
                conn.execute(
                    "SELECT token_hash FROM sessions WHERE user_id = 1"
                ).fetchone()[0],
                "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
            )

            # transactions ganhou colunas novas
            tx_columns = {row[1] for row in conn.execute("PRAGMA table_info(transactions)")}
            self.assertIn("category_id", tx_columns)
            self.assertIn("subcategory_id", tx_columns)
            self.assertIn("tag_id", tx_columns)
            self.assertIn("amount_brl_cents", tx_columns)

            # consultor_analyses ganhou created_date
            consultor_columns = {row[1] for row in conn.execute("PRAGMA table_info(consultor_analyses)")}
            self.assertIn("created_date", consultor_columns)

            # categorias ganhou constraint UNIQUE (user_id, group_type, name)
            table_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'categories'"
            ).fetchone()[0]
            self.assertIn("UNIQUE (user_id, group_type, name)", table_sql)

    @property
    def backup_path(self) -> Path:
        return database.DATA_DIR / database.LEGACY_BACKUP_NAME

    def create_legacy_database(self) -> None:
        database.create_database(database.DB_PATH)
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

    def create_genuine_legacy_database(self) -> None:
        """Create a v1-like database with old tables, columns and constraints."""
        database.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(database.DB_PATH)) as conn:
            conn.executescript(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE checking_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    bank_name TEXT NOT NULL,
                    initial_balance_cents INTEGER NOT NULL DEFAULT 0,
                    current_balance_cents INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
                    description TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    account_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE consultor_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    analysis_id TEXT NOT NULL,
                    analysis_output TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES ('Ana', 'ana@example.com', 'hash')"
            )
            conn.execute("INSERT INTO sessions (token, user_id) VALUES ('foo', 1)")
            conn.execute(
                "INSERT INTO checking_accounts (id, user_id, name, bank_name) VALUES (1, 1, 'Conta principal', 'Banco')"
            )
            conn.execute(
                "INSERT INTO categories (id, user_id, name) VALUES (1, 1, 'Moradia')"
            )
            conn.execute(
                """
                INSERT INTO transactions (user_id, type, description, amount_cents, date, account_id)
                VALUES (1, 'expense', 'Aluguel', 100000, '2024-01-05', 1)
                """
            )
            conn.execute(
                "INSERT INTO consultor_analyses (user_id, analysis_id, analysis_output) VALUES (1, 'abc', '{}')"
            )
            conn.execute("PRAGMA user_version = 0")
            conn.commit()

    @staticmethod
    def schema_version(path: Path) -> int:
        with closing(sqlite3.connect(path)) as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
