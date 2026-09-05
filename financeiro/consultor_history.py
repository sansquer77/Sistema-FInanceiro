from __future__ import annotations

from datetime import date, datetime, timedelta

from financeiro.database import get_connection


CONSULTOR_DAILY_QUOTA = 20
CONSULTOR_FAILURE_COOLDOWN_SECONDS = 30
_FAILURE_COOLDOWNS: dict[tuple[int, str], datetime] = {}


def daily_usage(user_id: int, current_date: date) -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM consultor_analyses
            WHERE user_id = ? AND created_date = ?
            """,
            (int(user_id), current_date.isoformat()),
        ).fetchone()
    return int(row["total"] if row else 0)


def daily_quota_exceeded(user_id: int, current_date: date) -> bool:
    return daily_usage(user_id, current_date) >= CONSULTOR_DAILY_QUOTA


def persist_analysis(
    user_id: int,
    analysis_id: str,
    period_window: str | None,
    output: str,
    current_time: datetime,
) -> dict:
    created_at = current_time.strftime("%Y-%m-%d %H:%M:%S")
    created_date = current_time.date().isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO consultor_analyses (
                user_id, analysis_id, period_window, analysis_output, created_at, created_date
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(user_id), analysis_id, period_window, output, created_at, created_date),
        )
        execution_id = int(cursor.lastrowid)
    return {"id": execution_id, "created_at": created_at}


def list_history(user_id: int, *, limit: int = 50) -> list[dict]:
    bounded_limit = min(max(int(limit), 1), 100)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, analysis_id, period_window, analysis_output, created_at
            FROM consultor_analyses
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (int(user_id), bounded_limit),
        ).fetchall()
    return [
        {
            "analysis_execution_id": int(row["id"]),
            "analysis_id": row["analysis_id"],
            "period_window": row["period_window"] or None,
            "analysis_output": row["analysis_output"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def delete_history(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM consultor_analyses WHERE user_id = ?",
            (int(user_id),),
        )
        return int(cursor.rowcount or 0)


def register_failure_cooldown(user_id: int, analysis_id: str, current_time: datetime) -> None:
    _FAILURE_COOLDOWNS[(int(user_id), analysis_id)] = current_time + timedelta(
        seconds=CONSULTOR_FAILURE_COOLDOWN_SECONDS
    )


def clear_failure_cooldown(user_id: int, analysis_id: str) -> None:
    _FAILURE_COOLDOWNS.pop((int(user_id), analysis_id), None)


def failure_cooldown_remaining(user_id: int, analysis_id: str, current_time: datetime) -> int:
    expires_at = _FAILURE_COOLDOWNS.get((int(user_id), analysis_id))
    if expires_at is None:
        return 0
    remaining = int((expires_at - current_time).total_seconds())
    if remaining <= 0:
        clear_failure_cooldown(user_id, analysis_id)
        return 0
    return remaining
