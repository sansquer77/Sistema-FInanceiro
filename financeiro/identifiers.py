from __future__ import annotations


def positive_int_id(value: object) -> int:
    try:
        normalized = int(str(value or "").strip())
    except ValueError as exc:
        raise ValueError("invalid identifier") from exc
    if normalized <= 0:
        raise ValueError("invalid identifier")
    return normalized


def optional_positive_int_id(value: object) -> int | None:
    if not str(value or "").strip():
        return None
    return positive_int_id(value)
