from __future__ import annotations

from collections import OrderedDict
from datetime import date, timedelta


def trim_cache_to_limit(cache: OrderedDict, max_entries: int) -> None:
    while len(cache) > max_entries:
        cache.popitem(last=False)


def previous_business_day(reference_date: date) -> date:
    day = reference_date - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def yahoo_symbol(position: dict, aliases: dict[tuple[str, str], str]) -> str:
    identifier = str(position.get("asset_identifier") or "").strip().upper()
    if not identifier:
        return ""
    currency = str(position.get("currency") or "BRL").strip().upper()
    if (identifier, currency) in aliases:
        return aliases[(identifier, currency)]
    if "." in identifier or currency != "BRL":
        return identifier
    return f"{identifier}.SA" if currency == "BRL" else identifier
