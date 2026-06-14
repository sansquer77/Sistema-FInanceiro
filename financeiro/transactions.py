from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from financeiro.accounts import cents_to_money, empty_to_none, money_to_cents
from financeiro.categories import ClassificationError, get_or_create_category, get_or_create_subcategory, get_or_create_tag, normalize_name
from financeiro.database import get_connection, row_to_dict

TRANSACTION_TYPES = {"income", "expense", "transfer"}
EXCHANGE_RATE_SCALE = Decimal("1000000")
FRANKFURTER_RATE_URL = "https://api.frankfurter.dev/v2/rate/{base}/BRL"


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
                source.account_type AS account_type,
                destination.name AS destination_account_name,
                destination.account_type AS destination_account_type,
                categories.name AS category_name,
                subcategories.name AS subcategory_name,
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
            LEFT JOIN subcategories
                ON subcategories.id = transactions.subcategory_id
                AND subcategories.user_id = transactions.user_id
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
        exchange_rate_micros = resolve_exchange_rate_micros(source["currency"], transaction["date"], transaction["exchange_rate"])
        amount_brl_cents = convert_to_brl_cents(transaction["amount_cents"], exchange_rate_micros)
        category_id = get_or_create_category(conn, user_id, transaction["category"])
        subcategory_id = get_or_create_subcategory(conn, user_id, category_id, transaction["subcategory"])
        tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in transaction["tags"]]
        apply_balance_delta(conn, source["id"], balance_delta(transaction["type"], transaction["amount_cents"], "source"))
        if destination:
            apply_balance_delta(conn, destination["id"], balance_delta(transaction["type"], transaction["amount_cents"], "destination"))
        cursor = conn.execute(
            """
            INSERT INTO transactions (
                user_id, type, description, amount_cents, exchange_rate_micros, amount_brl_cents, date, account_id,
                destination_account_id, category_id, subcategory_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                transaction["type"],
                transaction["description"],
                transaction["amount_cents"],
                exchange_rate_micros,
                amount_brl_cents,
                transaction["date"],
                source["id"],
                destination["id"] if destination else None,
                category_id,
                subcategory_id,
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
        "exchange_rate": data.get("exchange_rate_to_brl") or data.get("exchange_rate"),
        "category": normalize_name(data.get("category"), "Informe a categoria."),
        "subcategory": normalize_optional_name(data.get("subcategory")),
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


def get_exchange_rate_to_brl(currency: str, transaction_date: str | None = None) -> Decimal:
    normalized_currency = str(currency or "BRL").strip().upper()
    if normalized_currency == "BRL":
        return Decimal("1")
    query_date = normalize_date(transaction_date) if transaction_date else date.today().isoformat()
    url = f"{FRANKFURTER_RATE_URL.format(base=normalized_currency)}?date={query_date}"
    request = Request(url, headers={"User-Agent": "SistemaFinanceiro/0.1"})
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise TransactionError("Nao foi possivel consultar a cotacao. Informe a cotacao manualmente.") from exc
    try:
        return parse_exchange_rate(payload["rate"])
    except (KeyError, TypeError, InvalidOperation) as exc:
        raise TransactionError("Cotacao nao encontrada para esta moeda. Informe a cotacao manualmente.") from exc


def resolve_exchange_rate_micros(currency: str, transaction_date: str, raw_rate: object) -> int:
    normalized_currency = str(currency or "BRL").strip().upper()
    if normalized_currency == "BRL":
        return rate_to_micros(Decimal("1"))
    if str(raw_rate or "").strip():
        return rate_to_micros(parse_exchange_rate(raw_rate))
    return rate_to_micros(get_exchange_rate_to_brl(normalized_currency, transaction_date))


def parse_exchange_rate(value: object) -> Decimal:
    raw = str(value or "").strip()
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        rate = Decimal(raw).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise TransactionError("Cotacao invalida.") from exc
    if rate <= 0:
        raise TransactionError("Informe uma cotacao maior que zero.")
    return rate


def rate_to_micros(rate: Decimal) -> int:
    return int((rate * EXCHANGE_RATE_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def micros_to_rate(micros: int) -> str:
    rate = Decimal(micros) / EXCHANGE_RATE_SCALE
    return f"{rate:.6f}"


def convert_to_brl_cents(amount_cents: int, exchange_rate_micros: int) -> int:
    amount = Decimal(amount_cents) * Decimal(exchange_rate_micros) / EXCHANGE_RATE_SCALE
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


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
                source.account_type AS account_type,
                destination.name AS destination_account_name,
                destination.account_type AS destination_account_type,
                categories.name AS category_name,
                subcategories.name AS subcategory_name,
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
            LEFT JOIN subcategories
                ON subcategories.id = transactions.subcategory_id
                AND subcategories.user_id = transactions.user_id
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
    transaction["exchange_rate_to_brl"] = micros_to_rate(transaction.pop("exchange_rate_micros"))
    transaction["amount_brl"] = cents_to_money(transaction.pop("amount_brl_cents"))
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


def normalize_optional_name(value: object) -> str | None:
    if not str(value or "").strip():
        return None
    try:
        return normalize_name(value, "Informe a subcategoria.")
    except ClassificationError as exc:
        raise TransactionError(exc.message) from exc
