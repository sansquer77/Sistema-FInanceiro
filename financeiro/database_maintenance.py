from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

# spec: persistencia/manutencao-cache-cotacoes v1.1 — critérios 1 a 8
QUOTE_CACHE_STALE_RETENTION_DAYS = 30
QUOTE_CACHE_MAX_ENTRIES = 1500
QUOTE_CACHE_MAX_ENTRIES_PER_PROVIDER = 1000
QUOTE_CACHE_VACUUM_MIN_FREE_BYTES = 1024 * 1024
QUOTE_CACHE_VACUUM_MIN_FREE_RATIO = 0.20

SQLITE_BUSY_TIMEOUT_MS = 5000


def maintain_quote_cache(
    db_path: Path,
    *,
    connection_factory: Callable[[Path], sqlite3.Connection],
    now: datetime | None = None,
) -> dict:
    """Prune regenerable quote payloads without touching financial records."""
    reference_time = now or datetime.now()
    stale_cutoff = reference_time - timedelta(days=QUOTE_CACHE_STALE_RETENTION_DAYS)
    result = {"deleted": 0, "vacuumed": False, "free_bytes": 0, "free_ratio": 0.0}
    try:
        with connection_factory(db_path) as conn:
            table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'quote_cache'"
            ).fetchone()
            if not table_exists:
                return result
            before = int(conn.execute("SELECT COUNT(*) FROM quote_cache").fetchone()[0])
            conn.execute(
                "DELETE FROM quote_cache WHERE datetime(expires_at) < datetime(?)",
                (stale_cutoff.isoformat(),),
            )
            _trim_quote_cache_per_provider(conn, reference_time)
            _trim_quote_cache_total(conn, reference_time)
            after = int(conn.execute("SELECT COUNT(*) FROM quote_cache").fetchone()[0])
            result["deleted"] = before - after

        if result["deleted"] <= 0:
            return result

        with closing(sqlite3.connect(db_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            page_size = int(conn.execute("PRAGMA page_size").fetchone()[0])
            page_count = int(conn.execute("PRAGMA page_count").fetchone()[0])
            free_pages = int(conn.execute("PRAGMA freelist_count").fetchone()[0])
        result["free_bytes"] = free_pages * page_size
        result["free_ratio"] = free_pages / page_count if page_count else 0.0
        if (
            result["free_bytes"] >= QUOTE_CACHE_VACUUM_MIN_FREE_BYTES
            and result["free_ratio"] >= QUOTE_CACHE_VACUUM_MIN_FREE_RATIO
        ):
            with closing(sqlite3.connect(db_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
                conn.execute("VACUUM")
            result["vacuumed"] = True
    except sqlite3.DatabaseError:
        # spec: persistencia/manutencao-cache-cotacoes v1.1 — critério 8
        # Cache é regenerável e sua manutenção nunca bloqueia a abertura do app.
        return result
    return result


def _trim_quote_cache_per_provider(conn: sqlite3.Connection, now: datetime) -> None:
    conn.execute(
        """
        DELETE FROM quote_cache
        WHERE cache_key IN (
            SELECT cache_key
            FROM (
                SELECT
                    cache_key,
                    ROW_NUMBER() OVER (
                        PARTITION BY CASE
                            WHEN instr(cache_key, ':') > 0
                                THEN substr(cache_key, 1, instr(cache_key, ':') - 1)
                            ELSE cache_key
                        END
                        ORDER BY
                            CASE WHEN datetime(expires_at) > datetime(?) THEN 0 ELSE 1 END,
                            datetime(updated_at) DESC,
                            cache_key DESC
                    ) AS position
                FROM quote_cache
            )
            WHERE position > ?
        )
        """,
        (now.isoformat(), QUOTE_CACHE_MAX_ENTRIES_PER_PROVIDER),
    )


def _trim_quote_cache_total(conn: sqlite3.Connection, now: datetime) -> None:
    conn.execute(
        """
        DELETE FROM quote_cache
        WHERE cache_key IN (
            SELECT cache_key
            FROM quote_cache
            ORDER BY
                CASE WHEN datetime(expires_at) > datetime(?) THEN 0 ELSE 1 END,
                datetime(updated_at) DESC,
                cache_key DESC
            LIMIT -1 OFFSET ?
        )
        """,
        (now.isoformat(), QUOTE_CACHE_MAX_ENTRIES),
    )
