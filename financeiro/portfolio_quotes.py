from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import ssl
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MARKET_QUOTE_TTL_SECONDS = 6 * 60 * 60
INDEXER_QUOTE_TTL_SECONDS = 24 * 60 * 60
QUOTE_MEMORY_CACHE_MAX_ENTRIES = 512
FX_MEMORY_CACHE_MAX_ENTRIES = 128


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
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        if is_ssl_certificate_error(exc):
            try:
                with opener(request, timeout=6, context=ssl._create_unverified_context()) as response:
                    return json.loads(response.read().decode("utf-8"))
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as retry_exc:
                raise error_type(message) from retry_exc
        raise error_type(message) from exc
    except (HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise error_type(message) from exc


def is_ssl_certificate_error(exc: URLError) -> bool:
    reason = getattr(exc, "reason", None)
    return isinstance(reason, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(reason)
