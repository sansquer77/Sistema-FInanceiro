from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.database import get_connection, initialize_database


class DatabaseIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_initialize_database_creates_high_volume_navigation_indexes(self) -> None:
        initialize_database()

        with get_connection() as conn:
            transaction_indexes = index_names(conn, "transactions")
            card_transaction_indexes = index_names(conn, "credit_card_transactions")
            card_payment_indexes = index_names(conn, "credit_card_payments")

        self.assertIn("idx_transactions_user_account_date", transaction_indexes)
        self.assertIn("idx_transactions_user_destination_date", transaction_indexes)
        self.assertIn("idx_transactions_user_series_date", transaction_indexes)
        self.assertIn("idx_credit_card_transactions_user_card_invoice_date", card_transaction_indexes)
        self.assertIn("idx_credit_card_transactions_user_invoice_date", card_transaction_indexes)
        self.assertIn("idx_credit_card_transactions_user_series_invoice_date", card_transaction_indexes)
        self.assertIn("idx_credit_card_payments_user_card_invoice", card_payment_indexes)
        self.assertIn("idx_credit_card_payments_user_date", card_payment_indexes)

    def test_initialize_database_creates_consultor_schema(self) -> None:
        initialize_database()
        initialize_database()

        with get_connection() as conn:
            settings_columns = column_names(conn, "consultor_settings")
            analyses_columns = column_names(conn, "consultor_analyses")
            perfil_columns = column_names(conn, "consultor_perfil_complementar")
            analyses_indexes = index_names(conn, "consultor_analyses")
            settings_indexes = index_names(conn, "consultor_settings")
            perfil_indexes = index_names(conn, "consultor_perfil_complementar")

        self.assertEqual(
            {
                "id",
                "user_id",
                "consultor_enabled",
                "investor_profile",
                "data_access_consent",
                "consented_at",
                "created_at",
                "updated_at",
            },
            settings_columns,
        )
        self.assertEqual(
            {
                "id",
                "user_id",
                "analysis_id",
                "period_window",
                "analysis_output",
                "created_at",
                "created_date",
            },
            analyses_columns,
        )
        self.assertEqual(
            {
                "id",
                "user_id",
                "payload_enc",
                "schema_version",
                "atualizado_em",
                "created_at",
                "updated_at",
            },
            perfil_columns,
        )
        self.assertIn("idx_consultor_settings_user", settings_indexes)
        self.assertIn("idx_consultor_analyses_user_created", analyses_indexes)
        self.assertIn("idx_consultor_analyses_user_day", analyses_indexes)
        self.assertIn("idx_consultor_analyses_user_analysis_created", analyses_indexes)
        self.assertIn("idx_consultor_perfil_complementar_user", perfil_indexes)

    def test_consultor_schema_enforces_user_isolation_enums_and_cascade(self) -> None:
        initialize_database()

        with get_connection() as conn:
            user_id = conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES ('Ana', 'ana@example.com', 'hash')
                RETURNING id
                """
            ).fetchone()["id"]
            conn.execute(
                """
                INSERT INTO consultor_settings (
                    user_id, consultor_enabled, investor_profile, data_access_consent
                )
                VALUES (?, 1, 'moderado', 1)
                """,
                (user_id,),
            )
            conn.execute(
                """
                INSERT INTO consultor_analyses (
                    user_id, analysis_id, period_window, analysis_output, created_at, created_date
                )
                VALUES (?, 'ralos_financeiros', '3m', 'Resumo', '2026-08-10 10:00:00', '2026-08-10')
                """,
                (user_id,),
            )
            conn.execute(
                """
                INSERT INTO consultor_perfil_complementar (user_id, payload_enc)
                VALUES (?, '{"ciphertext":"x"}')
                """,
                (user_id,),
            )

            with self.assertRaises(sqlite3.IntegrityError):
                other_user_id = conn.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES ('Bia', 'bia@example.com', 'hash')
                    RETURNING id
                    """
                ).fetchone()["id"]
                conn.execute(
                    """
                    INSERT INTO consultor_settings (
                        user_id, consultor_enabled, investor_profile, data_access_consent
                    )
                    VALUES (?, 1, 'agressivo', 1)
                    """,
                    (other_user_id,),
                )

            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO consultor_analyses (
                        user_id, analysis_id, period_window, analysis_output
                    )
                    VALUES (?, 'ralos_financeiros', '24m', 'Resumo')
                    """,
                    (user_id,),
                )

            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            settings_count = conn.execute("SELECT COUNT(*) FROM consultor_settings").fetchone()[0]
            analyses_count = conn.execute("SELECT COUNT(*) FROM consultor_analyses").fetchone()[0]
            perfil_count = conn.execute("SELECT COUNT(*) FROM consultor_perfil_complementar").fetchone()[0]

        self.assertEqual(settings_count, 0)
        self.assertEqual(analyses_count, 0)
        self.assertEqual(perfil_count, 0)

    def test_initialize_database_creates_notification_reads_schema(self) -> None:
        # spec: cockpit/alertas-cockpit v0.3 — critério 11
        initialize_database()
        initialize_database()

        with get_connection() as conn:
            columns = column_names(conn, "notification_reads")

        self.assertEqual({"user_id", "notification_id", "seen_at"}, columns)

    def test_notification_reads_enforces_composite_pk_and_cascade(self) -> None:
        # spec: cockpit/alertas-cockpit v0.3 — critério 11
        initialize_database()

        with get_connection() as conn:
            user_id = conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES ('Carlos', 'carlos@example.com', 'hash')
                RETURNING id
                """
            ).fetchone()["id"]

            conn.execute(
                """
                INSERT INTO notification_reads (user_id, notification_id, seen_at)
                VALUES (?, 'dividend_week:ITUB4:2026-09-05', '2026-09-03T12:00:00Z')
                """,
                (user_id,),
            )

            # Duplicatas do par (user_id, notification_id) devem falhar pela PK composta
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO notification_reads (user_id, notification_id, seen_at)
                    VALUES (?, 'dividend_week:ITUB4:2026-09-05', '2026-09-03T13:00:00Z')
                    """,
                    (user_id,),
                )

            # Exclusão do usuário deve remover registros em cascata
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            reads_count = conn.execute(
                "SELECT COUNT(*) FROM notification_reads WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

        self.assertEqual(reads_count, 0)

    def test_get_connection_closes_after_context_exit(self) -> None:
        initialize_database()

        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()

        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1").fetchone()

    def test_get_connection_enables_wal_and_busy_timeout(self) -> None:
        initialize_database()

        with get_connection() as conn:
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]

        self.assertEqual(journal_mode.lower(), "wal")
        self.assertEqual(busy_timeout, database.SQLITE_BUSY_TIMEOUT_MS)


def index_names(conn, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA index_list({table_name})")}


def column_names(conn, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}


if __name__ == "__main__":
    unittest.main()
