from __future__ import annotations

import json
import sqlite3
from http import HTTPStatus

from financeiro.database import get_connection, row_to_dict

MODULES = {
    "accounts",
    "transactions",
    "cards",
    "portfolio",
    "imports",
    "classifications",
    "limits",
    "user_admin",
}
OPERATION_TYPES = {
    "create",
    "update",
    "delete",
    "archive",
    "restore",
    "reconcile",
    "unreconcile",
    "move",
    "pay",
    "import",
    "redeem",
    "close",
    "value_update",
    "clear",
}
ENTITY_TYPES = {
    "account",
    "transaction",
    "credit_card",
    "credit_card_transaction",
    "credit_card_payment",
    "portfolio_position",
    "portfolio_redemption",
    "category",
    "subcategory",
    "tag",
    "spending_limit",
    "user",
}
MAX_LIMIT = 100


class OperationLogError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def create_operation_log(
    user_id: int,
    *,
    module: str,
    operation_type: str,
    entity_type: str,
    description: str,
    entity_id: object | None = None,
    account_id: object | None = None,
    credit_card_id: object | None = None,
    operation_batch_id: object | None = None,
    metadata: dict | None = None,
) -> dict:
    with get_connection() as conn:
        return create_operation_log_with_conn(
            conn,
            user_id,
            module=module,
            operation_type=operation_type,
            entity_type=entity_type,
            description=description,
            entity_id=entity_id,
            account_id=account_id,
            credit_card_id=credit_card_id,
            operation_batch_id=operation_batch_id,
            metadata=metadata,
        )


def create_operation_log_with_conn(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    module: str,
    operation_type: str,
    entity_type: str,
    description: str,
    entity_id: object | None = None,
    account_id: object | None = None,
    credit_card_id: object | None = None,
    operation_batch_id: object | None = None,
    metadata: dict | None = None,
) -> dict:
    normalized_module = validate_choice(module, MODULES, "Modulo de auditoria invalido.")
    normalized_operation = validate_choice(operation_type, OPERATION_TYPES, "Tipo de operacao invalido.")
    normalized_entity = validate_choice(entity_type, ENTITY_TYPES, "Tipo de entidade invalido.")
    clean_description = str(description or "").strip()
    if not clean_description:
        raise OperationLogError("Informe a descricao da operacao.")
    payload = safe_metadata(metadata or {})
    cursor = conn.execute(
        """
        INSERT INTO operation_logs (
            user_id, operation_batch_id, module, operation_type, entity_type,
            entity_id, account_id, credit_card_id, description, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            clean_optional_text(operation_batch_id),
            normalized_module,
            normalized_operation,
            normalized_entity,
            clean_optional_text(entity_id),
            normalize_optional_int(account_id, "Conta invalida."),
            normalize_optional_int(credit_card_id, "Cartao invalido."),
            clean_description[:240],
            json.dumps(payload, ensure_ascii=True, sort_keys=True),
        ),
    )
    return get_operation_log(user_id, cursor.lastrowid, conn=conn)


def list_operation_logs(user_id: int, filters: dict) -> dict:
    where = ["operation_logs.user_id = ?"]
    params: list[object] = [user_id]
    date_from = clean_optional_text(filters.get("date_from"))
    date_to = clean_optional_text(filters.get("date_to"))
    if date_from:
        where.append("DATE(operation_logs.created_at) >= DATE(?)")
        params.append(date_from)
    if date_to:
        where.append("DATE(operation_logs.created_at) <= DATE(?)")
        params.append(date_to)
    for field in ("module", "operation_type"):
        value = clean_optional_text(filters.get(field))
        if value:
            where.append(f"operation_logs.{field} = ?")
            params.append(value)
    account_id = normalize_optional_int(filters.get("account_id"), "Conta invalida.")
    if account_id is not None:
        where.append("operation_logs.account_id = ?")
        params.append(account_id)
    credit_card_id = normalize_optional_int(filters.get("credit_card_id"), "Cartao invalido.")
    if credit_card_id is not None:
        where.append("operation_logs.credit_card_id = ?")
        params.append(credit_card_id)
    query = clean_optional_text(filters.get("q"))
    if query:
        like = f"%{query.lower()}%"
        where.append(
            """
            (
                LOWER(operation_logs.description) LIKE ?
                OR LOWER(operation_logs.module) LIKE ?
                OR LOWER(operation_logs.operation_type) LIKE ?
                OR LOWER(operation_logs.entity_type) LIKE ?
                OR LOWER(COALESCE(operation_logs.operation_batch_id, '')) LIKE ?
                OR LOWER(operation_logs.metadata_json) LIKE ?
            )
            """
        )
        params.extend([like, like, like, like, like, like])
    limit = normalize_limit(filters.get("limit"))
    offset = normalize_offset(filters.get("offset"))
    params.extend([limit + 1, offset])
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT operation_logs.*,
                users.name AS user_name,
                users.email AS user_email,
                checking_accounts.name AS account_name,
                credit_cards.name AS credit_card_name
            FROM operation_logs
            JOIN users ON users.id = operation_logs.user_id
            LEFT JOIN checking_accounts ON checking_accounts.id = operation_logs.account_id
                AND checking_accounts.user_id = operation_logs.user_id
            LEFT JOIN credit_cards ON credit_cards.id = operation_logs.credit_card_id
                AND credit_cards.user_id = operation_logs.user_id
            WHERE {' AND '.join(where)}
            ORDER BY operation_logs.created_at DESC, operation_logs.id DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
    logs = [format_operation_log(row) for row in rows[:limit]]
    return {
        "logs": logs,
        "limit": limit,
        "offset": offset,
        "has_more": len(rows) > limit,
    }


def get_operation_log(user_id: int, log_id: object, conn: sqlite3.Connection | None = None) -> dict:
    normalized_id = normalize_optional_int(log_id, "Operacao nao encontrada.")
    if normalized_id is None:
        raise OperationLogError("Operacao nao encontrada.", HTTPStatus.NOT_FOUND)
    query = """
        SELECT operation_logs.*,
            users.name AS user_name,
            users.email AS user_email,
            checking_accounts.name AS account_name,
            credit_cards.name AS credit_card_name
        FROM operation_logs
        JOIN users ON users.id = operation_logs.user_id
        LEFT JOIN checking_accounts ON checking_accounts.id = operation_logs.account_id
            AND checking_accounts.user_id = operation_logs.user_id
        LEFT JOIN credit_cards ON credit_cards.id = operation_logs.credit_card_id
            AND credit_cards.user_id = operation_logs.user_id
        WHERE operation_logs.id = ? AND operation_logs.user_id = ?
    """
    if conn is not None:
        row = conn.execute(query, (normalized_id, user_id)).fetchone()
    else:
        with get_connection() as local_conn:
            row = local_conn.execute(query, (normalized_id, user_id)).fetchone()
    if not row:
        raise OperationLogError("Operacao nao encontrada.", HTTPStatus.NOT_FOUND)
    return format_operation_log(row)


def format_operation_log(row: sqlite3.Row) -> dict:
    log = row_to_dict(row)
    try:
        metadata = json.loads(log.pop("metadata_json") or "{}")
    except json.JSONDecodeError:
        metadata = {}
    log["metadata"] = metadata if isinstance(metadata, dict) else {}
    return log


def validate_choice(value: str, allowed: set[str], message: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in allowed:
        raise OperationLogError(message)
    return normalized


def safe_metadata(metadata: dict) -> dict:
    blocked = {"password", "current_password", "new_password", "token", "session", "smtp_password"}
    safe = {}
    for key, value in metadata.items():
        key_text = str(key)
        if key_text.lower() in blocked:
            continue
        safe[key_text] = safe_metadata_value(value, blocked)
    return safe


def safe_metadata_value(value: object, blocked: set[str]) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {
            str(key): safe_metadata_value(item, blocked)
            for key, item in value.items()
            if str(key).lower() not in blocked
        }
    if isinstance(value, (list, tuple)):
        return [safe_metadata_value(item, blocked) for item in value]
    return str(value)


def clean_optional_text(value: object | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def normalize_optional_int(value: object | None, message: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise OperationLogError(message) from exc


def normalize_limit(value: object | None) -> int:
    try:
        limit = int(value or 50)
    except (TypeError, ValueError) as exc:
        raise OperationLogError("Limite invalido.") from exc
    return min(max(limit, 1), MAX_LIMIT)


def normalize_offset(value: object | None) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError) as exc:
        raise OperationLogError("Pagina invalida.") from exc
