from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from financeiro import database
from financeiro.secure_config import (
    SecureConfigError,
    delete_secure_config,
    load_secure_config,
    save_secure_config,
    secure_config_exists,
)

ALLOWED_FREQUENCIES = {"on_start", "daily", "weekly", "monthly"}
MIN_RETENTION = 1
MAX_RETENTION = 100
MIN_PASSWORD_LENGTH = 12


class BackupSettingsError(ValueError):
    pass


def get_backup_settings() -> dict:
    with database.get_connection() as conn:
        row = conn.execute("SELECT * FROM backup_settings WHERE id = 1").fetchone()
    if row is None:
        return _default_settings()
    return _public_settings(dict(row))


def user_can_manage_backups(user_id: int) -> bool:
    with database.get_connection() as conn:
        row = conn.execute("SELECT MIN(id) AS owner_id FROM users").fetchone()
    return bool(row and row["owner_id"] is not None and int(row["owner_id"]) == int(user_id))


def require_backup_manager(user_id: int) -> None:
    if not user_can_manage_backups(user_id):
        raise BackupSettingsError("Somente o responsavel pela instalacao pode gerenciar backups.")


def save_backup_settings(user_id: int, data: dict) -> dict:
    require_backup_manager(user_id)
    directory = validate_backup_directory(data.get("backup_directory"))
    frequency = str(data.get("schedule_frequency") or "weekly").strip().lower()
    if frequency not in ALLOWED_FREQUENCIES:
        raise BackupSettingsError("Frequencia de backup invalida.")
    try:
        retention = int(data.get("retention_count") or 5)
    except (TypeError, ValueError) as exc:
        raise BackupSettingsError("Informe uma retencao valida.") from exc
    if not MIN_RETENTION <= retention <= MAX_RETENTION:
        raise BackupSettingsError("A retencao deve ficar entre 1 e 100 pacotes.")

    remember_password = bool(data.get("remember_password", False))
    password = str(data.get("password") or "")
    confirmation = str(data.get("password_confirmation") or "")
    if password or confirmation:
        validate_backup_password(password, confirmation)
    if remember_password:
        if password:
            save_secure_config(user_id, "backup_password", {"password": password})
        elif not secure_config_exists(user_id, "backup_password"):
            raise BackupSettingsError("Informe e confirme a senha para ativar o backup automatico.")
    else:
        delete_secure_config(user_id, "backup_password")

    with database.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO backup_settings (
                id, backup_directory, schedule_frequency, retention_count,
                remember_password, configured_by_user_id
            ) VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                backup_directory = excluded.backup_directory,
                schedule_frequency = excluded.schedule_frequency,
                retention_count = excluded.retention_count,
                remember_password = excluded.remember_password,
                configured_by_user_id = excluded.configured_by_user_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (str(directory), frequency, retention, int(remember_password), int(user_id)),
        )
    return get_backup_settings()


def validate_backup_directory(value: object) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise BackupSettingsError("Informe o diretorio dos backups.")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise BackupSettingsError("O diretorio de backup deve usar um caminho absoluto.")
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise BackupSettingsError("O diretorio de backup nao existe ou nao pode ser acessado.") from exc
    if not resolved.is_dir():
        raise BackupSettingsError("O destino do backup deve ser um diretorio.")

    protected_roots = (
        database.DATA_DIR.resolve(),
        (database.DATA_DIR.parent / "secure").resolve(),
        (database.DATA_DIR / ".backup-work").resolve(),
    )
    if any(_is_same_or_inside(resolved, protected) for protected in protected_roots):
        raise BackupSettingsError("Escolha um diretorio fora das pastas internas data e secure.")
    if not os.access(resolved, os.W_OK | os.X_OK):
        raise BackupSettingsError("O diretorio de backup nao permite gravacao.")
    return resolved


def validate_backup_password(password: str, confirmation: str | None = None) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise BackupSettingsError("A senha do backup deve ter pelo menos 12 caracteres.")
    if confirmation is not None and password != confirmation:
        raise BackupSettingsError("A confirmacao da senha do backup nao confere.")
    return password


def load_remembered_password() -> str:
    settings = _settings_row()
    if not settings or not settings["remember_password"] or not settings["configured_by_user_id"]:
        return ""
    try:
        payload = load_secure_config(int(settings["configured_by_user_id"]), "backup_password")
    except SecureConfigError:
        return ""
    return str(payload.get("password") or "")


def backup_is_due(now: datetime | None = None) -> bool:
    row = _settings_row()
    if not row or not row["backup_directory"] or not row["remember_password"]:
        return False
    if row["schedule_frequency"] == "on_start":
        return True
    if not row["last_backup_at"]:
        return True
    current = now or datetime.now(timezone.utc)
    try:
        last = datetime.fromisoformat(str(row["last_backup_at"]).replace("Z", "+00:00"))
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed = current - last
    thresholds = {"daily": timedelta(days=1), "weekly": timedelta(days=7)}
    if row["schedule_frequency"] == "monthly":
        return (current.year, current.month) != (last.year, last.month)
    return elapsed >= thresholds[str(row["schedule_frequency"])]


def record_backup_result(*, success: bool, filename: str = "", error: str = "") -> None:
    safe_error = str(error or "")[:240]
    with database.get_connection() as conn:
        conn.execute(
            """
            UPDATE backup_settings
            SET last_backup_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE last_backup_at END,
                last_backup_status = ?, last_package_filename = ?, last_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (int(success), "success" if success else "failed", filename if success else "", safe_error),
        )


def _settings_row():
    with database.get_connection() as conn:
        return conn.execute("SELECT * FROM backup_settings WHERE id = 1").fetchone()


def _default_settings() -> dict:
    return {
        "configured": False,
        "backup_directory": "",
        "schedule_frequency": "weekly",
        "retention_count": 5,
        "remember_password": False,
        "has_remembered_password": False,
        "last_backup_at": None,
        "last_backup_status": "never_run",
        "last_package_filename": "",
        "last_error": "",
    }


def _public_settings(row: dict) -> dict:
    user_id = row.get("configured_by_user_id")
    has_password = bool(user_id and secure_config_exists(int(user_id), "backup_password"))
    return {
        "configured": bool(row.get("backup_directory")),
        "backup_directory": str(row.get("backup_directory") or ""),
        "schedule_frequency": str(row.get("schedule_frequency") or "weekly"),
        "retention_count": int(row.get("retention_count") or 5),
        "remember_password": bool(row.get("remember_password")),
        "has_remembered_password": has_password,
        "last_backup_at": row.get("last_backup_at"),
        "last_backup_status": str(row.get("last_backup_status") or "never_run"),
        "last_package_filename": str(row.get("last_package_filename") or ""),
        "last_error": str(row.get("last_error") or ""),
    }


def _is_same_or_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
