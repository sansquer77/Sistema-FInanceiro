from __future__ import annotations

from datetime import date, timedelta

from financeiro.calendar_rules import add_months


SERIES_KINDS = frozenset({"single", "installment", "recurring"})
RECURRENCE_FREQUENCIES = frozenset({"weekly", "monthly", "quarterly", "semiannual", "annual"})
MONTHLY_RECURRENCE_FREQUENCIES = frozenset({"monthly"})


def add_recurrence(start_date: date, frequency: str, index: int) -> date:
    if frequency == "weekly":
        return start_date + timedelta(days=7 * index)
    months = {
        "monthly": 1,
        "quarterly": 3,
        "semiannual": 6,
        "annual": 12,
    }.get(frequency)
    if months is None:
        raise ValueError("unsupported recurrence frequency")
    return add_months(start_date, months * index)
