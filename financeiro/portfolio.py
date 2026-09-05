from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus
import json
import re
import sqlite3
from urllib.parse import quote

from financeiro.accounts import cents_to_money, empty_to_none, money_to_cents, recompute_account_balance
from financeiro.calendar_rules import add_months, normalize_iso_date
from financeiro.database import begin_immediate, get_connection, row_to_dict
from financeiro.identifiers import positive_int_id
from financeiro.money import MONEY_SCALE, cents_to_decimal, decimal_to_cents
from financeiro import portfolio_calculations as calculations
from financeiro import portfolio_positions as positions_store
from financeiro import portfolio_quotes as quotes
from financeiro import portfolio_presentation as presentation
from financeiro import portfolio_events as events
from financeiro.market_calendar import load_holiday_dates
from financeiro.portfolio_valuation import PositionValuation
from financeiro.portfolio_returns import PortfolioReturns
from financeiro.portfolio_snapshots import list_snapshots, upsert_snapshots
from financeiro.secure_config import load_mais_retorno_api_key
from financeiro.transactions import convert_to_brl_cents, get_exchange_rate_to_brl, parse_exchange_rate, rate_to_micros

MICRO_SCALE = Decimal("1000000")
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies={currency}&include_24hr_change=true"
MAIS_RETORNO_QUOTES_URL = "https://data.maisretorno.com/mr-data/v4/api/quotes/{symbol}?start_date={start}&end_date={end}"
BCB_SERIES_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados/ultimos/1?formato=json"
BCB_SERIES_RANGE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados?formato=json&dataInicial={start}&dataFinal={end}"
MARKET_QUOTE_TTL_SECONDS = quotes.MARKET_QUOTE_TTL_SECONDS
INDEXER_QUOTE_TTL_SECONDS = quotes.INDEXER_QUOTE_TTL_SECONDS
QUOTE_MEMORY_CACHE_MAX_ENTRIES = quotes.QUOTE_MEMORY_CACHE_MAX_ENTRIES
FX_MEMORY_CACHE_MAX_ENTRIES = quotes.FX_MEMORY_CACHE_MAX_ENTRIES

ASSET_TYPE_LABELS = {
    "stock": "Renda variável",
    "crypto": "Cripto",
    "stablecoin": "Stablecoin",
    "fund": "Fundos",
    "fixed_income": "Renda fixa",
    "private_pension": "Previdência privada",
    "savings": "Poupança",
    "other": "Outros",
}
ALLOCATION_GOAL_LABELS = {
    **ASSET_TYPE_LABELS,
    "stock_usd": "Renda variável - USD",
}
PORTFOLIO_ACCOUNT_TYPES = {"liquidity", "investment"}

INDEXER_SERIES = {
    "CDI": "12",
    "SELIC": "11",
    "IPCA": "433",
    "IGP-M": "189",
    "TR": "226",
    "PREFIXADO": "",
}

MONTHLY_INDEXERS = {"IPCA", "IGP-M"}
INDEXER_FALLBACK_ANNUAL_RATES = {
    "CDI": Decimal("0.1490"),
    "SELIC": Decimal("0.1500"),
    "IPCA": Decimal("0.0450"),
    "IGP-M": Decimal("0.0400"),
    "TR": Decimal("0.0100"),
}
CRYPTO_ASSETS = {"BTC", "ETH", "SOL", "USDC", "USDT"}
STABLECOIN_ASSETS = {"USDC", "USDT", "DAI", "FDUSD", "PYUSD", "TUSD", "USDP", "USDE"}
CRYPTO_ALIASES = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "SOLANA": "SOL",
    "USD COIN": "USDC",
    "TETHER": "USDT",
}
CRYPTO_COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "USDC": "usd-coin",
    "USDT": "tether",
}
CRYPTO_QUOTE_SYMBOLS = {
    "BRL": {
        "BTC": "BTC-BRL",
        "ETH": "ETH-BRL",
        "SOL": "SOL-BRL",
        "USDC": "USDC-BRL",
        "USDT": "USDT-BRL",
    },
    "USD": {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD",
        "USDC": "USDC-USD",
        "USDT": "USDT-USD",
    },
}
CRYPTO_QUOTE_SUFFIXES = ("BRL", "USD", "USDT", "USDC")
YAHOO_SYMBOL_ALIASES = {
    ("VWRA", "USD"): "VWRA.L",
}


class PortfolioError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


urlopen = quotes.urlopen  # Compatibility seam for existing consumers/tests.
_quote_cache = quotes.QuoteCache(
    connection_factory=lambda: get_connection(),
    read_json=lambda *args, **kwargs: read_json_url(*args, **kwargs),
    error_type=PortfolioError,
    clock=lambda: datetime.now(),
    max_entries=QUOTE_MEMORY_CACHE_MAX_ENTRIES,
    fx_max_entries=FX_MEMORY_CACHE_MAX_ENTRIES,
)
QUOTE_MEMORY_CACHE = _quote_cache.memory
QUOTE_MEMORY_CACHE_LOCK = _quote_cache.memory_lock
FX_MEMORY_CACHE = _quote_cache.fx_memory
FX_MEMORY_CACHE_LOCK = _quote_cache.fx_lock


def get_portfolio(user_id: int, force_refresh: bool = False) -> dict:
    # spec: arquitetura-v2/desconcentracao-arquitetura-v2 v2.3 — critérios 12–14
    with get_connection() as conn:
        conn.execute("BEGIN")
        inputs = positions_store.load_position_inputs(conn, user_id)
        redemption_rows = positions_store.load_redemption_history(conn, user_id)

    positions = assemble_portfolio_positions(inputs, user_id, force_refresh=force_refresh)
    closed_rows = sorted(inputs["closed"], key=lambda row: (row["closed_at"], row["id"]), reverse=True)
    result = {
        "positions": [format_quoted_position(position) for position in positions],
        "history": [format_closed_position(row) for row in closed_rows],
        "redemption_history": [format_redemption_summary(row) for row in redemption_rows],
        "summary": summarize_positions(positions),
        "indexers": indexer_catalog(),
        "allocation_goals": get_allocation_goals(user_id),
    }
    result["presentation"] = presentation.build_presentation(result["positions"], result["summary"], result["allocation_goals"])
    return result


def get_portfolio_events(user_id: int, force_refresh: bool = False, start_date: date | None = None) -> dict:
    # Fecha o snapshot SQLite antes de qualquer consulta ao provedor externo.
    with get_connection() as conn:
        conn.execute("BEGIN")
        inputs = positions_store.load_position_inputs(conn, user_id)
    event_assets = events.build_event_assets(build_unquoted_portfolio_positions(inputs), yahoo_symbol)
    return events.get_events(
        event_assets,
        cached_json=cached_json_url,
        cached_calendar=cached_yahoo_calendar,
        error_type=PortfolioError,
        force_refresh=force_refresh,
        start_date=start_date,
        holidays=load_holiday_dates(get_connection),
    )


def cached_yahoo_calendar(symbol: str, message: str, cache_key: str, ttl_seconds: int, force_refresh: bool = False) -> dict:
    return _quote_cache.cached_loader(
        cache_key,
        message,
        ttl_seconds,
        lambda: quotes.read_yahoo_calendar_json(symbol, message, opener=urlopen, error_type=PortfolioError),
        force_refresh=force_refresh,
    )


def preview_portfolio(data: dict) -> dict:
    return presentation.preview(data, PortfolioError)


def get_allocation_goals(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT asset_type, target_percent_micros FROM portfolio_allocation_goals WHERE user_id = ? ORDER BY asset_type",
            (user_id,),
        ).fetchall()
    goals = {row["asset_type"]: int(row["target_percent_micros"] or 0) for row in rows}
    return [
        {
            "asset_type": asset_type,
            "label": label,
            "target_percent": decimal_to_string(Decimal(goals.get(asset_type, 0)) / MICRO_SCALE),
        }
        for asset_type, label in ALLOCATION_GOAL_LABELS.items()
    ]


def save_allocation_goals(user_id: int, data: dict) -> dict:
    # spec: investimentos-portfolio v2.53 — critérios 62-66
    raw_goals = data.get("goals")
    if not isinstance(raw_goals, list):
        raise PortfolioError("Informe as metas de alocacao.")
    normalized = {}
    for item in raw_goals:
        if not isinstance(item, dict):
            raise PortfolioError("Meta de alocacao invalida.")
        asset_type = str(item.get("asset_type") or "").strip().lower()
        if asset_type not in ALLOCATION_GOAL_LABELS or asset_type in normalized:
            raise PortfolioError("Classe de ativo invalida ou duplicada.")
        target_micros = decimal_to_micros(item.get("target_percent"))
        if target_micros < 0 or target_micros > int(Decimal("100") * MICRO_SCALE):
            raise PortfolioError("Cada meta deve ficar entre 0% e 100%.")
        normalized[asset_type] = target_micros
    total_micros = sum(normalized.values())
    if normalized and total_micros != int(Decimal("100") * MICRO_SCALE):
        raise PortfolioError("A soma das metas deve ser exatamente 100%.")
    with get_connection() as conn:
        conn.execute("DELETE FROM portfolio_allocation_goals WHERE user_id = ?", (user_id,))
        conn.executemany(
            """
            INSERT INTO portfolio_allocation_goals (user_id, asset_type, target_percent_micros)
            VALUES (?, ?, ?)
            """,
            [(user_id, asset_type, target) for asset_type, target in normalized.items() if target > 0],
        )
    return get_portfolio(user_id)


def allocation_goal_key(position: dict) -> str:
    return positions_store.allocation_goal_key(position)


def portfolio_row_with_redemptions(row: dict, redemption_totals: dict[tuple, dict]) -> dict:
    totals = redemption_totals.get((row["source_type"], row["source_id"]), {})
    row["redeemed_cost_cents"] = int(totals.get("redeemed_cost_cents") or 0)
    row["redeemed_quantity_micros"] = int(totals.get("redeemed_quantity_micros") or 0)
    return row


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
        ensure_portfolio_account(account)
        exchange_rate_micros = resolve_position_exchange_rate(account["currency"], position["acquisition_date"], position["exchange_rate"])
        conn.execute(
            """
            INSERT INTO investment_opening_positions (
                user_id, account_id, asset_type, asset_identifier, asset_name, cnpj,
                acquisition_date, quantity_micros, unit_price_cents, total_cost_cents,
                exchange_rate_micros, fixed_income_mode, fixed_income_indexer,
                fixed_income_rate_micros, fixed_income_maturity_date,
                apply_tax_estimate, emergency_reserve_eligible, savings_anniversaries_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                position["fixed_income_maturity_date"],
                position["apply_tax_estimate"],
                position["emergency_reserve_eligible"],
                position["savings_anniversaries_json"],
                position["notes"],
            ),
        )
    return get_portfolio(user_id)


def update_opening_position(user_id: int, position_id: object, data: dict) -> dict:
    normalized_id = normalize_id(position_id, "Posicao nao encontrada.")
    position = normalize_opening_position_payload(data)
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM investment_opening_positions
            WHERE id = ? AND user_id = ?
            """,
            (normalized_id, user_id),
        ).fetchone()
        if not existing:
            raise PortfolioError("Posicao nao encontrada.", HTTPStatus.NOT_FOUND)
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
        ensure_portfolio_account(account)
        exchange_rate_micros = resolve_position_exchange_rate(account["currency"], position["acquisition_date"], position["exchange_rate"])
        conn.execute(
            """
            UPDATE investment_opening_positions
            SET account_id = ?, asset_type = ?, asset_identifier = ?, asset_name = ?, cnpj = ?,
                acquisition_date = ?, quantity_micros = ?, unit_price_cents = ?, total_cost_cents = ?,
                exchange_rate_micros = ?, fixed_income_mode = ?, fixed_income_indexer = ?,
                fixed_income_rate_micros = ?, fixed_income_maturity_date = ?,
                apply_tax_estimate = ?, emergency_reserve_eligible = ?,
                savings_anniversaries_json = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (
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
                position["fixed_income_maturity_date"],
                position["apply_tax_estimate"],
                position["emergency_reserve_eligible"],
                position["savings_anniversaries_json"],
                position["notes"],
                normalized_id,
                user_id,
            ),
        )
    return get_portfolio(user_id)


def update_position_value_override(user_id: int, data: dict) -> dict:
    selector = normalize_position_value_override_payload(data)
    with get_connection() as conn:
        account = conn.execute(
            """
            SELECT id
            FROM checking_accounts
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (selector["account_id"], user_id),
        ).fetchone()
        if not account:
            raise PortfolioError("Conta da carteira nao encontrada.", HTTPStatus.NOT_FOUND)
        conn.execute(
            """
            INSERT INTO investment_value_overrides (
                user_id, account_id, asset_type, asset_identifier, asset_name, cnpj,
                fixed_income_indexer, fixed_income_maturity_date, current_value_cents,
                quote_date, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (
                user_id, account_id, asset_type, asset_identifier, asset_name,
                cnpj, fixed_income_indexer, fixed_income_maturity_date
            ) DO UPDATE SET
                current_value_cents = excluded.current_value_cents,
                quote_date = excluded.quote_date,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                selector["account_id"],
                selector["asset_type"],
                selector["asset_identifier"],
                selector["asset_name"],
                selector["cnpj"],
                selector["fixed_income_indexer"],
                selector["fixed_income_maturity_date"],
                selector["current_value_cents"],
                selector["quote_date"],
                selector["notes"],
            ),
        )
    return get_portfolio(user_id)


def delete_position_value_override(user_id: int, data: dict) -> dict:
    selector = normalize_position_value_override_payload({**data, "current_value": "0"})
    selector_key = portfolio_override_key(selector)
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM investment_value_overrides WHERE user_id = ?", (user_id,)).fetchall()
        matching_ids = [row["id"] for row in rows if portfolio_override_key(row_to_dict(row)) == selector_key]
        if not matching_ids:
            raise PortfolioError("Ajuste manual nao encontrado.", HTTPStatus.NOT_FOUND)
        conn.executemany(
            "DELETE FROM investment_value_overrides WHERE id = ? AND user_id = ?",
            [(override_id, user_id) for override_id in matching_ids],
        )
    return get_portfolio(user_id, force_refresh=True)


def delete_opening_position(user_id: int, position_id: object) -> dict:
    normalized_id = normalize_id(position_id, "Posicao nao encontrada.")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM investment_opening_positions
            WHERE id = ? AND user_id = ?
            """,
            (normalized_id, user_id),
        )
        if cursor.rowcount == 0:
            raise PortfolioError("Posicao nao encontrada.", HTTPStatus.NOT_FOUND)
    return get_portfolio(user_id)


def redeem_position(user_id: int, data: dict) -> dict:
    # spec: investimentos-portfolio v2.53 — criterios 9, 55-58
    # (em posicao com multiplas origens, o consumo do resgate segue FIFO pela
    #  data da primeira operacao — candidates.sort abaixo garante essa ordem)
    selector = normalize_redemption_selector(data)
    requested_quantity_micros = decimal_to_micros(data.get("quantity"))
    quantity_mode = requested_quantity_micros > 0
    gross_value_cents = money_to_cents(data.get("gross_amount", data.get("amount", "0")))
    unit_price_cents = money_to_cents(data.get("unit_price", "0")) if str(data.get("unit_price") or "").strip() else 0
    if quantity_mode and gross_value_cents <= 0 and unit_price_cents > 0:
        gross_value_cents = int((Decimal(requested_quantity_micros) * Decimal(unit_price_cents) / MICRO_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    fees_cents = money_to_cents(data.get("fees", "0")) if str(data.get("fees") or "").strip() else 0
    redemption_value_cents = money_to_cents(data.get("amount", "0")) if str(data.get("amount") or "").strip() else gross_value_cents - fees_cents
    if gross_value_cents <= 0 or redemption_value_cents <= 0:
        raise PortfolioError("Informe um valor de resgate valido.")
    if fees_cents < 0 or redemption_value_cents > gross_value_cents:
        raise PortfolioError("O saldo liquido deve ser menor ou igual ao valor bruto.")
    if redemption_value_cents != gross_value_cents - fees_cents:
        raise PortfolioError("O saldo liquido deve corresponder ao valor bruto menos as taxas.")
    redemption_date = normalize_date(data.get("date") or date.today().isoformat())
    with get_connection() as conn:
        account = conn.execute(
            """
            SELECT id, currency
            FROM checking_accounts
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (selector["account_id"], user_id),
        ).fetchone()
        if not account:
            raise PortfolioError("Conta da carteira nao encontrada.", HTTPStatus.NOT_FOUND)
    inputs, positions = prepare_portfolio_positions(user_id)
    with get_connection() as conn:
        begin_immediate(conn)
        assert_portfolio_inputs_unchanged(conn, user_id, inputs)
        candidates = [
            candidate
            for position in positions
            if matches_redemption_selector(position, selector)
            for candidate in expand_redemption_candidates(position)
            if (quantity_mode or int(candidate["current_value_cents"] or 0) > 0)
            and int(candidate["total_cost_cents"] or 0) > 0
        ]
        candidates.sort(key=lambda position: (position["first_operation_date"], 0 if position["source_type"] == "operation" else 1, position["source_id"] or 0))
        available_cents = sum(int(position["current_value_cents"] or 0) for position in candidates)
        available_quantity_micros = sum(decimal_to_micros_value(position["quantity"]) for position in candidates)
        if quantity_mode and requested_quantity_micros > available_quantity_micros:
            raise PortfolioError("Quantidade de resgate maior que a quantidade disponivel para este ativo.")
        if not quantity_mode and redemption_value_cents > available_cents:
            raise PortfolioError("Valor de resgate maior que o valor disponivel para este ativo.")
        account = conn.execute(
            """
            SELECT id, currency
            FROM checking_accounts
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (selector["account_id"], user_id),
        ).fetchone()
        if not account:
            raise PortfolioError("Conta da carteira nao encontrada.", HTTPStatus.NOT_FOUND)
        exchange_rate_micros = rate_to_micros(Decimal("1"))
        amount_brl_cents = convert_to_brl_cents(redemption_value_cents, exchange_rate_micros)
        description = f"Resgate - {selector['asset_name'] or selector['asset_identifier'] or 'Investimento'}"
        cursor = conn.execute(
            """
            INSERT INTO transactions (
                user_id, type, description, amount_cents, destination_amount_cents,
                exchange_rate_micros, transfer_exchange_rate_micros, amount_brl_cents,
                date, account_id, series_kind, notes
            ) VALUES (?, 'income', ?, ?, 0, ?, 0, ?, ?, ?, 'single', ?)
            """,
            (
                user_id,
                description,
                redemption_value_cents,
                exchange_rate_micros,
                amount_brl_cents,
                redemption_date,
                account["id"],
                empty_to_none(data.get("notes")),
            ),
        )
        recompute_account_balance(conn, user_id, account["id"])
        remaining_cents = gross_value_cents
        remaining_quantity_micros = requested_quantity_micros
        redemptions = []
        for position in candidates:
            if (quantity_mode and remaining_quantity_micros <= 0) or (not quantity_mode and remaining_cents <= 0):
                break
            current_cents = int(position["current_value_cents"] or 0)
            position_quantity_micros = decimal_to_micros_value(position["quantity"])
            if quantity_mode:
                take_quantity_micros = min(remaining_quantity_micros, position_quantity_micros)
                ratio = Decimal(take_quantity_micros) / Decimal(position_quantity_micros)
                take_cents = remaining_cents if take_quantity_micros == remaining_quantity_micros else min(
                    remaining_cents,
                    int((Decimal(gross_value_cents) * Decimal(take_quantity_micros) / Decimal(requested_quantity_micros)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
                )
            else:
                take_cents = min(remaining_cents, current_cents)
                ratio = Decimal(take_cents) / Decimal(current_cents)
                take_quantity_micros = int((Decimal(position_quantity_micros) * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if position_quantity_micros > 0 else 0
            cost_cents = int((Decimal(position["total_cost_cents"]) * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            redemptions.append((
                user_id,
                account["id"],
                cursor.lastrowid,
                position["source_type"],
                position["source_id"],
                take_cents,
                cost_cents,
                take_quantity_micros,
                redemption_date,
                empty_to_none(data.get("notes")),
            ))
            remaining_cents -= take_cents
            remaining_quantity_micros -= take_quantity_micros
        conn.executemany(
            """
            INSERT INTO investment_redemptions (
                user_id, account_id, transaction_id, source_type, source_id,
                redeemed_value_cents, redeemed_cost_cents, redeemed_quantity_micros,
                date, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            redemptions,
        )
        redeemed_cost_cents = sum(int(redemption[6]) for redemption in redemptions)
        redeemed_quantity_micros = sum(int(redemption[7]) for redemption in redemptions)
        conn.execute(
            """
            INSERT INTO investment_redemption_summaries (
                user_id, transaction_id, account_id, currency, asset_type,
                asset_identifier, asset_name, date, redeemed_quantity_micros,
                gross_value_cents, fees_cents, net_value_cents, redeemed_cost_cents,
                realized_result_cents, remaining_quantity_micros, remaining_cost_cents, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                cursor.lastrowid,
                account["id"],
                account["currency"],
                selector["asset_type"],
                selector["asset_identifier"],
                selector["asset_name"],
                redemption_date,
                redeemed_quantity_micros,
                gross_value_cents,
                fees_cents,
                redemption_value_cents,
                redeemed_cost_cents,
                redemption_value_cents - redeemed_cost_cents,
                max(available_quantity_micros - redeemed_quantity_micros, 0),
                max(sum(int(candidate["total_cost_cents"] or 0) for candidate in candidates) - redeemed_cost_cents, 0),
                empty_to_none(data.get("notes")),
            ),
        )
    return get_portfolio(user_id)


def expand_redemption_candidates(position: dict) -> list[dict]:
    sources = position.get("sources") or []
    if not sources:
        return [position] if position.get("source_type") in {"operation", "opening"} else []
    total_quantity = Decimal(str(position.get("quantity") or "0"))
    total_cost_cents = int(position.get("total_cost_cents") or 0)
    candidates = []
    allocated_current_cents = 0
    for index, source in enumerate(sources):
        source_quantity = Decimal(str(source.get("quantity") or "0"))
        source_cost_cents = int(source.get("total_cost_cents") or 0)
        if total_quantity > 0:
            ratio = source_quantity / total_quantity
        elif total_cost_cents > 0:
            ratio = Decimal(source_cost_cents) / Decimal(total_cost_cents)
        else:
            ratio = Decimal("0")
        current_value_cents = (
            int(position.get("current_value_cents") or 0) - allocated_current_cents
            if index == len(sources) - 1
            else int((Decimal(int(position.get("current_value_cents") or 0)) * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        )
        allocated_current_cents += current_value_cents
        candidates.append({
            **position,
            "source_type": source["source_type"],
            "source_id": source["source_id"],
            "source_transaction_id": source.get("source_transaction_id"),
            "first_operation_date": source["date"],
            "last_operation_date": source["date"],
            "quantity": source_quantity,
            "total_cost_cents": source_cost_cents,
            "current_value_cents": current_value_cents,
        })
    return candidates


def close_position(user_id: int, data: dict) -> dict:
    selector = normalize_redemption_selector(data)
    closed_at = normalize_date(data.get("date") or date.today().isoformat())
    closing_value_cents = money_to_cents(data.get("closing_value", data.get("current_value", "0")))
    if closing_value_cents < 0:
        raise PortfolioError("Informe um valor final valido.")
    register_credit = should_register_closing_credit(data)
    with get_connection() as conn:
        account = conn.execute(
            """
            SELECT id, currency
            FROM checking_accounts
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (selector["account_id"], user_id),
        ).fetchone()
        if not account:
            raise PortfolioError("Conta da carteira nao encontrada.", HTTPStatus.NOT_FOUND)
    inputs, positions = prepare_portfolio_positions(user_id)
    matches = [
        position for position in positions
        if matches_redemption_selector(position, selector)
        and position["first_operation_date"] <= closed_at
    ]
    if not matches:
        raise PortfolioError("Posicao nao encontrada para encerramento.", HTTPStatus.NOT_FOUND)
    exchange_rate_micros = rate_to_micros(Decimal("1"))
    closing_value_brl_cents = convert_to_brl_cents(closing_value_cents, exchange_rate_micros)
    with get_connection() as conn:
        begin_immediate(conn)
        assert_portfolio_inputs_unchanged(conn, user_id, inputs)
        matches = [
            position for position in positions
            if matches_redemption_selector(position, selector)
            and position["first_operation_date"] <= closed_at
        ]
        if not matches:
            raise PortfolioError("Posicao nao encontrada para encerramento.", HTTPStatus.NOT_FOUND)
        position = aggregate_backend_positions(matches)
        total_cost_brl_cents = int(position["total_cost_brl_cents"] or 0)
        result_brl_cents = closing_value_brl_cents - total_cost_brl_cents
        result_percent_micros = int((Decimal(result_brl_cents) * MICRO_SCALE / Decimal(total_cost_brl_cents)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if total_cost_brl_cents > 0 else 0
        closed_indexer = common_value(matches, "fixed_income_indexer")
        closed_maturity_date = common_value(matches, "fixed_income_maturity_date")
        snapshot = format_quoted_position({**position})
        snapshot["closed_at"] = closed_at
        snapshot["closing_value"] = cents_to_money(closing_value_cents)
        snapshot["closing_value_brl"] = cents_to_money(closing_value_brl_cents)
        account = conn.execute(
            """
            SELECT id, currency
            FROM checking_accounts
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (selector["account_id"], user_id),
        ).fetchone()
        if not account:
            raise PortfolioError("Conta da carteira nao encontrada.", HTTPStatus.NOT_FOUND)
        existing_closed_position = conn.execute(
            """
            SELECT id
            FROM investment_closed_positions
            WHERE user_id = ? AND account_id = ? AND asset_type = ?
                AND asset_identifier = ? AND asset_name = ? AND cnpj = ?
                AND fixed_income_indexer = ? AND fixed_income_maturity_date = ?
                AND closed_at = ?
            """,
            (
                user_id,
                selector["account_id"],
                selector["asset_type"],
                selector["asset_identifier"],
                selector["asset_name"],
                selector["cnpj"],
                closed_indexer,
                closed_maturity_date,
                closed_at,
            ),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO investment_closed_positions (
                user_id, account_id, currency, asset_type, asset_identifier, asset_name,
                cnpj, fixed_income_indexer, fixed_income_maturity_date, closed_at,
                source_count, quantity_micros, total_cost_cents, total_cost_brl_cents,
                closing_value_cents, closing_value_brl_cents, result_brl_cents,
                result_percent_micros, first_operation_date, last_operation_date,
                quote_source, notes, position_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (
                user_id, account_id, asset_type, asset_identifier, asset_name,
                cnpj, fixed_income_indexer, fixed_income_maturity_date, closed_at
            ) DO UPDATE SET
                source_count = excluded.source_count,
                quantity_micros = excluded.quantity_micros,
                total_cost_cents = excluded.total_cost_cents,
                total_cost_brl_cents = excluded.total_cost_brl_cents,
                closing_value_cents = excluded.closing_value_cents,
                closing_value_brl_cents = excluded.closing_value_brl_cents,
                result_brl_cents = excluded.result_brl_cents,
                result_percent_micros = excluded.result_percent_micros,
                first_operation_date = excluded.first_operation_date,
                last_operation_date = excluded.last_operation_date,
                quote_source = excluded.quote_source,
                notes = excluded.notes,
                position_json = excluded.position_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                selector["account_id"],
                account["currency"],
                selector["asset_type"],
                selector["asset_identifier"],
                selector["asset_name"],
                selector["cnpj"],
                closed_indexer,
                closed_maturity_date,
                closed_at,
                len(matches),
                decimal_to_micros_value(position["quantity"]),
                int(position["total_cost_cents"] or 0),
                total_cost_brl_cents,
                closing_value_cents,
                closing_value_brl_cents,
                result_brl_cents,
                result_percent_micros,
                position["first_operation_date"],
                position["last_operation_date"],
                position.get("quote_source"),
                empty_to_none(data.get("notes")),
                json.dumps(snapshot, ensure_ascii=True),
            ),
        )
        if register_credit and not existing_closed_position and closing_value_cents > 0:
            record_portfolio_closing_credit(
                conn,
                user_id,
                account["id"],
                closing_value_cents,
                closing_value_brl_cents,
                closed_at,
                selector["asset_name"] or selector["asset_identifier"] or "Investimento",
                data.get("notes"),
            )
    return get_portfolio(user_id)


def should_register_closing_credit(data: dict) -> bool:
    # spec: investimentos-portfolio v2.53 — criterios 10-11
    # (a opcao de credito e opt-in explicito e vem desmarcada por padrao no
    #  formulario, justamente para evitar duplicidade com resgates ja lancados)
    return str(data.get("register_credit") or "").strip().lower() in {"1", "true", "on", "yes", "sim"}


def record_portfolio_closing_credit(
    conn: sqlite3.Connection,
    user_id: int,
    account_id: int,
    amount_cents: int,
    amount_brl_cents: int,
    transaction_date: str,
    asset_label: str,
    notes: object,
) -> None:
    description = f"Encerramento - {asset_label}"
    conn.execute(
        """
        INSERT INTO transactions (
            user_id, type, description, amount_cents, destination_amount_cents,
            exchange_rate_micros, transfer_exchange_rate_micros, amount_brl_cents,
            date, account_id, series_kind, notes
        ) VALUES (?, 'income', ?, ?, 0, ?, 0, ?, ?, ?, 'single', ?)
        """,
        (
            user_id,
            description,
            amount_cents,
            rate_to_micros(Decimal("1")),
            amount_brl_cents,
            transaction_date,
            account_id,
            empty_to_none(notes),
        ),
    )
    recompute_account_balance(conn, user_id, account_id)


def current_portfolio_positions(user_id: int, force_refresh: bool = False) -> list[dict]:
    return prepare_portfolio_positions(user_id, force_refresh=force_refresh)[1]


def prepare_portfolio_positions(user_id: int, force_refresh: bool = False) -> tuple[dict, list[dict]]:
    # spec: investimentos/investimentos-portfolio v2.53 — critérios 77-79
    # Fecha o snapshot de leitura antes de consultar cotações, indexadores ou câmbio.
    with get_connection() as conn:
        conn.execute("BEGIN")
        inputs = positions_store.load_position_inputs(conn, user_id)
    return inputs, assemble_portfolio_positions(inputs, user_id, force_refresh=force_refresh)


def assemble_portfolio_positions(inputs: dict, user_id: int, force_refresh: bool = False) -> list[dict]:
    """Monta e valoriza um snapshot já desconectado, sem modificar suas entradas."""
    # spec: arquitetura-v2/desconcentracao-arquitetura-v2 v2.3 — critérios 12 e 13
    positions = build_unquoted_portfolio_positions(inputs)
    quote_positions(positions, user_id=user_id, force_refresh=force_refresh)
    apply_value_overrides(user_id, positions, rows=inputs["overrides"])
    return positions


def build_unquoted_portfolio_positions(inputs: dict) -> list[dict]:
    """Monta posições abertas a partir do snapshot local, sem SQL ou rede."""
    redemption_totals = {
        (row["source_type"], row["source_id"]): {
            "redeemed_cost_cents": int(row["redeemed_cost_cents"] or 0),
            "redeemed_quantity_micros": int(row["redeemed_quantity_micros"] or 0),
        }
        for row in inputs["redemptions"]
    }
    closed_positions = [format_closed_position(row_to_dict(row)) for row in inputs["closed"]]
    rows = [portfolio_row_with_redemptions(row_to_dict(row), redemption_totals) for row in [*inputs["operations"], *inputs["openings"]]]
    rows = filter_closed_portfolio_rows(rows, closed_positions)
    return build_positions(sorted(rows, key=lambda row: (row["date"], row["id"])))


def assert_portfolio_inputs_unchanged(conn, user_id: int, inputs: dict) -> None:
    # spec: investimentos/investimentos-portfolio v2.53 — critério 78
    # BEGIN IMMEDIATE protege esta revalidação e todas as gravações seguintes.
    if positions_store.load_position_inputs(conn, user_id) != inputs:
        raise PortfolioError(
            "A carteira foi alterada durante a operacao. Atualize e tente novamente.",
            HTTPStatus.CONFLICT,
        )


def filter_closed_portfolio_rows(rows: list[dict], closed_positions: list[dict]) -> list[dict]:
    if not closed_positions:
        return rows
    closed_by_key: dict[tuple, list[dict]] = {}
    for closed in closed_positions:
        key = _closed_position_key(closed)
        closed_by_key.setdefault(key, []).append(closed)
    filtered = []
    for row in rows:
        base_key = (
            int(row["account_id"]),
            str(row["account_currency"] or "").upper(),
            row["asset_type"] or "other",
            normalize_asset_identifier(row["asset_identifier"], row["asset_type"] or "other"),
        )
        base_key, candidates = base_key, closed_by_key.get(base_key)
        if candidates is None:
            candidates = ()
        if any(row_matches_closed_position(row, closed) for closed in candidates):
            continue
        filtered.append(row)
    return filtered


def _closed_position_key(closed: dict) -> tuple:
    return (
        int(closed["account_id"]),
        str(closed.get("currency") or "").upper(),
        closed["asset_type"],
        closed["asset_identifier"],
    )


def row_matches_closed_position(row: dict, closed: dict) -> bool:
    asset_type = row["asset_type"] or "other"
    closed_indexer = str(closed.get("fixed_income_indexer") or "")
    closed_maturity_date = str(closed.get("fixed_income_maturity_date") or "")
    return (
        int(row["account_id"]) == int(closed["account_id"])
        and str(row["account_currency"] or "").upper() == str(closed["currency"] or "").upper()
        and asset_type == closed["asset_type"]
        and normalize_asset_identifier(row["asset_identifier"], asset_type) == closed["asset_identifier"]
        and str(row.get("asset_name") or normalize_asset_identifier(row["asset_identifier"], asset_type) or row.get("description") or "") == closed["asset_name"]
        and str(row.get("cnpj") or "") == closed["cnpj"]
        and (not closed_indexer or normalize_indexer(row.get("fixed_income_indexer")) == closed_indexer)
        and (not closed_maturity_date or str(row.get("fixed_income_maturity_date") or "") == closed_maturity_date)
        and str(row.get("date") or "") <= str(closed["closed_at"] or "")
    )


def aggregate_backend_positions(positions: list[dict]) -> dict:
    base = {**positions[0]}
    quantity = sum(Decimal(str(position["quantity"] or "0")) for position in positions)
    for field in (
        "invested_cents",
        "costs_cents",
        "total_cost_cents",
        "total_cost_brl_cents",
        "current_value_cents",
        "current_value_brl_cents",
        "fixed_income_gross_value_cents",
        "fixed_income_iof_tax_cents",
        "fixed_income_income_tax_cents",
        "fixed_income_custody_fee_cents",
        "fixed_income_net_value_cents",
        "day_result_cents",
        "day_result_brl_cents",
    ):
        base[field] = sum(int(position.get(field) or 0) for position in positions)
    base["quantity"] = quantity
    base["operations_count"] = sum(int(position.get("operations_count") or 1) for position in positions)
    base["source_type"] = positions[0]["source_type"] if len(positions) == 1 else "mixed"
    base["source_id"] = positions[0]["source_id"] if len(positions) == 1 else None
    base["source_transaction_id"] = positions[0]["source_transaction_id"] if len(positions) == 1 else None
    base["first_operation_date"] = min(position["first_operation_date"] for position in positions)
    base["last_operation_date"] = max(position["last_operation_date"] for position in positions)
    base["last_unit_price_cents"] = positions[-1].get("last_unit_price_cents") or 0
    return base


def decimal_to_micros_value(value: Decimal) -> int:
    return positions_store.decimal_to_micros_value(Decimal(value or 0))


def common_value(positions: list[dict], key: str) -> str:
    values = {str(position.get(key) or "") for position in positions}
    return values.pop() if len(values) == 1 else ""


def format_closed_position(row: dict) -> dict:
    asset_type = effective_asset_type(row["asset_type"], row["asset_identifier"])
    result_percent = Decimal(int(row["result_percent_micros"] or 0)) / Decimal("10000")
    return {
        "id": row["id"],
        "account_id": row["account_id"],
        "account_name": row.get("account_name") or "",
        "currency": row["currency"],
        "asset_type": asset_type,
        "asset_type_label": ASSET_TYPE_LABELS.get(asset_type, "Outros"),
        "asset_identifier": row["asset_identifier"],
        "asset_name": row["asset_name"],
        "cnpj": row["cnpj"],
        "fixed_income_indexer": row["fixed_income_indexer"],
        "fixed_income_maturity_date": row["fixed_income_maturity_date"],
        "closed_at": row["closed_at"],
        "source_count": row["source_count"],
        "quantity": decimal_to_string(micros_to_decimal(row["quantity_micros"])),
        "total_cost": cents_to_money(row["total_cost_cents"]),
        "total_cost_brl": cents_to_money(row["total_cost_brl_cents"]),
        "closing_value": cents_to_money(row["closing_value_cents"]),
        "closing_value_brl": cents_to_money(row["closing_value_brl_cents"]),
        "result_brl": cents_to_money(row["result_brl_cents"]),
        "result_percent": f"{result_percent:.2f}",
        "first_operation_date": row["first_operation_date"],
        "last_operation_date": row["last_operation_date"],
        "quote_source": row["quote_source"],
        "notes": row["notes"],
    }


def format_redemption_summary(row: dict) -> dict:
    return {
        "id": row["id"],
        "transaction_id": row["transaction_id"],
        "account_id": row["account_id"],
        "account_name": row.get("account_name") or "",
        "currency": row["currency"],
        "asset_type": effective_asset_type(row["asset_type"], row["asset_identifier"]),
        "asset_type_label": ASSET_TYPE_LABELS.get(effective_asset_type(row["asset_type"], row["asset_identifier"]), "Outros"),
        "asset_identifier": row["asset_identifier"] or "",
        "asset_name": row["asset_name"] or row["asset_identifier"] or "Investimento",
        "date": row["date"],
        "redeemed_quantity": decimal_to_string(micros_to_decimal(row["redeemed_quantity_micros"])),
        "gross_value": cents_to_money(row["gross_value_cents"]),
        "fees": cents_to_money(row["fees_cents"]),
        "net_value": cents_to_money(row["net_value_cents"]),
        "redeemed_cost": cents_to_money(row["redeemed_cost_cents"]),
        "realized_result": cents_to_money(row["realized_result_cents"]),
        "remaining_quantity": decimal_to_string(micros_to_decimal(row["remaining_quantity_micros"])),
        "remaining_cost": cents_to_money(row["remaining_cost_cents"]),
        "notes": row["notes"],
    }


def normalize_redemption_selector(data: dict) -> dict:
    return {
        "account_id": normalize_id(data.get("account_id"), "Carteira nao encontrada."),
        "currency": str(data.get("currency") or "").strip().upper(),
        "asset_type": str(data.get("asset_type") or "").strip(),
        "asset_identifier": str(data.get("asset_identifier") or "").strip(),
        "asset_name": str(data.get("asset_name") or "").strip(),
        "cnpj": str(data.get("cnpj") or "").strip(),
    }


def matches_redemption_selector(position: dict, selector: dict) -> bool:
    return (
        int(position["account_id"]) == selector["account_id"]
        and str(position["currency"] or "").upper() == selector["currency"]
        and str(position["asset_type"] or "") == selector["asset_type"]
        and str(position.get("asset_name") or "").strip() == selector["asset_name"]
        and str(position.get("cnpj") or "").strip() == selector["cnpj"]
    )


def ensure_portfolio_account(account) -> None:
    if account["account_type"] not in PORTFOLIO_ACCOUNT_TYPES:
        raise PortfolioError("Selecione uma conta de liquidez ou investimento para a posicao inicial.")


def normalize_opening_position_payload(data: dict) -> dict:
    account_id = normalize_id(data.get("account_id"), "Informe a carteira.")
    asset_type = str(data.get("asset_type") or "other").strip().lower()
    if asset_type not in ASSET_TYPE_LABELS:
        raise PortfolioError("Tipo de investimento invalido.")
    asset_identifier = empty_to_none(data.get("asset_identifier"))
    asset_type = effective_asset_type(asset_type, asset_identifier)
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
    savings_anniversaries = normalize_savings_anniversaries(data.get("savings_anniversaries"), acquisition_date)
    if asset_type == "savings":
        if not savings_anniversaries:
            savings_anniversaries = [{"date": acquisition_date, "amount_cents": total_cost_cents}]
        anniversary_total_cents = sum(int(item["amount_cents"]) for item in savings_anniversaries)
        if anniversary_total_cents > 0:
            total_cost_cents = anniversary_total_cents
        if not empty_to_none(data.get("asset_identifier")):
            data["asset_identifier"] = "POUPANCA"
            asset_identifier = "POUPANCA"
    return {
        "account_id": account_id,
        "asset_type": asset_type,
        "asset_identifier": asset_identifier,
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
        "fixed_income_maturity_date": normalize_optional_date(data.get("fixed_income_maturity_date")),
        "apply_tax_estimate": 1 if str(data.get("apply_tax_estimate") or "").strip().lower() in {"1", "true", "on", "yes"} else 0,
        "emergency_reserve_eligible": normalize_emergency_reserve_eligible(data, asset_type),
        "savings_anniversaries_json": serialize_savings_anniversaries(savings_anniversaries),
        "notes": empty_to_none(data.get("notes")),
    }


def normalize_emergency_reserve_eligible(data: dict, asset_type: str) -> int:
    # spec: investimentos/investimentos-portfolio v2.53 — critérios 20 e 21
    if asset_type not in {"fixed_income", "savings"}:
        return 0
    return 1 if str(data.get("emergency_reserve_eligible") or "").strip().lower() in {"1", "true", "on", "yes"} else 0


def normalize_savings_anniversaries(value: object, default_date: str) -> list[dict]:
    raw = str(value or "").strip()
    if not raw:
        return []
    entries = []
    if raw.startswith("["):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PortfolioError("Informe aniversarios da poupanca validos.") from exc
        for item in payload:
            if not isinstance(item, dict):
                raise PortfolioError("Informe aniversarios da poupanca validos.")
            if "amount_cents" in item:
                entries.append(normalize_savings_anniversary_item(item.get("date") or default_date, item.get("amount_cents")))
            else:
                entries.append(normalize_savings_anniversary_money_item(item.get("date") or default_date, item.get("amount")))
        return entries
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ";" in stripped:
            raw_date, raw_amount = stripped.split(";", 1)
        else:
            parts = stripped.rsplit(None, 1)
            if len(parts) != 2:
                raise PortfolioError("Use uma linha por aniversario no formato AAAA-MM-DD; valor.")
            raw_date, raw_amount = parts
        entries.append(normalize_savings_anniversary_money_item(raw_date, raw_amount))
    return entries


def normalize_savings_anniversary_item(raw_date: object, raw_amount: object) -> dict:
    anniversary_date = normalize_date(raw_date)
    if isinstance(raw_amount, dict):
        raise PortfolioError("Informe aniversarios da poupanca validos.")
    if str(raw_amount or "").strip().isdigit() and not any(char in str(raw_amount) for char in ",."):
        amount_cents = int(raw_amount)
    else:
        amount_cents = money_to_cents(raw_amount)
    if amount_cents <= 0:
        raise PortfolioError("Informe valores positivos para os aniversarios da poupanca.")
    return {"date": anniversary_date, "amount_cents": amount_cents}


def normalize_savings_anniversary_money_item(raw_date: object, raw_amount: object) -> dict:
    anniversary_date = normalize_date(raw_date)
    amount_cents = money_to_cents(raw_amount)
    if amount_cents <= 0:
        raise PortfolioError("Informe valores positivos para os aniversarios da poupanca.")
    return {"date": anniversary_date, "amount_cents": amount_cents}


def serialize_savings_anniversaries(entries: list[dict]) -> str | None:
    if not entries:
        return None
    ordered = sorted(entries, key=lambda item: item["date"])
    return json.dumps(ordered, ensure_ascii=True)


def parse_savings_anniversaries(value: object, fallback_date: object, fallback_amount_cents: int) -> list[dict]:
    raw = str(value or "").strip()
    entries = []
    if raw:
        try:
            payload = json.loads(raw)
            for item in payload:
                if not isinstance(item, dict):
                    continue
                amount_cents = int(item.get("amount_cents") or 0)
                anniversary_date = str(item.get("date") or "").strip()
                if amount_cents > 0 and parse_optional_iso_date(anniversary_date):
                    entries.append({"date": anniversary_date, "amount_cents": amount_cents})
        except (TypeError, ValueError, json.JSONDecodeError):
            entries = []
    if not entries and fallback_amount_cents > 0:
        entries.append({"date": str(fallback_date), "amount_cents": int(fallback_amount_cents)})
    return entries


def consume_savings_anniversaries_fifo(entries: list[dict], redeemed_cost_cents: int) -> list[dict]:
    # spec: investimentos-portfolio v2.53 — criterio poupanca-resgate-fifo
    # (resgates de poupanca consomem primeiro os aniversarios mais antigos para
    # manter a base de rentabilidade alinhada ao saldo remanescente por lote)
    return positions_store.consume_savings_anniversaries_fifo(entries, redeemed_cost_cents)


def normalize_position_value_override_payload(data: dict) -> dict:
    asset_type = str(data.get("asset_type") or "other").strip().lower()
    if asset_type not in ASSET_TYPE_LABELS:
        raise PortfolioError("Tipo de ativo invalido.")
    current_value_cents = money_to_cents(data.get("current_value", "0"))
    if current_value_cents < 0:
        raise PortfolioError("Informe um valor atual valido.")
    return {
        "account_id": normalize_id(data.get("account_id"), "Conta da carteira nao encontrada."),
        "asset_type": asset_type,
        "asset_identifier": normalize_asset_identifier(data.get("asset_identifier"), asset_type),
        "asset_name": str(data.get("asset_name") or "").strip(),
        "cnpj": str(data.get("cnpj") or "").strip(),
        "fixed_income_indexer": normalize_indexer(data.get("fixed_income_indexer")),
        "fixed_income_maturity_date": normalize_optional_date(data.get("fixed_income_maturity_date")) or "",
        "current_value_cents": current_value_cents,
        "quote_date": normalize_date(data.get("quote_date") or date.today().isoformat()),
        "notes": empty_to_none(data.get("notes")),
    }


def apply_value_overrides(user_id: int, positions: list[dict], *, rows=None) -> None:
    if not positions:
        return
    if rows is None:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM investment_value_overrides
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()
    overrides = {portfolio_override_key(row_to_dict(row)): row_to_dict(row) for row in rows}
    for position in positions:
        override = overrides.get(portfolio_override_key(position))
        if not override:
            continue
        current_value_cents = int(override["current_value_cents"] or 0)
        position["current_value_cents"] = current_value_cents
        position["current_value_brl_cents"] = value_to_brl(current_value_cents, position["currency"])
        position["fixed_income_gross_value_cents"] = 0
        position["fixed_income_iof_tax_cents"] = 0
        position["fixed_income_income_tax_cents"] = 0
        position["fixed_income_custody_fee_cents"] = 0
        position["fixed_income_net_value_cents"] = current_value_cents
        position["day_result_cents"] = 0
        position["day_result_brl_cents"] = 0
        position["quote"] = "-"
        position["quote_source"] = "Valor atual informado manualmente"
        position["quote_status"] = "ok"
        position["quote_date"] = override["quote_date"]
        position["manual_value_override"] = True
        position["manual_value_notes"] = override["notes"]


def portfolio_override_key(row: dict) -> tuple:
    asset_type = effective_asset_type(row.get("asset_type"), row.get("asset_identifier"))
    return (
        int(row["account_id"]),
        asset_type,
        normalize_asset_identifier(row.get("asset_identifier"), asset_type),
        str(row.get("asset_name") or "").strip(),
        str(row.get("cnpj") or "").strip(),
        normalize_indexer(row.get("fixed_income_indexer")),
        str(row.get("fixed_income_maturity_date") or "").strip(),
    )


def resolve_position_exchange_rate(currency: str, acquisition_date: str, raw_rate: object) -> int:
    if str(currency or "BRL").upper() == "BRL":
        return rate_to_micros(Decimal("1"))
    if str(raw_rate or "").strip():
        return rate_to_micros(parse_exchange_rate(raw_rate))
    # spec: investimentos-portfolio v2.53 — criterio 48
    # (sem cotacao manual, consulta a ultima PTAX de venda disponivel
    #  ate a data de aquisicao, como em Lancamentos)
    return rate_to_micros(get_exchange_rate_to_brl(currency, acquisition_date))


def normalize_id(value: object, message: str) -> int:
    try:
        return positive_int_id(value)
    except ValueError as exc:
        raise PortfolioError(message) from exc


def normalize_date(value: object) -> str:
    try:
        return normalize_iso_date(value)
    except ValueError as exc:
        raise PortfolioError("Informe uma data valida.") from exc


def normalize_optional_date(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return normalize_iso_date(raw)
    except ValueError as exc:
        raise PortfolioError("Informe uma data valida.") from exc


def optional_key(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    return raw or None


def build_positions(rows) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    for row in rows:
        asset_type = effective_asset_type(row["asset_type"], row["asset_identifier"])
        identifier = normalize_asset_identifier(row["asset_identifier"], asset_type)
        key = portfolio_position_key(row, asset_type, identifier)
        original_quantity_micros = int(row["quantity_micros"] or 0)
        redeemed_quantity_micros = min(int(row.get("redeemed_quantity_micros") or 0), original_quantity_micros)
        quantity = micros_to_decimal(max(original_quantity_micros - redeemed_quantity_micros, 0))
        costs_cents = sum(int(row[field] or 0) for field in (
            "brokerage_fee_cents",
            "exchange_fee_cents",
            "tax_cents",
            "other_costs_cents",
        ))
        original_total_cost_cents = investment_operation_total_cost_cents(row, costs_cents)
        invested_cents = original_total_cost_cents
        redeemed_cost_cents = min(int(row.get("redeemed_cost_cents") or 0), original_total_cost_cents)
        total_cost_cents = max(original_total_cost_cents - redeemed_cost_cents, 0)
        if original_total_cost_cents > 0 and redeemed_cost_cents > 0:
            invested_cents = total_cost_cents
            costs_cents = int((Decimal(costs_cents) * Decimal(total_cost_cents) / Decimal(original_total_cost_cents)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if total_cost_cents <= 0 and quantity <= 0:
            continue
        position = grouped.setdefault(key, empty_position(row, asset_type, identifier))
        source_savings_anniversaries = parse_savings_anniversaries(
            row.get("savings_anniversaries_json"),
            row["date"],
            original_total_cost_cents,
        ) if asset_type == "savings" else []
        if asset_type == "savings" and redeemed_cost_cents > 0:
            source_savings_anniversaries = consume_savings_anniversaries_fifo(
                source_savings_anniversaries,
                redeemed_cost_cents,
            )
        position["quantity"] += quantity
        position["invested_cents"] += invested_cents
        position["costs_cents"] += costs_cents
        position["total_cost_cents"] += total_cost_cents
        position["total_cost_brl_cents"] += convert_to_brl_cents(total_cost_cents, int(row["exchange_rate_micros"] or 1000000))
        position["savings_anniversaries"].extend(source_savings_anniversaries)
        if row.get("emergency_reserve_eligible"):
            position["emergency_reserve_eligible"] = True
        position["sources"].append({
            "source_type": row["source_type"],
            "source_id": row["source_id"],
            "source_transaction_id": row["transaction_id"],
            "description": row["description"],
            "date": row["date"],
            "quantity": quantity,
            "invested_cents": invested_cents,
            "costs_cents": costs_cents,
            "total_cost_cents": total_cost_cents,
            "total_cost_brl_cents": convert_to_brl_cents(total_cost_cents, int(row["exchange_rate_micros"] or 1000000)),
            "unit_price_cents": int(row["unit_price_cents"] or 0),
            "emergency_reserve_eligible": bool(row.get("emergency_reserve_eligible") or 0),
            "savings_anniversaries": source_savings_anniversaries,
        })
        position["operations_count"] += 1
        if position["operations_count"] == 1:
            position["source_type"] = row["source_type"]
            position["source_id"] = row["source_id"]
            position["source_transaction_id"] = row["transaction_id"]
        else:
            position["source_type"] = "mixed"
            position["source_id"] = None
            position["source_transaction_id"] = None
        position["last_operation_date"] = row["date"]
        position["first_operation_date"] = min(position["first_operation_date"], row["date"])
        if row["unit_price_cents"]:
            position["last_unit_price_cents"] = int(row["unit_price_cents"])
    return list(grouped.values())


def investment_operation_total_cost_cents(row: dict, costs_cents: int) -> int:
    invested_cents = int(row["invested_amount_cents"] or 0)
    if invested_cents > 0:
        return invested_cents
    amount_cents = int(row["amount_cents"] or 0)
    if amount_cents > 0:
        return amount_cents
    quantity_micros = int(row["quantity_micros"] or 0)
    unit_price_cents = int(row["unit_price_cents"] or 0)
    gross_cents = int((Decimal(quantity_micros) * Decimal(unit_price_cents) / MICRO_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return gross_cents + costs_cents


def portfolio_position_key(row, asset_type: str, identifier: str) -> tuple:
    base_key = (
        row["account_id"],
        row["account_currency"],
        asset_type,
        identifier,
        row["asset_name"] or "",
        row["cnpj"] or "",
        row["fixed_income_indexer"] or "",
        row["fixed_income_maturity_date"] or "",
    )
    if asset_type == "fixed_income":
        return (*base_key, row["source_type"], row["source_id"])
    return base_key


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
        "fixed_income_maturity_date": row["fixed_income_maturity_date"],
        "apply_tax_estimate": bool(row["apply_tax_estimate"] or 0),
        "emergency_reserve_eligible": bool(row.get("emergency_reserve_eligible") or 0),
        "market_label": "Brasil" if row["account_currency"] == "BRL" else "Exterior",
        "quantity": Decimal("0"),
        "invested_cents": 0,
        "costs_cents": 0,
        "total_cost_cents": 0,
        "total_cost_brl_cents": 0,
        "current_value_cents": 0,
        "current_value_brl_cents": 0,
        "fixed_income_gross_value_cents": 0,
        "fixed_income_iof_tax_cents": 0,
        "fixed_income_income_tax_cents": 0,
        "fixed_income_custody_fee_cents": 0,
        "fixed_income_net_value_cents": 0,
        "savings_anniversaries": [],
        "day_result_cents": 0,
        "day_result_brl_cents": 0,
        "quote": None,
        "quote_source": None,
        "quote_status": "pending",
        "quote_date": None,
        "source_type": None,
        "source_id": None,
        "source_transaction_id": None,
        "sources": [],
        "operations_count": 0,
        "first_operation_date": row["date"],
        "last_operation_date": row["date"],
        "last_unit_price_cents": 0,
    }


def quote_positions(positions: list[dict], user_id: int | None = None, force_refresh: bool = False) -> None:
    if len(positions) <= 1:
        for position in positions:
            quote_position(position, user_id=user_id, force_refresh=force_refresh)
        return
    workers = min(8, len(positions))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(quote_position, position, user_id, force_refresh) for position in positions]
        for future in futures:
            future.result()


def quote_position(position: dict, user_id: int | None = None, force_refresh: bool = False) -> None:
    if position["asset_type"] in {"stock", "crypto", "stablecoin"}:
        apply_market_quote(position, force_refresh=force_refresh)
    elif position["asset_type"] in {"fund", "private_pension"}:
        apply_fund_quote(position, user_id=user_id, force_refresh=force_refresh)
    elif position["asset_type"] == "fixed_income":
        apply_fixed_income_value(position, force_refresh=force_refresh)
    elif position["asset_type"] == "savings":
        apply_savings_value(position, force_refresh=force_refresh)
    else:
        apply_cost_value(position, "Cotacao manual pendente")


def apply_market_quote(position: dict, force_refresh: bool = False) -> None:
    symbol = yahoo_symbol(position)
    if not symbol:
        apply_cost_value(position, "Ativo sem codigo")
        return
    try:
        if position["asset_type"] in {"crypto", "stablecoin"}:
            quote = fetch_crypto_quote(position["asset_identifier"], position["currency"], force_refresh=force_refresh)
        else:
            quote = fetch_yahoo_quote(symbol, force_refresh=force_refresh)
        position["quote"] = cents_to_money(quote["price_cents"])
        position["quote_source"] = quote.get("source") or f"Yahoo Finance ({symbol})"
        position["quote_status"] = "ok"
        position["quote_date"] = quote["date"]
        position["current_value_cents"] = decimal_to_cents(position["quantity"] * cents_to_decimal(quote["price_cents"]))
        position["current_value_brl_cents"] = value_to_brl(position["current_value_cents"], position["currency"])
        position["day_result_cents"] = decimal_to_cents(position["quantity"] * cents_to_decimal(quote["day_change_cents"]))
        position["day_result_brl_cents"] = value_to_brl(position["day_result_cents"], position["currency"])
    except PortfolioError as exc:
        apply_cost_value(position, exc.message)


def apply_fund_quote(position: dict, user_id: int | None = None, force_refresh: bool = False) -> None:
    # spec: investimentos/investimentos-portfolio v2.53 — criterios 27 e 28
    # (cotas de fundos via API Mais Retorno: opt-in configurado nas Preferencias,
    #  posicao com CNPJ e carteira em BRL; sem isso a posicao mantem valor de
    #  custo com status "Cotacao manual pendente")
    identifier = mais_retorno_fund_identifier(position)
    api_key = load_mais_retorno_api_key(user_id) if user_id is not None else ""
    if not identifier or str(position["currency"] or "BRL").upper() != "BRL" or not api_key:
        apply_cost_value(position, "Cotacao manual pendente")
        return
    try:
        quote = fetch_mais_retorno_quote(identifier, api_key, force_refresh=force_refresh)
        position["quote"] = cents_to_money(quote["price_cents"])
        position["quote_source"] = quote.get("source") or f"Mais Retorno ({identifier})"
        position["quote_status"] = "ok"
        position["quote_date"] = quote["date"]
        position["current_value_cents"] = decimal_to_cents(position["quantity"] * cents_to_decimal(quote["price_cents"]))
        position["current_value_brl_cents"] = value_to_brl(position["current_value_cents"], position["currency"])
        position["day_result_cents"] = decimal_to_cents(position["quantity"] * cents_to_decimal(quote["day_change_cents"]))
        position["day_result_brl_cents"] = value_to_brl(position["day_result_cents"], position["currency"])
    except PortfolioError as exc:
        apply_cost_value(position, exc.message)


def fetch_fund_quote_for_user(user_id: int, cnpj: str, force_refresh: bool = False) -> dict:
    # spec: lancamentos v3.35 — criterio cota-fundo-lancamento
    # (busca assistida de cota de fundo no formulario de aporte; o preco segue editavel)
    identifier = mais_retorno_identifier_from_cnpj(cnpj)
    if not identifier:
        raise PortfolioError("Informe o CNPJ do fundo.")
    api_key = load_mais_retorno_api_key(user_id)
    if not api_key:
        raise PortfolioError("Configure a API da Mais Retorno em Preferencias > APIs.")
    quote = fetch_mais_retorno_quote(identifier, api_key, force_refresh=force_refresh)
    return {
        "cnpj": re.sub(r"\D", "", str(cnpj or "")),
        "identifier": identifier,
        "unit_price": cents_to_money(quote["price_cents"]),
        "quote_date": quote["date"],
        "quote_source": quote.get("source") or f"Mais Retorno ({identifier})",
    }


def mais_retorno_fund_identifier(position: dict) -> str:
    # spec: investimentos/investimentos-portfolio v2.53 — criterio fundos-mais-retorno
    # (API exige CNPJ somente com digitos, sem pontos/barra, mais sufixo ":fi")
    return mais_retorno_identifier_from_cnpj(position.get("cnpj"))


def mais_retorno_identifier_from_cnpj(cnpj_value: object) -> str:
    cnpj = re.sub(r"\D", "", str(cnpj_value or ""))
    return f"{cnpj}:fi" if cnpj else ""


def mais_retorno_quotes_for_range(
    start: str,
    end: str,
    identifier: str,
    api_key: str,
    force_refresh: bool = False,
    cache_suffix: str = "",
) -> list:
    # spec: investimentos/investimentos-portfolio v2.53 — criterios 27 e 28:
    # range de datas questionado junto com a data atual; cache diario (ate o
    # fim do dia) para evitar re-consumo da API ao entrar na tela no mesmo dia
    url = MAIS_RETORNO_QUOTES_URL.format(symbol=quote(identifier), start=start, end=end)
    payload = cached_json_url(
        url,
        "Nao foi possivel consultar a cotacao do fundo.",
        f"maisretorno:{identifier}{cache_suffix}",
        seconds_until_end_of_day(),
        force_refresh=force_refresh,
        headers={"X-Api-Key": api_key},
    )
    try:
        quotes = payload["quotes"]
    except (KeyError, TypeError):
        return []
    return quotes if isinstance(quotes, list) else []


def fetch_mais_retorno_quote(identifier: str, api_key: str, force_refresh: bool = False) -> dict:
    today = date.today().isoformat()
    # spec: investimentos/investimentos-portfolio v2.53 — criterios 27 e 28:
    # 1a tentativa sempre com a data atual; em dias sem cota publicada (fim de
    # semana/feriado) a API retorna lista vazia, entao re-consulta com janela
    # retroativa de 7 dias e usa a ultima cota publicada
    quotes = mais_retorno_quotes_for_range(today, today, identifier, api_key, force_refresh)
    if not quotes:
        start = (date.today() - timedelta(days=7)).isoformat()
        quotes = mais_retorno_quotes_for_range(
            start, today, identifier, api_key, force_refresh, cache_suffix=":7d"
        )
    try:
        if not quotes:
            raise KeyError
        latest = max(quotes, key=lambda item: str(item["d"]))
        earlier = [item for item in quotes if str(item["d"]) < str(latest["d"])]
        previous = max(earlier, key=lambda item: str(item["d"])) if earlier else latest
        # spec: investimentos/investimentos-portfolio v2.53 — criterios 27 e 28:
        # a API usa "." como separador decimal (JSON); normaliza virgula por
        # seguranca antes de converter para Decimal
        price = Decimal(str(latest["c"]).replace(",", "."))
        previous_price = Decimal(str(previous["c"]).replace(",", "."))
        quote_date = str(latest["d"])
        if not parse_optional_iso_date(quote_date):
            quote_date = date.today().isoformat()
    except (KeyError, IndexError, TypeError, InvalidOperation) as exc:
        raise PortfolioError("Cotacao do fundo indisponivel") from exc
    return {
        "price_cents": decimal_to_cents(price),
        "day_change_cents": decimal_to_cents(price - previous_price),
        "date": quote_date,
        "source": f"Mais Retorno ({identifier})",
    }


def apply_fixed_income_value(position: dict, force_refresh: bool = False) -> None:
    return _valuation.apply_fixed_income_value(position=position, force_refresh=force_refresh)


def day_variation_cents(
    position: dict,
    current_value_cents: int,
    as_of_date: date,
    value_provider: object,
    force_refresh: bool = False,
    factor_cache: dict[str, Decimal] | None = None,
) -> int:
    return _valuation.day_variation_cents(position=position, current_value_cents=current_value_cents, as_of_date=as_of_date, value_provider=value_provider, force_refresh=force_refresh, factor_cache=factor_cache)


def fixed_income_value_as_of(
    position: dict,
    as_of_date: date,
    force_refresh: bool = False,
    factor_cache: dict[str, Decimal] | None = None,
) -> tuple[int, int, int, int, int, Decimal, str]:
    return _valuation.fixed_income_value_as_of(position=position, as_of_date=as_of_date, force_refresh=force_refresh, factor_cache=factor_cache)


def _position_value_native_as_of(
    position: dict,
    as_of_date: date,
    force_refresh: bool = False,
    factor_cache: dict[str, Decimal] | None = None,
) -> int:
    return _valuation._position_value_native_as_of(position=position, as_of_date=as_of_date, force_refresh=force_refresh, factor_cache=factor_cache)


def position_value_snapshot_metadata(
    position: dict,
    as_of_date: date,
    force_refresh: bool = False,
    factor_cache: dict[str, Decimal] | None = None,
) -> dict:
    return _valuation.position_value_snapshot_metadata(
        position=position, as_of_date=as_of_date, force_refresh=force_refresh, factor_cache=factor_cache
    )


def _accumulated_factor_by_month(
    indexer: str,
    start_date: date,
    end_date: date,
    multiplier: Decimal,
    month_cache: dict[str, Decimal],
    force_refresh: bool = False,
) -> Decimal:
    return _valuation._accumulated_factor_by_month(indexer=indexer, start_date=start_date, end_date=end_date, multiplier=multiplier, month_cache=month_cache, force_refresh=force_refresh)


def _monthly_return_pct(prev_value: int, end_value: int, net_contribution: int) -> Decimal:
    return _returns._monthly_return_pct(prev_value=prev_value, end_value=end_value, net_contribution=net_contribution)


def get_portfolio_returns(user_id: int, force_refresh: bool = False, positions: list[dict] | None = None) -> dict:
    resolved_positions = positions
    if resolved_positions is None:
        resolved_positions = (get_portfolio(user_id, force_refresh=force_refresh).get("positions") or [])
    if resolved_positions:
        _capture_current_portfolio_snapshot(user_id, resolved_positions, force_refresh=force_refresh)
    return _returns.get_portfolio_returns(user_id=user_id, force_refresh=force_refresh, positions=resolved_positions)


def _capture_current_portfolio_snapshot(user_id: int, positions: list[dict], *, force_refresh: bool = False) -> None:
    """Captura a competência atual após toda valorização e rede estarem concluídas."""
    reference_date = date.today()
    snapshot_month = reference_date.strftime("%Y-%m")
    previous_rows = _list_portfolio_snapshots(user_id)
    previous_by_asset = {}
    for row in previous_rows:
        if row["snapshot_month"] >= snapshot_month:
            continue
        key = (row["account_id"], row["currency"], row["asset_type"], row["asset_identifier"], row["asset_name"])
        if key not in previous_by_asset or row["snapshot_month"] > previous_by_asset[key]["snapshot_month"]:
            previous_by_asset[key] = row
    factor_cache: dict[str, Decimal] = {}
    snapshots_by_asset: dict[tuple, dict] = {}
    for position in positions:
        metadata = position_value_snapshot_metadata(
            position, reference_date, force_refresh=force_refresh, factor_cache=factor_cache
        )
        asset_key = (
            int(position["account_id"]), str(position.get("currency") or "BRL").upper(),
            position.get("asset_type") or "other", position.get("asset_identifier") or "",
            position.get("asset_name") or "",
        )
        current_cost = int(position.get("total_cost_cents") or 0)
        quantity_micros = decimal_to_micros_value(Decimal(str(position.get("quantity") or 0)))
        first_operation = date.fromisoformat(position["first_operation_date"])
        snapshot = snapshots_by_asset.setdefault(asset_key, {
            "user_id": user_id,
            "snapshot_month": snapshot_month,
            "as_of_date": metadata["as_of_date"],
            "account_id": int(position["account_id"]),
            "currency": str(position.get("currency") or "BRL").upper(),
            "asset_type": position.get("asset_type") or "other",
            "asset_identifier": position.get("asset_identifier") or "",
            "asset_name": position.get("asset_name") or "",
            "quantity_micros": 0,
            "unit_price_cents": 0,
            "market_value_cents": 0,
            "cost_basis_cents": 0,
            "contribution_cents": 0,
            "redemption_cents": 0,
            "dividend_cents": 0,
            "quote_source": metadata["quote_source"],
            "valuation_status": metadata["valuation_status"],
        })
        # spec: rentabilidade-portfolio v2.9 — critérios 9, 10 e 14
        # A posição apresentada pode conter vários lotes com a mesma identidade.
        # O snapshot é único por ativo, portanto consolida os lotes antes do
        # UPSERT para que nenhum valor seja substituído pelo último lote.
        snapshot["quantity_micros"] += quantity_micros
        snapshot["market_value_cents"] += int(metadata["value_cents"])
        snapshot["cost_basis_cents"] += current_cost
        if first_operation.strftime("%Y-%m") == snapshot_month:
            snapshot["contribution_cents"] += current_cost
        if metadata["valuation_status"] != "observed":
            snapshot["valuation_status"] = "approximate"
        if metadata["as_of_date"] < snapshot["as_of_date"]:
            snapshot["as_of_date"] = metadata["as_of_date"]
        if metadata["quote_source"] != snapshot["quote_source"]:
            snapshot["quote_source"] = "mixed"

    snapshots = list(snapshots_by_asset.values())
    for snapshot in snapshots:
        asset_key = (
            snapshot["account_id"], snapshot["currency"], snapshot["asset_type"],
            snapshot["asset_identifier"], snapshot["asset_name"],
        )
        previous_snapshot = previous_by_asset.get(asset_key)
        if previous_snapshot is not None:
            cost_delta = snapshot["cost_basis_cents"] - int(previous_snapshot.get("cost_basis_cents") or 0)
            snapshot["contribution_cents"] = max(cost_delta, 0)
            snapshot["redemption_cents"] = max(-cost_delta, 0)
        quantity_micros = snapshot["quantity_micros"]
        snapshot["unit_price_cents"] = (
            int((Decimal(snapshot["market_value_cents"]) * Decimal("1000000") / Decimal(quantity_micros)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            if quantity_micros > 0 else 0
        )
    with get_connection() as conn:
        upsert_snapshots(conn, snapshots)


def _list_portfolio_snapshots(user_id: int) -> list[dict]:
    with get_connection() as conn:
        return list_snapshots(conn, user_id)


def _cdi_factor_for_period(start_date: date, end_date: date, force_refresh: bool = False) -> Decimal:
    return _returns._cdi_factor_for_period(start_date=start_date, end_date=end_date, force_refresh=force_refresh)


def _cdi_factor_for_month(month_date: date, as_of: date, cache: dict[str, Decimal] | None = None, force_refresh: bool = False) -> Decimal:
    return _returns._cdi_factor_for_month(month_date=month_date, as_of=as_of, cache=cache, force_refresh=force_refresh)


def _ipca_factor_for_month(month_date: date, as_of: date, cache: dict[str, float] | None = None, force_refresh: bool = False) -> float:
    return _returns._ipca_factor_for_month(month_date=month_date, as_of=as_of, cache=cache, force_refresh=force_refresh)


def apply_savings_value(position: dict, force_refresh: bool = False) -> None:
    return _valuation.apply_savings_value(position=position, force_refresh=force_refresh)


def savings_value_as_of_with_meta(
    position: dict,
    as_of_date: date,
    force_refresh: bool = False,
    factor_cache: dict[str, Decimal] | None = None,
) -> tuple[int, Decimal, str, str]:
    return _valuation.savings_value_as_of_with_meta(position=position, as_of_date=as_of_date, force_refresh=force_refresh, factor_cache=factor_cache)


def savings_value_as_of(
    position: dict,
    as_of_date: date,
    force_refresh: bool = False,
    factor_cache: dict[str, Decimal] | None = None,
) -> int:
    return _valuation.savings_value_as_of(position=position, as_of_date=as_of_date, force_refresh=force_refresh, factor_cache=factor_cache)


def savings_factor_for_anniversary(
    start_date: date,
    end_date: date,
    additional_monthly_rate: Decimal,
    force_refresh: bool = False,
    factor_cache: dict[str, Decimal] | None = None,
) -> Decimal:
    return _valuation.savings_factor_for_anniversary(start_date=start_date, end_date=end_date, additional_monthly_rate=additional_monthly_rate, force_refresh=force_refresh, factor_cache=factor_cache)


def aggregate_savings_anniversaries(entries: list[dict]) -> list[dict]:
    return positions_store.aggregate_savings_anniversaries(entries)


def completed_savings_anniversaries(start_date: date, end_date: date) -> int:
    return _valuation.completed_savings_anniversaries(start_date=start_date, end_date=end_date)


def savings_additional_monthly_rate(force_refresh: bool = False) -> Decimal:
    return _valuation.savings_additional_monthly_rate(force_refresh=force_refresh)


def savings_additional_monthly_rate_from_selic(selic_annual: Decimal) -> Decimal:
    return _valuation.savings_additional_monthly_rate_from_selic(selic_annual=selic_annual)


def savings_quote_label(additional_monthly_rate: Decimal) -> str:
    return _valuation.savings_quote_label(additional_monthly_rate=additional_monthly_rate)


def parse_optional_iso_date(value: object) -> date | None:
    return _valuation.parse_optional_iso_date(value=value)


def compound_annual_factor(rate: Decimal, days: int) -> Decimal:
    return _valuation.compound_annual_factor(rate=rate, days=days)


def fixed_income_quote_label(mode: str, indexer: str, annual_rate: Decimal, rate_factor: Decimal) -> str:
    return _valuation.fixed_income_quote_label(mode=mode, indexer=indexer, annual_rate=annual_rate, rate_factor=rate_factor)


def should_apply_fixed_income_taxes(position: dict) -> bool:
    return _valuation.should_apply_fixed_income_taxes(position=position)


def fallback_indexer_annual_rate(indexer: str) -> Decimal:
    return INDEXER_FALLBACK_ANNUAL_RATES.get(normalize_indexer(indexer), Decimal("0"))


def fixed_income_income_tax_cents(gross_profit_cents: int, days: int) -> int:
    return _valuation.fixed_income_income_tax_cents(gross_profit_cents=gross_profit_cents, days=days)


def fixed_income_custody_fee_cents(position: dict, gross_cents: int, days: int) -> int:
    return _valuation.fixed_income_custody_fee_cents(position=position, gross_cents=gross_cents, days=days)


def is_treasury_direct_position(position: dict) -> bool:
    return _valuation.is_treasury_direct_position(position=position)


def treasury_position_name(position: dict) -> str:
    return _valuation.treasury_position_name(position=position)


def fixed_income_iof_tax_cents(gross_profit_cents: int, days: int) -> int:
    return _valuation.fixed_income_iof_tax_cents(gross_profit_cents=gross_profit_cents, days=days)


def apply_cost_value(position: dict, status: str) -> None:
    return _valuation.apply_cost_value(position=position, status=status)


def fetch_yahoo_quote(symbol: str, force_refresh: bool = False) -> dict:
    url = YAHOO_CHART_URL.format(symbol=quote(symbol))
    payload = cached_json_url(
        url,
        "Nao foi possivel consultar a cotacao do ativo.",
        f"yahoo:{symbol}:5d:1d",
        MARKET_QUOTE_TTL_SECONDS,
        force_refresh=force_refresh,
    )
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


def fetch_crypto_quote(identifier: str, currency: str, force_refresh: bool = False) -> dict:
    normalized_identifier = normalize_asset_identifier(identifier, "crypto")
    normalized_currency = str(currency or "USD").strip().upper()
    coin_id = CRYPTO_COINGECKO_IDS.get(normalized_identifier)
    if not coin_id or normalized_currency not in {"BRL", "USD"}:
        symbol = crypto_yahoo_symbol(normalized_identifier, normalized_currency)
        yahoo_quote = fetch_yahoo_quote(symbol, force_refresh=force_refresh)
        yahoo_quote["source"] = f"Yahoo Finance ({symbol})"
        return yahoo_quote
    vs_currency = normalized_currency.lower()
    url = COINGECKO_SIMPLE_PRICE_URL.format(ids=quote(coin_id), currency=vs_currency)
    try:
        payload = cached_json_url(
            url,
            "Nao foi possivel consultar a cotacao do criptoativo.",
            f"coingecko:{normalized_identifier}:{normalized_currency}",
            MARKET_QUOTE_TTL_SECONDS,
            force_refresh=force_refresh,
        )
        coin_payload = payload[coin_id]
        price = Decimal(str(coin_payload[vs_currency]))
        change_percent = Decimal(str(coin_payload.get(f"{vs_currency}_24h_change") or 0))
        previous_price = price / (Decimal("1") + change_percent / Decimal("100")) if change_percent > Decimal("-100") else price
    except (PortfolioError, KeyError, TypeError, InvalidOperation, ZeroDivisionError):
        symbol = crypto_yahoo_symbol(normalized_identifier, normalized_currency)
        yahoo_quote = fetch_yahoo_quote(symbol, force_refresh=force_refresh)
        yahoo_quote["source"] = f"Yahoo Finance ({symbol}); CoinGecko indisponivel"
        return yahoo_quote
    return {
        "price_cents": decimal_to_cents(price),
        "day_change_cents": decimal_to_cents(price - previous_price),
        "date": date.today().isoformat(),
        "source": f"CoinGecko ({normalized_identifier}/{normalized_currency})",
    }


def fetch_indexer_rate(indexer: str, force_refresh: bool = False) -> Decimal:
    normalized = normalize_indexer(indexer)
    series = INDEXER_SERIES.get(normalized)
    if not series:
        raise PortfolioError("Indexador sem serie automatica")
    payload = cached_json_url(
        BCB_SERIES_URL.format(series=series),
        "Nao foi possivel consultar o indexador.",
        f"bcb:last:{normalized}",
        INDEXER_QUOTE_TTL_SECONDS,
        force_refresh=force_refresh,
    )
    try:
        daily_percent = Decimal(str(payload[-1]["valor"]).replace(",", "."))
    except (IndexError, KeyError, InvalidOperation, TypeError) as exc:
        raise PortfolioError("Indexador indisponivel") from exc
    if normalized in {"CDI", "SELIC"}:
        return ((Decimal("1") + daily_percent / Decimal("100")) ** Decimal("252")) - Decimal("1")
    return daily_percent / Decimal("100")


def fetch_accumulated_indexer_factor(
    indexer: str,
    start_date: date,
    end_date: date,
    multiplier: Decimal = Decimal("1"),
    force_refresh: bool = False,
) -> Decimal:
    normalized = normalize_indexer(indexer)
    series = INDEXER_SERIES.get(normalized)
    if not series:
        raise PortfolioError("Indexador sem serie automatica")
    if end_date < start_date:
        return Decimal("1")
    url = BCB_SERIES_RANGE_URL.format(
        series=series,
        start=format_bcb_date(start_date),
        end=format_bcb_date(end_date),
    )
    payload = cached_json_url(
        url,
        "Nao foi possivel consultar o indexador.",
        f"bcb:range:{normalized}:{start_date.isoformat()}:{end_date.isoformat()}",
        bcb_range_ttl_seconds(end_date),
        force_refresh=force_refresh,
    )
    if not payload:
        latest_rate = fetch_indexer_rate(indexer, force_refresh=force_refresh)
        return compound_annual_factor(latest_rate, max((end_date - start_date).days, 0))
    factor = Decimal("1")
    try:
        for row in payload:
            percent_value = Decimal(str(row["valor"]).replace(",", "."))
            if normalized in MONTHLY_INDEXERS:
                row_date = parse_bcb_row_date(row["data"])
                weight = monthly_overlap_weight(row_date, start_date, end_date)
                if weight <= 0:
                    continue
                weighted_rate = ((Decimal("1") + percent_value / Decimal("100")) ** weight) - Decimal("1")
                factor *= Decimal("1") + weighted_rate * multiplier
            else:
                factor *= Decimal("1") + (percent_value / Decimal("100")) * multiplier
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise PortfolioError("Indexador indisponivel") from exc
    return factor


def parse_bcb_row_date(value: str) -> date:
    day, month, year = str(value).split("/")
    return date(int(year), int(month), int(day))


def monthly_overlap_weight(reference_date: date, start_date: date, end_date: date) -> Decimal:
    month_start = date(reference_date.year, reference_date.month, 1)
    next_month = add_months(month_start, 1)
    month_end = next_month - timedelta(days=1)
    overlap_start = max(month_start, start_date)
    overlap_end = min(month_end, end_date)
    if overlap_end < overlap_start:
        return Decimal("0")
    overlap_days = (overlap_end - overlap_start).days + 1
    month_days = (month_end - month_start).days + 1
    return Decimal(overlap_days) / Decimal(month_days)


def format_bcb_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def bcb_range_ttl_seconds(end_date: date) -> int:
    return quotes.bcb_range_ttl_seconds(end_date, date.today())


def seconds_until_end_of_day() -> int:
    # spec: investimentos/investimentos-portfolio v2.53 — criterios 27 e 28
    # (cache de cotacao de fundos vale ate o fim do dia corrente)
    return quotes.seconds_until_end_of_day(datetime.now())


def cached_json_url(
    url: str,
    message: str,
    cache_key: str,
    ttl_seconds: int,
    force_refresh: bool = False,
    headers: dict | None = None,
) -> dict | list:
    return _quote_cache.cached_json_url(url, message, cache_key, ttl_seconds, force_refresh=force_refresh, headers=headers)


def get_memory_cached_payload(cache_key: str, now: datetime) -> dict | list | None:
    return _quote_cache.get_memory_cached_payload(cache_key, now)


def get_persistent_cached_payload(cache_key: str, now: datetime, allow_stale: bool = False) -> dict | list | None:
    return _quote_cache.get_persistent_cached_payload(cache_key, now, allow_stale=allow_stale)


def store_cached_payload(cache_key: str, payload: dict | list, expires_at: datetime) -> None:
    return _quote_cache.store_cached_payload(cache_key, payload, expires_at)


def set_quote_memory_cache(cache_key: str, expires_at: datetime, payload: dict | list, now: datetime) -> None:
    return _quote_cache.set_quote_memory_cache(cache_key, expires_at, payload, now)


def prune_quote_memory_cache(now: datetime) -> None:
    return _quote_cache.prune_quote_memory_cache(now)


def prune_quote_memory_cache_locked(now: datetime) -> None:
    return _quote_cache.prune_quote_memory_cache_locked(now)


def _trim_cache_to_limit(cache: OrderedDict, max_entries: int) -> None:
    quotes.trim_cache_to_limit(cache, max_entries)


def read_json_url(url: str, message: str, headers: dict | None = None) -> dict | list:
    return quotes.read_json_url(url, message, headers=headers, opener=urlopen, error_type=PortfolioError)


def yahoo_symbol(position: dict) -> str:
    identifier = position["asset_identifier"]
    if not identifier:
        return ""
    if position["asset_type"] in {"crypto", "stablecoin"}:
        return crypto_yahoo_symbol(identifier, position["currency"])
    return quotes.yahoo_symbol(position, YAHOO_SYMBOL_ALIASES)


def crypto_yahoo_symbol(identifier: str, currency: str) -> str:
    normalized_identifier = normalize_asset_identifier(identifier, "crypto")
    normalized_currency = str(currency or "USD").strip().upper()
    currency_pairs = CRYPTO_QUOTE_SYMBOLS.get(normalized_currency)
    if currency_pairs and normalized_identifier in currency_pairs:
        return currency_pairs[normalized_identifier]
    if "-" in identifier:
        return identifier
    return f"{normalized_identifier}-{normalized_currency if normalized_currency in {'BRL', 'USD'} else 'USD'}"


def summarize_positions(positions: list[dict]) -> dict:
    return calculations.summarize_positions(positions)


def format_quoted_position(position: dict) -> dict:
    position = format_position(position)
    position["current_value"] = cents_to_money(position["current_value_cents"])
    position["current_value_brl"] = cents_to_money(position["current_value_brl_cents"])
    position["fixed_income_gross_value"] = cents_to_money(position["fixed_income_gross_value_cents"])
    position["fixed_income_iof_tax"] = cents_to_money(position["fixed_income_iof_tax_cents"])
    position["fixed_income_income_tax"] = cents_to_money(position["fixed_income_income_tax_cents"])
    position["fixed_income_custody_fee"] = cents_to_money(position["fixed_income_custody_fee_cents"])
    position["fixed_income_net_value"] = cents_to_money(position["fixed_income_net_value_cents"])
    position["fixed_income_maturity_date"] = position.get("fixed_income_maturity_date")
    position["apply_tax_estimate"] = bool(position.get("apply_tax_estimate"))
    position["emergency_reserve_eligible"] = bool(position.get("emergency_reserve_eligible"))
    position["day_result"] = cents_to_money(position["day_result_cents"])
    position["day_result_brl"] = cents_to_money(position["day_result_brl_cents"])
    return presentation.decorate_position(position)


def group_positions(positions: list[dict], key: str) -> list[dict]:
    return calculations.group_positions(positions, key)


def portfolio_group_label(position: dict, key: str) -> str:
    return calculations.portfolio_group_label(position, key)


def format_position(position: dict) -> dict:
    average_cents = decimal_to_cents(Decimal(position["total_cost_cents"]) / position["quantity"] / MONEY_SCALE) if position["quantity"] else position["last_unit_price_cents"]
    position["sources"] = format_position_sources(position)
    position["savings_anniversaries"] = format_savings_anniversaries(aggregate_savings_anniversaries(position.get("savings_anniversaries") or []))
    position["quantity"] = decimal_to_string(position["quantity"])
    position["fixed_income_rate"] = format_decimal_percent(position["fixed_income_rate"])
    position["average_price"] = cents_to_money(average_cents)
    position["invested"] = cents_to_money(position["invested_cents"])
    position["costs"] = cents_to_money(position["costs_cents"])
    position["total_cost"] = cents_to_money(position["total_cost_cents"])
    position["total_cost_brl"] = cents_to_money(position["total_cost_brl_cents"])
    return position


def format_position_sources(position: dict) -> list[dict]:
    sources = position.get("sources") or []
    total_cost_cents = int(position.get("total_cost_cents") or 0)
    current_value_cents = int(position.get("current_value_cents") or 0)
    current_value_brl_cents = int(position.get("current_value_brl_cents") or 0)
    formatted = []
    for index, source in enumerate(sources, start=1):
        source_cost_cents = int(source.get("total_cost_cents") or 0)
        if total_cost_cents > 0:
            ratio = Decimal(source_cost_cents) / Decimal(total_cost_cents)
            source_current_value_cents = int((Decimal(current_value_cents) * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            source_current_value_brl_cents = int((Decimal(current_value_brl_cents) * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        else:
            source_current_value_cents = 0
            source_current_value_brl_cents = 0
        quantity = Decimal(source.get("quantity") or 0)
        average_cents = decimal_to_cents(Decimal(source_cost_cents) / quantity / MONEY_SCALE) if quantity else int(source.get("unit_price_cents") or 0)
        formatted.append({
            "source_type": source.get("source_type"),
            "source_id": source.get("source_id"),
            "source_transaction_id": source.get("source_transaction_id"),
            "description": source.get("description") or f"Lancamento {index}",
            "date": source.get("date"),
            "quantity": decimal_to_string(quantity),
            "average_price": cents_to_money(average_cents),
            "invested": cents_to_money(source.get("invested_cents") or 0),
            "costs": cents_to_money(source.get("costs_cents") or 0),
            "total_cost": cents_to_money(source_cost_cents),
            "total_cost_brl": cents_to_money(source.get("total_cost_brl_cents") or 0),
            "current_value": cents_to_money(source_current_value_cents),
            "current_value_brl": cents_to_money(source_current_value_brl_cents),
            "current_value_cents": source_current_value_cents,
            "current_value_brl_cents": source_current_value_brl_cents,
            "emergency_reserve_eligible": bool(source.get("emergency_reserve_eligible")),
            "savings_anniversaries": format_savings_anniversaries(source.get("savings_anniversaries") or []),
        })
    return formatted


def format_savings_anniversaries(entries: list[dict]) -> list[dict]:
    return [
        {
            "date": entry.get("date"),
            "amount": cents_to_money(entry.get("amount_cents") or 0),
            "amount_cents": int(entry.get("amount_cents") or 0),
        }
        for entry in sorted(entries, key=lambda item: str(item.get("date") or ""))
    ]


def indexer_catalog() -> list[dict]:
    return [{"label": label, "automatic": bool(series)} for label, series in INDEXER_SERIES.items()]


def normalize_asset_identifier(value: object, asset_type: str) -> str:
    return calculations.normalize_asset_identifier(value, asset_type)


def effective_asset_type(asset_type: object, identifier: object) -> str:
    return calculations.effective_asset_type(asset_type, identifier)


def normalize_indexer(value: object) -> str:
    return calculations.normalize_indexer(value)


def micros_to_decimal(micros: int) -> Decimal:
    return calculations.micros_to_decimal(micros)


def parse_rate_decimal(value: object) -> Decimal:
    # spec: rentabilidade-portfolio v2.9 — critério 4
    # get_portfolio retorna a taxa ja formatada (ex.: "4,27"); aceita Decimal ou
    # string com ponto/virgula para nao quebrar o calculo de valor por data.
    return calculations.parse_rate_decimal(value)


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


def decimal_to_string(value: Decimal) -> str:
    # spec: investimentos/investimentos-portfolio v2.53 — critério normalização de quantidade
    # com até 2 casas decimais (half-up) para não estourar o layout das tabelas.
    return calculations.decimal_to_string(value)


def format_decimal_percent(value: Decimal) -> str:
    return calculations.format_decimal_percent(value)


def value_to_brl(amount_cents: int, currency: str) -> int:
    normalized_currency = str(currency or "BRL").strip().upper()
    if normalized_currency == "BRL":
        return amount_cents
    rate_micros = portfolio_exchange_rate_micros(normalized_currency)
    return convert_to_brl_cents(amount_cents, rate_micros)


def portfolio_exchange_rate_micros(currency: str) -> int:
    quote_date = previous_business_day(date.today()).isoformat()
    return _quote_cache.exchange_rate_micros(
        currency, quote_date, get_rate=get_exchange_rate_to_brl, to_micros=rate_to_micros,
    )


def previous_business_day(reference_date: date) -> date:
    return quotes.previous_business_day(reference_date)


def percent(delta: int, base: int) -> str:
    return calculations.percent(delta, base)


_valuation = PositionValuation(
    today=lambda: date.today(),
    error_type=PortfolioError,
    fetch_accumulated_indexer_factor=lambda *args, **kwargs: fetch_accumulated_indexer_factor(*args, **kwargs),
    fetch_indexer_rate=lambda *args, **kwargs: fetch_indexer_rate(*args, **kwargs),
    value_to_brl=lambda *args, **kwargs: value_to_brl(*args, **kwargs),
    fallback_indexer_annual_rate=lambda *args, **kwargs: fallback_indexer_annual_rate(*args, **kwargs),
    parse_rate_decimal=lambda *args, **kwargs: parse_rate_decimal(*args, **kwargs),
    format_decimal_percent=lambda *args, **kwargs: format_decimal_percent(*args, **kwargs),
)


_returns = PortfolioReturns(
    today=lambda: date.today(),
    error_type=PortfolioError,
    get_portfolio=lambda *args, **kwargs: get_portfolio(*args, **kwargs),
    _position_value_native_as_of=lambda *args, **kwargs: _position_value_native_as_of(*args, **kwargs),
    fetch_accumulated_indexer_factor=lambda *args, **kwargs: fetch_accumulated_indexer_factor(*args, **kwargs),
    fetch_indexer_rate=lambda *args, **kwargs: fetch_indexer_rate(*args, **kwargs),
    compound_annual_factor=lambda *args, **kwargs: compound_annual_factor(*args, **kwargs),
    list_snapshots=lambda user_id: _list_portfolio_snapshots(user_id),
)
