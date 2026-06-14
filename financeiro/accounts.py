from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus

from financeiro.database import get_connection, row_to_dict

SUPPORTED_CURRENCIES = {"BRL", "USD", "EUR", "GBP"}
ACCOUNT_TYPES = {"liquidity", "investment"}


class AccountError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def list_checking_accounts(user_id: int) -> list[dict]:
    return list_accounts_by_status(user_id, archived=False)


def list_archived_checking_accounts(user_id: int) -> list[dict]:
    return list_accounts_by_status(user_id, archived=True)


def list_accounts_by_status(user_id: int, archived: bool) -> list[dict]:
    archived_filter = "archived_at IS NOT NULL" if archived else "archived_at IS NULL"
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM checking_accounts
            WHERE user_id = ? AND {archived_filter}
            ORDER BY bank_name COLLATE NOCASE, name COLLATE NOCASE
            """,
            (user_id,),
        ).fetchall()
    return [format_account(row_to_dict(row)) for row in rows]


def create_checking_account(user_id: int, data: dict) -> dict:
    account = normalize_account_payload(data)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO checking_accounts (
                user_id, name, bank_name, branch, account_number, account_type, currency,
                initial_balance_cents, current_balance_cents, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                account["name"],
                account["bank_name"],
                account["branch"],
                account["account_number"],
                account["account_type"],
                account["currency"],
                account["initial_balance_cents"],
                account["initial_balance_cents"],
                account["notes"],
            ),
        )
        row = conn.execute("SELECT * FROM checking_accounts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return format_account(row_to_dict(row))


def update_checking_account(user_id: int, account_id: str, data: dict) -> dict:
    account = normalize_account_payload(data)
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id, currency, initial_balance_cents, current_balance_cents
            FROM checking_accounts
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (account_id, user_id),
        ).fetchone()
        if not existing:
            raise AccountError("Conta nao encontrada.", HTTPStatus.NOT_FOUND)
        transaction_count = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM transactions
            WHERE user_id = ? AND archived_at IS NULL
                AND (account_id = ? OR destination_account_id = ?)
            """,
            (user_id, account_id, account_id),
        ).fetchone()["total"]
        if transaction_count and account["currency"] != existing["currency"]:
            raise AccountError("Nao altere a moeda de uma conta com lancamentos.")
        balance_delta = account["initial_balance_cents"] - existing["initial_balance_cents"]
        updated_current_balance = existing["current_balance_cents"] + balance_delta
        conn.execute(
            """
            UPDATE checking_accounts
            SET name = ?, bank_name = ?, branch = ?, account_number = ?, account_type = ?, currency = ?,
                initial_balance_cents = ?, current_balance_cents = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (
                account["name"],
                account["bank_name"],
                account["branch"],
                account["account_number"],
                account["account_type"],
                account["currency"],
                account["initial_balance_cents"],
                updated_current_balance,
                account["notes"],
                account_id,
                user_id,
            ),
        )
        row = conn.execute("SELECT * FROM checking_accounts WHERE id = ?", (account_id,)).fetchone()
    return format_account(row_to_dict(row))


def archive_checking_account(user_id: int, account_id: str) -> None:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE checking_accounts
            SET archived_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (account_id, user_id),
        )
        if cursor.rowcount == 0:
            raise AccountError("Conta nao encontrada.", HTTPStatus.NOT_FOUND)


def restore_checking_account(user_id: int, account_id: str) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE checking_accounts
            SET archived_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NOT NULL
            """,
            (account_id, user_id),
        )
        if cursor.rowcount == 0:
            raise AccountError("Conta arquivada nao encontrada.", HTTPStatus.NOT_FOUND)
        row = conn.execute(
            "SELECT * FROM checking_accounts WHERE id = ? AND user_id = ?",
            (account_id, user_id),
        ).fetchone()
    return format_account(row_to_dict(row))


def normalize_account_payload(data: dict) -> dict:
    name = str(data.get("name", "")).strip()
    bank_name = str(data.get("bank_name", "")).strip()
    currency = str(data.get("currency", "BRL")).strip().upper()
    account_type = str(data.get("account_type", "liquidity")).strip().lower()
    if not name:
        raise AccountError("Informe o nome da conta.")
    if not bank_name:
        raise AccountError("Informe o banco.")
    if account_type not in ACCOUNT_TYPES:
        raise AccountError("Natureza da conta invalida.")
    if currency not in SUPPORTED_CURRENCIES:
        raise AccountError("Moeda nao suportada neste modulo inicial.")
    return {
        "name": name,
        "bank_name": bank_name,
        "account_type": account_type,
        "branch": empty_to_none(data.get("branch")),
        "account_number": empty_to_none(data.get("account_number")),
        "currency": currency,
        "initial_balance_cents": money_to_cents(data.get("initial_balance", "0")),
        "notes": empty_to_none(data.get("notes")),
    }


def money_to_cents(value: object) -> int:
    raw = str(value or "0").strip().replace(".", "").replace(",", ".")
    try:
        decimal = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise AccountError("Saldo inicial invalido.") from exc
    return int(decimal * 100)


def cents_to_money(cents: int) -> str:
    value = Decimal(cents) / Decimal(100)
    return f"{value:.2f}"


def empty_to_none(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def format_account(account: dict) -> dict:
    account["initial_balance"] = cents_to_money(account.pop("initial_balance_cents"))
    account["current_balance"] = cents_to_money(account.pop("current_balance_cents"))
    return account
