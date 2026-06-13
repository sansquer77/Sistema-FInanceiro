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


def get_or_create_subcategory(conn, user_id: int, category_id: int, name: str | None) -> int | None:
    if not str(name or "").strip():
        return None
    ensure_category_exists(conn, user_id, category_id)
    normalized = normalize_name(name, "Informe a subcategoria.")
    row = conn.execute(
        """
        SELECT id
        FROM subcategories
        WHERE user_id = ? AND category_id = ? AND name = ?
        """,
        (user_id, category_id, normalized),
    ).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute(
        """
        INSERT INTO subcategories (user_id, category_id, name)
        VALUES (?, ?, ?)
        """,
        (user_id, category_id, normalized),
    )
    return cursor.lastrowid


def get_or_create_tag(conn, user_id: int, name: str) -> int:
    return get_or_create_named_item(conn, "tags", user_id, name, "Informe a tag.")


def list_categories(user_id: int) -> list[dict]:
    return list_named_items("categories", user_id)


def list_tags(user_id: int) -> list[dict]:
    return list_named_items("tags", user_id)


def create_category(user_id: int, name: str) -> dict:
    return create_named_item("categories", user_id, name, "Informe a categoria.")


def create_subcategory(user_id: int, category_id: object, name: str) -> dict:
    normalized_category_id = normalize_item_id(category_id, "Informe a categoria.")
    normalized = normalize_name(name, "Informe a subcategoria.")
    try:
        with get_connection() as conn:
            ensure_category_exists(conn, user_id, normalized_category_id)
            cursor = conn.execute(
                """
                INSERT INTO subcategories (user_id, category_id, name)
                VALUES (?, ?, ?)
                """,
                (user_id, normalized_category_id, normalized),
            )
            return fetch_subcategory(conn, user_id, cursor.lastrowid)
    except ClassificationError:
        raise
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ClassificationError("Ja existe uma subcategoria com este nome nesta categoria.", HTTPStatus.CONFLICT) from exc
        raise


def create_tag(user_id: int, name: str) -> dict:
    return create_named_item("tags", user_id, name, "Informe a tag.")


def update_category(user_id: int, item_id: str, name: str) -> dict:
    return update_named_item("categories", user_id, item_id, name, "Informe a categoria.")


def update_subcategory(user_id: int, item_id: str, name: str) -> dict:
    normalized_id = normalize_item_id(item_id, "Subcategoria nao encontrada.")
    normalized = normalize_name(name, "Informe a subcategoria.")
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE subcategories
                SET name = ?
                WHERE id = ? AND user_id = ?
                """,
                (normalized, normalized_id, user_id),
            )
            if cursor.rowcount == 0:
                raise ClassificationError("Subcategoria nao encontrada.", HTTPStatus.NOT_FOUND)
            return fetch_subcategory(conn, user_id, normalized_id)
    except ClassificationError:
        raise
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ClassificationError("Ja existe uma subcategoria com este nome nesta categoria.", HTTPStatus.CONFLICT) from exc
        raise


def update_tag(user_id: int, item_id: str, name: str) -> dict:
    return update_named_item("tags", user_id, item_id, name, "Informe a tag.")


def delete_category(user_id: int, item_id: str) -> None:
    delete_named_item("categories", user_id, item_id)


def delete_subcategory(user_id: int, item_id: str) -> None:
    normalized_id = normalize_item_id(item_id, "Subcategoria nao encontrada.")
    with get_connection() as conn:
        used = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM transactions
            WHERE subcategory_id = ? AND user_id = ?
            """,
            (normalized_id, user_id),
        ).fetchone()["total"]
        if used:
            raise ClassificationError("Nao e possivel excluir uma subcategoria usada em lancamentos.")
        cursor = conn.execute(
            """
            DELETE FROM subcategories
            WHERE id = ? AND user_id = ?
            """,
            (normalized_id, user_id),
        )
        if cursor.rowcount == 0:
            raise ClassificationError("Subcategoria nao encontrada.", HTTPStatus.NOT_FOUND)


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
        items = [row_to_dict(row) for row in rows]
        if table == "categories":
            attach_subcategories(conn, user_id, items)
    return items


def attach_subcategories(conn, user_id: int, categories: list[dict]) -> None:
    if not categories:
        return
    rows = conn.execute(
        """
        SELECT
            subcategories.id,
            subcategories.category_id,
            subcategories.name,
            subcategories.created_at,
            COUNT(transactions.id) AS transaction_count
        FROM subcategories
        LEFT JOIN transactions
            ON transactions.subcategory_id = subcategories.id
            AND transactions.user_id = subcategories.user_id
        WHERE subcategories.user_id = ?
        GROUP BY subcategories.id
        ORDER BY subcategories.name COLLATE NOCASE
        """,
        (user_id,),
    ).fetchall()
    by_category = {category["id"]: [] for category in categories}
    for row in rows:
        subcategory = row_to_dict(row)
        if subcategory["category_id"] in by_category:
            by_category[subcategory["category_id"]].append(subcategory)
    for category in categories:
        category["subcategories"] = by_category[category["id"]]


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
    normalized_id = normalize_item_id(item_id, "Item nao encontrado.")
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
        used = conn.execute(usage_query, (normalized_id, user_id)).fetchone()["total"]
        if used:
            raise ClassificationError("Nao e possivel excluir um item usado em lancamentos.")
        cursor = conn.execute(f"DELETE FROM {table} WHERE id = ? AND user_id = ?", (normalized_id, user_id))
        if cursor.rowcount == 0:
            raise ClassificationError("Item nao encontrado.", HTTPStatus.NOT_FOUND)


def ensure_category_exists(conn, user_id: int, category_id: int) -> None:
    row = conn.execute(
        """
        SELECT id
        FROM categories
        WHERE id = ? AND user_id = ?
        """,
        (category_id, user_id),
    ).fetchone()
    if not row:
        raise ClassificationError("Categoria nao encontrada.", HTTPStatus.NOT_FOUND)


def fetch_subcategory(conn, user_id: int, subcategory_id: int) -> dict:
    row = conn.execute(
        """
        SELECT
            subcategories.id,
            subcategories.user_id,
            subcategories.category_id,
            subcategories.name,
            subcategories.created_at,
            COUNT(transactions.id) AS transaction_count
        FROM subcategories
        LEFT JOIN transactions
            ON transactions.subcategory_id = subcategories.id
            AND transactions.user_id = subcategories.user_id
        WHERE subcategories.id = ? AND subcategories.user_id = ?
        GROUP BY subcategories.id
        """,
        (subcategory_id, user_id),
    ).fetchone()
    if not row:
        raise ClassificationError("Subcategoria nao encontrada.", HTTPStatus.NOT_FOUND)
    return row_to_dict(row)


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


def normalize_item_id(value: object, message: str) -> int:
    try:
        normalized = int(str(value or "").strip())
    except ValueError as exc:
        raise ClassificationError(message) from exc
    if normalized <= 0:
        raise ClassificationError(message)
    return normalized


def ensure_allowed_table(table: str) -> None:
    if table not in {"categories", "tags"}:
        raise ClassificationError("Classificacao invalida.")
