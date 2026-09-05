from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from financeiro.portfolio_quotes import open_verified_url
from financeiro.database_schema import MARKET_CALENDAR_SCHEMA_SQL


ANBIMA_HOLIDAYS_URL = "https://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls"
ANBIMA_SOURCE = "ANBIMA"
MAX_ANBIMA_XLS_BYTES = 512 * 1024
EXCEL_DATE_BASE = date(1899, 12, 30)
MIN_HOLIDAY_DATE = date(2001, 1, 1)
MAX_HOLIDAY_DATE = date(2099, 12, 31)

def ensure_market_calendar_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(MARKET_CALENDAR_SCHEMA_SQL)


def refresh_anbima_calendar_if_due(
    db_path,
    *,
    connection_factory: Callable,
    today: date | None = None,
    opener=urlopen,
) -> dict:
    """Atualiza no máximo uma vez ao ano e preserva integralmente a cópia válida."""
    reference_date = today or date.today()
    with connection_factory(db_path) as conn:
        ensure_market_calendar_schema(conn)
        state = conn.execute(
            "SELECT imported_at, last_attempt_at, checked_year, row_count FROM market_calendar_state WHERE source = ?",
            (ANBIMA_SOURCE,),
        ).fetchone()
    if state and state[2] == reference_date.year and state[3] > 0:
        return {"updated": False, "row_count": int(state[3]), "reason": "current"}
    if state and str(state[1] or "").startswith(reference_date.isoformat()):
        return {"updated": False, "row_count": int(state[3]), "reason": "attempted_today"}

    attempted_at = datetime.now().isoformat(timespec="seconds")
    try:
        payload = download_anbima_xls(opener=opener)
        holidays = parse_anbima_holidays(payload)
        if not holidays:
            raise ValueError("A planilha ANBIMA não contém feriados válidos.")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        _record_attempt(db_path, connection_factory, attempted_at, reference_date.year)
        return {"updated": False, "row_count": int(state[3]) if state else 0, "reason": "unavailable"}

    digest = hashlib.sha256(payload).hexdigest()
    with connection_factory(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        ensure_market_calendar_schema(conn)
        conn.execute("DELETE FROM market_holidays")
        conn.executemany(
            "INSERT INTO market_holidays (holiday_date, name, source) VALUES (?, ?, ?)",
            [(holiday_date, name, ANBIMA_SOURCE) for holiday_date, name in holidays],
        )
        conn.execute(
            """
            INSERT INTO market_calendar_state
                (source, imported_at, last_attempt_at, checked_year, content_sha256, row_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                imported_at = excluded.imported_at,
                last_attempt_at = excluded.last_attempt_at,
                checked_year = excluded.checked_year,
                content_sha256 = excluded.content_sha256,
                row_count = excluded.row_count
            """,
            (ANBIMA_SOURCE, attempted_at, attempted_at, reference_date.year, digest, len(holidays)),
        )
    return {"updated": True, "row_count": len(holidays), "reason": "downloaded"}


def download_anbima_xls(*, opener=urlopen) -> bytes:
    request = Request(ANBIMA_HOLIDAYS_URL, headers={"User-Agent": "SistemaFinanceiro/2.0"})
    with open_verified_url(opener, request) as response:
        content_length = response.headers.get("Content-Length") if getattr(response, "headers", None) else None
        if content_length:
            try:
                if int(content_length) > MAX_ANBIMA_XLS_BYTES:
                    raise ValueError("Planilha ANBIMA excede o limite permitido.")
            except ValueError as exc:
                raise ValueError("Tamanho inválido da planilha ANBIMA.") from exc
        payload = response.read(MAX_ANBIMA_XLS_BYTES + 1)
    if len(payload) > MAX_ANBIMA_XLS_BYTES:
        raise ValueError("Planilha ANBIMA excede o limite permitido.")
    return bytes(payload)


def parse_anbima_holidays(payload: bytes) -> list[tuple[str, str]]:
    # Import tardio evita acoplamento circular durante a inicialização do banco.
    from financeiro.imports import parse_xls_rows

    rows = parse_xls_rows(payload)
    holidays: dict[str, str] = {}
    for row in rows[1:]:
        if not row:
            continue
        holiday_date = _excel_serial_date(row[0])
        if holiday_date is None or not (MIN_HOLIDAY_DATE <= holiday_date <= MAX_HOLIDAY_DATE):
            continue
        name = str(row[2] if len(row) > 2 else "Feriado nacional").strip() or "Feriado nacional"
        holidays[holiday_date.isoformat()] = name[:160]
    return sorted(holidays.items())


def load_holiday_dates(connection_factory: Callable) -> frozenset[date]:
    try:
        with connection_factory() as conn:
            ensure_market_calendar_schema(conn)
            rows = conn.execute("SELECT holiday_date FROM market_holidays").fetchall()
        return frozenset(date.fromisoformat(str(row[0])) for row in rows)
    except (sqlite3.DatabaseError, ValueError):
        return frozenset()


def next_business_day(value: date, holidays: frozenset[date] | set[date]) -> date:
    result = value + timedelta(days=1)
    while result.weekday() >= 5 or result in holidays:
        result += timedelta(days=1)
    return result


def _excel_serial_date(value: object) -> date | None:
    try:
        serial = int(Decimal(str(value)))
        return EXCEL_DATE_BASE + timedelta(days=serial)
    except (InvalidOperation, ValueError, OverflowError):
        return None


def _record_attempt(db_path, connection_factory: Callable, attempted_at: str, checked_year: int) -> None:
    try:
        with connection_factory(db_path) as conn:
            ensure_market_calendar_schema(conn)
            conn.execute(
                """
                INSERT INTO market_calendar_state (source, last_attempt_at, checked_year, row_count)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(source) DO UPDATE SET last_attempt_at = excluded.last_attempt_at
                """,
                (ANBIMA_SOURCE, attempted_at, checked_year),
            )
    except sqlite3.DatabaseError:
        pass
