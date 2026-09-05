from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from financeiro import database
from financeiro.backup_settings import (
    BackupSettingsError,
    backup_is_due,
    get_backup_settings,
    load_remembered_password,
    save_backup_settings,
)


class BackupSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data_dir = self.root / "data"
        self.destination = self.root / "backups"
        self.destination.mkdir()
        self.db_patch = mock.patch.object(database, "DATA_DIR", self.data_dir)
        self.path_patch = mock.patch.object(database, "DB_PATH", self.data_dir / "finance.db")
        self.db_patch.start()
        self.path_patch.start()
        database.initialize_database()
        with database.get_connection() as conn:
            self.user_id = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES ('Teste', 't@e.st', 'hash')"
            ).lastrowid

    def tearDown(self) -> None:
        self.path_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def test_defaults_do_not_expose_a_password(self) -> None:
        status = get_backup_settings()
        self.assertFalse(status["configured"])
        self.assertNotIn("password", status)

    def test_saves_policy_and_remembered_password_encrypted(self) -> None:
        status = save_backup_settings(self.user_id, {
            "backup_directory": str(self.destination),
            "schedule_frequency": "weekly",
            "retention_count": 7,
            "remember_password": True,
            "password": "segredo-forte-123",
            "password_confirmation": "segredo-forte-123",
        })
        self.assertTrue(status["configured"])
        self.assertTrue(status["has_remembered_password"])
        self.assertEqual(load_remembered_password(), "segredo-forte-123")
        with database.get_connection() as conn:
            encrypted = conn.execute(
                "SELECT payload_enc FROM secure_configs WHERE config_type = 'backup_password'"
            ).fetchone()[0]
        self.assertNotIn("segredo-forte-123", encrypted)

    def test_rejects_protected_relative_and_weak_settings(self) -> None:
        base = {
            "schedule_frequency": "weekly", "retention_count": 5,
            "remember_password": False,
        }
        for directory in ("relative", str(self.data_dir), str(self.data_dir / "nested")):
            if Path(directory).is_absolute():
                Path(directory).mkdir(parents=True, exist_ok=True)
            with self.assertRaises(BackupSettingsError):
                save_backup_settings(self.user_id, {**base, "backup_directory": directory})
        with self.assertRaises(BackupSettingsError):
            save_backup_settings(self.user_id, {
                **base, "backup_directory": str(self.destination),
                "remember_password": True, "password": "curta", "password_confirmation": "curta",
            })

    def test_due_policy_uses_last_success(self) -> None:
        save_backup_settings(self.user_id, {
            "backup_directory": str(self.destination), "schedule_frequency": "daily",
            "retention_count": 5, "remember_password": True,
            "password": "segredo-forte-123", "password_confirmation": "segredo-forte-123",
        })
        now = datetime.now(timezone.utc)
        with database.get_connection() as conn:
            conn.execute(
                "UPDATE backup_settings SET last_backup_at = ? WHERE id = 1",
                ((now - timedelta(hours=23)).isoformat(),),
            )
        self.assertFalse(backup_is_due(now))
        self.assertTrue(backup_is_due(now + timedelta(hours=2)))

    def test_only_oldest_active_user_can_manage_installation_backup(self) -> None:
        with database.get_connection() as conn:
            second_user = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES ('Outra', 'outra@example.test', 'hash')"
            ).lastrowid
        with self.assertRaises(BackupSettingsError):
            save_backup_settings(second_user, {
                "backup_directory": str(self.destination), "schedule_frequency": "weekly",
                "retention_count": 5, "remember_password": False,
            })


if __name__ == "__main__":
    unittest.main()
