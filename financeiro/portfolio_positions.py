from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def allocation_goal_key(position: dict) -> str:
    if position.get("asset_type") == "stock" and str(position.get("currency") or "BRL").upper() == "USD":
        return "stock_usd"
    return str(position.get("asset_type") or "other")


def consume_savings_anniversaries_fifo(entries: list[dict], redeemed_cost_cents: int) -> list[dict]:
    remaining = max(int(redeemed_cost_cents or 0), 0)
    result = []
    for entry in sorted(entries, key=lambda item: str(item.get("date") or "")):
        amount = max(int(entry.get("amount_cents") or 0), 0)
        consumed = min(amount, remaining)
        remaining -= consumed
        if amount > consumed:
            result.append({**entry, "amount_cents": amount - consumed})
    return result


def aggregate_savings_anniversaries(entries: list[dict]) -> list[dict]:
    grouped: dict[str, int] = {}
    for entry in entries:
        key = str(entry.get("date") or "").strip()
        try:
            date.fromisoformat(key)
        except ValueError:
            continue
        grouped[key] = grouped.get(key, 0) + int(entry.get("amount_cents") or 0)
    return [{"date": key, "amount_cents": amount} for key, amount in sorted(grouped.items()) if key and amount > 0]


def decimal_to_micros_value(value: Decimal) -> int:
    return int((value * Decimal("1000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
