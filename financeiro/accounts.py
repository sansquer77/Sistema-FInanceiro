from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus

from financeiro.database import begin_immediate, get_connection, row_to_dict

SUPPORTED_CURRENCIES = {"BRL", "USD", "EUR", "GBP"}
ACCOUNT_TYPES = {"liquidity", "wallet", "investment"}


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
    today = date.today().isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                checking_accounts.id,
                checking_accounts.user_id,
                checking_accounts.name,
                checking_accounts.bank_name,
                checking_accounts.branch,
                checking_accounts.account_number,
                checking_accounts.account_type,
                checking_accounts.currency,
                checking_accounts.initial_balance_cents,
                checking_accounts.current_balance_cents AS stored_current_balance_cents,
                checking_accounts.notes,
                checking_accounts.archived_at,
                checking_accounts.created_at,
                checking_accounts.updated_at,
                checking_accounts.initial_balance_cents
                    + COALESCE(SUM(
                        CASE
                            WHEN transactions.account_id = checking_accounts.id
                                AND transactions.type = 'income'
                                THEN transactions.amount_cents
                            WHEN transactions.account_id = checking_accounts.id
                                AND transactions.type IN ('expense', 'investment', 'transfer')
                                THEN -transactions.amount_cents
                            WHEN transactions.destination_account_id = checking_accounts.id
                                AND transactions.type = 'transfer'
                                THEN COALESCE(NULLIF(transactions.destination_amount_cents, 0), transactions.amount_cents)
                            ELSE 0
                        END
                    ), 0) AS effective_current_balance_cents
            FROM checking_accounts
            LEFT JOIN transactions
                ON transactions.user_id = checking_accounts.user_id
                AND transactions.archived_at IS NULL
                AND transactions.date <= ?
                AND (
                    transactions.account_id = checking_accounts.id
                    OR transactions.destination_account_id = checking_accounts.id
                )
            WHERE checking_accounts.user_id = ? AND checking_accounts.{archived_filter}
            GROUP BY checking_accounts.id
            ORDER BY checking_accounts.bank_name COLLATE NOCASE, checking_accounts.name COLLATE NOCASE
            """,
            (today, user_id),
        ).fetchall()
    return [format_account(row_to_dict(row)) for row in rows]


def recompute_account_balance(conn, user_id: int, account_id: int) -> None:
    # spec: contas-correntes v1.2 — criterio 3
    # (saldo atual = saldo inicial + deltas de lancamentos com data <= hoje;
    #  lancamentos futuros nao movem o saldo armazenado, mantendo o cache
    #  sempre igual ao saldo efetivo exibido pela listagem)
    today = date.today().isoformat()
    conn.execute(
        """
        UPDATE checking_accounts
        SET current_balance_cents = (
                SELECT initial_balance_cents + COALESCE(SUM(
                    CASE
                        WHEN transactions.account_id = checking_accounts.id
                            AND transactions.type = 'income'
                            THEN transactions.amount_cents
                        WHEN transactions.account_id = checking_accounts.id
                            AND transactions.type IN ('expense', 'investment', 'transfer')
                            THEN -transactions.amount_cents
                        WHEN transactions.destination_account_id = checking_accounts.id
                            AND transactions.type = 'transfer'
                            THEN COALESCE(NULLIF(transactions.destination_amount_cents, 0), transactions.amount_cents)
                        ELSE 0
                    END
                ), 0)
                FROM transactions
                WHERE transactions.user_id = checking_accounts.user_id
                    AND transactions.archived_at IS NULL
                    AND transactions.date <= ?
                    AND (
                        transactions.account_id = checking_accounts.id
                        OR transactions.destination_account_id = checking_accounts.id
                    )
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE checking_accounts.id = ? AND checking_accounts.user_id = ?
        """,
        (today, account_id, user_id),
    )


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
        begin_immediate(conn)
        existing = conn.execute(
            """
            SELECT id, currency, initial_balance_cents
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
        conn.execute(
            """
            UPDATE checking_accounts
            SET name = ?, bank_name = ?, branch = ?, account_number = ?, account_type = ?, currency = ?,
                initial_balance_cents = ?,
                notes = ?,
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
                account["notes"],
                account_id,
                user_id,
            ),
        )
        recompute_account_balance(conn, user_id, account_id)
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
        recompute_account_balance(conn, user_id, account_id)
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
    if account_type == "wallet" and not bank_name:
        bank_name = "Carteira"
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
        "branch": None if account_type == "wallet" else empty_to_none(data.get("branch")),
        "account_number": None if account_type == "wallet" else empty_to_none(data.get("account_number")),
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
    stored_balance = account.pop("stored_current_balance_cents", None)
    if stored_balance is not None:
        account["stored_current_balance"] = cents_to_money(stored_balance)
    effective_balance = account.pop("effective_current_balance_cents", None)
    if effective_balance is not None:
        account["current_balance_cents"] = effective_balance
        account["balance_source"] = "calculated"
    else:
        account["balance_source"] = "stored"
    account["current_balance"] = cents_to_money(account.pop("current_balance_cents"))
    return account
