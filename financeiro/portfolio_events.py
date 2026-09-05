from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import re
from urllib.parse import quote

from financeiro.market_calendar import next_business_day


EVENT_MEMORY_TTL_SECONDS = 24 * 60 * 60
EVENT_CALENDAR_TTL_SECONDS = 24 * 60 * 60
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
B3_EVENTS_URL = (
    "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/"
    "GetListedSupplementCompany/{params}"
)
NASDAQ_DIVIDENDS_URL = "https://api.nasdaq.com/api/quote/{symbol}/dividends?assetclass={asset_class}"
B3_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.b3.com.br",
    "Referer": "https://sistemaswebb3-listados.b3.com.br/",
    "User-Agent": "Mozilla/5.0",
}
NASDAQ_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
    "User-Agent": "Mozilla/5.0",
}


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
    holidays: frozenset[date] | set[date] = frozenset(),
) -> dict:
    # spec: investimentos/investimentos-portfolio v2.61 — critérios 80 a 102
    reference_date = today or date.today()
    month_start = reference_date.replace(day=1)
    window_end = _add_months(month_start, 3) - timedelta(days=1)
    requested_start = min(start_date, reference_date) if start_date else month_start
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
                holidays=holidays,
            ),
            assets,
        )
        for asset_events, failure in results:
            events.extend(asset_events)
            if failure:
                unavailable.append(failure)

    events.sort(key=lambda item: (item["date"], item["asset_identifier"], item["amount_per_share_micros"] or -1), reverse=True)
    return {"events": events, "unavailable": unavailable, "as_of": reference_date.isoformat()}


def _fetch_asset_events(asset, *, cached_json, cached_calendar, error_type, reference_date, force_refresh, requested_start, window_end, holidays):
    provider_events = _fetch_primary_provider_events(
        asset,
        cached_json=cached_json,
        error_type=error_type,
        reference_date=reference_date,
        force_refresh=force_refresh,
        requested_start=requested_start,
        window_end=window_end,
        holidays=holidays,
    )
    if provider_events:
        return provider_events, None
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


def _fetch_primary_provider_events(asset, *, cached_json, error_type, reference_date, force_refresh, requested_start, window_end, holidays):
    if _is_brazilian_asset(asset):
        company = _b3_issuing_company(asset["asset_identifier"])
        if not company:
            return []
        params = base64.b64encode(json.dumps(
            {"issuingCompany": company, "language": "pt-br"}, separators=(",", ":")
        ).encode("utf-8")).decode("ascii")
        url = B3_EVENTS_URL.format(params=quote(params, safe=""))
        try:
            payload = cached_json(
                url, "Eventos B3 temporariamente indisponiveis.",
                f"b3-events:{company}", EVENT_CALENDAR_TTL_SECONDS,
                force_refresh=force_refresh, headers=B3_HEADERS,
            )
            return parse_b3_events(payload, asset, minimum_date=requested_start, maximum_date=window_end, holidays=holidays)
        except error_type:
            return []

    symbol = str(asset["symbol"]).split(".", 1)[0].upper()
    for asset_class in ("stocks", "etf"):
        url = NASDAQ_DIVIDENDS_URL.format(symbol=quote(symbol, safe=""), asset_class=asset_class)
        try:
            payload = cached_json(
                url, "Eventos Nasdaq temporariamente indisponiveis.",
                f"nasdaq-events:{symbol}:{asset_class}", EVENT_CALENDAR_TTL_SECONDS,
                force_refresh=force_refresh, headers=NASDAQ_HEADERS,
            )
        except error_type:
            continue
        parsed = parse_nasdaq_events(payload, asset, minimum_date=requested_start, maximum_date=window_end)
        if parsed:
            return parsed
    return []


def parse_b3_events(payload: object, asset: dict, *, minimum_date: date, maximum_date: date, holidays=frozenset()) -> list[dict]:
    companies = payload if isinstance(payload, list) else []
    company = companies[0] if companies and isinstance(companies[0], dict) else {}
    cash_dividends = company.get("cashDividends") or []
    stock_dividends = company.get("stockDividends") or []
    cash_dividends = cash_dividends if isinstance(cash_dividends, list) else []
    stock_dividends = stock_dividends if isinstance(stock_dividends, list) else []
    parsed = []
    seen = set()
    for raw in cash_dividends:
        if not isinstance(raw, dict) or not _b3_share_type_matches(asset["asset_identifier"], raw.get("assetIssued")):
            continue
        last_date_prior = _parse_provider_date(raw.get("lastDatePrior"), "%d/%m/%Y")
        event_date = next_business_day(last_date_prior, holidays) if last_date_prior else None
        payment_date = _parse_provider_date(raw.get("paymentDate"), "%d/%m/%Y")
        amount_micros = _decimal_to_micros(raw.get("rate"), decimal_comma=True)
        if not event_date or not (minimum_date <= event_date <= maximum_date):
            continue
        identity = (event_date, payment_date, amount_micros, str(raw.get("label") or ""))
        if identity in seen:
            continue
        seen.add(identity)
        label = _b3_event_label(raw.get("label"))
        parsed.append(_event_record(
            asset, event_date, payment_date, amount_micros,
            event_type="dividend_or_jcp", event_label=label,
            source="B3", confirmation_label="Anunciado · B3",
        ))
    for raw in stock_dividends:
        if not isinstance(raw, dict) or not _b3_share_type_matches(asset["asset_identifier"], raw.get("assetIssued")):
            continue
        last_date_prior = _parse_provider_date(raw.get("lastDatePrior"), "%d/%m/%Y")
        event_date = next_business_day(last_date_prior, holidays) if last_date_prior else None
        if not event_date or not (minimum_date <= event_date <= maximum_date):
            continue
        label = _b3_event_label(raw.get("label"))
        if label not in {"Bonificação", "Desdobramento", "Grupamento"}:
            continue
        identity = (event_date, None, None, label, str(raw.get("assetIssued") or ""))
        if identity in seen:
            continue
        seen.add(identity)
        parsed.append(_event_record(
            asset, event_date, None, None,
            event_type=_b3_corporate_event_type(label), event_label=label,
            source="B3", confirmation_label="Anunciado · B3",
        ))
    return parsed


def parse_nasdaq_events(payload: object, asset: dict, *, minimum_date: date, maximum_date: date) -> list[dict]:
    try:
        rows = payload["data"]["dividends"]["rows"]
    except (KeyError, TypeError):
        return []
    if not isinstance(rows, list):
        return []
    parsed = []
    seen = set()
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        event_date = _parse_provider_date(raw.get("exOrEffDate"), "%m/%d/%Y")
        payment_date = _parse_provider_date(raw.get("paymentDate"), "%m/%d/%Y")
        amount_micros = _decimal_to_micros(raw.get("amount"))
        if not event_date or not (minimum_date <= event_date <= maximum_date):
            continue
        identity = (event_date, payment_date, amount_micros)
        if identity in seen:
            continue
        seen.add(identity)
        parsed.append(_event_record(
            asset, event_date, payment_date, amount_micros,
            event_type="dividend", event_label="Dividendo",
            source="Nasdaq", confirmation_label="Detectado · Nasdaq",
            currency=str(raw.get("currency") or asset.get("currency") or "USD").upper(),
        ))
    return parsed


def _event_record(asset, event_date, payment_date, amount_micros, *, event_type, event_label, source, confirmation_label, currency=None):
    return {
        "date": event_date.isoformat(),
        "payment_date": payment_date.isoformat() if payment_date else None,
        "event_type": event_type,
        "event_label": event_label,
        "asset_identifier": asset["asset_identifier"],
        "asset_name": asset["asset_name"],
        "currency": currency or asset["currency"],
        "portfolio_names": asset.get("portfolio_names", []),
        "amount_per_share_micros": amount_micros,
        "source": source,
        "confirmation_level": "provider_detected",
        "confirmation_label": confirmation_label,
    }


def _is_brazilian_asset(asset: dict) -> bool:
    return str(asset.get("symbol") or "").upper().endswith(".SA")


def _b3_issuing_company(identifier: object) -> str | None:
    match = re.fullmatch(r"([A-Z]{4})\d{1,2}", str(identifier or "").strip().upper())
    return match.group(1) if match else None


def _b3_share_type_matches(identifier: object, isin: object) -> bool:
    text = str(identifier or "").upper()
    isin_text = str(isin or "").upper()
    if text.endswith("3"):
        return "NOR" in isin_text
    if text[-1:] in {"4", "5", "6", "7", "8"}:
        return "NPR" in isin_text
    return True


def _parse_provider_date(value: object, date_format: str) -> date | None:
    text = str(value or "").strip()
    if not text or text.upper() == "N/A" or len(text) > MAX_PROVIDER_NUMBER_LENGTH:
        return None
    try:
        parsed = datetime.strptime(text, date_format).date()
    except ValueError:
        return None
    return parsed if MIN_PROVIDER_DATE <= parsed <= MAX_PROVIDER_DATE else None


def _decimal_to_micros(value: object, *, decimal_comma: bool = False) -> int | None:
    text = str(value or "").strip().replace("$", "").replace(" ", "")
    if decimal_comma:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    if not text or len(text) > MAX_PROVIDER_NUMBER_LENGTH:
        return None
    try:
        amount = Decimal(text)
        micros = int((amount * MICRO_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return None
    return micros if amount.is_finite() and amount > 0 and 0 < micros <= MAX_SAFE_MICROS else None


def _b3_event_label(value: object) -> str:
    normalized = str(value or "").strip().upper()
    if "JRS CAP" in normalized or "JUROS" in normalized:
        return "JCP"
    if "DIVIDENDO" in normalized:
        return "Dividendo"
    if "RENDIMENTO" in normalized:
        return "Rendimento"
    if "BONIF" in normalized:
        return "Bonificação"
    if "DESDOBRAMENTO" in normalized:
        return "Desdobramento"
    if "GRUPAMENTO" in normalized:
        return "Grupamento"
    return "Provento"


def _b3_corporate_event_type(label: str) -> str:
    return {
        "Bonificação": "stock_bonus",
        "Desdobramento": "stock_split",
        "Grupamento": "reverse_stock_split",
    }[label]


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
            "confirmation_label": "Detectado · Yahoo Finance",
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
            "confirmation_label": "Detectado · Yahoo Finance",
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
