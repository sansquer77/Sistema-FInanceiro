from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus
import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from financeiro.accounts import cents_to_money, empty_to_none, money_to_cents
from financeiro.database import get_connection, row_to_dict
from financeiro.transactions import convert_to_brl_cents, get_exchange_rate_to_brl, parse_exchange_rate, rate_to_micros

MONEY_SCALE = Decimal("100")
MICRO_SCALE = Decimal("1000000")
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies={currency}&include_24hr_change=true"
BCB_SERIES_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados/ultimos/1?formato=json"
BCB_SERIES_RANGE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados?formato=json&dataInicial={start}&dataFinal={end}"
MARKET_QUOTE_TTL_SECONDS = 6 * 60 * 60
INDEXER_QUOTE_TTL_SECONDS = 24 * 60 * 60
QUOTE_MEMORY_CACHE: dict[str, tuple[datetime, dict | list]] = {}

ASSET_TYPE_LABELS = {
    "stock": "Renda variável",
    "crypto": "Cripto",
    "fund": "Fundos",
    "fixed_income": "Renda fixa",
    "private_pension": "Previdência privada",
    "savings": "Poupança",
    "other": "Outros",
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


class PortfolioError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def get_portfolio(user_id: int, force_refresh: bool = False) -> dict:
    with get_connection() as conn:
        operation_rows_raw = conn.execute(
            """
            SELECT
                investment_operations.*,
                'operation' AS source_type,
                investment_operations.id AS source_id,
                1 AS apply_tax_estimate,
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
                AND (
                    transactions.reconciled_at IS NOT NULL
                    OR (
                        transactions.series_kind = 'single'
                        AND transactions.date <= DATE('now', 'localtime')
                    )
                )
            JOIN checking_accounts
                ON checking_accounts.id = investment_operations.account_id
                AND checking_accounts.user_id = investment_operations.user_id
            WHERE investment_operations.user_id = ?
            ORDER BY transactions.date ASC, investment_operations.id ASC
            """,
            (user_id,),
        ).fetchall()
        opening_rows_raw = conn.execute(
            """
            SELECT
                investment_opening_positions.id,
                'opening' AS source_type,
                investment_opening_positions.id AS source_id,
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
                investment_opening_positions.fixed_income_maturity_date,
                investment_opening_positions.apply_tax_estimate,
                investment_opening_positions.savings_anniversaries_json,
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
        redemption_rows = conn.execute(
            """
            SELECT
                source_type,
                source_id,
                SUM(redeemed_cost_cents) AS redeemed_cost_cents,
                SUM(redeemed_quantity_micros) AS redeemed_quantity_micros
            FROM investment_redemptions
            WHERE user_id = ?
            GROUP BY source_type, source_id
            """,
            (user_id,),
        ).fetchall()
        closed_rows = conn.execute(
            """
            SELECT investment_closed_positions.*, checking_accounts.name AS account_name
            FROM investment_closed_positions
            JOIN checking_accounts
                ON checking_accounts.id = investment_closed_positions.account_id
                AND checking_accounts.user_id = investment_closed_positions.user_id
            WHERE investment_closed_positions.user_id = ?
            ORDER BY investment_closed_positions.closed_at DESC, investment_closed_positions.id DESC
            """,
            (user_id,),
        ).fetchall()

    redemption_totals = {
        (row["source_type"], row["source_id"]): {
            "redeemed_cost_cents": int(row["redeemed_cost_cents"] or 0),
            "redeemed_quantity_micros": int(row["redeemed_quantity_micros"] or 0),
        }
        for row in redemption_rows
    }
    operation_rows = [portfolio_row_with_redemptions(row_to_dict(row), redemption_totals) for row in operation_rows_raw]
    opening_rows = [portfolio_row_with_redemptions(row_to_dict(row), redemption_totals) for row in opening_rows_raw]
    closed_positions = [format_closed_position(row_to_dict(row)) for row in closed_rows]
    rows = filter_closed_portfolio_rows([*operation_rows, *opening_rows], closed_positions)
    rows = sorted(rows, key=lambda row: (row["date"], row["id"]))
    positions = build_positions(rows)
    quote_positions(positions, force_refresh=force_refresh)
    apply_value_overrides(user_id, positions)
    summary = summarize_positions(positions)
    positions = [format_quoted_position(position) for position in positions]
    return {
        "positions": positions,
        "history": closed_positions,
        "summary": summary,
        "indexers": indexer_catalog(),
    }


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
                apply_tax_estimate, savings_anniversaries_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                apply_tax_estimate = ?, savings_anniversaries_json = ?, notes = ?,
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
    selector = normalize_redemption_selector(data)
    redemption_value_cents = money_to_cents(data.get("amount", "0"))
    if redemption_value_cents <= 0:
        raise PortfolioError("Informe o valor do resgate.")
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
        positions = current_portfolio_positions(user_id)
        candidates = [
            position for position in positions
            if matches_redemption_selector(position, selector)
            and position["source_type"] in {"operation", "opening"}
            and int(position["current_value_cents"] or 0) > 0
            and int(position["total_cost_cents"] or 0) > 0
        ]
        candidates.sort(key=lambda position: (position["first_operation_date"], 0 if position["source_type"] == "operation" else 1, position["source_id"] or 0))
        available_cents = sum(int(position["current_value_cents"] or 0) for position in candidates)
        if redemption_value_cents > available_cents:
            raise PortfolioError("Valor de resgate maior que o valor disponivel para este ativo.")
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
        conn.execute(
            """
            UPDATE checking_accounts
            SET current_balance_cents = current_balance_cents + ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (redemption_value_cents, account["id"], user_id),
        )
        remaining_cents = redemption_value_cents
        redemptions = []
        for position in candidates:
            if remaining_cents <= 0:
                break
            current_cents = int(position["current_value_cents"] or 0)
            take_cents = min(remaining_cents, current_cents)
            ratio = Decimal(take_cents) / Decimal(current_cents)
            cost_cents = int((Decimal(position["total_cost_cents"]) * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            quantity_micros = int((Decimal(str(position["quantity"])) * MICRO_SCALE * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if Decimal(str(position["quantity"] or "0")) > 0 else 0
            redemptions.append((
                user_id,
                account["id"],
                cursor.lastrowid,
                position["source_type"],
                position["source_id"],
                take_cents,
                cost_cents,
                quantity_micros,
                redemption_date,
                empty_to_none(data.get("notes")),
            ))
            remaining_cents -= take_cents
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
    return get_portfolio(user_id)


def close_position(user_id: int, data: dict) -> dict:
    selector = normalize_redemption_selector(data)
    closed_at = normalize_date(data.get("date") or date.today().isoformat())
    closing_value_cents = money_to_cents(data.get("closing_value", data.get("current_value", "0")))
    if closing_value_cents < 0:
        raise PortfolioError("Informe um valor final valido.")
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
        positions = current_portfolio_positions(user_id)
        matches = [
            position for position in positions
            if matches_redemption_selector(position, selector)
            and position["first_operation_date"] <= closed_at
        ]
        if not matches:
            raise PortfolioError("Posicao nao encontrada para encerramento.", HTTPStatus.NOT_FOUND)
        position = aggregate_backend_positions(matches)
        exchange_rate_micros = rate_to_micros(Decimal("1"))
        closing_value_brl_cents = convert_to_brl_cents(closing_value_cents, exchange_rate_micros)
        total_cost_brl_cents = int(position["total_cost_brl_cents"] or 0)
        result_brl_cents = closing_value_brl_cents - total_cost_brl_cents
        result_percent_micros = int((Decimal(result_brl_cents) * MICRO_SCALE / Decimal(total_cost_brl_cents)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if total_cost_brl_cents > 0 else 0
        closed_indexer = common_value(matches, "fixed_income_indexer")
        closed_maturity_date = common_value(matches, "fixed_income_maturity_date")
        snapshot = format_quoted_position({**position})
        snapshot["closed_at"] = closed_at
        snapshot["closing_value"] = cents_to_money(closing_value_cents)
        snapshot["closing_value_brl"] = cents_to_money(closing_value_brl_cents)
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
    return get_portfolio(user_id)


def current_portfolio_positions(user_id: int, force_refresh: bool = False) -> list[dict]:
    with get_connection() as conn:
        operation_rows_raw = conn.execute(
            """
            SELECT investment_operations.*, 'operation' AS source_type, investment_operations.id AS source_id,
                1 AS apply_tax_estimate, transactions.date, transactions.description, transactions.amount_cents,
                transactions.exchange_rate_micros, transactions.amount_brl_cents,
                checking_accounts.name AS account_name, checking_accounts.currency AS account_currency
            FROM investment_operations
            JOIN transactions ON transactions.id = investment_operations.transaction_id
                AND transactions.user_id = investment_operations.user_id
                AND transactions.archived_at IS NULL
                AND (
                    transactions.reconciled_at IS NOT NULL
                    OR (
                        transactions.series_kind = 'single'
                        AND transactions.date <= DATE('now', 'localtime')
                    )
                )
            JOIN checking_accounts ON checking_accounts.id = investment_operations.account_id
                AND checking_accounts.user_id = investment_operations.user_id
            WHERE investment_operations.user_id = ?
            """,
            (user_id,),
        ).fetchall()
        opening_rows_raw = conn.execute(
            """
            SELECT investment_opening_positions.id, 'opening' AS source_type,
                investment_opening_positions.id AS source_id, investment_opening_positions.user_id,
                NULL AS transaction_id, investment_opening_positions.account_id,
                investment_opening_positions.asset_type, investment_opening_positions.asset_identifier,
                investment_opening_positions.asset_name, investment_opening_positions.cnpj,
                investment_opening_positions.quantity_micros, investment_opening_positions.unit_price_cents,
                investment_opening_positions.total_cost_cents AS invested_amount_cents,
                0 AS brokerage_fee_cents, 0 AS exchange_fee_cents, 0 AS tax_cents, 0 AS other_costs_cents,
                investment_opening_positions.fixed_income_mode, investment_opening_positions.fixed_income_indexer,
                investment_opening_positions.fixed_income_rate_micros, investment_opening_positions.fixed_income_maturity_date,
                investment_opening_positions.apply_tax_estimate, investment_opening_positions.savings_anniversaries_json,
                investment_opening_positions.acquisition_date AS date,
                'Posicao inicial' AS description, investment_opening_positions.total_cost_cents AS amount_cents,
                investment_opening_positions.exchange_rate_micros, 0 AS amount_brl_cents,
                checking_accounts.name AS account_name, checking_accounts.currency AS account_currency
            FROM investment_opening_positions
            JOIN checking_accounts ON checking_accounts.id = investment_opening_positions.account_id
                AND checking_accounts.user_id = investment_opening_positions.user_id
            WHERE investment_opening_positions.user_id = ?
            """,
            (user_id,),
        ).fetchall()
        redemption_rows = conn.execute(
            """
            SELECT source_type, source_id, SUM(redeemed_cost_cents) AS redeemed_cost_cents,
                SUM(redeemed_quantity_micros) AS redeemed_quantity_micros
            FROM investment_redemptions
            WHERE user_id = ?
            GROUP BY source_type, source_id
            """,
            (user_id,),
        ).fetchall()
        closed_rows = conn.execute(
            "SELECT * FROM investment_closed_positions WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    redemption_totals = {(row["source_type"], row["source_id"]): {"redeemed_cost_cents": int(row["redeemed_cost_cents"] or 0), "redeemed_quantity_micros": int(row["redeemed_quantity_micros"] or 0)} for row in redemption_rows}
    closed_positions = [format_closed_position(row_to_dict(row)) for row in closed_rows]
    rows = [portfolio_row_with_redemptions(row_to_dict(row), redemption_totals) for row in [*operation_rows_raw, *opening_rows_raw]]
    rows = filter_closed_portfolio_rows(rows, closed_positions)
    positions = build_positions(sorted(rows, key=lambda row: (row["date"], row["id"])))
    quote_positions(positions, force_refresh=force_refresh)
    apply_value_overrides(user_id, positions)
    return positions


def filter_closed_portfolio_rows(rows: list[dict], closed_positions: list[dict]) -> list[dict]:
    if not closed_positions:
        return rows
    filtered = []
    for row in rows:
        if any(row_matches_closed_position(row, closed) for closed in closed_positions):
            continue
        filtered.append(row)
    return filtered


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
    return int((Decimal(value or 0) * MICRO_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def common_value(positions: list[dict], key: str) -> str:
    values = {str(position.get(key) or "") for position in positions}
    return values.pop() if len(values) == 1 else ""


def format_closed_position(row: dict) -> dict:
    result_percent = Decimal(int(row["result_percent_micros"] or 0)) / Decimal("10000")
    return {
        "id": row["id"],
        "account_id": row["account_id"],
        "account_name": row.get("account_name") or "",
        "currency": row["currency"],
        "asset_type": row["asset_type"],
        "asset_type_label": ASSET_TYPE_LABELS.get(row["asset_type"], "Outros"),
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
        "fixed_income_maturity_date": normalize_optional_date(data.get("fixed_income_maturity_date")),
        "apply_tax_estimate": 1 if str(data.get("apply_tax_estimate") or "").strip().lower() in {"1", "true", "on", "yes"} else 0,
        "savings_anniversaries_json": serialize_savings_anniversaries(savings_anniversaries),
        "notes": empty_to_none(data.get("notes")),
    }


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


def apply_value_overrides(user_id: int, positions: list[dict]) -> None:
    if not positions:
        return
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
    return (
        int(row["account_id"]),
        str(row.get("asset_type") or "other").strip().lower(),
        normalize_asset_identifier(row.get("asset_identifier"), row.get("asset_type")),
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
    return rate_to_micros(Decimal("1"))


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


def normalize_optional_date(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
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
        key = portfolio_position_key(row, asset_type, identifier)
        position = grouped.setdefault(key, empty_position(row, asset_type, identifier))
        original_quantity_micros = int(row["quantity_micros"] or 0)
        redeemed_quantity_micros = min(int(row.get("redeemed_quantity_micros") or 0), original_quantity_micros)
        quantity = micros_to_decimal(max(original_quantity_micros - redeemed_quantity_micros, 0))
        invested_cents = int(row["invested_amount_cents"] or row["amount_cents"] or 0)
        costs_cents = sum(int(row[field] or 0) for field in (
            "brokerage_fee_cents",
            "exchange_fee_cents",
            "tax_cents",
            "other_costs_cents",
        ))
        original_total_cost_cents = invested_cents + costs_cents
        redeemed_cost_cents = min(int(row.get("redeemed_cost_cents") or 0), original_total_cost_cents)
        total_cost_cents = max(original_total_cost_cents - redeemed_cost_cents, 0)
        if original_total_cost_cents > 0 and redeemed_cost_cents > 0:
            invested_cents = int((Decimal(invested_cents) * Decimal(total_cost_cents) / Decimal(original_total_cost_cents)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            costs_cents = total_cost_cents - invested_cents
        if total_cost_cents <= 0 and quantity <= 0:
            continue
        source_savings_anniversaries = parse_savings_anniversaries(
            row.get("savings_anniversaries_json"),
            row["date"],
            total_cost_cents,
        ) if asset_type == "savings" else []
        position["quantity"] += quantity
        position["invested_cents"] += invested_cents
        position["costs_cents"] += costs_cents
        position["total_cost_cents"] += total_cost_cents
        position["total_cost_brl_cents"] += convert_to_brl_cents(total_cost_cents, int(row["exchange_rate_micros"] or 1000000))
        position["savings_anniversaries"].extend(source_savings_anniversaries)
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


def quote_positions(positions: list[dict], force_refresh: bool = False) -> None:
    for position in positions:
        if position["asset_type"] in {"stock", "crypto"}:
            apply_market_quote(position, force_refresh=force_refresh)
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
        if position["asset_type"] == "crypto":
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


def apply_fixed_income_value(position: dict, force_refresh: bool = False) -> None:
    start_date = date.fromisoformat(position["first_operation_date"])
    maturity_date = parse_optional_iso_date(position.get("fixed_income_maturity_date"))
    end_date = min(date.today(), maturity_date) if maturity_date else date.today()
    days = max((end_date - start_date).days, 0)
    annual_rate = Decimal(str(position["fixed_income_rate"] or "0"))
    mode = position["fixed_income_mode"] or "post"
    indexer = position["fixed_income_indexer"] or "CDI"
    rate_factor = Decimal("0")
    gross_factor = Decimal("1")
    status = "ok"
    source = "Taxa cadastrada"
    fallback_source = ""
    try:
        if mode == "pre":
            rate_factor = annual_rate / Decimal("100")
            gross_factor = compound_annual_factor(rate_factor, days)
        else:
            multiplier = annual_rate / Decimal("100") if annual_rate else Decimal("1")
            indexer_factor = fetch_accumulated_indexer_factor(indexer, start_date, end_date, multiplier, force_refresh=force_refresh)
            source = f"Banco Central SGS ({indexer} acumulado)"
            if mode == "hybrid":
                indexer_factor = fetch_accumulated_indexer_factor(indexer, start_date, end_date, force_refresh=force_refresh)
                rate_factor = indexer_factor - Decimal("1") + annual_rate / Decimal("100")
                gross_factor = indexer_factor * compound_annual_factor(annual_rate / Decimal("100"), days)
            else:
                rate_factor = indexer_factor - Decimal("1")
                gross_factor = indexer_factor
    except PortfolioError as exc:
        if mode == "pre":
            status = exc.message
            rate_factor = annual_rate / Decimal("100")
            gross_factor = compound_annual_factor(rate_factor, days)
        else:
            fallback_indexer_rate = fallback_indexer_annual_rate(indexer)
            multiplier = annual_rate / Decimal("100") if annual_rate else Decimal("1")
            fallback_indexer_factor = compound_annual_factor(fallback_indexer_rate * multiplier, days)
            fallback_source = f"Estimativa local ({indexer}); Banco Central indisponivel"
            status = "ok"
            if mode == "hybrid":
                fallback_indexer_factor = compound_annual_factor(fallback_indexer_rate, days)
                rate_factor = fallback_indexer_factor - Decimal("1") + annual_rate / Decimal("100")
                gross_factor = fallback_indexer_factor * compound_annual_factor(annual_rate / Decimal("100"), days)
            else:
                rate_factor = fallback_indexer_factor - Decimal("1")
                gross_factor = fallback_indexer_factor
    gross = Decimal(position["total_cost_cents"]) * gross_factor
    gross_cents = int(gross.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    iof_tax_cents = 0
    income_tax_cents = 0
    net_cents = gross_cents
    if should_apply_fixed_income_taxes(position):
        gross_profit_cents = max(gross_cents - position["total_cost_cents"], 0)
        iof_tax_cents = fixed_income_iof_tax_cents(gross_profit_cents, days)
        income_tax_cents = fixed_income_income_tax_cents(max(gross_profit_cents - iof_tax_cents, 0), days)
        net_cents = max(gross_cents - iof_tax_cents - income_tax_cents, 0)
    position["quote"] = fixed_income_quote_label(mode, indexer, annual_rate, rate_factor)
    position["quote_source"] = fallback_source or source
    position["quote_status"] = status
    position["quote_date"] = date.today().isoformat()
    position["current_value_cents"] = net_cents
    position["current_value_brl_cents"] = value_to_brl(position["current_value_cents"], position["currency"])
    position["fixed_income_gross_value_cents"] = gross_cents
    position["fixed_income_iof_tax_cents"] = iof_tax_cents
    position["fixed_income_income_tax_cents"] = income_tax_cents
    position["fixed_income_net_value_cents"] = net_cents
    position["day_result_cents"] = 0
    position["day_result_brl_cents"] = 0


def apply_savings_value(position: dict, force_refresh: bool = False) -> None:
    today = date.today()
    anniversaries = aggregate_savings_anniversaries(position.get("savings_anniversaries") or [])
    if not anniversaries:
        anniversaries = [{"date": position["first_operation_date"], "amount_cents": position["total_cost_cents"]}]
    current_value = Decimal("0")
    status = "ok"
    source = "Banco Central SGS (TR/SELIC); aniversarios mensais"
    try:
        additional_monthly_rate = savings_additional_monthly_rate(force_refresh=force_refresh)
        for anniversary in anniversaries:
            start_date = parse_optional_iso_date(anniversary.get("date"))
            amount_cents = int(anniversary.get("amount_cents") or 0)
            if not start_date or amount_cents <= 0:
                continue
            current_value += Decimal(amount_cents) * savings_factor_for_anniversary(
                start_date,
                today,
                additional_monthly_rate,
                force_refresh=force_refresh,
            )
    except PortfolioError as exc:
        status = exc.message
        source = "Estimativa local; Banco Central indisponivel"
        fallback_rate = fallback_indexer_annual_rate("SELIC")
        additional_monthly_rate = savings_additional_monthly_rate_from_selic(fallback_rate)
        for anniversary in anniversaries:
            start_date = parse_optional_iso_date(anniversary.get("date"))
            amount_cents = int(anniversary.get("amount_cents") or 0)
            if not start_date or amount_cents <= 0:
                continue
            completed_months = completed_savings_anniversaries(start_date, today)
            current_value += Decimal(amount_cents) * ((Decimal("1") + additional_monthly_rate) ** completed_months)
    current_cents = int(current_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    position["quote"] = savings_quote_label(additional_monthly_rate)
    position["quote_source"] = source
    position["quote_status"] = status
    position["quote_date"] = today.isoformat()
    position["current_value_cents"] = current_cents
    position["current_value_brl_cents"] = value_to_brl(current_cents, position["currency"])
    position["fixed_income_gross_value_cents"] = current_cents
    position["fixed_income_iof_tax_cents"] = 0
    position["fixed_income_income_tax_cents"] = 0
    position["fixed_income_net_value_cents"] = current_cents
    position["day_result_cents"] = 0
    position["day_result_brl_cents"] = 0


def savings_factor_for_anniversary(
    start_date: date,
    end_date: date,
    additional_monthly_rate: Decimal,
    force_refresh: bool = False,
) -> Decimal:
    factor = Decimal("1")
    completed_months = completed_savings_anniversaries(start_date, end_date)
    for month_index in range(1, completed_months + 1):
        period_start = add_months(start_date, month_index - 1)
        period_end = add_months(start_date, month_index)
        tr_factor = fetch_accumulated_indexer_factor("TR", period_start, period_end, force_refresh=force_refresh)
        factor *= tr_factor * (Decimal("1") + additional_monthly_rate)
    return factor


def aggregate_savings_anniversaries(entries: list[dict]) -> list[dict]:
    totals: dict[str, int] = {}
    for entry in entries:
        anniversary_date = str(entry.get("date") or "").strip()
        if not parse_optional_iso_date(anniversary_date):
            continue
        totals[anniversary_date] = totals.get(anniversary_date, 0) + int(entry.get("amount_cents") or 0)
    return [
        {"date": anniversary_date, "amount_cents": amount_cents}
        for anniversary_date, amount_cents in sorted(totals.items())
        if amount_cents > 0
    ]


def completed_savings_anniversaries(start_date: date, end_date: date) -> int:
    if end_date < add_months(start_date, 1):
        return 0
    completed = 0
    while add_months(start_date, completed + 1) <= end_date:
        completed += 1
    return completed


def savings_additional_monthly_rate(force_refresh: bool = False) -> Decimal:
    selic_annual = fetch_indexer_rate("SELIC", force_refresh=force_refresh)
    return savings_additional_monthly_rate_from_selic(selic_annual)


def savings_additional_monthly_rate_from_selic(selic_annual: Decimal) -> Decimal:
    if selic_annual > Decimal("0.085"):
        return Decimal("0.005")
    return (Decimal("1") + selic_annual * Decimal("0.70")) ** (Decimal("1") / Decimal("12")) - Decimal("1")


def savings_quote_label(additional_monthly_rate: Decimal) -> str:
    return f"TR + {format_decimal_percent(additional_monthly_rate * Decimal('100'))}% a.m."


def parse_optional_iso_date(value: object) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def compound_annual_factor(rate: Decimal, days: int) -> Decimal:
    if not rate or days <= 0:
        return Decimal("1")
    return (Decimal("1") + rate) ** (Decimal(days) / Decimal("365"))


def fixed_income_quote_label(mode: str, indexer: str, annual_rate: Decimal, rate_factor: Decimal) -> str:
    if mode == "pre":
        return f"{format_decimal_percent(annual_rate)}% a.a."
    if mode == "hybrid":
        return f"{indexer} + {format_decimal_percent(annual_rate)}% a.a."
    if annual_rate:
        return f"{format_decimal_percent(annual_rate)}% do {indexer}"
    return f"{format_decimal_percent(rate_factor * Decimal('100'))}% acumulado"


def should_apply_fixed_income_taxes(position: dict) -> bool:
    return position["source_type"] == "operation" or (
        position["source_type"] == "opening" and bool(position.get("apply_tax_estimate"))
    )


def fallback_indexer_annual_rate(indexer: str) -> Decimal:
    return INDEXER_FALLBACK_ANNUAL_RATES.get(normalize_indexer(indexer), Decimal("0"))


def fixed_income_income_tax_cents(gross_profit_cents: int, days: int) -> int:
    if gross_profit_cents <= 0:
        return 0
    if days <= 180:
        tax_rate = Decimal("0.225")
    elif days <= 360:
        tax_rate = Decimal("0.20")
    elif days <= 720:
        tax_rate = Decimal("0.175")
    else:
        tax_rate = Decimal("0.15")
    return int((Decimal(gross_profit_cents) * tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fixed_income_iof_tax_cents(gross_profit_cents: int, days: int) -> int:
    if gross_profit_cents <= 0 or days >= 30:
        return 0
    daily_rates = {
        0: Decimal("1"),
        1: Decimal("0.96"),
        2: Decimal("0.93"),
        3: Decimal("0.90"),
        4: Decimal("0.86"),
        5: Decimal("0.83"),
        6: Decimal("0.80"),
        7: Decimal("0.76"),
        8: Decimal("0.73"),
        9: Decimal("0.70"),
        10: Decimal("0.66"),
        11: Decimal("0.63"),
        12: Decimal("0.60"),
        13: Decimal("0.56"),
        14: Decimal("0.53"),
        15: Decimal("0.50"),
        16: Decimal("0.46"),
        17: Decimal("0.43"),
        18: Decimal("0.40"),
        19: Decimal("0.36"),
        20: Decimal("0.33"),
        21: Decimal("0.30"),
        22: Decimal("0.26"),
        23: Decimal("0.23"),
        24: Decimal("0.20"),
        25: Decimal("0.16"),
        26: Decimal("0.13"),
        27: Decimal("0.10"),
        28: Decimal("0.06"),
        29: Decimal("0.03"),
    }
    tax_rate = daily_rates.get(max(days, 0), Decimal("0"))
    return int((Decimal(gross_profit_cents) * tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def apply_cost_value(position: dict, status: str) -> None:
    position["current_value_cents"] = position["total_cost_cents"]
    position["current_value_brl_cents"] = position["total_cost_brl_cents"]
    position["day_result_cents"] = 0
    position["day_result_brl_cents"] = 0
    position["quote_status"] = status


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


def format_bcb_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def bcb_range_ttl_seconds(end_date: date) -> int:
    if end_date < date.today():
        return 30 * 24 * 60 * 60
    return INDEXER_QUOTE_TTL_SECONDS


def cached_json_url(
    url: str,
    message: str,
    cache_key: str,
    ttl_seconds: int,
    force_refresh: bool = False,
) -> dict | list:
    now = datetime.now()
    if not force_refresh:
        memory_payload = get_memory_cached_payload(cache_key, now)
        if memory_payload is not None:
            return memory_payload
        persistent_payload = get_persistent_cached_payload(cache_key, now)
        if persistent_payload is not None:
            return persistent_payload
    try:
        payload = read_json_url(url, message)
        store_cached_payload(cache_key, payload, now + timedelta(seconds=ttl_seconds))
        return payload
    except PortfolioError:
        stale_payload = get_persistent_cached_payload(cache_key, now, allow_stale=True)
        if stale_payload is not None:
            return stale_payload
        raise


def get_memory_cached_payload(cache_key: str, now: datetime) -> dict | list | None:
    cached = QUOTE_MEMORY_CACHE.get(cache_key)
    if not cached:
        return None
    expires_at, payload = cached
    if expires_at > now:
        return payload
    QUOTE_MEMORY_CACHE.pop(cache_key, None)
    return None


def get_persistent_cached_payload(cache_key: str, now: datetime, allow_stale: bool = False) -> dict | list | None:
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT payload_json, expires_at FROM quote_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    try:
        expires_at = datetime.fromisoformat(row["expires_at"])
        payload = json.loads(row["payload_json"])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not allow_stale and expires_at <= now:
        return None
    QUOTE_MEMORY_CACHE[cache_key] = (expires_at, payload)
    return payload


def store_cached_payload(cache_key: str, payload: dict | list, expires_at: datetime) -> None:
    QUOTE_MEMORY_CACHE[cache_key] = (expires_at, payload)
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO quote_cache (cache_key, payload_json, expires_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    expires_at = excluded.expires_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (cache_key, json.dumps(payload, ensure_ascii=True), expires_at.isoformat()),
            )
    except Exception:
        return


def read_json_url(url: str, message: str) -> dict | list:
    request = Request(url, headers={"User-Agent": "SistemaFinanceiro/0.1"})
    try:
        with urlopen(request, timeout=6) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        if is_ssl_certificate_error(exc):
            try:
                with urlopen(request, timeout=6, context=ssl._create_unverified_context()) as response:
                    return json.loads(response.read().decode("utf-8"))
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as retry_exc:
                raise PortfolioError(message) from retry_exc
        raise PortfolioError(message) from exc
    except (HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise PortfolioError(message) from exc


def is_ssl_certificate_error(exc: URLError) -> bool:
    reason = getattr(exc, "reason", None)
    return isinstance(reason, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(reason)


def yahoo_symbol(position: dict) -> str:
    identifier = position["asset_identifier"]
    if not identifier:
        return ""
    if position["asset_type"] == "crypto":
        return crypto_yahoo_symbol(identifier, position["currency"])
    if "." in identifier or position["currency"] != "BRL":
        return identifier
    return f"{identifier}.SA"


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
    total_cost = sum(position["total_cost_brl_cents"] for position in positions)
    current_value = sum(position["current_value_brl_cents"] for position in positions)
    day_result = sum(position["day_result_brl_cents"] for position in positions)
    by_type = group_positions(positions, "asset_type_label")
    by_indexer = group_positions(positions, "fixed_income_indexer")
    by_currency = group_positions(positions, "currency")
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
        "by_account": by_account,
    }


def format_quoted_position(position: dict) -> dict:
    position = format_position(position)
    position["current_value"] = cents_to_money(position["current_value_cents"])
    position["current_value_brl"] = cents_to_money(position["current_value_brl_cents"])
    position["fixed_income_gross_value"] = cents_to_money(position["fixed_income_gross_value_cents"])
    position["fixed_income_iof_tax"] = cents_to_money(position["fixed_income_iof_tax_cents"])
    position["fixed_income_income_tax"] = cents_to_money(position["fixed_income_income_tax_cents"])
    position["fixed_income_net_value"] = cents_to_money(position["fixed_income_net_value_cents"])
    position["fixed_income_maturity_date"] = position.get("fixed_income_maturity_date")
    position["apply_tax_estimate"] = bool(position.get("apply_tax_estimate"))
    position["day_result"] = cents_to_money(position["day_result_cents"])
    position["day_result_brl"] = cents_to_money(position["day_result_brl_cents"])
    return position


def group_positions(positions: list[dict], key: str) -> list[dict]:
    totals = defaultdict(lambda: {"label": "", "currency": "BRL", "cost_brl_cents": 0, "current_brl_cents": 0, "day_result_brl_cents": 0, "count": 0})
    for position in positions:
        label = portfolio_group_label(position, key)
        currency = position.get("currency") or "BRL"
        row = totals[(label, currency)]
        row["label"] = label
        row["currency"] = currency
        row["cost_brl_cents"] += position["total_cost_brl_cents"]
        row["current_brl_cents"] += position["current_value_brl_cents"]
        row["day_result_brl_cents"] += position["day_result_brl_cents"]
        row["count"] += 1
    return [
        {
            "label": row["label"],
            "cost_brl": cents_to_money(row["cost_brl_cents"]),
            "current_brl": cents_to_money(row["current_brl_cents"]),
            "result_brl": cents_to_money(row["current_brl_cents"] - row["cost_brl_cents"]),
            "result_percent": percent(row["current_brl_cents"] - row["cost_brl_cents"], row["cost_brl_cents"]),
            "day_result_brl": cents_to_money(row["day_result_brl_cents"]),
            "day_result_percent": percent(row["day_result_brl_cents"], row["current_brl_cents"] - row["day_result_brl_cents"]),
            "count": row["count"],
            "currency": row["currency"],
        }
        for row in sorted(totals.values(), key=lambda item: item["current_brl_cents"], reverse=True)
    ]


def portfolio_group_label(position: dict, key: str) -> str:
    label = position.get(key)
    if key == "fixed_income_indexer" and position.get("asset_type") == "savings":
        return "Poupança"
    if key == "fixed_income_indexer" and not label and position.get("currency") != "BRL":
        return position.get("currency") or "Nao informado"
    return label or "Nao informado"


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
    identifier = str(value or "").strip().upper()
    if asset_type == "crypto":
        identifier = CRYPTO_ALIASES.get(identifier, identifier)
        compact = identifier.replace("/", "-")
        if "-" in compact:
            base, quote_currency = compact.split("-", 1)
            if base and quote_currency in CRYPTO_QUOTE_SUFFIXES:
                return base
            return compact
        if identifier in CRYPTO_ASSETS:
            return identifier
        for suffix in CRYPTO_QUOTE_SUFFIXES:
            if identifier.endswith(suffix) and len(identifier) > len(suffix):
                return identifier[:-len(suffix)]
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
    return amount_cents


def percent(delta: int, base: int) -> str:
    if not base:
        return "0.00"
    value = Decimal(delta) / Decimal(base) * Decimal("100")
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
