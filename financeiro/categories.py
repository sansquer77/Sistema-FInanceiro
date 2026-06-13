from __future__ import annotations

from http import HTTPStatus

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


def get_or_create_named_item(conn, table: str, user_id: int, name: str, required_message: str) -> int:
    if table not in {"categories", "tags"}:
        raise ClassificationError("Classificacao invalida.")
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
