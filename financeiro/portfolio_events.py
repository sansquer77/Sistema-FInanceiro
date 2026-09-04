from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import quote


EVENT_MEMORY_TTL_SECONDS = 24 * 60 * 60
EVENT_MAX_WORKERS = 4
MICRO_SCALE = Decimal("1000000")
YAHOO_EVENTS_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1={period1}&period2={period2}&interval=3mo&events=div"
)


def build_event_assets(positions: list[dict], symbol_resolver) -> list[dict]:
    """Deduplica somente posições abertas elegíveis, sem consultar rede."""
    assets: dict[tuple[str, str], dict] = {}
    for position in positions:
        if position.get("asset_type") != "stock":
            continue
        symbol = symbol_resolver(position)
        if not symbol:
            continue
        currency = str(position.get("currency") or "BRL").upper()
        key = (symbol, currency)
        acquired_at = str(position.get("first_operation_date") or date.today().isoformat())
        current = assets.get(key)
        if current and current["acquired_at"] <= acquired_at:
            continue
        assets[key] = {
            "symbol": symbol,
            "asset_identifier": str(position.get("asset_identifier") or symbol),
            "asset_name": str(position.get("asset_name") or position.get("asset_identifier") or symbol),
            "currency": currency,
            "acquired_at": acquired_at,
        }
    return sorted(assets.values(), key=lambda item: (item["asset_identifier"], item["currency"]))


def get_events(
    assets: list[dict],
    *,
    cached_json,
    error_type,
    today: date | None = None,
    force_refresh: bool = False,
) -> dict:
    # spec: investimentos/investimentos-portfolio v2.52 — critérios 80 a 84
    reference_date = today or date.today()
    if not assets:
        return {"events": [], "unavailable": [], "as_of": reference_date.isoformat()}

    events: list[dict] = []
    unavailable: list[dict] = []
    workers = min(EVENT_MAX_WORKERS, len(assets))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = executor.map(
            lambda asset: _fetch_asset_events(
                asset,
                cached_json=cached_json,
                error_type=error_type,
                reference_date=reference_date,
                force_refresh=force_refresh,
            ),
            assets,
        )
        for asset_events, failure in results:
            events.extend(asset_events)
            if failure:
                unavailable.append(failure)

    events.sort(key=lambda item: (item["date"], item["asset_identifier"], item["amount_per_share_micros"]), reverse=True)
    return {"events": events, "unavailable": unavailable, "as_of": reference_date.isoformat()}


def _fetch_asset_events(asset, *, cached_json, error_type, reference_date, force_refresh):
    try:
        start = date.fromisoformat(asset["acquired_at"])
    except (TypeError, ValueError):
        start = reference_date - timedelta(days=365)
    start = min(start, reference_date)
    period1 = int(datetime.combine(start, time.min, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.combine(reference_date + timedelta(days=1), time.min, tzinfo=timezone.utc).timestamp())
    symbol = asset["symbol"]
    url = YAHOO_EVENTS_URL.format(symbol=quote(symbol, safe=""), period1=period1, period2=period2)
    # A mesma chave é sobrescrita após expirar, evitando uma cópia do histórico por dia.
    cache_key = f"yahoo-events:{symbol}:{start.isoformat()}"
    try:
        payload = cached_json(
            url,
            "Eventos temporariamente indisponiveis.",
            cache_key,
            EVENT_MEMORY_TTL_SECONDS,
            force_refresh=force_refresh,
        )
        return parse_yahoo_events(payload, asset), None
    except error_type:
        return [], {
            "asset_identifier": asset["asset_identifier"],
            "asset_name": asset["asset_name"],
            "message": "Eventos indisponíveis no momento.",
        }


def parse_yahoo_events(payload: object, asset: dict) -> list[dict]:
    try:
        result = payload["chart"]["result"][0]
        dividends = (result.get("events") or {}).get("dividends") or {}
    except (KeyError, IndexError, TypeError, AttributeError):
        return []
    parsed = []
    seen = set()
    for raw in dividends.values():
        if not isinstance(raw, dict):
            continue
        try:
            amount = Decimal(str(raw.get("amount")))
            timestamp = int(raw.get("date"))
        except (InvalidOperation, TypeError, ValueError):
            continue
        if not amount.is_finite() or amount <= 0 or timestamp <= 0:
            continue
        amount_micros = int((amount * MICRO_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        event_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
        identity = (event_date, amount_micros)
        if identity in seen:
            continue
        seen.add(identity)
        parsed.append({
            "date": event_date,
            "event_type": "dividend_or_jcp",
            "event_label": "Dividendo/JCP",
            "asset_identifier": asset["asset_identifier"],
            "asset_name": asset["asset_name"],
            "currency": asset["currency"],
            "amount_per_share_micros": amount_micros,
            "source": "Yahoo Finance",
            "confirmation_level": "provider_detected",
            "confirmation_label": "Detectado pelo provedor",
        })
    return parsed
