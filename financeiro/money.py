from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_SCALE = Decimal("100")


def decimal_to_cents(value: Decimal) -> int:
    return int((value * MONEY_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cents_to_decimal(cents: int) -> Decimal:
    return Decimal(cents) / MONEY_SCALE


def cents_to_money(cents: int) -> str:
    return f"{cents_to_decimal(cents):.2f}"


def localized_money_to_cents(value: object) -> int:
    raw = str(value or "0").strip().replace(".", "").replace(",", ".")
    try:
        decimal = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError("invalid money") from exc
    return decimal_to_cents(decimal)


def split_cents(total_cents: int, count: int) -> list[int]:
    if count <= 0:
        raise ValueError("count must be positive")
    base, remainder = divmod(total_cents, count)
    return [base + (1 if index < remainder else 0) for index in range(count)]


def split_optional_cents(total_cents: int | None, count: int) -> list[int | None]:
    if total_cents is None:
        if count <= 0:
            raise ValueError("count must be positive")
        return [None for _ in range(count)]
    return split_cents(total_cents, count)
