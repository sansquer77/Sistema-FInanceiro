from __future__ import annotations

from datetime import date, timedelta
from http import HTTPStatus
import re
from uuid import uuid4

from financeiro.accounts import SUPPORTED_CURRENCIES, cents_to_money, empty_to_none, money_to_cents
from financeiro.categories import get_or_create_category, get_or_create_subcategory, get_or_create_tag, normalize_name
from financeiro.database import get_connection, row_to_dict
from financeiro.transactions import create_transaction, normalize_optional_tags

CARD_TRANSACTION_TYPES = {"income", "expense"}
CARD_SERIES_KINDS = {"single", "installment", "recurring"}
CARD_RECURRENCE_FREQUENCIES = {"weekly", "monthly", "quarterly", "semiannual", "annual"}
MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")

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


def list_credit_card_invoice(user_id: int, card_id: object, month: object) -> dict:
    normalized_card_id = normalize_card_id(card_id)
    normalized_month = normalize_month(month)
    with get_connection() as conn:
        card = get_active_credit_card(conn, user_id, normalized_card_id)
        rows = conn.execute(
            """
            SELECT
                credit_card_transactions.*,
                categories.name AS category_name,
                subcategories.name AS subcategory_name,
                GROUP_CONCAT(tags.name, '||') AS tag_names
            FROM credit_card_transactions
            LEFT JOIN categories
                ON categories.id = credit_card_transactions.category_id
                AND categories.user_id = credit_card_transactions.user_id
            LEFT JOIN subcategories
                ON subcategories.id = credit_card_transactions.subcategory_id
                AND subcategories.user_id = credit_card_transactions.user_id
            LEFT JOIN credit_card_transaction_tags
                ON credit_card_transaction_tags.credit_card_transaction_id = credit_card_transactions.id
            LEFT JOIN tags
                ON tags.id = credit_card_transaction_tags.tag_id
                AND tags.user_id = credit_card_transactions.user_id
            WHERE credit_card_transactions.user_id = ?
                AND credit_card_transactions.credit_card_id = ?
                AND credit_card_transactions.invoice_month = ?
                AND credit_card_transactions.archived_at IS NULL
            GROUP BY credit_card_transactions.id
            ORDER BY credit_card_transactions.date DESC, credit_card_transactions.id DESC
            """,
            (user_id, normalized_card_id, normalized_month),
        ).fetchall()
        payment_rows = conn.execute(
            """
            SELECT
                credit_card_payments.*,
                checking_accounts.name AS account_name
            FROM credit_card_payments
            JOIN checking_accounts
                ON checking_accounts.id = credit_card_payments.account_id
                AND checking_accounts.user_id = credit_card_payments.user_id
            WHERE credit_card_payments.user_id = ?
                AND credit_card_payments.credit_card_id = ?
                AND credit_card_payments.invoice_month = ?
            ORDER BY credit_card_payments.payment_date DESC, credit_card_payments.id DESC
            """,
            (user_id, normalized_card_id, normalized_month),
        ).fetchall()
    transactions = [format_card_transaction(row_to_dict(row), card["currency"]) for row in rows]
    payments = [format_card_payment(row_to_dict(row), card["currency"]) for row in payment_rows]
    return {
        "card": format_credit_card(row_to_dict(card)),
        "month": normalized_month,
        "transactions": transactions,
        "payments": payments,
    }


def list_credit_card_transactions(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                credit_card_transactions.*,
                credit_cards.name AS credit_card_name,
                credit_cards.issuer AS credit_card_issuer,
                credit_cards.currency AS card_currency,
                categories.name AS category_name,
                subcategories.name AS subcategory_name,
                GROUP_CONCAT(tags.name, '||') AS tag_names
            FROM credit_card_transactions
            JOIN credit_cards
                ON credit_cards.id = credit_card_transactions.credit_card_id
                AND credit_cards.user_id = credit_card_transactions.user_id
            LEFT JOIN categories
                ON categories.id = credit_card_transactions.category_id
                AND categories.user_id = credit_card_transactions.user_id
            LEFT JOIN subcategories
                ON subcategories.id = credit_card_transactions.subcategory_id
                AND subcategories.user_id = credit_card_transactions.user_id
            LEFT JOIN credit_card_transaction_tags
                ON credit_card_transaction_tags.credit_card_transaction_id = credit_card_transactions.id
            LEFT JOIN tags
                ON tags.id = credit_card_transaction_tags.tag_id
                AND tags.user_id = credit_card_transactions.user_id
            WHERE credit_card_transactions.user_id = ?
                AND credit_card_transactions.archived_at IS NULL
            GROUP BY credit_card_transactions.id
            ORDER BY credit_card_transactions.date DESC, credit_card_transactions.id DESC
            """,
            (user_id,),
        ).fetchall()
    return [
        format_card_transaction(row_to_dict(row), row["card_currency"])
        for row in rows
    ]


def list_credit_card_payments(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                credit_card_payments.*,
                credit_cards.currency AS card_currency,
                checking_accounts.name AS account_name
            FROM credit_card_payments
            JOIN credit_cards
                ON credit_cards.id = credit_card_payments.credit_card_id
                AND credit_cards.user_id = credit_card_payments.user_id
            JOIN checking_accounts
                ON checking_accounts.id = credit_card_payments.account_id
                AND checking_accounts.user_id = credit_card_payments.user_id
            WHERE credit_card_payments.user_id = ?
            ORDER BY credit_card_payments.payment_date DESC, credit_card_payments.id DESC
            """,
            (user_id,),
        ).fetchall()
    return [
        format_card_payment(row_to_dict(row), row["card_currency"])
        for row in rows
    ]


def create_credit_card(user_id: int, data: dict) -> dict:
    card = normalize_credit_card_payload(data)
    try:
        with get_connection() as conn:
            validate_preferred_payment_account(conn, user_id, card["preferred_payment_account_id"], card["currency"])
            cursor = conn.execute(
                """
                INSERT INTO credit_cards (
                    user_id, name, issuer, network, currency, limit_cents,
                    closing_day, due_day, preferred_payment_account_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    card["preferred_payment_account_id"],
                    card["notes"],
                ),
            )
            row = conn.execute("SELECT * FROM credit_cards WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise CreditCardError("Ja existe um cartao com este nome.", HTTPStatus.CONFLICT) from exc
        raise
    return format_credit_card(row_to_dict(row))


def create_credit_card_transaction(user_id: int, data: dict) -> dict:
    transaction = normalize_card_transaction_payload(data)
    with get_connection() as conn:
        card = get_active_credit_card(conn, user_id, transaction["credit_card_id"])
        ensure_invoice_is_open(conn, user_id, card["id"], transaction["invoice_month"])
        ensure_not_before_previous_closed_invoice(conn, user_id, card, transaction["invoice_month"], transaction["date"])
        category_id = get_or_create_category(conn, user_id, transaction["category"], transaction["type"])
        subcategory_id = get_or_create_subcategory(conn, user_id, category_id, transaction["subcategory"])
        tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in transaction["tags"]]
        occurrences = build_card_transaction_occurrences(transaction)
        series_id = str(uuid4()) if transaction["series_kind"] != "single" else None
        first_transaction_id = None
        for occurrence in occurrences:
            ensure_invoice_is_open(conn, user_id, card["id"], occurrence["invoice_month"])
            ensure_not_before_previous_closed_invoice(conn, user_id, card, occurrence["invoice_month"], occurrence["date"])
            cursor = conn.execute(
                """
                INSERT INTO credit_card_transactions (
                    user_id, credit_card_id, type, description, amount_cents, date,
                    invoice_month, series_id, series_kind, installment_index,
                    installment_count, recurrence_frequency, category_id, subcategory_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    card["id"],
                    transaction["type"],
                    occurrence["description"],
                    transaction["amount_cents"],
                    occurrence["date"],
                    occurrence["invoice_month"],
                    series_id,
                    transaction["series_kind"],
                    occurrence["installment_index"],
                    occurrence["installment_count"],
                    transaction["recurrence_frequency"],
                    category_id,
                    subcategory_id,
                    transaction["notes"],
                ),
            )
            if first_transaction_id is None:
                first_transaction_id = cursor.lastrowid
            replace_credit_card_transaction_tags(conn, cursor.lastrowid, tag_ids)
        row = fetch_card_transaction(conn, user_id, first_transaction_id)
    return format_card_transaction(row, card["currency"])


def update_credit_card_transaction(user_id: int, transaction_id: str, data: dict) -> dict:
    normalized_id = normalize_card_id(transaction_id)
    transaction = normalize_card_transaction_payload(data)
    apply_to_future = should_apply_to_future_card(data)
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT *
            FROM credit_card_transactions
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (normalized_id, user_id),
        ).fetchone()
        if not existing:
            raise CreditCardError("Lancamento do cartao nao encontrado.", HTTPStatus.NOT_FOUND)
        ensure_invoice_is_open(conn, user_id, existing["credit_card_id"], existing["invoice_month"])
        card = get_active_credit_card(conn, user_id, transaction["credit_card_id"])
        if card["id"] != existing["credit_card_id"]:
            raise CreditCardError("Nao e possivel mover lancamento entre cartoes.")
        if transaction["invoice_month"] != existing["invoice_month"]:
            raise CreditCardError("Nao e possivel mover lancamento entre faturas.")
        ensure_not_before_previous_closed_invoice(conn, user_id, card, existing["invoice_month"], transaction["date"])
        category_id = get_or_create_category(conn, user_id, transaction["category"], transaction["type"])
        subcategory_id = get_or_create_subcategory(conn, user_id, category_id, transaction["subcategory"])
        tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in transaction["tags"]]
        conn.execute(
            """
            UPDATE credit_card_transactions
            SET type = ?, description = ?, amount_cents = ?, date = ?, category_id = ?,
                subcategory_id = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (
                transaction["type"],
                transaction["description"],
                transaction["amount_cents"],
                transaction["date"],
                category_id,
                subcategory_id,
                transaction["notes"],
                normalized_id,
                user_id,
            ),
        )
        replace_credit_card_transaction_tags(conn, normalized_id, tag_ids)
        if apply_to_future:
            update_future_card_series(conn, user_id, existing, transaction, category_id, subcategory_id, tag_ids)
        row = fetch_card_transaction(conn, user_id, normalized_id)
    return format_card_transaction(row, card["currency"])


def update_future_card_series(
    conn,
    user_id: int,
    existing,
    transaction: dict,
    category_id: int,
    subcategory_id: int | None,
    tag_ids: list[int],
) -> None:
    if not existing["series_id"]:
        return
    if not is_card_series(existing):
        return
    date_delta = date.fromisoformat(transaction["date"]) - date.fromisoformat(existing["date"])
    future_filter = "installment_index > ?" if is_installment_card_series(existing) and existing["installment_index"] else "date > ?"
    future_marker = existing["installment_index"] if is_installment_card_series(existing) and existing["installment_index"] else existing["date"]
    future_rows = conn.execute(
        f"""
        SELECT *
        FROM credit_card_transactions
        WHERE user_id = ? AND archived_at IS NULL
            AND series_id = ? AND id <> ? AND reconciled_at IS NULL
            AND {future_filter}
        ORDER BY invoice_month ASC, date ASC, id ASC
        """,
        (user_id, existing["series_id"], existing["id"], future_marker),
    ).fetchall()
    for row in future_rows:
        ensure_invoice_is_open(conn, user_id, row["credit_card_id"], row["invoice_month"])
        shifted_date = (date.fromisoformat(row["date"]) + date_delta).isoformat()
        card = get_active_credit_card(conn, user_id, row["credit_card_id"])
        ensure_not_before_previous_closed_invoice(conn, user_id, card, row["invoice_month"], shifted_date)
        conn.execute(
            """
            UPDATE credit_card_transactions
            SET type = ?, description = ?, amount_cents = ?, date = ?, category_id = ?,
                subcategory_id = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (
                transaction["type"],
                transaction["description"],
                transaction["amount_cents"],
                shifted_date,
                category_id,
                subcategory_id,
                transaction["notes"],
                row["id"],
                user_id,
            ),
        )
        replace_credit_card_transaction_tags(conn, row["id"], tag_ids)


def delete_credit_card_transaction(user_id: int, transaction_id: str, apply_to_future: bool = False) -> None:
    normalized_id = normalize_card_id(transaction_id)
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT *
            FROM credit_card_transactions
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (normalized_id, user_id),
        ).fetchone()
        if not existing:
            raise CreditCardError("Lancamento do cartao nao encontrado.", HTTPStatus.NOT_FOUND)
        ensure_invoice_is_open(conn, user_id, existing["credit_card_id"], existing["invoice_month"])
        transaction_ids = [existing["id"], *[
            row["id"] for row in future_card_transactions_to_delete(conn, user_id, existing, apply_to_future)
        ]]
        cursor = conn.execute(
            f"""
            UPDATE credit_card_transactions
            SET archived_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND archived_at IS NULL
                AND id IN ({",".join("?" for _ in transaction_ids)})
            """,
            (user_id, *transaction_ids),
        )
        if cursor.rowcount == 0:
            raise CreditCardError("Lancamento do cartao nao encontrado.", HTTPStatus.NOT_FOUND)


def future_card_transactions_to_delete(conn, user_id: int, transaction, apply_to_future: bool):
    if not apply_to_future or not transaction["series_id"]:
        return []
    if not is_card_series(transaction):
        return []
    future_filter = "installment_index > ?" if is_installment_card_series(transaction) and transaction["installment_index"] else "date > ?"
    future_marker = transaction["installment_index"] if is_installment_card_series(transaction) and transaction["installment_index"] else transaction["date"]
    return conn.execute(
        f"""
        SELECT credit_card_transactions.*
        FROM credit_card_transactions
        LEFT JOIN credit_card_payments
            ON credit_card_payments.user_id = credit_card_transactions.user_id
            AND credit_card_payments.credit_card_id = credit_card_transactions.credit_card_id
            AND credit_card_payments.invoice_month = credit_card_transactions.invoice_month
        WHERE credit_card_transactions.user_id = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.series_id = ?
            AND credit_card_transactions.id <> ?
            AND credit_card_transactions.reconciled_at IS NULL
            AND credit_card_payments.id IS NULL
            AND {future_filter}
        ORDER BY credit_card_transactions.invoice_month ASC, credit_card_transactions.date ASC, credit_card_transactions.id ASC
        """,
        (user_id, transaction["series_id"], transaction["id"], future_marker),
    ).fetchall()


def is_installment_card_series(transaction) -> bool:
    return transaction["series_kind"] == "installment" or (
        transaction["installment_index"] and transaction["installment_count"]
    )


def is_card_series(transaction) -> bool:
    return transaction["series_kind"] == "recurring" or is_installment_card_series(transaction)


def set_credit_card_transaction_reconciled(user_id: int, transaction_id: str, reconciled: bool) -> dict:
    normalized_id = normalize_card_id(transaction_id)
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT credit_card_id, invoice_month
            FROM credit_card_transactions
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (normalized_id, user_id),
        ).fetchone()
        if not existing:
            raise CreditCardError("Lancamento do cartao nao encontrado.", HTTPStatus.NOT_FOUND)
        ensure_invoice_is_open(conn, user_id, existing["credit_card_id"], existing["invoice_month"])
        cursor = conn.execute(
            """
            UPDATE credit_card_transactions
            SET reconciled_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (1 if reconciled else 0, normalized_id, user_id),
        )
        if cursor.rowcount == 0:
            raise CreditCardError("Lancamento do cartao nao encontrado.", HTTPStatus.NOT_FOUND)
        row = fetch_card_transaction(conn, user_id, normalized_id)
        card = get_active_credit_card(conn, user_id, row["credit_card_id"])
    return format_card_transaction(row, card["currency"])


def pay_credit_card_invoice(user_id: int, data: dict) -> dict:
    card_id = normalize_card_id(data.get("credit_card_id"))
    invoice_month = normalize_month(data.get("invoice_month"))
    account_id = normalize_card_id(data.get("account_id"))
    payment_date = normalize_date(data.get("payment_date"))
    notes = empty_to_none(data.get("notes"))
    with get_connection() as conn:
        card = get_active_credit_card(conn, user_id, card_id)
        account = conn.execute(
            """
            SELECT id, name, currency
            FROM checking_accounts
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (account_id, user_id),
        ).fetchone()
        if not account:
            raise CreditCardError("Conta de pagamento nao encontrada.", HTTPStatus.NOT_FOUND)
        if account["currency"] != card["currency"]:
            raise CreditCardError("A conta de pagamento deve ter a mesma moeda do cartao.")
        existing = conn.execute(
            """
            SELECT id
            FROM credit_card_payments
            WHERE user_id = ? AND credit_card_id = ? AND invoice_month = ?
            """,
            (user_id, card_id, invoice_month),
        ).fetchone()
        if existing:
            raise CreditCardError("Esta fatura ja foi paga.", HTTPStatus.CONFLICT)
        amount_cents = invoice_balance_cents(conn, user_id, card_id, invoice_month)
    if amount_cents <= 0:
        raise CreditCardError("Nao ha valor em aberto para pagar nesta fatura.")
    payment_transaction = create_transaction(
        user_id,
        {
            "type": "expense",
            "description": f"Pagamento fatura {card['name']} {format_invoice_month(invoice_month)}",
            "amount": cents_to_money(amount_cents).replace(".", ","),
            "date": payment_date,
            "account_id": str(account_id),
            "category": "Serviços Financeiros e Impostos",
            "subcategory": "Pagamento de Fatura de Cartão",
            "tags": "Cartão de Crédito",
            "notes": notes or f"Pagamento da fatura {invoice_month}.",
        },
    )
    try:
        with get_connection() as conn:
            validate_preferred_payment_account(conn, user_id, card["preferred_payment_account_id"], card["currency"])
            cursor = conn.execute(
                """
                INSERT INTO credit_card_payments (
                    user_id, credit_card_id, invoice_month, account_id, transaction_id,
                    payment_date, amount_cents, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    card_id,
                    invoice_month,
                    account_id,
                    payment_transaction["id"],
                    payment_date,
                    amount_cents,
                    notes,
                ),
            )
            row = conn.execute(
                """
                SELECT
                    credit_card_payments.*,
                    checking_accounts.name AS account_name
                FROM credit_card_payments
                JOIN checking_accounts
                    ON checking_accounts.id = credit_card_payments.account_id
                WHERE credit_card_payments.id = ? AND credit_card_payments.user_id = ?
                """,
                (cursor.lastrowid, user_id),
            ).fetchone()
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise CreditCardError("Esta fatura ja foi paga.", HTTPStatus.CONFLICT) from exc
        raise
    return {
        "payment": format_card_payment(row_to_dict(row), card["currency"]),
        "transaction": payment_transaction,
    }


def update_credit_card(user_id: int, card_id: str, data: dict) -> dict:
    normalized_id = normalize_card_id(card_id)
    card = normalize_credit_card_payload(data)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE credit_cards
                SET name = ?, issuer = ?, network = ?, currency = ?, limit_cents = ?,
                    closing_day = ?, due_day = ?, preferred_payment_account_id = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
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
                    card["preferred_payment_account_id"],
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
    preferred_payment_account_id = normalize_optional_card_id(data.get("preferred_payment_account_id"))
    return {
        "name": name,
        "issuer": issuer,
        "network": empty_to_none(data.get("network")),
        "currency": currency,
        "limit_cents": limit_cents,
        "closing_day": normalize_day(data.get("closing_day"), "Informe o dia de fechamento."),
        "due_day": normalize_day(data.get("due_day"), "Informe o dia de vencimento."),
        "preferred_payment_account_id": preferred_payment_account_id,
        "notes": empty_to_none(data.get("notes")),
    }


def normalize_card_transaction_payload(data: dict) -> dict:
    transaction_type = str(data.get("type", "")).strip().lower()
    description = str(data.get("description", "")).strip()
    try:
        amount_cents = money_to_cents(data.get("amount", "0"))
    except Exception as exc:
        raise CreditCardError("Valor invalido.") from exc
    if transaction_type not in CARD_TRANSACTION_TYPES:
        raise CreditCardError("Cartao aceita apenas despesas e receitas.")
    if not description:
        raise CreditCardError("Informe a descricao do lancamento.")
    if amount_cents <= 0:
        raise CreditCardError("Informe um valor maior que zero.")
    series_kind = normalize_card_series_kind(data)
    installment_count = normalize_card_repeat_count(data.get("installment_count"), series_kind)
    return {
        "credit_card_id": normalize_card_id(data.get("credit_card_id")),
        "type": transaction_type,
        "description": description,
        "amount_cents": amount_cents,
        "date": normalize_date(data.get("date")),
        "invoice_month": normalize_month(data.get("invoice_month")),
        "category": normalize_name(data.get("category"), "Informe a categoria."),
        "subcategory": normalize_optional_name(data.get("subcategory")),
        "tags": normalize_optional_tags(data.get("tags") or data.get("tag")),
        "notes": empty_to_none(data.get("notes")),
        "series_kind": series_kind,
        "installment_count": installment_count,
        "recurrence_frequency": normalize_card_recurrence_frequency(data),
    }


def normalize_card_series_kind(data: dict) -> str:
    series_kind = str(data.get("series_kind") or "single").strip().lower()
    if series_kind not in CARD_SERIES_KINDS:
        raise CreditCardError("Tipo de repeticao invalido.")
    return series_kind


def normalize_card_repeat_count(value: object, series_kind: str) -> int | None:
    if series_kind == "single":
        return None
    raw = str(value or "").strip()
    if not raw and series_kind == "installment":
        return None
    if not raw:
        raise CreditCardError("Informe a quantidade de ocorrencias.")
    try:
        count = int(raw)
    except ValueError as exc:
        raise CreditCardError("Informe a quantidade de repeticoes.") from exc
    maximum = 240 if series_kind == "recurring" else 120
    if count < 2 or count > maximum:
        raise CreditCardError(f"Informe entre 2 e {maximum} repeticoes.")
    return count


def normalize_card_recurrence_frequency(data: dict) -> str | None:
    if str(data.get("series_kind") or "single").strip().lower() != "recurring":
        return None
    frequency = str(data.get("recurrence_frequency") or "").strip().lower()
    if frequency not in CARD_RECURRENCE_FREQUENCIES:
        raise CreditCardError("Informe a frequencia da recorrencia.")
    return frequency


def should_apply_to_future_card(data: dict) -> bool:
    return str(data.get("apply_to_future") or "").strip().lower() in {"1", "true", "yes", "sim"}


def build_card_transaction_occurrences(transaction: dict) -> list[dict]:
    start_date = date.fromisoformat(transaction["date"])
    if transaction["series_kind"] == "recurring":
        count = transaction["installment_count"] or 12
        return [
            {
                "date": add_recurrence(start_date, transaction["recurrence_frequency"], index).isoformat(),
                "invoice_month": add_recurrence(date.fromisoformat(f"{transaction['invoice_month']}-01"), transaction["recurrence_frequency"], index).strftime("%Y-%m"),
                "description": transaction["description"],
                "installment_index": None,
                "installment_count": count,
            }
            for index in range(count)
        ]
    if transaction["series_kind"] != "installment":
        return [{
            "date": transaction["date"],
            "invoice_month": transaction["invoice_month"],
            "description": transaction["description"],
            "installment_index": None,
            "installment_count": None,
        }]
    count = transaction["installment_count"] or 2
    return [
        {
            "date": add_months(start_date, index).isoformat(),
            "invoice_month": shift_month(transaction["invoice_month"], index),
            "description": transaction["description"],
            "installment_index": index + 1,
            "installment_count": count,
        }
        for index in range(count)
    ]


def add_recurrence(start_date: date, frequency: str, index: int) -> date:
    if frequency == "weekly":
        return start_date + timedelta(days=7 * index)
    months = {
        "monthly": 1,
        "quarterly": 3,
        "semiannual": 6,
        "annual": 12,
    }[frequency]
    return add_months(start_date, months * index)


def shift_month(value: str, delta: int) -> str:
    year, month = value.split("-")
    shifted = add_months(date(int(year), int(month), 1), delta)
    return f"{shifted.year}-{shifted.month:02d}"


def add_months(start_date: date, months: int) -> date:
    target_month = start_date.month - 1 + months
    year = start_date.year + target_month // 12
    month = target_month % 12 + 1
    day = min(start_date.day, days_in_month(year, month))
    return date(year, month, day)


def days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date.resolution).day


def normalize_day(value: object, message: str) -> int:
    try:
        day = int(str(value or "").strip())
    except ValueError as exc:
        raise CreditCardError(message) from exc
    if day < 1 or day > 31:
        raise CreditCardError("Informe um dia entre 1 e 31.")
    return day


def normalize_date(value: object) -> str:
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise CreditCardError("Data invalida.") from exc


def normalize_month(value: object) -> str:
    raw = str(value or "").strip()
    if not MONTH_PATTERN.match(raw):
        raise CreditCardError("Informe a fatura no formato AAAA-MM.")
    month = int(raw[-2:])
    if month < 1 or month > 12:
        raise CreditCardError("Informe uma fatura valida.")
    return raw


def normalize_optional_name(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    return normalize_name(raw, "Informe a subcategoria.")


def normalize_card_id(value: object) -> int:
    try:
        normalized = int(str(value or "").strip())
    except ValueError as exc:
        raise CreditCardError("Cartao nao encontrado.", HTTPStatus.NOT_FOUND) from exc
    if normalized <= 0:
        raise CreditCardError("Cartao nao encontrado.", HTTPStatus.NOT_FOUND)
    return normalized


def normalize_optional_card_id(value: object) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    return normalize_card_id(raw)


def validate_preferred_payment_account(conn, user_id: int, account_id: int | None, currency: str) -> None:
    if not account_id:
        return
    account = conn.execute(
        """
        SELECT id, currency
        FROM checking_accounts
        WHERE id = ? AND user_id = ? AND archived_at IS NULL
        """,
        (account_id, user_id),
    ).fetchone()
    if not account:
        raise CreditCardError("Conta preferencial de pagamento nao encontrada.")
    if account["currency"] != currency:
        raise CreditCardError("A conta preferencial deve ter a mesma moeda do cartao.")


def get_active_credit_card(conn, user_id: int, card_id: int):
    card = conn.execute(
        """
        SELECT *
        FROM credit_cards
        WHERE id = ? AND user_id = ? AND archived_at IS NULL
        """,
        (card_id, user_id),
    ).fetchone()
    if not card:
        raise CreditCardError("Cartao nao encontrado.", HTTPStatus.NOT_FOUND)
    return card


def fetch_card_transaction(conn, user_id: int, transaction_id: int) -> dict:
    row = conn.execute(
        """
        SELECT
            credit_card_transactions.*,
            credit_cards.currency AS card_currency,
            categories.name AS category_name,
            subcategories.name AS subcategory_name,
            GROUP_CONCAT(tags.name, '||') AS tag_names
        FROM credit_card_transactions
        JOIN credit_cards
            ON credit_cards.id = credit_card_transactions.credit_card_id
            AND credit_cards.user_id = credit_card_transactions.user_id
        LEFT JOIN categories
            ON categories.id = credit_card_transactions.category_id
            AND categories.user_id = credit_card_transactions.user_id
        LEFT JOIN subcategories
            ON subcategories.id = credit_card_transactions.subcategory_id
            AND subcategories.user_id = credit_card_transactions.user_id
        LEFT JOIN credit_card_transaction_tags
            ON credit_card_transaction_tags.credit_card_transaction_id = credit_card_transactions.id
        LEFT JOIN tags
            ON tags.id = credit_card_transaction_tags.tag_id
            AND tags.user_id = credit_card_transactions.user_id
        WHERE credit_card_transactions.id = ? AND credit_card_transactions.user_id = ?
        GROUP BY credit_card_transactions.id
        """,
        (transaction_id, user_id),
    ).fetchone()
    if not row:
        raise CreditCardError("Lancamento do cartao nao encontrado.", HTTPStatus.NOT_FOUND)
    return row_to_dict(row)


def invoice_balance_cents(conn, user_id: int, card_id: int, invoice_month: str) -> int:
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(
                CASE
                    WHEN type = 'expense' THEN amount_cents
                    WHEN type = 'income' THEN -amount_cents
                    ELSE 0
                END
            ), 0) AS total
        FROM credit_card_transactions
        WHERE user_id = ? AND credit_card_id = ? AND invoice_month = ?
            AND archived_at IS NULL
        """,
        (user_id, card_id, invoice_month),
    ).fetchone()
    return int(row["total"])


def ensure_invoice_is_open(conn, user_id: int, card_id: int, invoice_month: str) -> None:
    row = conn.execute(
        """
        SELECT id
        FROM credit_card_payments
        WHERE user_id = ? AND credit_card_id = ? AND invoice_month = ?
        """,
        (user_id, card_id, invoice_month),
    ).fetchone()
    if row:
        raise CreditCardError("Esta fatura ja foi paga e esta fechada.", HTTPStatus.CONFLICT)


def ensure_not_before_previous_closed_invoice(conn, user_id: int, card, invoice_month: str, transaction_date: str) -> None:
    previous_month = shift_month(invoice_month, -1)
    if not is_invoice_paid(conn, user_id, card["id"], previous_month):
        return
    previous_closing_date = card_invoice_date(previous_month, card["closing_day"])
    if transaction_date <= previous_closing_date:
        raise CreditCardError(
            f"A data do lancamento ({format_date_br(transaction_date)}) e anterior ou igual ao fechamento da fatura anterior ja fechada ({format_date_br(previous_closing_date)}). Ajuste a data ou use a fatura correta.",
            HTTPStatus.CONFLICT,
        )


def is_invoice_paid(conn, user_id: int, card_id: int, invoice_month: str) -> bool:
    row = conn.execute(
        """
        SELECT id
        FROM credit_card_payments
        WHERE user_id = ? AND credit_card_id = ? AND invoice_month = ?
        """,
        (user_id, card_id, invoice_month),
    ).fetchone()
    return bool(row)


def card_invoice_date(month: str, day: int) -> str:
    year, month_number = map(int, month.split("-"))
    normalized_day = min(int(day), days_in_month(year, month_number))
    return date(year, month_number, normalized_day).isoformat()


def format_date_br(value: str) -> str:
    parsed = date.fromisoformat(value)
    return parsed.strftime("%d/%m/%Y")


def format_invoice_month(value: str) -> str:
    year, month = value.split("-")
    return f"{month}/{year}"


def format_credit_card(card: dict) -> dict:
    card["limit"] = cents_to_money(card.pop("limit_cents"))
    return card


def format_card_transaction(transaction: dict, currency: str) -> dict:
    if transaction.get("installment_index") and transaction.get("installment_count"):
        transaction["series_kind"] = "installment"
        transaction["recurrence_frequency"] = None
    transaction["amount"] = cents_to_money(transaction.pop("amount_cents"))
    transaction["card_currency"] = transaction.pop("card_currency", currency) or currency
    raw_tags = transaction.pop("tag_names", "") or ""
    transaction["tags"] = [tag for tag in raw_tags.split("||") if tag]
    transaction["tag_name"] = ", ".join(transaction["tags"])
    return transaction


def replace_credit_card_transaction_tags(conn, transaction_id: int, tag_ids: list[int]) -> None:
    conn.execute("DELETE FROM credit_card_transaction_tags WHERE credit_card_transaction_id = ?", (transaction_id,))
    conn.executemany(
        "INSERT OR IGNORE INTO credit_card_transaction_tags (credit_card_transaction_id, tag_id) VALUES (?, ?)",
        [(transaction_id, tag_id) for tag_id in tag_ids],
    )


def format_card_payment(payment: dict, currency: str) -> dict:
    payment["amount"] = cents_to_money(payment.pop("amount_cents"))
    payment["card_currency"] = currency
    return payment
