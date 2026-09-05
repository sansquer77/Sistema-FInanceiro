from __future__ import annotations

import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from financeiro import database
from financeiro.backup_service import (
    apply_retention,
    BackupError,
    create_backup,
    restore_validated_package,
    run_scheduled_backup_if_due,
    validate_restore_package,
)
from financeiro.backup_settings import save_backup_settings


class BackupServiceTests(unittest.TestCase):
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
            self.user_ids = [
                conn.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, 'hash')",
                    (f"Pessoa {index}", f"p{index}@example.test"),
                ).lastrowid
                for index in range(3)
            ]
        save_backup_settings(self.user_ids[0], {
            "backup_directory": str(self.destination), "schedule_frequency": "weekly",
            "retention_count": 5, "remember_password": True,
            "password": "segredo-forte-123", "password_confirmation": "segredo-forte-123",
        })

    def tearDown(self) -> None:
        self.path_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def test_creates_encrypted_package_from_online_copy_for_all_users(self) -> None:
        result = create_backup("segredo-forte-123")
        package = Path(result["package_path"])
        self.assertTrue(package.exists())
        self.assertEqual(result["schema_version"], database.SCHEMA_VERSION)
        with zipfile.ZipFile(package) as archive:
            self.assertEqual(set(archive.namelist()), {"envelope.json", "payload.enc", "LEIA-ME.txt"})
            envelope = json.loads(archive.read("envelope.json"))
            encrypted = archive.read("payload.enc")
        self.assertEqual(envelope["cipher"], "AES-256-GCM")
        self.assertNotIn(b"Pessoa 0", encrypted)
        self.assertFalse(any(self.destination.glob("*.tmp")))

    def test_online_copy_remains_consistent_during_low_concurrency_write(self) -> None:
        barrier = threading.Barrier(2)

        def writer() -> None:
            barrier.wait()
            with database.get_connection() as conn:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES ('Concorrente', 'c@example.test', 'hash')"
                )

        thread = threading.Thread(target=writer)
        thread.start()
        barrier.wait()
        result = create_backup("segredo-forte-123")
        thread.join(timeout=5)
        self.assertTrue(Path(result["package_path"]).exists())

    def test_round_trip_restores_all_users_and_creates_safety_package(self) -> None:
        backup = create_backup("segredo-forte-123")
        with database.get_connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (self.user_ids[2],))
        validation = validate_restore_package(
            self.user_ids[0], backup["package_path"], "segredo-forte-123"
        )
        restored = restore_validated_package(
            self.user_ids[0], validation["confirmation_token"], "segredo-forte-123"
        )
        with database.get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 3)
        self.assertTrue(Path(restored["safety_backup_path"]).exists())
        self.assertTrue(restored["restart_required"])

    def test_wrong_password_and_tampering_never_change_active_database(self) -> None:
        backup = create_backup("segredo-forte-123")
        package = Path(backup["package_path"])
        with self.assertRaises(BackupError):
            validate_restore_package(self.user_ids[0], package, "senha-errada-123")
        with database.get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 3)

        with zipfile.ZipFile(package, "r") as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        payload = bytearray(entries["payload.enc"])
        payload[len(payload) // 2] ^= 1
        entries["payload.enc"] = bytes(payload)
        with zipfile.ZipFile(package, "w") as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
        with self.assertRaises(BackupError):
            validate_restore_package(self.user_ids[0], package, "segredo-forte-123")
        with database.get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 3)

    def test_retention_removes_only_old_authenticated_packages(self) -> None:
        packages = [Path(create_backup("segredo-forte-123")["package_path"]) for _ in range(3)]
        invalid = self.destination / "sistema-financeiro-00000000-000000-000000.sfbackup"
        invalid.write_bytes(b"nao e um backup")
        removed = apply_retention(self.destination, 2, "segredo-forte-123")
        self.assertEqual(len(removed), 1)
        self.assertTrue(invalid.exists())
        self.assertEqual(sum(path.exists() for path in packages), 2)

    def test_disk_failure_leaves_no_partial_package_and_records_failure(self) -> None:
        with mock.patch("financeiro.backup_service._write_outer_package", side_effect=OSError("disco cheio")):
            with self.assertRaises(BackupError):
                create_backup("segredo-forte-123")
        self.assertFalse(any(self.destination.glob("*.tmp")))
        with database.get_connection() as conn:
            status, error = conn.execute(
                "SELECT last_backup_status, last_error FROM backup_settings WHERE id = 1"
            ).fetchone()
        self.assertEqual(status, "failed")
        self.assertEqual(error, "Nao foi possivel gerar o backup completo.")

    def test_scheduled_backup_runs_once_when_policy_is_due(self) -> None:
        with mock.patch("financeiro.backup_service.backup_is_due", return_value=True):
            result = run_scheduled_backup_if_due()
        self.assertEqual(result["status"], "success")
        self.assertTrue(Path(result["package_path"]).exists())

if __name__ == "__main__":
    unittest.main()
