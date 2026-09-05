from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from financeiro.database_compatibility import normalize_legacy_schema
from financeiro.database_config import SQLITE_BUSY_TIMEOUT_MS
from financeiro.database_schema import (
    BASELINE_SCHEMA_VERSION,
    MIGRATIONS_SCHEMA_SQL,
    create_baseline_indexes,
    create_baseline_tables,
)


class DatabaseMigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class MigrationPaths:
    active: Path
    backup: Path
    work: Path
    candidate: Path


INCREMENTAL_MIGRATIONS = {
    20001: ("sqlite_operational_hardening", lambda conn: conn.execute(MIGRATIONS_SCHEMA_SQL)),
    20002: ("backup_settings", lambda conn: _migrate_backup_settings(conn)),
}


def _migrate_backup_settings(conn: sqlite3.Connection) -> None:
    """Extend secure config types and add the installation-wide backup policy."""
    conn.execute("ALTER TABLE secure_configs RENAME TO secure_configs_before_backup")
    conn.execute(
        """CREATE TABLE secure_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            config_type TEXT NOT NULL
                CHECK (config_type IN ('email', 'ai', 'mais_retorno', 'backup_password')),
            payload_enc TEXT NOT NULL,
            source_path TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, config_type)
        )"""
    )
    conn.execute(
        """INSERT INTO secure_configs (
            id, user_id, config_type, payload_enc, source_path, created_at, updated_at
        )
        SELECT id, user_id, config_type, payload_enc, source_path, created_at, updated_at
        FROM secure_configs_before_backup"""
    )
    conn.execute("DROP TABLE secure_configs_before_backup")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_secure_configs_user_type "
        "ON secure_configs (user_id, config_type)"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS backup_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            backup_directory TEXT NOT NULL DEFAULT '',
            schedule_frequency TEXT NOT NULL DEFAULT 'weekly'
                CHECK (schedule_frequency IN ('on_start', 'daily', 'weekly', 'monthly')),
            retention_count INTEGER NOT NULL DEFAULT 5 CHECK (retention_count BETWEEN 1 AND 100),
            remember_password INTEGER NOT NULL DEFAULT 0 CHECK (remember_password IN (0, 1)),
            configured_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            last_backup_at TEXT,
            last_backup_status TEXT NOT NULL DEFAULT 'never_run'
                CHECK (last_backup_status IN ('success', 'failed', 'never_run')),
            last_package_filename TEXT NOT NULL DEFAULT '',
            last_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )


def read_schema_version(db_path: Path) -> int:
    try:
        # spec: migracao-dados/migracao-banco-v2 v1.7 — critério 12
        # A URI mode=ro falha em algumas combinações do SQLite do macOS quando
        # o caminho contém espaços. A conexão normal é aberta sem executar
        # escrita e também consegue consultar bancos configurados em WAL.
        with closing(sqlite3.connect(db_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        raise DatabaseMigrationError("Nao foi possivel identificar a versao do banco de dados.") from exc


def set_schema_version(
    db_path: Path,
    version: int,
    *,
    connection_factory: Callable[[Path], sqlite3.Connection],
) -> None:
    with connection_factory(db_path) as conn:
        conn.execute(f"PRAGMA user_version = {int(version)}")


def migrate_incremental_database(
    db_path: Path,
    *,
    current_version: int,
    target_version: int,
    connection_factory: Callable[[Path], sqlite3.Connection],
) -> None:
    """Apply known post-baseline migrations atomically and in order."""
    # spec: migracao-dados/migracao-banco-v2 v1.7 — critério 13
    if current_version < BASELINE_SCHEMA_VERSION or current_version >= target_version:
        raise DatabaseMigrationError(f"Versao de banco nao suportada: {current_version}.")
    expected_versions = list(range(current_version + 1, target_version + 1))
    if any(version not in INCREMENTAL_MIGRATIONS for version in expected_versions):
        raise DatabaseMigrationError(
            f"Nao existe caminho de migracao do schema {current_version} para {target_version}."
        )
    with connection_factory(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(MIGRATIONS_SCHEMA_SQL)
        _record_schema_migration(conn, BASELINE_SCHEMA_VERSION, "v2_baseline")
        for version in expected_versions:
            name, migration = INCREMENTAL_MIGRATIONS[version]
            migration(conn)
            _record_schema_migration(conn, version, name)
            conn.execute(f"PRAGMA user_version = {int(version)}")


def record_schema_history(conn: sqlite3.Connection, target_version: int) -> None:
    """Record the baseline and every known step already present in a new candidate."""
    conn.execute(MIGRATIONS_SCHEMA_SQL)
    _record_schema_migration(conn, BASELINE_SCHEMA_VERSION, "v2_baseline")
    for version in range(BASELINE_SCHEMA_VERSION + 1, target_version + 1):
        migration = INCREMENTAL_MIGRATIONS.get(version)
        if migration is None:
            raise DatabaseMigrationError(f"Migracao de schema desconhecida: {version}.")
        _record_schema_migration(conn, version, migration[0])


def _record_schema_migration(conn: sqlite3.Connection, version: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
        (int(version), str(name)),
    )


def migrate_legacy_database(
    paths: MigrationPaths,
    *,
    target_version: int,
    connection_factory: Callable[[Path], sqlite3.Connection],
) -> None:
    """Transform a legacy database into a validated v2 candidate and promote it.

    The operation is recoverable: the original active file is preserved as the
    backup, and failures before promotion keep the legacy database in place.
    """
    # spec: migracao-dados/migracao-banco-v2 v1.7 — critérios 3, 4, 7, 8 e 11
    if paths.backup.exists():
        raise DatabaseMigrationError(
            f"A migracao foi bloqueada porque {paths.backup.name} ja existe. "
            "O backup legado nunca e sobrescrito automaticamente."
        )

    _remove_migration_artifacts(paths.work, paths.candidate)
    promoted_legacy = False
    try:
        _checkpoint_database(paths.active)
        _copy_database(paths.active, paths.work)
        with connection_factory(paths.work) as conn:
            create_baseline_tables(conn)
        with connection_factory(paths.work) as conn:
            normalize_legacy_schema(conn)
        with connection_factory(paths.work) as conn:
            create_baseline_indexes(conn)
            record_schema_history(conn, target_version)
        set_schema_version(paths.work, target_version, connection_factory=connection_factory)
        _validate_database(paths.work, target_version)
        _vacuum_into(paths.work, paths.candidate)
        _validate_database(paths.candidate, target_version)
        _validate_table_counts(paths.work, paths.candidate)

        os.replace(paths.active, paths.backup)
        promoted_legacy = True
        try:
            os.replace(paths.candidate, paths.active)
        except OSError:
            os.replace(paths.backup, paths.active)
            promoted_legacy = False
            raise
    except (OSError, sqlite3.DatabaseError, DatabaseMigrationError) as exc:
        if promoted_legacy and paths.backup.exists() and not paths.active.exists():
            os.replace(paths.backup, paths.active)
        if isinstance(exc, DatabaseMigrationError):
            raise
        raise DatabaseMigrationError(
            "Nao foi possivel migrar o banco legado. O arquivo original foi preservado."
        ) from exc
    finally:
        _remove_migration_artifacts(paths.work, paths.candidate)


def _checkpoint_database(db_path: Path) -> None:
    with closing(sqlite3.connect(db_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
        result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if result and int(result[0]) != 0:
            raise DatabaseMigrationError("O banco esta ocupado e nao pode ser migrado agora.")


def _copy_database(source_path: Path, destination_path: Path) -> None:
    source_uri = source_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(source_uri, uri=True, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as source:
        with closing(sqlite3.connect(destination_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as destination:
            source.backup(destination)


def _vacuum_into(source_path: Path, destination_path: Path) -> None:
    escaped_path = str(destination_path).replace("'", "''")
    with closing(sqlite3.connect(source_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
        conn.execute(f"VACUUM INTO '{escaped_path}'")


def _validate_database(db_path: Path, target_version: int) -> None:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
        integrity_rows = [row[0] for row in conn.execute("PRAGMA integrity_check")]
        if integrity_rows != ["ok"]:
            raise DatabaseMigrationError("A verificacao de integridade do banco candidato falhou.")
        foreign_key_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_rows:
            raise DatabaseMigrationError("O banco candidato possui referencias invalidas.")
        schema_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if schema_version != target_version:
            raise DatabaseMigrationError("O banco candidato nao possui a versao de schema esperada.")


def _validate_table_counts(source_path: Path, destination_path: Path) -> None:
    source_uri = source_path.resolve().as_uri() + "?mode=ro"
    destination_uri = destination_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(source_uri, uri=True)) as source, closing(
        sqlite3.connect(destination_uri, uri=True)
    ) as destination:
        source_tables = _user_table_names(source)
        destination_tables = _user_table_names(destination)
        if source_tables != destination_tables:
            raise DatabaseMigrationError("As tabelas do banco candidato divergem da origem normalizada.")
        for table_name in source_tables:
            quoted_name = table_name.replace('"', '""')
            source_count = source.execute(f'SELECT COUNT(*) FROM "{quoted_name}"').fetchone()[0]
            destination_count = destination.execute(f'SELECT COUNT(*) FROM "{quoted_name}"').fetchone()[0]
            if source_count != destination_count:
                raise DatabaseMigrationError(
                    f"A contagem da tabela {table_name} diverge no banco candidato."
                )


def _user_table_names(conn: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
    )


def _remove_migration_artifacts(*paths: Path) -> None:
    for path in paths:
        for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass
