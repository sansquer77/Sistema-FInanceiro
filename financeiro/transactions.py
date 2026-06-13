from __future__ import annotations

from datetime import date
from http import HTTPStatus

from financeiro.accounts import cents_to_money, empty_to_none, money_to_cents
from financeiro.categories import ClassificationError, get_or_create_category, get_or_create_tag, normalize_name
from financeiro.database import get_connection, row_to_dict

TRANSACTION_TYPES = {"income", "expense", "transfer"}


class TransactionError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def list_transactions(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                transactions.*,
                source.name AS account_name,
                source.currency AS account_currency,
                destination.name AS destination_account_name,
                categories.name AS category_name,
                GROUP_CONCAT(tags.name, '||') AS tag_names
            FROM transactions
            JOIN checking_accounts AS source
                ON source.id = transactions.account_id
                AND source.user_id = transactions.user_id
            LEFT JOIN checking_accounts AS destination
                ON destination.id = transactions.destination_account_id
                AND destination.user_id = transactions.user_id
            LEFT JOIN categories
                ON categories.id = transactions.category_id
                AND categories.user_id = transactions.user_id
            LEFT JOIN transaction_tags
                ON transaction_tags.transaction_id = transactions.id
            LEFT JOIN tags
                ON tags.id = transaction_tags.tag_id
                AND tags.user_id = transactions.user_id
            WHERE transactions.user_id = ? AND transactions.archived_at IS NULL
            GROUP BY transactions.id
            ORDER BY transactions.date DESC, transactions.id DESC
            """,
            (user_id,),
        ).fetchall()
    return [format_transaction(row_to_dict(row)) for row in rows]


def create_transaction(user_id: int, data: dict) -> dict:
    transaction = normalize_transaction_payload(data)
    with get_connection() as conn:
        source = get_active_account(conn, user_id, transaction["account_id"])
        destination = None
        if transaction["type"] == "transfer":
            destination = get_active_account(conn, user_id, transaction["destination_account_id"])
            if source["id"] == destination["id"]:
                raise TransactionError("Informe contas diferentes para transferencia.")
            if source["currency"] != destination["currency"]:
                raise TransactionError("Transferencias exigem contas com a mesma moeda.")
        category_id = get_or_create_category(conn, user_id, transaction["category"])
        tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in transaction["tags"]]
        apply_balance_delta(conn, source["id"], balance_delta(transaction["type"], transaction["amount_cents"], "source"))
        if destination:
            apply_balance_delta(conn, destination["id"], balance_delta(transaction["type"], transaction["amount_cents"], "destination"))
        cursor = conn.execute(
            """
            INSERT INTO transactions (
                user_id, type, description, amount_cents, date, account_id,
                destination_account_id, category_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                transaction["type"],
                transaction["description"],
                transaction["amount_cents"],
                transaction["date"],
                source["id"],
                destination["id"] if destination else None,
                category_id,
                transaction["notes"],
            ),
        )
        replace_transaction_tags(conn, cursor.lastrowid, tag_ids)
        row = fetch_transaction(conn, user_id, cursor.lastrowid)
    return format_transaction(row)


def delete_transaction(user_id: int, transaction_id: str) -> None:
    with get_connection() as conn:
        transaction = conn.execute(
            """
            SELECT *
            FROM transactions
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (transaction_id, user_id),
        ).fetchone()
        if not transaction:
            raise TransactionError("Lancamento nao encontrado.", HTTPStatus.NOT_FOUND)
        apply_balance_delta(conn, transaction["account_id"], -balance_delta(transaction["type"], transaction["amount_cents"], "source"))
        if transaction["destination_account_id"]:
            apply_balance_delta(
                conn,
                transaction["destination_account_id"],
                -balance_delta(transaction["type"], transaction["amount_cents"], "destination"),
            )
        conn.execute(
            """
            DELETE FROM transactions
            WHERE id = ? AND user_id = ?
            """,
            (transaction_id, user_id),
        )


def normalize_transaction_payload(data: dict) -> dict:
    transaction_type = str(data.get("type", "")).strip().lower()
    description = str(data.get("description", "")).strip()
    transaction_date = normalize_date(data.get("date"))
    if transaction_type not in TRANSACTION_TYPES:
        raise TransactionError("Tipo de lancamento invalido.")
    if not description:
        raise TransactionError("Informe a descricao do lancamento.")
    account_id = normalize_id(data.get("account_id"), "Informe a conta.")
    destination_account_id = None
    if transaction_type == "transfer":
        destination_account_id = normalize_id(data.get("destination_account_id"), "Informe a conta de destino.")
    amount_cents = money_to_cents(data.get("amount", "0"))
    if amount_cents <= 0:
        raise TransactionError("Informe um valor maior que zero.")
    return {
        "type": transaction_type,
        "description": description,
        "amount_cents": amount_cents,
        "date": transaction_date,
        "account_id": account_id,
        "destination_account_id": destination_account_id,
        "category": normalize_name(data.get("category"), "Informe a categoria."),
        "tags": normalize_tags(data.get("tags") or data.get("tag")),
        "notes": empty_to_none(data.get("notes")),
    }


def normalize_id(value: object, message: str) -> int:
    try:
        normalized = int(str(value or "").strip())
    except ValueError as exc:
        raise TransactionError(message) from exc
    if normalized <= 0:
        raise TransactionError(message)
    return normalized


def normalize_date(value: object) -> str:
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise TransactionError("Informe uma data valida.") from exc


def get_active_account(conn, user_id: int, account_id: int):
    account = conn.execute(
        """
        SELECT id, currency
        FROM checking_accounts
        WHERE id = ? AND user_id = ? AND archived_at IS NULL
        """,
        (account_id, user_id),
    ).fetchone()
    if not account:
        raise TransactionError("Conta nao encontrada.", HTTPStatus.NOT_FOUND)
    return account


def balance_delta(transaction_type: str, amount_cents: int, side: str) -> int:
    if transaction_type == "income":
        return amount_cents
    if transaction_type == "expense":
        return -amount_cents
    if side == "destination":
        return amount_cents
    return -amount_cents


def apply_balance_delta(conn, account_id: int, delta_cents: int) -> None:
    conn.execute(
        """
        UPDATE checking_accounts
        SET current_balance_cents = current_balance_cents + ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (delta_cents, account_id),
    )


def replace_transaction_tags(conn, transaction_id: int, tag_ids: list[int]) -> None:
    conn.execute("DELETE FROM transaction_tags WHERE transaction_id = ?", (transaction_id,))
    conn.executemany(
        "INSERT OR IGNORE INTO transaction_tags (transaction_id, tag_id) VALUES (?, ?)",
        [(transaction_id, tag_id) for tag_id in tag_ids],
    )


def fetch_transaction(conn, user_id: int, transaction_id: int) -> dict:
    row = conn.execute(
        """
        SELECT
            transactions.*,
                source.name AS account_name,
                source.currency AS account_currency,
                destination.name AS destination_account_name,
                categories.name AS category_name,
                GROUP_CONCAT(tags.name, '||') AS tag_names
            FROM transactions
            JOIN checking_accounts AS source
                ON source.id = transactions.account_id
                AND source.user_id = transactions.user_id
            LEFT JOIN checking_accounts AS destination
                ON destination.id = transactions.destination_account_id
                AND destination.user_id = transactions.user_id
            LEFT JOIN categories
                ON categories.id = transactions.category_id
                AND categories.user_id = transactions.user_id
            LEFT JOIN transaction_tags
                ON transaction_tags.transaction_id = transactions.id
            LEFT JOIN tags
                ON tags.id = transaction_tags.tag_id
                AND tags.user_id = transactions.user_id
            WHERE transactions.id = ? AND transactions.user_id = ?
            GROUP BY transactions.id
            """,
        (transaction_id, user_id),
    ).fetchone()
    return row_to_dict(row)


def format_transaction(transaction: dict) -> dict:
    transaction["amount"] = cents_to_money(transaction.pop("amount_cents"))
    raw_tags = transaction.pop("tag_names", "") or ""
    transaction["tags"] = [tag for tag in raw_tags.split("||") if tag]
    transaction["tag_name"] = ", ".join(transaction["tags"])
    return transaction


def normalize_tags(value: object) -> list[str]:
    if isinstance(value, list):
        raw_parts = value
    else:
        raw = str(value or "")
        for separator in (";", "|", "\n"):
            raw = raw.replace(separator, ",")
        raw_parts = raw.split(",")
    tags = []
    seen = set()
    for part in raw_parts:
        if not str(part or "").strip():
            continue
        try:
            tag = normalize_name(part, "Informe ao menos uma tag.")
        except ClassificationError as exc:
            raise TransactionError(exc.message) from exc
        key = tag.casefold()
        if key not in seen:
            seen.add(key)
            tags.append(tag)
    if not tags:
        raise TransactionError("Informe ao menos uma tag.")
    return tags
