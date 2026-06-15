from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from financeiro.accounts import cents_to_money, empty_to_none, money_to_cents
from financeiro.database import get_connection
from financeiro.transactions import convert_to_brl_cents, get_exchange_rate_to_brl, parse_exchange_rate, rate_to_micros

MONEY_SCALE = Decimal("100")
MICRO_SCALE = Decimal("1000000")
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
BCB_SERIES_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados/ultimos/1?formato=json"

ASSET_TYPE_LABELS = {
    "stock": "Renda variável",
    "crypto": "Cripto",
    "fund": "Fundos",
    "fixed_income": "Renda fixa",
    "other": "Outros",
}

INDEXER_SERIES = {
    "CDI": "12",
    "SELIC": "11",
    "IPCA": "433",
    "IGP-M": "189",
    "TR": "226",
    "PREFIXADO": "",
}


class PortfolioError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def get_portfolio(user_id: int) -> dict:
    with get_connection() as conn:
        operation_rows = conn.execute(
            """
            SELECT
                investment_operations.*,
                transactions.date,
                transactions.description,
                transactions.amount_cents,
                transactions.exchange_rate_micros,
                transactions.amount_brl_cents,
                checking_accounts.name AS account_name,
                checking_accounts.currency AS account_currency
            FROM investment_operations
            JOIN transactions
                ON transactions.id = investment_operations.transaction_id
                AND transactions.user_id = investment_operations.user_id
                AND transactions.archived_at IS NULL
            JOIN checking_accounts
                ON checking_accounts.id = investment_operations.account_id
                AND checking_accounts.user_id = investment_operations.user_id
            WHERE investment_operations.user_id = ?
            ORDER BY transactions.date ASC, investment_operations.id ASC
            """,
            (user_id,),
        ).fetchall()
        opening_rows = conn.execute(
            """
            SELECT
                investment_opening_positions.id,
                investment_opening_positions.user_id,
                NULL AS transaction_id,
                investment_opening_positions.account_id,
                investment_opening_positions.asset_type,
                investment_opening_positions.asset_identifier,
                investment_opening_positions.asset_name,
                investment_opening_positions.cnpj,
                investment_opening_positions.quantity_micros,
                investment_opening_positions.unit_price_cents,
                investment_opening_positions.total_cost_cents AS invested_amount_cents,
                0 AS brokerage_fee_cents,
                0 AS exchange_fee_cents,
                0 AS tax_cents,
                0 AS other_costs_cents,
                investment_opening_positions.fixed_income_mode,
                investment_opening_positions.fixed_income_indexer,
                investment_opening_positions.fixed_income_rate_micros,
                investment_opening_positions.acquisition_date AS date,
                'Posicao inicial' AS description,
                investment_opening_positions.total_cost_cents AS amount_cents,
                investment_opening_positions.exchange_rate_micros,
                convert_placeholder.amount_brl_cents AS amount_brl_cents,
                checking_accounts.name AS account_name,
                checking_accounts.currency AS account_currency
            FROM investment_opening_positions
            JOIN checking_accounts
                ON checking_accounts.id = investment_opening_positions.account_id
                AND checking_accounts.user_id = investment_opening_positions.user_id
            LEFT JOIN (
                SELECT 0 AS amount_brl_cents
            ) AS convert_placeholder
            WHERE investment_opening_positions.user_id = ?
            """,
            (user_id,),
        ).fetchall()

    rows = sorted([*operation_rows, *opening_rows], key=lambda row: (row["date"], row["id"]))
    positions = build_positions(rows)
    quote_positions(positions)
    summary = summarize_positions(positions)
    positions = [format_quoted_position(position) for position in positions]
    return {
        "positions": positions,
        "summary": summary,
        "indexers": indexer_catalog(),
    }


def create_opening_position(user_id: int, data: dict) -> dict:
    position = normalize_opening_position_payload(data)
    with get_connection() as conn:
        account = conn.execute(
            """
            SELECT id, currency, account_type
            FROM checking_accounts
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (position["account_id"], user_id),
        ).fetchone()
        if not account:
            raise PortfolioError("Conta nao encontrada.", HTTPStatus.NOT_FOUND)
        if account["account_type"] != "investment":
            raise PortfolioError("Selecione uma conta de investimento para a posicao inicial.")
        exchange_rate_micros = resolve_position_exchange_rate(account["currency"], position["acquisition_date"], position["exchange_rate"])
        conn.execute(
            """
            INSERT INTO investment_opening_positions (
                user_id, account_id, asset_type, asset_identifier, asset_name, cnpj,
                acquisition_date, quantity_micros, unit_price_cents, total_cost_cents,
                exchange_rate_micros, fixed_income_mode, fixed_income_indexer,
                fixed_income_rate_micros, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                position["account_id"],
                position["asset_type"],
                position["asset_identifier"],
                position["asset_name"],
                position["cnpj"],
                position["acquisition_date"],
                position["quantity_micros"],
                position["unit_price_cents"],
                position["total_cost_cents"],
                exchange_rate_micros,
                position["fixed_income_mode"],
                position["fixed_income_indexer"],
                position["fixed_income_rate_micros"],
                position["notes"],
            ),
        )
    return get_portfolio(user_id)


def normalize_opening_position_payload(data: dict) -> dict:
    account_id = normalize_id(data.get("account_id"), "Informe a carteira.")
    asset_type = str(data.get("asset_type") or "other").strip().lower()
    if asset_type not in ASSET_TYPE_LABELS:
        raise PortfolioError("Tipo de investimento invalido.")
    acquisition_date = normalize_date(data.get("acquisition_date"))
    quantity = decimal_to_micros(data.get("quantity"))
    unit_price_cents = money_to_cents(data.get("unit_price", "0")) if str(data.get("unit_price") or "").strip() else 0
    total_cost_cents = money_to_cents(data.get("total_cost", "0")) if str(data.get("total_cost") or "").strip() else 0
    if total_cost_cents <= 0 and quantity > 0 and unit_price_cents > 0:
        total_cost_cents = int((Decimal(quantity) * Decimal(unit_price_cents) / MICRO_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if total_cost_cents <= 0:
        raise PortfolioError("Informe o custo total da posicao.")
    fixed_income_mode = optional_key(data.get("fixed_income_mode"))
    if fixed_income_mode and fixed_income_mode not in {"pre", "post", "hybrid"}:
        raise PortfolioError("Modalidade de renda fixa invalida.")
    return {
        "account_id": account_id,
        "asset_type": asset_type,
        "asset_identifier": empty_to_none(data.get("asset_identifier")),
        "asset_name": empty_to_none(data.get("asset_name")),
        "cnpj": empty_to_none(data.get("cnpj")),
        "acquisition_date": acquisition_date,
        "quantity_micros": quantity,
        "unit_price_cents": unit_price_cents,
        "total_cost_cents": total_cost_cents,
        "exchange_rate": data.get("exchange_rate_to_brl") or data.get("exchange_rate"),
        "fixed_income_mode": fixed_income_mode,
        "fixed_income_indexer": empty_to_none(data.get("fixed_income_indexer")),
        "fixed_income_rate_micros": decimal_to_micros(data.get("fixed_income_rate")),
        "notes": empty_to_none(data.get("notes")),
    }


def resolve_position_exchange_rate(currency: str, acquisition_date: str, raw_rate: object) -> int:
    if str(currency or "BRL").upper() == "BRL":
        return rate_to_micros(Decimal("1"))
    if str(raw_rate or "").strip():
        return rate_to_micros(parse_exchange_rate(raw_rate))
    return rate_to_micros(get_exchange_rate_to_brl(currency, acquisition_date))


def normalize_id(value: object, message: str) -> int:
    try:
        normalized = int(str(value or "").strip())
    except ValueError as exc:
        raise PortfolioError(message) from exc
    if normalized <= 0:
        raise PortfolioError(message)
    return normalized


def normalize_date(value: object) -> str:
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise PortfolioError("Informe uma data valida.") from exc


def optional_key(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    return raw or None


def build_positions(rows) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    for row in rows:
        asset_type = row["asset_type"] or "other"
        identifier = normalize_asset_identifier(row["asset_identifier"], asset_type)
        key = (
            row["account_id"],
            row["account_currency"],
            asset_type,
            identifier,
            row["asset_name"] or "",
            row["cnpj"] or "",
            row["fixed_income_indexer"] or "",
        )
        position = grouped.setdefault(key, empty_position(row, asset_type, identifier))
        quantity = micros_to_decimal(row["quantity_micros"])
        invested_cents = int(row["invested_amount_cents"] or row["amount_cents"] or 0)
        costs_cents = sum(int(row[field] or 0) for field in (
            "brokerage_fee_cents",
            "exchange_fee_cents",
            "tax_cents",
            "other_costs_cents",
        ))
        total_cost_cents = invested_cents + costs_cents
        position["quantity"] += quantity
        position["invested_cents"] += invested_cents
        position["costs_cents"] += costs_cents
        position["total_cost_cents"] += total_cost_cents
        position["total_cost_brl_cents"] += convert_to_brl_cents(total_cost_cents, int(row["exchange_rate_micros"] or 1000000))
        position["operations_count"] += 1
        position["last_operation_date"] = row["date"]
        position["first_operation_date"] = min(position["first_operation_date"], row["date"])
        if row["unit_price_cents"]:
            position["last_unit_price_cents"] = int(row["unit_price_cents"])
    return list(grouped.values())


def empty_position(row, asset_type: str, identifier: str) -> dict:
    return {
        "account_id": row["account_id"],
        "account_name": row["account_name"],
        "currency": row["account_currency"],
        "asset_type": asset_type,
        "asset_type_label": ASSET_TYPE_LABELS.get(asset_type, "Outros"),
        "asset_identifier": identifier,
        "asset_name": row["asset_name"] or identifier or row["description"],
        "cnpj": row["cnpj"],
        "fixed_income_mode": row["fixed_income_mode"],
        "fixed_income_indexer": normalize_indexer(row["fixed_income_indexer"]),
        "fixed_income_rate": micros_to_decimal(row["fixed_income_rate_micros"]),
        "market_label": "Brasil" if row["account_currency"] == "BRL" else "Exterior",
        "quantity": Decimal("0"),
        "invested_cents": 0,
        "costs_cents": 0,
        "total_cost_cents": 0,
        "total_cost_brl_cents": 0,
        "current_value_cents": 0,
        "current_value_brl_cents": 0,
        "day_result_cents": 0,
        "day_result_brl_cents": 0,
        "quote": None,
        "quote_source": None,
        "quote_status": "pending",
        "quote_date": None,
        "operations_count": 0,
        "first_operation_date": row["date"],
        "last_operation_date": row["date"],
        "last_unit_price_cents": 0,
    }


def quote_positions(positions: list[dict]) -> None:
    for position in positions:
        if position["asset_type"] in {"stock", "crypto"}:
            apply_market_quote(position)
        elif position["asset_type"] == "fixed_income":
            apply_fixed_income_value(position)
        else:
            apply_cost_value(position, "Cotacao manual pendente")


def apply_market_quote(position: dict) -> None:
    symbol = yahoo_symbol(position)
    if not symbol:
        apply_cost_value(position, "Ativo sem codigo")
        return
    try:
        quote = fetch_yahoo_quote(symbol)
        position["quote"] = cents_to_money(quote["price_cents"])
        position["quote_source"] = f"Yahoo Finance ({symbol})"
        position["quote_status"] = "ok"
        position["quote_date"] = quote["date"]
        position["current_value_cents"] = decimal_to_cents(position["quantity"] * cents_to_decimal(quote["price_cents"]))
        position["current_value_brl_cents"] = value_to_brl(position["current_value_cents"], position["currency"])
        position["day_result_cents"] = decimal_to_cents(position["quantity"] * cents_to_decimal(quote["day_change_cents"]))
        position["day_result_brl_cents"] = value_to_brl(position["day_result_cents"], position["currency"])
    except PortfolioError as exc:
        apply_cost_value(position, exc.message)


def apply_fixed_income_value(position: dict) -> None:
    days = max((date.today() - date.fromisoformat(position["first_operation_date"])).days, 0)
    annual_rate = Decimal(str(position["fixed_income_rate"] or "0"))
    mode = position["fixed_income_mode"] or "post"
    indexer = position["fixed_income_indexer"] or "CDI"
    rate_factor = Decimal("0")
    status = "ok"
    source = "Taxa cadastrada"
    try:
        if mode == "pre":
            rate_factor = annual_rate / Decimal("100")
        else:
            indexer_rate = fetch_indexer_rate(indexer)
            source = f"Banco Central SGS ({indexer})"
            rate_factor = indexer_rate * (annual_rate / Decimal("100") if annual_rate else Decimal("1"))
            if mode == "hybrid":
                rate_factor += annual_rate / Decimal("100")
    except PortfolioError as exc:
        status = exc.message
        rate_factor = annual_rate / Decimal("100")
    gross_factor = (Decimal("1") + rate_factor) ** (Decimal(days) / Decimal("365")) if rate_factor else Decimal("1")
    current = Decimal(position["total_cost_cents"]) * gross_factor
    position["quote"] = f"{format_decimal_percent(rate_factor * Decimal('100'))}% a.a."
    position["quote_source"] = source
    position["quote_status"] = status
    position["quote_date"] = date.today().isoformat()
    position["current_value_cents"] = int(current.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    position["current_value_brl_cents"] = value_to_brl(position["current_value_cents"], position["currency"])
    position["day_result_cents"] = 0
    position["day_result_brl_cents"] = 0


def apply_cost_value(position: dict, status: str) -> None:
    position["current_value_cents"] = position["total_cost_cents"]
    position["current_value_brl_cents"] = position["total_cost_brl_cents"]
    position["day_result_cents"] = 0
    position["day_result_brl_cents"] = 0
    position["quote_status"] = status


def fetch_yahoo_quote(symbol: str) -> dict:
    url = YAHOO_CHART_URL.format(symbol=quote(symbol))
    payload = read_json_url(url, "Nao foi possivel consultar a cotacao do ativo.")
    try:
        result = payload["chart"]["result"][0]
        meta = result["meta"]
        price = Decimal(str(meta.get("regularMarketPrice") or meta.get("previousClose")))
        previous_close = Decimal(str(meta.get("chartPreviousClose") or meta.get("previousClose") or price))
        timestamp = int(meta.get("regularMarketTime") or result["timestamp"][-1])
    except (KeyError, IndexError, TypeError, InvalidOperation) as exc:
        raise PortfolioError("Cotacao indisponivel") from exc
    return {
        "price_cents": decimal_to_cents(price),
        "day_change_cents": decimal_to_cents(price - previous_close),
        "date": date.fromtimestamp(timestamp).isoformat(),
    }


def fetch_indexer_rate(indexer: str) -> Decimal:
    normalized = normalize_indexer(indexer)
    series = INDEXER_SERIES.get(normalized)
    if not series:
        raise PortfolioError("Indexador sem serie automatica")
    payload = read_json_url(BCB_SERIES_URL.format(series=series), "Nao foi possivel consultar o indexador.")
    try:
        daily_percent = Decimal(str(payload[-1]["valor"]).replace(",", "."))
    except (IndexError, KeyError, InvalidOperation, TypeError) as exc:
        raise PortfolioError("Indexador indisponivel") from exc
    if normalized in {"CDI", "SELIC"}:
        return ((Decimal("1") + daily_percent / Decimal("100")) ** Decimal("252")) - Decimal("1")
    return daily_percent / Decimal("100")


def read_json_url(url: str, message: str) -> dict | list:
    request = Request(url, headers={"User-Agent": "SistemaFinanceiro/0.1"})
    try:
        with urlopen(request, timeout=6) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PortfolioError(message) from exc


def yahoo_symbol(position: dict) -> str:
    identifier = position["asset_identifier"]
    if not identifier:
        return ""
    if position["asset_type"] == "crypto":
        return identifier if "-" in identifier else f"{identifier}-USD"
    if "." in identifier or position["currency"] != "BRL":
        return identifier
    return f"{identifier}.SA"


def summarize_positions(positions: list[dict]) -> dict:
    total_cost = sum(position["total_cost_brl_cents"] for position in positions)
    current_value = sum(position["current_value_brl_cents"] for position in positions)
    day_result = sum(position["day_result_brl_cents"] for position in positions)
    by_type = group_positions(positions, "asset_type_label")
    by_indexer = group_positions(positions, "fixed_income_indexer")
    by_currency = group_positions(positions, "currency")
    by_market = group_positions(positions, "market_label")
    by_account = group_positions(positions, "account_name")
    return {
        "total_cost_brl": cents_to_money(total_cost),
        "current_value_brl": cents_to_money(current_value),
        "result_brl": cents_to_money(current_value - total_cost),
        "result_percent": percent(current_value - total_cost, total_cost),
        "day_result_brl": cents_to_money(day_result),
        "day_result_percent": percent(day_result, current_value - day_result),
        "position_count": len(positions),
        "by_type": by_type,
        "by_indexer": by_indexer,
        "by_currency": by_currency,
        "by_market": by_market,
        "by_account": by_account,
    }


def format_quoted_position(position: dict) -> dict:
    position = format_position(position)
    position["current_value"] = cents_to_money(position["current_value_cents"])
    position["current_value_brl"] = cents_to_money(position["current_value_brl_cents"])
    position["day_result"] = cents_to_money(position["day_result_cents"])
    position["day_result_brl"] = cents_to_money(position["day_result_brl_cents"])
    return position


def group_positions(positions: list[dict], key: str) -> list[dict]:
    totals = defaultdict(lambda: {"label": "", "cost_brl_cents": 0, "current_brl_cents": 0, "count": 0})
    for position in positions:
        label = position.get(key) or "Nao informado"
        row = totals[label]
        row["label"] = label
        row["cost_brl_cents"] += position["total_cost_brl_cents"]
        row["current_brl_cents"] += position["current_value_brl_cents"]
        row["count"] += 1
    return [
        {
            "label": row["label"],
            "cost_brl": cents_to_money(row["cost_brl_cents"]),
            "current_brl": cents_to_money(row["current_brl_cents"]),
            "result_brl": cents_to_money(row["current_brl_cents"] - row["cost_brl_cents"]),
            "result_percent": percent(row["current_brl_cents"] - row["cost_brl_cents"], row["cost_brl_cents"]),
            "count": row["count"],
        }
        for row in sorted(totals.values(), key=lambda item: item["current_brl_cents"], reverse=True)
    ]


def format_position(position: dict) -> dict:
    average_cents = decimal_to_cents(Decimal(position["total_cost_cents"]) / position["quantity"] / MONEY_SCALE) if position["quantity"] else position["last_unit_price_cents"]
    position["quantity"] = decimal_to_string(position["quantity"])
    position["fixed_income_rate"] = format_decimal_percent(position["fixed_income_rate"])
    position["average_price"] = cents_to_money(average_cents)
    position["invested"] = cents_to_money(position["invested_cents"])
    position["costs"] = cents_to_money(position["costs_cents"])
    position["total_cost"] = cents_to_money(position["total_cost_cents"])
    position["total_cost_brl"] = cents_to_money(position["total_cost_brl_cents"])
    return position


def indexer_catalog() -> list[dict]:
    return [{"label": label, "automatic": bool(series)} for label, series in INDEXER_SERIES.items()]


def normalize_asset_identifier(value: object, asset_type: str) -> str:
    identifier = str(value or "").strip().upper()
    if asset_type == "crypto" and identifier.endswith("USDT"):
        return identifier[:-4]
    return identifier


def normalize_indexer(value: object) -> str:
    return str(value or "").strip().upper().replace("Í", "I")


def micros_to_decimal(micros: int) -> Decimal:
    return Decimal(int(micros or 0)) / MICRO_SCALE


def decimal_to_micros(value: object) -> int:
    raw = str(value or "").strip()
    if not raw:
        return 0
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        decimal_value = Decimal(raw)
    except InvalidOperation as exc:
        raise PortfolioError("Informe um numero valido na posicao inicial.") from exc
    if decimal_value < 0:
        raise PortfolioError("Informe valores positivos na posicao inicial.")
    return int((decimal_value * MICRO_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def decimal_to_cents(value: Decimal) -> int:
    return int((value * MONEY_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cents_to_decimal(cents: int) -> Decimal:
    return Decimal(cents) / MONEY_SCALE


def decimal_to_string(value: Decimal) -> str:
    if not value:
        return "0"
    return f"{value.normalize():f}"


def format_decimal_percent(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    text = f"{rounded.normalize():f}"
    return text.replace(".", ",")


def value_to_brl(amount_cents: int, currency: str) -> int:
    if currency == "BRL":
        return amount_cents
    try:
        rate = get_exchange_rate_to_brl(currency, date.today().isoformat())
    except Exception:
        return 0
    return convert_to_brl_cents(amount_cents, int((rate * MICRO_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def percent(delta: int, base: int) -> str:
    if not base:
        return "0.00"
    value = Decimal(delta) / Decimal(base) * Decimal("100")
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
