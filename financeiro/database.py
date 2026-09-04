from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from financeiro.database_maintenance import maintain_quote_cache
from financeiro.database_migrations import (
    DatabaseMigrationError,
    MigrationPaths,
    migrate_legacy_database,
    read_schema_version,
    set_schema_version,
)
from financeiro.database_schema import SCHEMA_VERSION, create_baseline_schema

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("SISTEMA_FINANCEIRO_DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "finance.db"
SQLITE_BUSY_TIMEOUT_MS = 5000
LEGACY_BACKUP_NAME = "finance-v1.bkp"
MIGRATION_WORK_NAME = ".finance-v2-migration-work.db"
MIGRATION_CANDIDATE_NAME = ".finance-v2-migration-candidate.db"


class ManagedConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000, factory=ManagedConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def begin_immediate(conn: sqlite3.Connection) -> None:
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        create_database(DB_PATH)
    elif read_schema_version(DB_PATH) == SCHEMA_VERSION:
        pass
    else:
        migrate_if_supported(DB_PATH)

    maintain_quote_cache(
        DB_PATH,
        connection_factory=get_connection,
    )


def create_database(db_path: Path) -> None:
    with get_connection(db_path) as conn:
        create_baseline_schema(conn)
    set_schema_version(db_path, SCHEMA_VERSION, connection_factory=get_connection)


def migrate_if_supported(db_path: Path) -> None:
    schema_version = read_schema_version(db_path)
    if schema_version == SCHEMA_VERSION:
        return
    if schema_version != 0:
        raise DatabaseMigrationError(
            f"Versao de banco nao suportada: {schema_version}. "
            f"Esta versao do app aceita o schema legado 1.x ou {SCHEMA_VERSION}."
        )
    paths = MigrationPaths(
        active=db_path,
        backup=db_path.with_name(LEGACY_BACKUP_NAME),
        work=db_path.with_name(MIGRATION_WORK_NAME),
        candidate=db_path.with_name(MIGRATION_CANDIDATE_NAME),
    )
    migrate_legacy_database(
        paths,
        target_version=SCHEMA_VERSION,
        connection_factory=get_connection,
    )


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}
