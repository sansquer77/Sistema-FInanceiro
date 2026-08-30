from __future__ import annotations

from datetime import date, timedelta
import re


MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def add_months(start_date: date, months: int) -> date:
    target_month = start_date.month - 1 + months
    year = start_date.year + target_month // 12
    month = target_month % 12 + 1
    day = min(start_date.day, days_in_month(year, month))
    return date(year, month, day)


def shift_month(value: str, delta: int) -> str:
    year, month = value.split("-")
    shifted = add_months(date(int(year), int(month), 1), delta)
    return shifted.strftime("%Y-%m")


def normalize_iso_date(value: object) -> str:
    return date.fromisoformat(str(value or "").strip()).isoformat()


def normalize_iso_month(value: object) -> str:
    raw = str(value or "").strip()
    if not MONTH_PATTERN.fullmatch(raw):
        raise ValueError("invalid month")
    date.fromisoformat(f"{raw}-01")
    return raw
