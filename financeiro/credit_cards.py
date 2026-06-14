from __future__ import annotations

from http import HTTPStatus

from financeiro.accounts import SUPPORTED_CURRENCIES, cents_to_money, empty_to_none, money_to_cents
from financeiro.database import get_connection, row_to_dict


class CreditCardError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def list_credit_cards(user_id: int) -> list[dict]:
    return list_credit_cards_by_status(user_id, archived=False)


def list_archived_credit_cards(user_id: int) -> list[dict]:
    return list_credit_cards_by_status(user_id, archived=True)


def list_credit_cards_by_status(user_id: int, archived: bool) -> list[dict]:
    archived_filter = "archived_at IS NOT NULL" if archived else "archived_at IS NULL"
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM credit_cards
            WHERE user_id = ? AND {archived_filter}
            ORDER BY issuer COLLATE NOCASE, name COLLATE NOCASE
            """,
            (user_id,),
        ).fetchall()
    return [format_credit_card(row_to_dict(row)) for row in rows]


def create_credit_card(user_id: int, data: dict) -> dict:
    card = normalize_credit_card_payload(data)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO credit_cards (
                    user_id, name, issuer, network, currency, limit_cents,
                    closing_day, due_day, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    card["name"],
                    card["issuer"],
                    card["network"],
                    card["currency"],
                    card["limit_cents"],
                    card["closing_day"],
                    card["due_day"],
                    card["notes"],
                ),
            )
            row = conn.execute("SELECT * FROM credit_cards WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise CreditCardError("Ja existe um cartao com este nome.", HTTPStatus.CONFLICT) from exc
        raise
    return format_credit_card(row_to_dict(row))


def update_credit_card(user_id: int, card_id: str, data: dict) -> dict:
    normalized_id = normalize_card_id(card_id)
    card = normalize_credit_card_payload(data)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE credit_cards
                SET name = ?, issuer = ?, network = ?, currency = ?, limit_cents = ?,
                    closing_day = ?, due_day = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND archived_at IS NULL
                """,
                (
                    card["name"],
                    card["issuer"],
                    card["network"],
                    card["currency"],
                    card["limit_cents"],
                    card["closing_day"],
                    card["due_day"],
                    card["notes"],
                    normalized_id,
                    user_id,
                ),
            )
            if cursor.rowcount == 0:
                raise CreditCardError("Cartao nao encontrado.", HTTPStatus.NOT_FOUND)
            row = conn.execute("SELECT * FROM credit_cards WHERE id = ?", (normalized_id,)).fetchone()
    except CreditCardError:
        raise
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise CreditCardError("Ja existe um cartao com este nome.", HTTPStatus.CONFLICT) from exc
        raise
    return format_credit_card(row_to_dict(row))


def archive_credit_card(user_id: int, card_id: str) -> None:
    normalized_id = normalize_card_id(card_id)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE credit_cards
            SET archived_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (normalized_id, user_id),
        )
        if cursor.rowcount == 0:
            raise CreditCardError("Cartao nao encontrado.", HTTPStatus.NOT_FOUND)


def restore_credit_card(user_id: int, card_id: str) -> dict:
    normalized_id = normalize_card_id(card_id)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE credit_cards
            SET archived_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NOT NULL
            """,
            (normalized_id, user_id),
        )
        if cursor.rowcount == 0:
            raise CreditCardError("Cartao arquivado nao encontrado.", HTTPStatus.NOT_FOUND)
        row = conn.execute(
            "SELECT * FROM credit_cards WHERE id = ? AND user_id = ?",
            (normalized_id, user_id),
        ).fetchone()
    return format_credit_card(row_to_dict(row))


def normalize_credit_card_payload(data: dict) -> dict:
    name = str(data.get("name", "")).strip()
    issuer = str(data.get("issuer", "")).strip()
    currency = str(data.get("currency", "BRL")).strip().upper()
    try:
        limit_cents = money_to_cents(data.get("limit", "0"))
    except Exception as exc:
        raise CreditCardError("Limite invalido.") from exc
    if not name:
        raise CreditCardError("Informe o nome do cartao.")
    if not issuer:
        raise CreditCardError("Informe o emissor do cartao.")
    if currency not in SUPPORTED_CURRENCIES:
        raise CreditCardError("Moeda nao suportada neste modulo inicial.")
    if limit_cents <= 0:
        raise CreditCardError("Informe um limite maior que zero.")
    return {
        "name": name,
        "issuer": issuer,
        "network": empty_to_none(data.get("network")),
        "currency": currency,
        "limit_cents": limit_cents,
        "closing_day": normalize_day(data.get("closing_day"), "Informe o dia de fechamento."),
        "due_day": normalize_day(data.get("due_day"), "Informe o dia de vencimento."),
        "notes": empty_to_none(data.get("notes")),
    }


def normalize_day(value: object, message: str) -> int:
    try:
        day = int(str(value or "").strip())
    except ValueError as exc:
        raise CreditCardError(message) from exc
    if day < 1 or day > 31:
        raise CreditCardError("Informe um dia entre 1 e 31.")
    return day


def normalize_card_id(value: object) -> int:
    try:
        normalized = int(str(value or "").strip())
    except ValueError as exc:
        raise CreditCardError("Cartao nao encontrado.", HTTPStatus.NOT_FOUND) from exc
    if normalized <= 0:
        raise CreditCardError("Cartao nao encontrado.", HTTPStatus.NOT_FOUND)
    return normalized


def format_credit_card(card: dict) -> dict:
    card["limit"] = cents_to_money(card.pop("limit_cents"))
    return card
