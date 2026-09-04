from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import ssl
import time
from threading import Lock
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from financeiro.outbound_json import MAX_QUOTE_JSON_BYTES, OutboundJsonError, read_limited_json

MARKET_QUOTE_TTL_SECONDS = 6 * 60 * 60
INDEXER_QUOTE_TTL_SECONDS = 24 * 60 * 60
QUOTE_MEMORY_CACHE_MAX_ENTRIES = 512
FX_MEMORY_CACHE_MAX_ENTRIES = 128
YAHOO_CALENDAR_TTL_SECONDS = 6 * 60 * 60
YAHOO_CALENDAR_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=calendarEvents&crumb={crumb}"
YAHOO_COOKIE_URL = "https://fc.yahoo.com"
YAHOO_CRUMB_URL = "https://query1.finance.yahoo.com/v1/test/getcrumb"
YAHOO_AUTH_MAX_BYTES = 4 * 1024
YAHOO_SESSION_TTL_SECONDS = 10 * 60
_YAHOO_SESSION = None
_YAHOO_SESSION_EXPIRES = 0.0
_YAHOO_SESSION_LOCK = Lock()


def bcb_range_ttl_seconds(end_date: date, today: date) -> int:
    return 30 * 24 * 60 * 60 if end_date < today else INDEXER_QUOTE_TTL_SECONDS


def seconds_until_end_of_day(now: datetime) -> int:
    end = datetime(now.year, now.month, now.day) + timedelta(days=1)
    return max(1, int((end - now).total_seconds()))


def trim_cache_to_limit(cache: OrderedDict, max_entries: int) -> None:
    while len(cache) > max_entries:
        cache.popitem(last=False)


def previous_business_day(reference_date: date) -> date:
    day = reference_date - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def yahoo_symbol(position: dict, aliases: dict[tuple[str, str], str]) -> str:
    identifier = str(position.get("asset_identifier") or "").strip().upper()
    if not identifier:
        return ""
    currency = str(position.get("currency") or "BRL").strip().upper()
    if (identifier, currency) in aliases:
        return aliases[(identifier, currency)]
    if "." in identifier or currency != "BRL":
        return identifier
    return f"{identifier}.SA" if currency == "BRL" else identifier


class QuoteCache:
    """Owns quote/FX caches; dependencies are injected without importing the facade."""
    # spec: arquitetura-v2/desconcentracao-arquitetura-v2 v2.3 — critérios 15–17

    def __init__(self, *, connection_factory, read_json, error_type, clock=datetime.now,
                 max_entries=QUOTE_MEMORY_CACHE_MAX_ENTRIES, fx_max_entries=FX_MEMORY_CACHE_MAX_ENTRIES):
        self.connection_factory = connection_factory
        self.read_json = read_json
        self.error_type = error_type
        self.clock = clock
        self.memory = OrderedDict()
        self.memory_lock = Lock()
        self.max_entries = max_entries
        self.fx_memory = OrderedDict()
        self.fx_lock = Lock()
        self.fx_max_entries = fx_max_entries

    def cached_json_url(self,
        url: str,
        message: str,
        cache_key: str,
        ttl_seconds: int,
        force_refresh: bool = False,
        headers: dict | None = None,
    ) -> dict | list:
        now = self.clock()
        if not force_refresh:
            memory_payload = self.get_memory_cached_payload(cache_key, now)
            if memory_payload is not None:
                return memory_payload
            persistent_payload = self.get_persistent_cached_payload(cache_key, now)
            if persistent_payload is not None:
                return persistent_payload
        try:
            payload = self.read_json(url, message, headers=headers)
            self.store_cached_payload(cache_key, payload, now + timedelta(seconds=ttl_seconds))
            return payload
        except self.error_type:
            stale_payload = self.get_persistent_cached_payload(cache_key, now, allow_stale=True)
            if stale_payload is not None:
                return stale_payload
            raise

    def cached_loader(self, cache_key: str, message: str, ttl_seconds: int, loader, force_refresh: bool = False):
        now = self.clock()
        if not force_refresh:
            memory_payload = self.get_memory_cached_payload(cache_key, now)
            if memory_payload is not None:
                return memory_payload
            persistent_payload = self.get_persistent_cached_payload(cache_key, now)
            if persistent_payload is not None:
                return persistent_payload
        try:
            payload = loader()
            self.store_cached_payload(cache_key, payload, now + timedelta(seconds=ttl_seconds))
            return payload
        except self.error_type:
            stale_payload = self.get_persistent_cached_payload(cache_key, now, allow_stale=True)
            if stale_payload is not None:
                return stale_payload
            raise


    def get_memory_cached_payload(self, cache_key: str, now: datetime) -> dict | list | None:
        with self.memory_lock:
            self.prune_quote_memory_cache_locked(now)
            cached = self.memory.get(cache_key)
            if not cached:
                return None
            expires_at, payload = cached
            if expires_at > now:
                # Move para o fim para manter política LRU sob pressão de memória.
                self.memory.move_to_end(cache_key)
                return payload
            self.memory.pop(cache_key, None)
            return None


    def get_persistent_cached_payload(self, cache_key: str, now: datetime, allow_stale: bool = False) -> dict | list | None:
        try:
            with self.connection_factory() as conn:
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
        self.set_quote_memory_cache(cache_key, expires_at, payload, now)
        return payload


    def store_cached_payload(self, cache_key: str, payload: dict | list, expires_at: datetime) -> None:
        self.set_quote_memory_cache(cache_key, expires_at, payload, self.clock())
        try:
            with self.connection_factory() as conn:
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


    def set_quote_memory_cache(self, cache_key: str, expires_at: datetime, payload: dict | list, now: datetime) -> None:
        with self.memory_lock:
            self.prune_quote_memory_cache_locked(now)
            self.memory[cache_key] = (expires_at, payload)
            trim_cache_to_limit(self.memory, self.max_entries)


    def prune_quote_memory_cache(self, now: datetime) -> None:
        with self.memory_lock:
            self.prune_quote_memory_cache_locked(now)


    def prune_quote_memory_cache_locked(self, now: datetime) -> None:
        expired_keys = [key for key, (expires_at, _payload) in self.memory.items() if expires_at <= now]
        for key in expired_keys:
            self.memory.pop(key, None)

    def exchange_rate_micros(self, currency, quote_date, *, get_rate, to_micros):
        cache_key = (currency, quote_date)
        with self.fx_lock:
            if cache_key not in self.fx_memory:
                try:
                    self.fx_memory[cache_key] = to_micros(get_rate(currency, quote_date))
                except Exception:
                    self.fx_memory[cache_key] = to_micros(Decimal("1"))
                trim_cache_to_limit(self.fx_memory, self.fx_max_entries)
            else:
                self.fx_memory.move_to_end(cache_key)
            return self.fx_memory[cache_key]


def read_json_url(url: str, message: str, headers: dict | None = None, *, opener=urlopen, error_type) -> dict | list:
    request_headers = {"User-Agent": "SistemaFinanceiro/0.1", **(headers or {})}
    request = Request(url, headers=request_headers)
    try:
        with opener(request, timeout=6) as response:
            return read_limited_json(response, max_bytes=MAX_QUOTE_JSON_BYTES)
    except (HTTPError, URLError, TimeoutError, OutboundJsonError) as exc:
        raise error_type(message) from exc


def read_yahoo_calendar_json(symbol: str, message: str, *, opener=urlopen, error_type) -> dict:
    """Consulta calendarEvents com sessão Yahoo (cookie + crumb) e limite de leitura."""
    try:
        cookie, crumb = _yahoo_session(opener)
        url = YAHOO_CALENDAR_URL.format(symbol=quote(symbol, safe=""), crumb=quote(crumb, safe=""))
        request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Cookie": cookie})
        with _open_yahoo(opener, request) as response:
            payload = read_limited_json(response, max_bytes=MAX_QUOTE_JSON_BYTES)
        return payload if isinstance(payload, dict) else {}
    except (HTTPError, URLError, TimeoutError, OSError, OutboundJsonError, ValueError) as exc:
        raise error_type(message) from exc


def _yahoo_cookie(opener) -> str:
    try:
        response = _open_yahoo(opener, Request(YAHOO_COOKIE_URL, headers={"User-Agent": "Mozilla/5.0"}))
    except HTTPError as exc:
        response = exc
    try:
        headers = getattr(response, "headers", None)
        values = headers.get_all("Set-Cookie") if headers is not None and hasattr(headers, "get_all") else []
        pairs = []
        for value in values or []:
            pair = str(value).split(";", 1)[0].strip()
            if "=" in pair:
                pairs.append(pair)
        if not pairs:
            raise ValueError("Sessão Yahoo sem cookie.")
        return "; ".join(pairs)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


def _yahoo_crumb(cookie: str, opener) -> str:
    request = Request(YAHOO_CRUMB_URL, headers={"User-Agent": "Mozilla/5.0", "Cookie": cookie})
    with _open_yahoo(opener, request) as response:
        body = response.read(YAHOO_AUTH_MAX_BYTES + 1)
    if not isinstance(body, (bytes, bytearray)) or len(body) > YAHOO_AUTH_MAX_BYTES:
        raise ValueError("Credencial Yahoo excede o limite permitido.")
    crumb = bytes(body).decode("utf-8").strip()
    if not crumb or len(crumb) > YAHOO_AUTH_MAX_BYTES or any(char in crumb for char in "\r\n"):
        raise ValueError("Credencial Yahoo inválida.")
    return crumb


def _yahoo_session(opener) -> tuple[str, str]:
    global _YAHOO_SESSION, _YAHOO_SESSION_EXPIRES
    now = time.monotonic()
    with _YAHOO_SESSION_LOCK:
        if _YAHOO_SESSION and now < _YAHOO_SESSION_EXPIRES:
            return _YAHOO_SESSION
        cookie = _yahoo_cookie(opener)
        crumb = _yahoo_crumb(cookie, opener)
        _YAHOO_SESSION = (cookie, crumb)
        _YAHOO_SESSION_EXPIRES = now + YAHOO_SESSION_TTL_SECONDS
        return _YAHOO_SESSION


def _open_yahoo(opener, request):
    try:
        import certifi  # type: ignore

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = ssl.create_default_context()
    return opener(request, timeout=6, context=context)
