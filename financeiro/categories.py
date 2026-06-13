from __future__ import annotations

from http import HTTPStatus

from financeiro.database import get_connection
from financeiro.database import row_to_dict


class ClassificationError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def get_or_create_category(conn, user_id: int, name: str) -> int:
    return get_or_create_named_item(conn, "categories", user_id, name, "Informe a categoria.")


def get_or_create_tag(conn, user_id: int, name: str) -> int:
    return get_or_create_named_item(conn, "tags", user_id, name, "Informe a tag.")


def list_categories(user_id: int) -> list[dict]:
    return list_named_items("categories", user_id)


def list_tags(user_id: int) -> list[dict]:
    return list_named_items("tags", user_id)


def create_category(user_id: int, name: str) -> dict:
    return create_named_item("categories", user_id, name, "Informe a categoria.")


def create_tag(user_id: int, name: str) -> dict:
    return create_named_item("tags", user_id, name, "Informe a tag.")


def update_category(user_id: int, item_id: str, name: str) -> dict:
    return update_named_item("categories", user_id, item_id, name, "Informe a categoria.")


def update_tag(user_id: int, item_id: str, name: str) -> dict:
    return update_named_item("tags", user_id, item_id, name, "Informe a tag.")


def delete_category(user_id: int, item_id: str) -> None:
    delete_named_item("categories", user_id, item_id)


def delete_tag(user_id: int, item_id: str) -> None:
    delete_named_item("tags", user_id, item_id)


def list_named_items(table: str, user_id: int) -> list[dict]:
    ensure_allowed_table(table)
    usage_sql = {
        "categories": """
            SELECT COUNT(*) FROM transactions
            WHERE transactions.category_id = items.id AND transactions.user_id = ?
        """,
        "tags": """
            SELECT COUNT(*)
            FROM transaction_tags
            JOIN transactions ON transactions.id = transaction_tags.transaction_id
            WHERE transaction_tags.tag_id = items.id AND transactions.user_id = ?
        """,
    }[table]
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                items.id,
                items.name,
                items.created_at,
                ({usage_sql}) AS transaction_count
            FROM {table} AS items
            WHERE items.user_id = ?
            ORDER BY items.name COLLATE NOCASE
            """,
            (user_id, user_id),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_named_item(table: str, user_id: int, name: str, required_message: str) -> dict:
    ensure_allowed_table(table)
    normalized = normalize_name(name, required_message)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                f"INSERT INTO {table} (user_id, name) VALUES (?, ?)",
                (user_id, normalized),
            )
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ? AND user_id = ?", (cursor.lastrowid, user_id)).fetchone()
            return row_to_dict(row)
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ClassificationError("Ja existe um item com este nome.", HTTPStatus.CONFLICT) from exc
        raise


def update_named_item(table: str, user_id: int, item_id: str, name: str, required_message: str) -> dict:
    ensure_allowed_table(table)
    normalized = normalize_name(name, required_message)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE {table} SET name = ? WHERE id = ? AND user_id = ?",
                (normalized, item_id, user_id),
            )
            if cursor.rowcount == 0:
                raise ClassificationError("Item nao encontrado.", HTTPStatus.NOT_FOUND)
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ? AND user_id = ?", (item_id, user_id)).fetchone()
            return row_to_dict(row)
    except ClassificationError:
        raise
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ClassificationError("Ja existe um item com este nome.", HTTPStatus.CONFLICT) from exc
        raise


def delete_named_item(table: str, user_id: int, item_id: str) -> None:
    ensure_allowed_table(table)
    usage_query = {
        "categories": """
            SELECT COUNT(*) AS total
            FROM transactions
            WHERE category_id = ? AND user_id = ?
        """,
        "tags": """
            SELECT COUNT(*) AS total
            FROM transaction_tags
            JOIN transactions ON transactions.id = transaction_tags.transaction_id
            WHERE transaction_tags.tag_id = ? AND transactions.user_id = ?
        """,
    }[table]
    with get_connection() as conn:
        used = conn.execute(usage_query, (item_id, user_id)).fetchone()["total"]
        if used:
            raise ClassificationError("Nao e possivel excluir um item usado em lancamentos.")
        cursor = conn.execute(f"DELETE FROM {table} WHERE id = ? AND user_id = ?", (item_id, user_id))
        if cursor.rowcount == 0:
            raise ClassificationError("Item nao encontrado.", HTTPStatus.NOT_FOUND)


def get_or_create_named_item(conn, table: str, user_id: int, name: str, required_message: str) -> int:
    ensure_allowed_table(table)
    normalized = normalize_name(name, required_message)
    row = conn.execute(
        f"SELECT id FROM {table} WHERE user_id = ? AND name = ?",
        (user_id, normalized),
    ).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute(
        f"INSERT INTO {table} (user_id, name) VALUES (?, ?)",
        (user_id, normalized),
    )
    return cursor.lastrowid


def format_classification(row) -> dict | None:
    return row_to_dict(row)


def normalize_name(name: object, required_message: str) -> str:
    normalized = " ".join(str(name or "").strip().split())
    if not normalized:
        raise ClassificationError(required_message)
    if len(normalized) > 80:
        raise ClassificationError("Categoria ou tag deve ter ate 80 caracteres.")
    return normalized


def ensure_allowed_table(table: str) -> None:
    if table not in {"categories", "tags"}:
        raise ClassificationError("Classificacao invalida.")
