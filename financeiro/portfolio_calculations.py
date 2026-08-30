from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from financeiro.accounts import cents_to_money

MICRO_SCALE = Decimal("1000000")
CRYPTO_ASSETS = {"BTC", "ETH", "SOL", "USDC", "USDT"}
STABLECOIN_ASSETS = {"USDC", "USDT", "DAI", "FDUSD", "PYUSD", "TUSD", "USDP", "USDE"}
CRYPTO_ALIASES = {"BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL", "USD COIN": "USDC", "TETHER": "USDT"}
CRYPTO_QUOTE_SUFFIXES = ("BRL", "USD", "USDT", "USDC")


def summarize_positions(positions: list[dict]) -> dict:
    total_cost = sum(position["total_cost_brl_cents"] for position in positions)
    current_value = sum(position["current_value_brl_cents"] for position in positions)
    day_result = sum(position["day_result_brl_cents"] for position in positions)
    return {
        "total_cost_brl": cents_to_money(total_cost),
        "current_value_brl": cents_to_money(current_value),
        "result_brl": cents_to_money(current_value - total_cost),
        "result_percent": percent(current_value - total_cost, total_cost),
        "day_result_brl": cents_to_money(day_result),
        "day_result_percent": percent(day_result, current_value - day_result),
        "position_count": len(positions),
        "by_type": group_positions(positions, "asset_type_label"),
        "by_indexer": group_positions(positions, "fixed_income_indexer"),
        "by_currency": group_positions(positions, "currency"),
        "by_account": group_positions(positions, "account_name"),
    }


def group_positions(positions: list[dict], key: str) -> list[dict]:
    totals = defaultdict(lambda: {"label": "", "currency": "BRL", "cost_cents": 0, "current_cents": 0, "day_result_cents": 0, "cost_brl_cents": 0, "current_brl_cents": 0, "day_result_brl_cents": 0, "count": 0})
    for position in positions:
        label = portfolio_group_label(position, key)
        currency = position.get("currency") or "BRL"
        row = totals[(label, currency)]
        row.update({"label": label, "currency": currency})
        for target, source in (("cost_cents", "total_cost_cents"), ("current_cents", "current_value_cents"), ("day_result_cents", "day_result_cents"), ("cost_brl_cents", "total_cost_brl_cents"), ("current_brl_cents", "current_value_brl_cents"), ("day_result_brl_cents", "day_result_brl_cents")):
            row[target] += position[source]
        row["count"] += 1
    return [{
        "label": row["label"], "cost_brl": cents_to_money(row["cost_cents"]),
        "current_brl": cents_to_money(row["current_cents"]),
        "result_brl": cents_to_money(row["current_cents"] - row["cost_cents"]),
        "result_percent": percent(row["current_cents"] - row["cost_cents"], row["cost_cents"]),
        "day_result_brl": cents_to_money(row["day_result_cents"]),
        "day_result_percent": percent(row["day_result_cents"], row["current_cents"] - row["day_result_cents"]),
        "chart_current_brl": cents_to_money(row["current_brl_cents"]), "count": row["count"], "currency": row["currency"],
    } for row in sorted(totals.values(), key=lambda item: item["current_brl_cents"], reverse=True)]


def portfolio_group_label(position: dict, key: str) -> str:
    label = position.get(key)
    if key == "fixed_income_indexer" and position.get("asset_type") == "savings":
        return "Poupança"
    if key == "fixed_income_indexer" and not label and position.get("currency") != "BRL":
        return position.get("currency") or "Nao informado"
    return label or "Nao informado"


def normalize_asset_identifier(value: object, asset_type: str) -> str:
    identifier = str(value or "").strip().upper()
    if asset_type in {"crypto", "stablecoin"}:
        identifier = CRYPTO_ALIASES.get(identifier, identifier)
        compact = identifier.replace("/", "-")
        if "-" in compact:
            base, quote_currency = compact.split("-", 1)
            return base if base and quote_currency in CRYPTO_QUOTE_SUFFIXES else compact
        if identifier in CRYPTO_ASSETS:
            return identifier
        for suffix in CRYPTO_QUOTE_SUFFIXES:
            if identifier.endswith(suffix) and len(identifier) > len(suffix):
                return identifier[:-len(suffix)]
    return identifier


def effective_asset_type(asset_type: object, identifier: object) -> str:
    normalized_type = str(asset_type or "other").strip().lower()
    if normalized_type in {"crypto", "stablecoin"} and normalize_asset_identifier(identifier, "crypto") in STABLECOIN_ASSETS:
        return "stablecoin"
    return normalized_type


def normalize_indexer(value: object) -> str:
    return str(value or "").strip().upper().replace("Í", "I")


def micros_to_decimal(micros: int) -> Decimal:
    return Decimal(int(micros or 0)) / MICRO_SCALE


def parse_rate_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    raw = str(value or "").strip()
    if not raw:
        return Decimal("0")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal("0")


def decimal_to_string(value: Decimal) -> str:
    if not value:
        return "0"
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP).normalize():f}"


def format_decimal_percent(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP).normalize():f}".replace(".", ",")


def percent(delta: int, base: int) -> str:
    if not base:
        return "0.00"
    value = Decimal(delta) / Decimal(base) * Decimal("100")
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
