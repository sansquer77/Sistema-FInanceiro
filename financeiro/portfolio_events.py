from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import quote


EVENT_MEMORY_TTL_SECONDS = 24 * 60 * 60
EVENT_CALENDAR_TTL_SECONDS = 6 * 60 * 60
EVENT_MAX_WORKERS = 4
MICRO_SCALE = Decimal("1000000")
MAX_PROVIDER_NUMBER_LENGTH = 64
MAX_SAFE_MICROS = 9_007_199_254_740_991
MIN_PROVIDER_DATE = date(1970, 1, 1)
MAX_PROVIDER_DATE = date(2100, 1, 1)
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
        portfolio_name = str(position.get("account_name") or "Carteira não informada")
        existing_portfolios = set(current.get("portfolio_names", [])) if current else set()
        if current:
            existing_portfolios.add(portfolio_name)
            current["portfolio_names"] = existing_portfolios
        if current and current["acquired_at"] <= acquired_at:
            continue
        assets[key] = {
            "symbol": symbol,
            "asset_identifier": str(position.get("asset_identifier") or symbol),
            "asset_name": str(position.get("asset_name") or position.get("asset_identifier") or symbol),
            "currency": currency,
            "acquired_at": acquired_at,
            "portfolio_names": existing_portfolios or {portfolio_name},
        }
    result = []
    for item in assets.values():
        item["portfolio_names"] = sorted(item["portfolio_names"])
        result.append(item)
    return sorted(result, key=lambda item: (item["asset_identifier"], item["currency"]))


def get_events(
    assets: list[dict],
    *,
    cached_json,
    cached_calendar=None,
    error_type,
    today: date | None = None,
    force_refresh: bool = False,
    start_date: date | None = None,
) -> dict:
    # spec: investimentos/investimentos-portfolio v2.54 — critérios 80 a 91
    reference_date = today or date.today()
    month_start = reference_date.replace(day=1)
    window_end = _add_months(month_start, 3) - timedelta(days=1)
    requested_start = min(start_date, reference_date) if start_date else reference_date
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
                requested_start=requested_start,
                window_end=window_end,
                cached_calendar=cached_calendar,
            ),
            assets,
        )
        for asset_events, failure in results:
            events.extend(asset_events)
            if failure:
                unavailable.append(failure)

    events.sort(key=lambda item: (item["date"], item["asset_identifier"], item["amount_per_share_micros"]), reverse=True)
    return {"events": events, "unavailable": unavailable, "as_of": reference_date.isoformat()}


def _fetch_asset_events(asset, *, cached_json, cached_calendar, error_type, reference_date, force_refresh, requested_start, window_end):
    if cached_calendar is not None:
        symbol = asset["symbol"]
        cache_key = f"yahoo-calendar:{symbol}:{reference_date.strftime('%Y-%m')}"
        try:
            payload = cached_calendar(symbol, "Eventos temporariamente indisponiveis.", cache_key, EVENT_CALENDAR_TTL_SECONDS, force_refresh=force_refresh)
            return parse_yahoo_calendar_events(payload, asset, minimum_date=requested_start, maximum_date=window_end), None
        except Exception:
            # Provedores externos são opcionais: qualquer falha de transporte,
            # sessão ou payload mantém os demais ativos disponíveis.
            return [], {"asset_identifier": asset["asset_identifier"], "asset_name": asset["asset_name"], "message": "Eventos indisponíveis no momento."}
    try:
        start = date.fromisoformat(asset["acquired_at"])
    except (TypeError, ValueError):
        start = reference_date - timedelta(days=365)
    if requested_start:
        start = max(start, requested_start)
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
        return parse_yahoo_events(payload, asset, minimum_date=start, maximum_date=reference_date), None
    except error_type:
        return [], {
            "asset_identifier": asset["asset_identifier"],
            "asset_name": asset["asset_name"],
            "message": "Eventos indisponíveis no momento.",
        }


def parse_yahoo_events(
    payload: object,
    asset: dict,
    *,
    minimum_date: date | None = None,
    maximum_date: date | None = None,
) -> list[dict]:
    try:
        result = payload["chart"]["result"][0]
        dividends = (result.get("events") or {}).get("dividends") or {}
    except (KeyError, IndexError, TypeError, AttributeError):
        return []
    if not isinstance(dividends, dict):
        return []
    parsed = []
    seen = set()
    for raw in dividends.values():
        if not isinstance(raw, dict):
            continue
        amount_text = str(raw.get("amount"))
        timestamp_text = str(raw.get("date"))
        if len(amount_text) > MAX_PROVIDER_NUMBER_LENGTH or len(timestamp_text) > MAX_PROVIDER_NUMBER_LENGTH:
            continue
        try:
            amount = Decimal(amount_text)
            timestamp = int(timestamp_text)
            event_date_value = datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
            amount_micros = int((amount * MICRO_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except (InvalidOperation, TypeError, ValueError, OverflowError, OSError):
            continue
        if (
            not amount.is_finite()
            or amount <= 0
            or amount_micros <= 0
            or amount_micros > MAX_SAFE_MICROS
            or event_date_value < MIN_PROVIDER_DATE
            or event_date_value > MAX_PROVIDER_DATE
            or (minimum_date and event_date_value < minimum_date)
            or (maximum_date and event_date_value > maximum_date)
        ):
            continue
        event_date = event_date_value.isoformat()
        payment_date = _parse_optional_provider_date(raw.get("paymentDate") or raw.get("payment_date"))
        if payment_date and payment_date < event_date:
            payment_date = None
        identity = (event_date, amount_micros)
        if identity in seen:
            continue
        seen.add(identity)
        parsed.append({
            "date": event_date,
            "payment_date": payment_date,
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


def parse_yahoo_calendar_events(payload: object, asset: dict, *, minimum_date: date, maximum_date: date) -> list[dict]:
    try:
        events = payload["quoteSummary"]["result"][0]["calendarEvents"]
    except (KeyError, IndexError, TypeError, AttributeError):
        return []
    if not isinstance(events, dict):
        return []
    ex_date = _parse_optional_provider_date((events.get("exDividendDate") or {}).get("raw"))
    payment_date = _parse_optional_provider_date((events.get("dividendDate") or {}).get("raw"))
    candidates = [(ex_date, payment_date)] if ex_date else [(payment_date, payment_date)]
    parsed = []
    seen = set()
    for event_date, payment in candidates:
        if not event_date or event_date in seen:
            continue
        seen.add(event_date)
        parsed_date = date.fromisoformat(event_date)
        if not (minimum_date <= parsed_date <= maximum_date):
            continue
        parsed.append({
            "date": event_date,
            "payment_date": payment,
            "event_type": "dividend_or_jcp",
            "event_label": "Dividendo/JCP",
            "asset_identifier": asset["asset_identifier"],
            "asset_name": asset["asset_name"],
            "currency": asset["currency"],
            "portfolio_names": asset.get("portfolio_names", []),
            "amount_per_share_micros": None,
            "source": "Yahoo Finance",
            "confirmation_level": "provider_detected",
            "confirmation_label": "Detectado pelo provedor",
        })
    return parsed


def _add_months(value: date, months: int) -> date:
    index = value.year * 12 + value.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def _parse_optional_provider_date(value: object) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text or len(text) > MAX_PROVIDER_NUMBER_LENGTH:
        return None
    try:
        parsed = date.fromisoformat(text[:10]) if "-" in text else datetime.fromtimestamp(int(text), tz=timezone.utc).date()
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    if parsed < MIN_PROVIDER_DATE or parsed > MAX_PROVIDER_DATE:
        return None
    return parsed.isoformat()
