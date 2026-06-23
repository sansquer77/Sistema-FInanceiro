from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus
import json
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from financeiro.accounts import cents_to_money, empty_to_none, money_to_cents
from financeiro.categories import ClassificationError, get_or_create_category, get_or_create_subcategory, get_or_create_tag, normalize_name
from financeiro.database import get_connection, row_to_dict

TRANSACTION_TYPES = {"income", "expense", "transfer", "investment"}
INVESTMENT_ASSET_TYPES = {"stock", "crypto", "fund", "fixed_income", "other"}
FIXED_INCOME_MODES = {"pre", "post", "hybrid"}
SERIES_KINDS = {"single", "installment", "recurring"}
RECURRENCE_FREQUENCIES = {"weekly", "monthly", "quarterly", "semiannual", "annual"}
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
                destination.currency AS destination_account_currency,
                categories.name AS category_name,
                subcategories.name AS subcategory_name,
                investment_operations.asset_type AS investment_asset_type,
                investment_operations.asset_identifier AS investment_asset_identifier,
                investment_operations.asset_name AS investment_asset_name,
                investment_operations.cnpj AS investment_cnpj,
                investment_operations.quantity_micros AS investment_quantity_micros,
                investment_operations.unit_price_cents AS investment_unit_price_cents,
                investment_operations.invested_amount_cents AS investment_invested_amount_cents,
                investment_operations.brokerage_fee_cents AS investment_brokerage_fee_cents,
                investment_operations.exchange_fee_cents AS investment_exchange_fee_cents,
                investment_operations.tax_cents AS investment_tax_cents,
                investment_operations.other_costs_cents AS investment_other_costs_cents,
                investment_operations.fixed_income_mode AS investment_fixed_income_mode,
                investment_operations.fixed_income_indexer AS investment_fixed_income_indexer,
                investment_operations.fixed_income_rate_micros AS investment_fixed_income_rate_micros,
                investment_operations.fixed_income_maturity_date AS investment_fixed_income_maturity_date,
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
            LEFT JOIN investment_operations
                ON investment_operations.transaction_id = transactions.id
                AND investment_operations.user_id = transactions.user_id
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
        if source["account_type"] == "wallet":
            force_single_transaction(transaction)
        occurrences = build_transaction_occurrences(transaction)
        destination = None
        if transaction["type"] == "transfer":
            destination = get_active_account(conn, user_id, transaction["destination_account_id"])
            ensure_transfer_accounts(source, destination)
            normalize_transfer_amounts(transaction, source, destination)
        exchange_rate_micros = resolve_exchange_rate_micros(source["currency"], transaction["date"], transaction["exchange_rate"])
        amount_brl_cents = convert_to_brl_cents(transaction["amount_cents"], exchange_rate_micros)
        category_id, subcategory_id = resolve_transaction_category(conn, user_id, transaction, destination)
        tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in transaction["tags"]]
        first_transaction_id = None
        series_id = str(uuid4()) if transaction["series_kind"] != "single" else None
        for occurrence in occurrences:
            apply_balance_delta(conn, source["id"], balance_delta(transaction["type"], transaction["amount_cents"], "source"))
            if destination:
                apply_balance_delta(conn, destination["id"], balance_delta(transaction["type"], destination_balance_amount(transaction), "destination"))
            cursor = conn.execute(
                """
                INSERT INTO transactions (
                    user_id, type, description, amount_cents, destination_amount_cents,
                    exchange_rate_micros, transfer_exchange_rate_micros, amount_brl_cents, date, account_id,
                    destination_account_id, category_id, subcategory_id, series_id, series_kind, installment_index,
                    installment_count, recurrence_frequency, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    transaction["type"],
                    occurrence["description"],
                    transaction["amount_cents"],
                    transaction["destination_amount_cents"],
                    exchange_rate_micros,
                    transaction["transfer_exchange_rate_micros"],
                    amount_brl_cents,
                    occurrence["date"],
                    source["id"],
                    destination["id"] if destination else None,
                    category_id,
                    subcategory_id,
                    series_id,
                    transaction["series_kind"],
                    occurrence["installment_index"],
                    occurrence["installment_count"],
                    transaction["recurrence_frequency"],
                    transaction["notes"],
                ),
            )
            if first_transaction_id is None:
                first_transaction_id = cursor.lastrowid
            replace_transaction_tags(conn, cursor.lastrowid, tag_ids)
            upsert_investment_operation(conn, user_id, cursor.lastrowid, source["id"], transaction)
        row = fetch_transaction(conn, user_id, first_transaction_id)
    return format_transaction(row)


def update_transaction(user_id: int, transaction_id: str, data: dict) -> dict:
    normalized_id = normalize_id(transaction_id, "Lancamento nao encontrado.")
    transaction = normalize_transaction_update_payload(data)
    apply_to_future = should_apply_to_future(data)
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT *
            FROM transactions
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (normalized_id, user_id),
        ).fetchone()
        if not existing:
            raise TransactionError("Lancamento nao encontrado.", HTTPStatus.NOT_FOUND)
        source = get_active_account(conn, user_id, transaction["account_id"])
        destination = None
        if transaction["type"] == "transfer":
            destination = get_active_account(conn, user_id, transaction["destination_account_id"])
            ensure_transfer_accounts(source, destination)
            normalize_transfer_amounts(transaction, source, destination)
        exchange_rate_micros = resolve_exchange_rate_micros(source["currency"], transaction["date"], transaction["exchange_rate"])
        amount_brl_cents = convert_to_brl_cents(transaction["amount_cents"], exchange_rate_micros)
        category_id, subcategory_id = resolve_transaction_category(conn, user_id, transaction, destination)
        tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in transaction["tags"]]

        apply_balance_delta(conn, existing["account_id"], -balance_delta(existing["type"], existing["amount_cents"], "source"))
        if existing["destination_account_id"]:
            apply_balance_delta(
                conn,
                existing["destination_account_id"],
                -balance_delta(existing["type"], existing_destination_balance_amount(existing), "destination"),
            )
        apply_balance_delta(conn, source["id"], balance_delta(transaction["type"], transaction["amount_cents"], "source"))
        if destination:
            apply_balance_delta(conn, destination["id"], balance_delta(transaction["type"], destination_balance_amount(transaction), "destination"))
        conn.execute(
            """
            UPDATE transactions
            SET type = ?, description = ?, amount_cents = ?, destination_amount_cents = ?,
                exchange_rate_micros = ?, transfer_exchange_rate_micros = ?,
                amount_brl_cents = ?, date = ?, account_id = ?, destination_account_id = ?,
                category_id = ?, subcategory_id = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (
                transaction["type"],
                    transaction["description"],
                    transaction["amount_cents"],
                    transaction["destination_amount_cents"],
                    exchange_rate_micros,
                    transaction["transfer_exchange_rate_micros"],
                    amount_brl_cents,
                transaction["date"],
                source["id"],
                destination["id"] if destination else None,
                category_id,
                subcategory_id,
                transaction["notes"],
                normalized_id,
                user_id,
            ),
        )
        replace_transaction_tags(conn, normalized_id, tag_ids)
        upsert_investment_operation(conn, user_id, normalized_id, source["id"], transaction)
        if apply_to_future:
            update_future_series_transactions(conn, user_id, existing, transaction)
        row = fetch_transaction(conn, user_id, normalized_id)
    return format_transaction(row)


def update_future_series_transactions(conn, user_id: int, existing, transaction: dict) -> None:
    if not existing["series_id"]:
        return
    is_installment = existing["series_kind"] == "installment" or (
        existing["installment_index"] and existing["installment_count"]
    )
    if existing["series_kind"] != "recurring" and not is_installment:
        return
    date_delta = date.fromisoformat(transaction["date"]) - date.fromisoformat(existing["date"])
    future_filter = "installment_index > ?" if is_installment and existing["installment_index"] else "date > ?"
    future_marker = existing["installment_index"] if is_installment and existing["installment_index"] else existing["date"]
    future_rows = conn.execute(
        f"""
        SELECT *
        FROM transactions
        WHERE user_id = ? AND archived_at IS NULL
            AND series_id = ? AND id <> ? AND reconciled_at IS NULL
            AND {future_filter}
        ORDER BY date ASC, id ASC
        """,
        (user_id, existing["series_id"], existing["id"], future_marker),
    ).fetchall()
    for row in future_rows:
        row_date = date.fromisoformat(row["date"])
        future_transaction = {**transaction, "date": (row_date + date_delta).isoformat()}
        source = get_active_account(conn, user_id, transaction["account_id"])
        destination = None
        if future_transaction["type"] == "transfer":
            destination = get_active_account(conn, user_id, future_transaction["destination_account_id"])
            ensure_transfer_accounts(source, destination)
            normalize_transfer_amounts(future_transaction, source, destination)
        exchange_rate_micros = resolve_exchange_rate_micros(source["currency"], future_transaction["date"], future_transaction["exchange_rate"])
        amount_brl_cents = convert_to_brl_cents(future_transaction["amount_cents"], exchange_rate_micros)
        category_id, subcategory_id = resolve_transaction_category(conn, user_id, future_transaction, destination)
        tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in future_transaction["tags"]]
        apply_balance_delta(conn, row["account_id"], -balance_delta(row["type"], row["amount_cents"], "source"))
        if row["destination_account_id"]:
            apply_balance_delta(conn, row["destination_account_id"], -balance_delta(row["type"], existing_destination_balance_amount(row), "destination"))
        apply_balance_delta(conn, source["id"], balance_delta(future_transaction["type"], future_transaction["amount_cents"], "source"))
        if destination:
            apply_balance_delta(conn, destination["id"], balance_delta(future_transaction["type"], destination_balance_amount(future_transaction), "destination"))
        conn.execute(
            """
            UPDATE transactions
            SET type = ?, description = ?, amount_cents = ?, destination_amount_cents = ?,
                exchange_rate_micros = ?, transfer_exchange_rate_micros = ?,
                amount_brl_cents = ?, date = ?, account_id = ?, destination_account_id = ?,
                category_id = ?, subcategory_id = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (
                future_transaction["type"],
                future_transaction["description"],
                future_transaction["amount_cents"],
                future_transaction["destination_amount_cents"],
                exchange_rate_micros,
                future_transaction["transfer_exchange_rate_micros"],
                amount_brl_cents,
                future_transaction["date"],
                source["id"],
                destination["id"] if destination else None,
                category_id,
                subcategory_id,
                future_transaction["notes"],
                row["id"],
                user_id,
            ),
        )
        replace_transaction_tags(conn, row["id"], tag_ids)
        upsert_investment_operation(conn, user_id, row["id"], source["id"], future_transaction)


def delete_transaction(user_id: int, transaction_id: str, apply_to_future: bool = False) -> None:
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
        transactions = [transaction, *future_transactions_to_delete(conn, user_id, transaction, apply_to_future)]
        for item in transactions:
            apply_balance_delta(conn, item["account_id"], -balance_delta(item["type"], item["amount_cents"], "source"))
            if item["destination_account_id"]:
                apply_balance_delta(
                    conn,
                    item["destination_account_id"],
                    -balance_delta(item["type"], existing_destination_balance_amount(item), "destination"),
                )
        transaction_ids = [item["id"] for item in transactions]
        conn.execute(
            f"""
            DELETE FROM transactions
            WHERE user_id = ? AND id IN ({",".join("?" for _ in transaction_ids)})
            """,
            (user_id, *transaction_ids),
        )


def future_transactions_to_delete(conn, user_id: int, transaction, apply_to_future: bool):
    if not apply_to_future or not transaction["series_id"]:
        return []
    is_installment = transaction["series_kind"] == "installment" or (
        transaction["installment_index"] and transaction["installment_count"]
    )
    if transaction["series_kind"] != "recurring" and not is_installment:
        return []
    future_filter = "installment_index > ?" if is_installment and transaction["installment_index"] else "date > ?"
    future_marker = transaction["installment_index"] if is_installment and transaction["installment_index"] else transaction["date"]
    return conn.execute(
        f"""
        SELECT *
        FROM transactions
        WHERE user_id = ? AND archived_at IS NULL
            AND series_id = ? AND id <> ? AND reconciled_at IS NULL
            AND {future_filter}
        ORDER BY date ASC, id ASC
        """,
        (user_id, transaction["series_id"], transaction["id"], future_marker),
    ).fetchall()


def set_transaction_reconciled(user_id: int, transaction_id: str, reconciled: bool) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE transactions
            SET reconciled_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (1 if reconciled else 0, transaction_id, user_id),
        )
        if cursor.rowcount == 0:
            raise TransactionError("Lancamento nao encontrado.", HTTPStatus.NOT_FOUND)
        row = fetch_transaction(conn, user_id, int(transaction_id))
    return format_transaction(row)


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
        "destination_amount_cents": money_to_cents(data.get("destination_amount", "0")) if str(data.get("destination_amount") or "").strip() else 0,
        "transfer_exchange_rate": data.get("transfer_exchange_rate"),
        "transfer_exchange_rate_micros": 0,
        "date": transaction_date,
        "account_id": account_id,
        "destination_account_id": destination_account_id,
        "exchange_rate": data.get("exchange_rate_to_brl") or data.get("exchange_rate"),
        "category": normalize_transaction_category(transaction_type, data.get("category")),
        "subcategory": normalize_optional_name(data.get("subcategory")) if transaction_type != "transfer" else None,
        "tags": normalize_optional_tags(data.get("tags") or data.get("tag")),
        "notes": empty_to_none(data.get("notes")),
        "investment_operation": normalize_investment_operation(data, amount_cents, transaction_type),
        **normalize_series_payload(data),
    }


def normalize_transaction_update_payload(data: dict) -> dict:
    transaction = normalize_transaction_payload({**data, "series_kind": "single"})
    transaction.pop("series_kind", None)
    transaction.pop("installment_count", None)
    transaction.pop("recurrence_frequency", None)
    transaction.pop("recurrence_count", None)
    return transaction


def normalize_transaction_category(transaction_type: str, value: object) -> str | None:
    if transaction_type == "transfer":
        return None
    return normalize_name(value, "Informe a categoria.")


def should_apply_to_future(data: dict) -> bool:
    return str(data.get("apply_to_future") or "").strip().lower() in {"1", "true", "yes", "sim"}


def normalize_series_payload(data: dict) -> dict:
    series_kind = str(data.get("series_kind") or data.get("payment_mode") or "single").strip().lower()
    if series_kind not in SERIES_KINDS:
        raise TransactionError("Tipo de repeticao invalido.")
    installment_count = None
    recurrence_frequency = None
    recurrence_count = None
    if series_kind == "installment":
        installment_count = normalize_count(data.get("installment_count"), "Informe a quantidade de parcelas.", maximum=120)
    if series_kind == "recurring":
        recurrence_frequency = str(data.get("recurrence_frequency", "")).strip().lower()
        if recurrence_frequency not in RECURRENCE_FREQUENCIES:
            raise TransactionError("Informe a frequencia da recorrencia.")
        recurrence_count = normalize_count(data.get("recurrence_count"), "Informe a quantidade de ocorrencias.", maximum=240)
    return {
        "series_kind": series_kind,
        "installment_count": installment_count,
        "recurrence_frequency": recurrence_frequency,
        "recurrence_count": recurrence_count,
    }


def normalize_count(value: object, message: str, maximum: int) -> int:
    try:
        count = int(str(value or "").strip())
    except ValueError as exc:
        raise TransactionError(message) from exc
    if count < 2:
        raise TransactionError(message)
    if count > maximum:
        raise TransactionError("Quantidade de repeticoes muito alta.")
    return count


def force_single_transaction(transaction: dict) -> None:
    transaction["series_kind"] = "single"
    transaction["installment_count"] = None
    transaction["recurrence_frequency"] = None
    transaction["recurrence_count"] = None


def normalize_investment_operation(data: dict, amount_cents: int, transaction_type: str) -> dict | None:
    if transaction_type != "investment":
        return None
    category = str(data.get("category") or "").strip()
    if category == "Renda Variável":
        asset_type = "stock"
    elif category == "Criptoativos":
        asset_type = "crypto"
    elif category == "Fundos de Investimentos":
        asset_type = "fund"
    elif category == "Renda Fixa":
        asset_type = "fixed_income"
    else:
        asset_type = "other"
    fixed_income_mode = normalize_optional_key(data.get("investment_fixed_income_mode"))
    if fixed_income_mode and fixed_income_mode not in FIXED_INCOME_MODES:
        raise TransactionError("Modalidade de renda fixa invalida.")
    invested_amount_cents = money_to_cents(data.get("investment_amount", "0")) if str(data.get("investment_amount") or "").strip() else amount_cents
    return {
        "asset_type": asset_type,
        "asset_identifier": empty_to_none(data.get("investment_asset_identifier")),
        "asset_name": empty_to_none(data.get("investment_asset_name")),
        "cnpj": empty_to_none(data.get("investment_cnpj")),
        "quantity_micros": decimal_to_micros(data.get("investment_quantity")),
        "unit_price_cents": money_to_cents(data.get("investment_unit_price", "0")) if str(data.get("investment_unit_price") or "").strip() else 0,
        "invested_amount_cents": invested_amount_cents,
        "brokerage_fee_cents": money_to_cents(data.get("investment_brokerage_fee", "0")) if str(data.get("investment_brokerage_fee") or "").strip() else 0,
        "exchange_fee_cents": money_to_cents(data.get("investment_exchange_fee", "0")) if str(data.get("investment_exchange_fee") or "").strip() else 0,
        "tax_cents": money_to_cents(data.get("investment_tax", "0")) if str(data.get("investment_tax") or "").strip() else 0,
        "other_costs_cents": money_to_cents(data.get("investment_other_costs", "0")) if str(data.get("investment_other_costs") or "").strip() else 0,
        "fixed_income_mode": fixed_income_mode,
        "fixed_income_indexer": empty_to_none(data.get("investment_fixed_income_indexer")),
        "fixed_income_rate_micros": decimal_to_micros(data.get("investment_fixed_income_rate")),
        "fixed_income_maturity_date": normalize_optional_date(data.get("investment_fixed_income_maturity_date")),
    }


def normalize_optional_key(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    return raw or None


def decimal_to_micros(value: object) -> int:
    raw = str(value or "").strip()
    if not raw:
        return 0
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        decimal_value = Decimal(raw)
    except InvalidOperation as exc:
        raise TransactionError("Informe um numero valido nos detalhes do investimento.") from exc
    if decimal_value < 0:
        raise TransactionError("Informe valores positivos nos detalhes do investimento.")
    return int((decimal_value * EXCHANGE_RATE_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def build_transaction_occurrences(transaction: dict) -> list[dict]:
    start_date = date.fromisoformat(transaction["date"])
    if transaction["series_kind"] == "installment":
        return [
            {
                "date": add_months(start_date, index).isoformat(),
                "description": f"{transaction['description']} ({index + 1}/{transaction['installment_count']})",
                "installment_index": index + 1,
                "installment_count": transaction["installment_count"],
            }
            for index in range(transaction["installment_count"])
        ]
    if transaction["series_kind"] == "recurring":
        return [
            {
                "date": add_recurrence(start_date, transaction["recurrence_frequency"], index).isoformat(),
                "description": transaction["description"],
                "installment_index": None,
                "installment_count": transaction["recurrence_count"],
            }
            for index in range(transaction["recurrence_count"])
        ]
    return [{
        "date": transaction["date"],
        "description": transaction["description"],
        "installment_index": None,
        "installment_count": None,
    }]


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


def add_months(start_date: date, months: int) -> date:
    target_month = start_date.month - 1 + months
    year = start_date.year + target_month // 12
    month = target_month % 12 + 1
    day = min(start_date.day, days_in_month(year, month))
    return date(year, month, day)


def days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


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


def normalize_optional_date(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise TransactionError("Informe uma data valida.") from exc


def get_active_account(conn, user_id: int, account_id: int):
    account = conn.execute(
        """
        SELECT id, currency, account_type
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
    return rate_to_micros(Decimal("1"))


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


def ensure_transfer_accounts(source, destination) -> None:
    if source["id"] == destination["id"]:
        raise TransactionError("Informe contas diferentes para transferencia.")


def normalize_transfer_amounts(transaction: dict, source, destination) -> None:
    if transaction["type"] != "transfer":
        transaction["destination_amount_cents"] = 0
        transaction["transfer_exchange_rate_micros"] = 0
        return
    if source["currency"] == destination["currency"]:
        transaction["destination_amount_cents"] = transaction["amount_cents"]
        transaction["transfer_exchange_rate_micros"] = rate_to_micros(Decimal("1"))
        return
    if transaction["destination_amount_cents"] <= 0 and str(transaction.get("transfer_exchange_rate") or "").strip():
        rate_micros = rate_to_micros(parse_exchange_rate(transaction["transfer_exchange_rate"]))
        transaction["transfer_exchange_rate_micros"] = rate_micros
        transaction["destination_amount_cents"] = convert_to_brl_cents(transaction["amount_cents"], rate_micros)
        return
    if transaction["destination_amount_cents"] <= 0:
        raise TransactionError("Informe o valor que entra na conta de destino.")
    rate = Decimal(transaction["destination_amount_cents"]) / Decimal(transaction["amount_cents"])
    transaction["transfer_exchange_rate_micros"] = rate_to_micros(rate)


def destination_balance_amount(transaction: dict) -> int:
    return transaction["destination_amount_cents"] or transaction["amount_cents"]


def existing_destination_balance_amount(transaction) -> int:
    try:
        amount = int(transaction["destination_amount_cents"] or 0)
    except (IndexError, KeyError):
        amount = 0
    return amount or int(transaction["amount_cents"])


def resolve_transaction_category(conn, user_id: int, transaction: dict, destination) -> tuple[int | None, int | None]:
    if not transaction["category"]:
        return None, None
    category_group_type = transaction_category_group(conn, user_id, transaction["type"], destination, transaction["category"])
    category_id = get_or_create_category(conn, user_id, transaction["category"], category_group_type)
    subcategory_id = get_or_create_subcategory(conn, user_id, category_id, transaction["subcategory"])
    return category_id, subcategory_id


def transaction_category_group(conn, user_id: int, transaction_type: str, destination, category_name: str) -> str:
    if transaction_type == "income":
        return "income"
    if transaction_type == "investment":
        return "investment"
    if transaction_type == "transfer":
        if destination and destination["account_type"] == "investment":
            return "investment"
        if category_name:
            row = conn.execute(
                "SELECT 1 FROM categories WHERE user_id = ? AND group_type = 'investment' AND name = ?",
                (user_id, category_name.strip()),
            ).fetchone()
            if row:
                return "investment"
    return "expense"


def balance_delta(transaction_type: str, amount_cents: int, side: str) -> int:
    if transaction_type == "income":
        return amount_cents
    if transaction_type in {"expense", "investment"}:
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


def upsert_investment_operation(conn, user_id: int, transaction_id: int, account_id: int, transaction: dict) -> None:
    operation = transaction.get("investment_operation")
    if transaction["type"] != "investment" or not operation:
        conn.execute("DELETE FROM investment_operations WHERE transaction_id = ?", (transaction_id,))
        return
    conn.execute(
        """
        INSERT INTO investment_operations (
            user_id, transaction_id, account_id, asset_type, asset_identifier, asset_name, cnpj,
            quantity_micros, unit_price_cents, invested_amount_cents, brokerage_fee_cents,
            exchange_fee_cents, tax_cents, other_costs_cents, fixed_income_mode,
            fixed_income_indexer, fixed_income_rate_micros, fixed_income_maturity_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(transaction_id) DO UPDATE SET
            account_id = excluded.account_id,
            asset_type = excluded.asset_type,
            asset_identifier = excluded.asset_identifier,
            asset_name = excluded.asset_name,
            cnpj = excluded.cnpj,
            quantity_micros = excluded.quantity_micros,
            unit_price_cents = excluded.unit_price_cents,
            invested_amount_cents = excluded.invested_amount_cents,
            brokerage_fee_cents = excluded.brokerage_fee_cents,
            exchange_fee_cents = excluded.exchange_fee_cents,
            tax_cents = excluded.tax_cents,
            other_costs_cents = excluded.other_costs_cents,
            fixed_income_mode = excluded.fixed_income_mode,
            fixed_income_indexer = excluded.fixed_income_indexer,
            fixed_income_rate_micros = excluded.fixed_income_rate_micros,
            fixed_income_maturity_date = excluded.fixed_income_maturity_date,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            user_id,
            transaction_id,
            account_id,
            operation["asset_type"],
            operation["asset_identifier"],
            operation["asset_name"],
            operation["cnpj"],
            operation["quantity_micros"],
            operation["unit_price_cents"],
            operation["invested_amount_cents"],
            operation["brokerage_fee_cents"],
            operation["exchange_fee_cents"],
            operation["tax_cents"],
            operation["other_costs_cents"],
            operation["fixed_income_mode"],
            operation["fixed_income_indexer"],
            operation["fixed_income_rate_micros"],
            operation["fixed_income_maturity_date"],
        ),
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
                destination.currency AS destination_account_currency,
                categories.name AS category_name,
                subcategories.name AS subcategory_name,
                investment_operations.asset_type AS investment_asset_type,
                investment_operations.asset_identifier AS investment_asset_identifier,
                investment_operations.asset_name AS investment_asset_name,
                investment_operations.cnpj AS investment_cnpj,
                investment_operations.quantity_micros AS investment_quantity_micros,
                investment_operations.unit_price_cents AS investment_unit_price_cents,
                investment_operations.invested_amount_cents AS investment_invested_amount_cents,
                investment_operations.brokerage_fee_cents AS investment_brokerage_fee_cents,
                investment_operations.exchange_fee_cents AS investment_exchange_fee_cents,
                investment_operations.tax_cents AS investment_tax_cents,
                investment_operations.other_costs_cents AS investment_other_costs_cents,
                investment_operations.fixed_income_mode AS investment_fixed_income_mode,
                investment_operations.fixed_income_indexer AS investment_fixed_income_indexer,
                investment_operations.fixed_income_rate_micros AS investment_fixed_income_rate_micros,
                investment_operations.fixed_income_maturity_date AS investment_fixed_income_maturity_date,
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
            LEFT JOIN investment_operations
                ON investment_operations.transaction_id = transactions.id
                AND investment_operations.user_id = transactions.user_id
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
    investment_operation = extract_investment_operation(transaction)
    transaction["amount"] = cents_to_money(transaction.pop("amount_cents"))
    transaction["destination_amount"] = cents_to_money(transaction.pop("destination_amount_cents", 0) or 0)
    transaction["exchange_rate_to_brl"] = micros_to_rate(transaction.pop("exchange_rate_micros"))
    transaction["transfer_exchange_rate"] = micros_to_rate(transaction.pop("transfer_exchange_rate_micros", 0) or 0)
    transaction["amount_brl"] = cents_to_money(transaction.pop("amount_brl_cents"))
    raw_tags = transaction.pop("tag_names", "") or ""
    transaction["tags"] = [tag for tag in raw_tags.split("||") if tag]
    transaction["tag_name"] = ", ".join(transaction["tags"])
    transaction["investment_operation"] = investment_operation
    return transaction


def extract_investment_operation(transaction: dict) -> dict | None:
    asset_type = transaction.pop("investment_asset_type", None)
    fields = {
        "asset_identifier": transaction.pop("investment_asset_identifier", None),
        "asset_name": transaction.pop("investment_asset_name", None),
        "cnpj": transaction.pop("investment_cnpj", None),
        "quantity": micros_to_decimal(transaction.pop("investment_quantity_micros", 0) or 0),
        "unit_price": cents_to_money(transaction.pop("investment_unit_price_cents", 0) or 0),
        "invested_amount": cents_to_money(transaction.pop("investment_invested_amount_cents", 0) or 0),
        "brokerage_fee": cents_to_money(transaction.pop("investment_brokerage_fee_cents", 0) or 0),
        "exchange_fee": cents_to_money(transaction.pop("investment_exchange_fee_cents", 0) or 0),
        "tax": cents_to_money(transaction.pop("investment_tax_cents", 0) or 0),
        "other_costs": cents_to_money(transaction.pop("investment_other_costs_cents", 0) or 0),
        "fixed_income_mode": transaction.pop("investment_fixed_income_mode", None),
        "fixed_income_indexer": transaction.pop("investment_fixed_income_indexer", None),
        "fixed_income_rate": micros_to_decimal(transaction.pop("investment_fixed_income_rate_micros", 0) or 0),
        "fixed_income_maturity_date": transaction.pop("investment_fixed_income_maturity_date", None),
    }
    if not asset_type:
        return None
    return {"asset_type": asset_type, **fields}


def micros_to_decimal(micros: int) -> str:
    if not micros:
        return ""
    value = Decimal(micros) / EXCHANGE_RATE_SCALE
    return f"{value.normalize():f}"


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


def normalize_optional_tags(value: object) -> list[str]:
    if isinstance(value, list):
        if not any(str(item or "").strip() for item in value):
            return []
    elif not str(value or "").strip():
        return []
    return normalize_tags(value)


def normalize_optional_name(value: object) -> str | None:
    if not str(value or "").strip():
        return None
    try:
        return normalize_name(value, "Informe a subcategoria.")
    except ClassificationError as exc:
        raise TransactionError(exc.message) from exc
