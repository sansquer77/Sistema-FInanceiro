from __future__ import annotations

import re
from http import HTTPStatus

from financeiro.accounts import cents_to_money, empty_to_none, money_to_cents
from financeiro.categories import normalize_item_id
from financeiro.database import get_connection, row_to_dict

MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


class SpendingLimitError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def list_spending_limits(user_id: int, month: object | None = None) -> list[dict]:
    normalized_month = normalize_month(month, required=False)
    month_filter = "AND spending_limits.month = ?" if normalized_month else ""
    params = [user_id]
    if normalized_month:
        params.append(normalized_month)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                spending_limits.*,
                categories.name AS category_name,
                subcategories.name AS subcategory_name
            FROM spending_limits
            JOIN categories
                ON categories.id = spending_limits.category_id
                AND categories.user_id = spending_limits.user_id
            LEFT JOIN subcategories
                ON subcategories.id = spending_limits.subcategory_id
                AND subcategories.user_id = spending_limits.user_id
            WHERE spending_limits.user_id = ? {month_filter}
            ORDER BY categories.name COLLATE NOCASE, subcategories.name COLLATE NOCASE
            """,
            tuple(params),
        ).fetchall()
    return [format_spending_limit(row_to_dict(row)) for row in rows]


def create_spending_limit(user_id: int, data: dict) -> dict:
    spending_limit = normalize_spending_limit_payload(data)
    with get_connection() as conn:
        ensure_expense_category(conn, user_id, spending_limit["category_id"], spending_limit["subcategory_id"])
        existing = fetch_existing_limit(
            conn,
            user_id,
            spending_limit["month"],
            spending_limit["category_id"],
            spending_limit["subcategory_id"],
        )
        if existing:
            row = update_limit_row(conn, user_id, existing["id"], spending_limit)
        else:
            cursor = conn.execute(
                """
                INSERT INTO spending_limits (
                    user_id, month, category_id, subcategory_id, limit_amount_cents, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    spending_limit["month"],
                    spending_limit["category_id"],
                    spending_limit["subcategory_id"],
                    spending_limit["limit_amount_cents"],
                    spending_limit["notes"],
                ),
            )
            row = fetch_limit(conn, user_id, cursor.lastrowid)
    return format_spending_limit(row)


def update_spending_limit(user_id: int, limit_id: str, data: dict) -> dict:
    normalized_id = normalize_item_id(limit_id, "Limite nao encontrado.")
    spending_limit = normalize_spending_limit_payload(data)
    with get_connection() as conn:
        ensure_expense_category(conn, user_id, spending_limit["category_id"], spending_limit["subcategory_id"])
        row = update_limit_row(conn, user_id, normalized_id, spending_limit)
    return format_spending_limit(row)


def delete_spending_limit(user_id: int, limit_id: str) -> None:
    normalized_id = normalize_item_id(limit_id, "Limite nao encontrado.")
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM spending_limits WHERE id = ? AND user_id = ?",
            (normalized_id, user_id),
        )
        if cursor.rowcount == 0:
            raise SpendingLimitError("Limite nao encontrado.", HTTPStatus.NOT_FOUND)


def update_limit_row(conn, user_id: int, limit_id: int, spending_limit: dict) -> dict:
    try:
        cursor = conn.execute(
            """
            UPDATE spending_limits
            SET month = ?, category_id = ?, subcategory_id = ?, limit_amount_cents = ?,
                notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (
                spending_limit["month"],
                spending_limit["category_id"],
                spending_limit["subcategory_id"],
                spending_limit["limit_amount_cents"],
                spending_limit["notes"],
                limit_id,
                user_id,
            ),
        )
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise SpendingLimitError("Ja existe um limite para este item neste mes.", HTTPStatus.CONFLICT) from exc
        raise
    if cursor.rowcount == 0:
        raise SpendingLimitError("Limite nao encontrado.", HTTPStatus.NOT_FOUND)
    return fetch_limit(conn, user_id, limit_id)


def fetch_existing_limit(conn, user_id: int, month: str, category_id: int, subcategory_id: int | None):
    if subcategory_id:
        return conn.execute(
            """
            SELECT id
            FROM spending_limits
            WHERE user_id = ? AND month = ? AND category_id = ? AND subcategory_id = ?
            """,
            (user_id, month, category_id, subcategory_id),
        ).fetchone()
    return conn.execute(
        """
        SELECT id
        FROM spending_limits
        WHERE user_id = ? AND month = ? AND category_id = ? AND subcategory_id IS NULL
        """,
        (user_id, month, category_id),
    ).fetchone()


def fetch_limit(conn, user_id: int, limit_id: int) -> dict:
    row = conn.execute(
        """
        SELECT
            spending_limits.*,
            categories.name AS category_name,
            subcategories.name AS subcategory_name
        FROM spending_limits
        JOIN categories
            ON categories.id = spending_limits.category_id
            AND categories.user_id = spending_limits.user_id
        LEFT JOIN subcategories
            ON subcategories.id = spending_limits.subcategory_id
            AND subcategories.user_id = spending_limits.user_id
        WHERE spending_limits.id = ? AND spending_limits.user_id = ?
        """,
        (limit_id, user_id),
    ).fetchone()
    if not row:
        raise SpendingLimitError("Limite nao encontrado.", HTTPStatus.NOT_FOUND)
    return row_to_dict(row)


def ensure_expense_category(conn, user_id: int, category_id: int, subcategory_id: int | None) -> None:
    category = conn.execute(
        """
        SELECT id
        FROM categories
        WHERE id = ? AND user_id = ? AND group_type = 'expense'
        """,
        (category_id, user_id),
    ).fetchone()
    if not category:
        raise SpendingLimitError("Escolha uma categoria de despesa.", HTTPStatus.BAD_REQUEST)
    if not subcategory_id:
        return
    subcategory = conn.execute(
        """
        SELECT id
        FROM subcategories
        WHERE id = ? AND user_id = ? AND category_id = ?
        """,
        (subcategory_id, user_id, category_id),
    ).fetchone()
    if not subcategory:
        raise SpendingLimitError("Subcategoria nao pertence a categoria escolhida.", HTTPStatus.BAD_REQUEST)


def normalize_spending_limit_payload(data: dict) -> dict:
    month = normalize_month(data.get("month"))
    category_id = normalize_item_id(data.get("category_id"), "Escolha uma categoria.")
    subcategory_id = normalize_optional_id(data.get("subcategory_id"))
    limit_amount_cents = money_to_cents(data.get("limit_amount", "0"))
    if limit_amount_cents <= 0:
        raise SpendingLimitError("Informe um limite maior que zero.")
    return {
        "month": month,
        "category_id": category_id,
        "subcategory_id": subcategory_id,
        "limit_amount_cents": limit_amount_cents,
        "notes": empty_to_none(data.get("notes")),
    }


def normalize_month(value: object | None, required: bool = True) -> str | None:
    text = str(value or "").strip()
    if not text and not required:
        return None
    if not MONTH_PATTERN.match(text):
        raise SpendingLimitError("Informe o mes no formato AAAA-MM.")
    month = int(text[-2:])
    if month < 1 or month > 12:
        raise SpendingLimitError("Informe um mes valido.")
    return text


def normalize_optional_id(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    return normalize_item_id(text, "Subcategoria invalida.")


def format_spending_limit(spending_limit: dict) -> dict:
    spending_limit["limit_amount"] = cents_to_money(spending_limit.pop("limit_amount_cents"))
    return spending_limit
