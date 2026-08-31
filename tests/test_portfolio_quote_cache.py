from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock
from urllib.error import URLError

from financeiro import portfolio, portfolio_quotes as quotes


class QuoteCacheTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "quotes.db"
        self.open_connections = 0
        self.now = datetime(2026, 8, 31, 12)

        @contextmanager
        def connection():
            conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            self.open_connections += 1
            try:
                with conn:
                    yield conn
            finally:
                conn.close()
                self.open_connections -= 1

        self.connection = connection
        with connection() as conn:
            conn.execute("CREATE TABLE quote_cache (cache_key TEXT PRIMARY KEY, payload_json TEXT, expires_at TEXT, updated_at TEXT)")

        def read(*args, **kwargs):
            self.assertEqual(self.open_connections, 0)
            return {"price": 7}

        self.read = Mock(side_effect=read)
        self.cache = quotes.QuoteCache(connection_factory=connection, read_json=self.read,
            error_type=portfolio.PortfolioError, clock=lambda: self.now, max_entries=2, fx_max_entries=2)

    def fetch(self, **kwargs):
        return self.cache.cached_json_url("https://example.invalid", "indisponivel", "asset", 60, **kwargs)

    def test_cold_memory_persistent_and_forced_refresh(self):
        self.assertEqual(self.fetch(), {"price": 7})
        self.assertEqual(self.fetch(), {"price": 7})
        self.cache.memory.clear()
        self.assertEqual(self.fetch(), {"price": 7})
        self.assertEqual(self.read.call_count, 1)
        self.fetch(force_refresh=True, headers={"X-Api-Key": "test-only"})
        self.assertEqual(self.read.call_count, 2)
        self.assertEqual(self.read.call_args.kwargs["headers"], {"X-Api-Key": "test-only"})

    def test_expired_cache_fallback_and_no_fallback_failure(self):
        self.fetch()
        self.now += timedelta(seconds=61)
        self.read.side_effect = portfolio.PortfolioError("offline")
        self.assertEqual(self.fetch(force_refresh=True), {"price": 7})
        self.assertIsNone(self.cache.get_memory_cached_payload("asset", self.now))
        with self.connection() as conn:
            conn.execute("DELETE FROM quote_cache")
        with self.assertRaisesRegex(portfolio.PortfolioError, "offline"):
            self.fetch()

    def test_invalid_persistence_and_storage_failure_are_tolerated(self):
        with self.connection() as conn:
            conn.execute("INSERT INTO quote_cache VALUES ('asset', 'not-json', 'bad-date', '')")
        self.assertEqual(self.fetch(), {"price": 7})
        self.cache.memory.clear()
        self.cache.connection_factory = Mock(side_effect=sqlite3.OperationalError("unavailable"))
        self.assertEqual(self.fetch(), {"price": 7})
        self.assertEqual(self.cache.get_memory_cached_payload("asset", self.now), {"price": 7})

    def test_memory_expiration_lru_and_limits(self):
        for key in ("a", "b"):
            self.cache.set_quote_memory_cache(key, self.now + timedelta(seconds=60), {"key": key}, self.now)
        self.cache.get_memory_cached_payload("a", self.now)
        self.cache.set_quote_memory_cache("c", self.now + timedelta(seconds=60), {}, self.now)
        self.assertEqual(list(self.cache.memory), ["a", "c"])
        self.cache.prune_quote_memory_cache(self.now + timedelta(seconds=60))
        self.assertEqual(len(self.cache.memory), 0)

    def test_fx_cache_and_fallback_preserve_policy(self):
        rate = Mock(return_value=Decimal("5"))
        def fetch(currency):
            return self.cache.exchange_rate_micros(currency, "2026-08-28", get_rate=rate, to_micros=lambda value: int(value * 1000000))
        self.assertEqual(fetch("USD"), 5000000)
        fetch("USD")
        self.assertEqual(rate.call_count, 1)
        fetch("EUR")
        fetch("USD")
        rate.side_effect = ValueError("offline")
        self.assertEqual(fetch("GBP"), 1000000)
        self.assertEqual(list(self.cache.fx_memory), [("USD", "2026-08-28"), ("GBP", "2026-08-28")])

    def test_transport_headers_timeout_and_public_error(self):
        opener = Mock(return_value=io.BytesIO(b'{"ok": true}'))
        result = quotes.read_json_url("https://example.invalid", "indisponivel", {"X-Api-Key": "test-only"}, opener=opener, error_type=portfolio.PortfolioError)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(opener.call_args.kwargs, {"timeout": 6})
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("X-api-key"), "test-only")
        for error in (URLError("offline"), TimeoutError()):
            opener.side_effect = error
            with self.assertRaisesRegex(portfolio.PortfolioError, "indisponivel"):
                quotes.read_json_url("https://example.invalid", "indisponivel", opener=opener, error_type=portfolio.PortfolioError)

    def test_public_cache_objects_alias_owned_state(self):
        self.assertIs(portfolio.QUOTE_MEMORY_CACHE, portfolio._quote_cache.memory)
        self.assertIs(portfolio.FX_MEMORY_CACHE, portfolio._quote_cache.fx_memory)
        self.assertIs(portfolio.QUOTE_MEMORY_CACHE_LOCK, portfolio._quote_cache.memory_lock)
        self.assertIs(portfolio.FX_MEMORY_CACHE_LOCK, portfolio._quote_cache.fx_lock)

    def test_ttls_remain_compatible(self):
        self.assertEqual(quotes.seconds_until_end_of_day(self.now), 43200)
        self.assertEqual(quotes.seconds_until_end_of_day(self.now.replace(hour=23, minute=59, second=59)), 1)
        self.assertEqual(quotes.bcb_range_ttl_seconds(self.now.date(), self.now.date()), 86400)
        self.assertEqual(quotes.bcb_range_ttl_seconds((self.now - timedelta(days=1)).date(), self.now.date()), 30 * 86400)

    def test_invalid_json_raises_public_error_and_corrupt_payload_is_a_cache_miss(self):
        with self.connection() as conn:
            conn.execute("INSERT INTO quote_cache VALUES ('asset', 'not-json', ?, '')",
                         ((self.now + timedelta(hours=1)).isoformat(),))
        self.assertEqual(self.fetch(), {"price": 7})
        with self.assertRaisesRegex(portfolio.PortfolioError, "indisponivel"):
            quotes.read_json_url("https://example.invalid", "indisponivel",
                opener=Mock(return_value=io.BytesIO(b"invalid")), error_type=portfolio.PortfolioError)

    def test_module_boundary_and_parallel_cache_limits(self):
        import ast
        from concurrent.futures import ThreadPoolExecutor
        source = Path(quotes.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "financeiro.portfolio")
                self.assertFalse(node.module == "financeiro" and any(alias.name == "portfolio" for alias in node.names))
        def write(index):
            self.cache.set_quote_memory_cache(str(index), self.now + timedelta(hours=1), {}, self.now)
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(write, range(100)))
        self.assertLessEqual(len(self.cache.memory), self.cache.max_entries)
