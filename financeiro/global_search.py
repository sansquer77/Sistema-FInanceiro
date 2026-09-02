from __future__ import annotations

from http import HTTPStatus

from financeiro.classification_suggestions import normalize_description
from financeiro.database import get_connection


class GlobalSearchError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def search_global(user_id: int, query: object, *, limit: int = 24, offset: int = 0) -> dict:
    raw_query = str(query or "").strip()
    if len(raw_query) < 2:
        raise GlobalSearchError("Digite ao menos dois caracteres para buscar.")
    if len(raw_query) > 100:
        raise GlobalSearchError("Termo de busca muito longo.")
    normalized_query = normalize_description(raw_query)
    normalized_pattern = f"%{escape_like(normalized_query)}%" if normalized_query else "\u0000"
    raw_pattern = f"%{escape_like(raw_query)}%"
    safe_limit = min(max(int(limit), 1), 50)
    safe_offset = max(int(offset), 0)
    # spec: frontend/frontend-modularizacao v4.24 — busca histórica sob demanda,
    # limitada e isolada pelo usuário, sem materializar históricos no estado global.
    with get_connection() as conn:
        rows = conn.execute(
            """
            WITH matches AS (
                SELECT
                    'account_transaction' AS kind,
                    transactions.id,
                    transactions.description AS title,
                    transactions.date AS event_date,
                    substr(transactions.date, 1, 7) AS event_month,
                    transactions.account_id AS owner_id,
                    accounts.name AS owner_name,
                    categories.name AS category_name
                FROM transactions
                JOIN checking_accounts AS accounts
                    ON accounts.id = transactions.account_id
                    AND accounts.user_id = transactions.user_id
                LEFT JOIN categories
                    ON categories.id = transactions.category_id
                    AND categories.user_id = transactions.user_id
                LEFT JOIN subcategories
                    ON subcategories.id = transactions.subcategory_id
                    AND subcategories.user_id = transactions.user_id
                WHERE transactions.user_id = ?
                    AND transactions.archived_at IS NULL
                    AND (
                        transactions.normalized_description LIKE ? ESCAPE '\\'
                        OR accounts.name LIKE ? ESCAPE '\\' COLLATE NOCASE
                        OR categories.name LIKE ? ESCAPE '\\' COLLATE NOCASE
                        OR subcategories.name LIKE ? ESCAPE '\\' COLLATE NOCASE
                    )
                UNION ALL
                SELECT
                    'card_transaction' AS kind,
                    card_transactions.id,
                    card_transactions.description AS title,
                    card_transactions.date AS event_date,
                    card_transactions.invoice_month AS event_month,
                    card_transactions.credit_card_id AS owner_id,
                    cards.name AS owner_name,
                    categories.name AS category_name
                FROM credit_card_transactions AS card_transactions
                JOIN credit_cards AS cards
                    ON cards.id = card_transactions.credit_card_id
                    AND cards.user_id = card_transactions.user_id
                LEFT JOIN categories
                    ON categories.id = card_transactions.category_id
                    AND categories.user_id = card_transactions.user_id
                LEFT JOIN subcategories
                    ON subcategories.id = card_transactions.subcategory_id
                    AND subcategories.user_id = card_transactions.user_id
                WHERE card_transactions.user_id = ?
                    AND card_transactions.archived_at IS NULL
                    AND (
                        card_transactions.normalized_description LIKE ? ESCAPE '\\'
                        OR cards.name LIKE ? ESCAPE '\\' COLLATE NOCASE
                        OR categories.name LIKE ? ESCAPE '\\' COLLATE NOCASE
                        OR subcategories.name LIKE ? ESCAPE '\\' COLLATE NOCASE
                    )
            )
            SELECT *
            FROM matches
            ORDER BY event_date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (
                user_id, normalized_pattern, raw_pattern, raw_pattern, raw_pattern,
                user_id, normalized_pattern, raw_pattern, raw_pattern, raw_pattern,
                safe_limit + 1, safe_offset,
            ),
        ).fetchall()
    results = [
        {
            "kind": row["kind"],
            "id": row["id"],
            "title": row["title"],
            "date": row["event_date"],
            "month": row["event_month"],
            "owner_id": row["owner_id"],
            "meta": " · ".join(part for part in (row["event_date"], row["owner_name"], row["category_name"]) if part),
        }
        for row in rows[:safe_limit]
    ]
    return {"results": results, "limit": safe_limit, "offset": safe_offset, "has_more": len(rows) > safe_limit}


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
