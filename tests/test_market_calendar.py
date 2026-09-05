from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock
from urllib.error import URLError

from financeiro import market_calendar


class Response(io.BytesIO):
    def __init__(self, payload: bytes, content_length: str | None = None):
        super().__init__(payload)
        self.headers = {"Content-Length": content_length or str(len(payload))}


class MarketCalendarTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "finance.db"

        @contextmanager
        def connection_factory(path=None):
            conn = sqlite3.connect(path or self.path)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        self.connection_factory = connection_factory

    def test_anbima_rows_are_normalized_from_excel_dates(self):
        rows = [
            ["Data", "Dia da Semana", "Feriado"],
            [Decimal("46023"), "quinta-feira", "Confraternização Universal"],
            ["nota", "", ""],
        ]
        with mock.patch("financeiro.imports.parse_xls_rows", return_value=rows):
            parsed = market_calendar.parse_anbima_holidays(b"xls")
        self.assertEqual(parsed, [("2026-01-01", "Confraternização Universal")])

    def test_successful_refresh_replaces_calendar_and_skips_same_year(self):
        with mock.patch.object(market_calendar, "download_anbima_xls", return_value=b"xls"), mock.patch.object(
            market_calendar, "parse_anbima_holidays", return_value=[("2026-01-01", "Ano Novo"), ("2026-04-03", "Paixão de Cristo")]
        ) as parser:
            first = market_calendar.refresh_anbima_calendar_if_due(
                self.path, connection_factory=self.connection_factory, today=date(2026, 9, 4)
            )
            second = market_calendar.refresh_anbima_calendar_if_due(
                self.path, connection_factory=self.connection_factory, today=date(2026, 9, 5)
            )
        self.assertTrue(first["updated"])
        self.assertEqual(second["reason"], "current")
        self.assertEqual(parser.call_count, 1)
        self.assertEqual(market_calendar.load_holiday_dates(self.connection_factory), {
            date(2026, 1, 1), date(2026, 4, 3),
        })

    def test_failed_refresh_preserves_existing_calendar(self):
        with self.connection_factory(self.path) as conn:
            market_calendar.ensure_market_calendar_schema(conn)
            conn.execute("INSERT INTO market_holidays VALUES ('2026-01-01', 'Ano Novo', 'ANBIMA')")
        with mock.patch.object(market_calendar, "download_anbima_xls", side_effect=URLError("offline")):
            result = market_calendar.refresh_anbima_calendar_if_due(
                self.path, connection_factory=self.connection_factory, today=date(2026, 9, 4)
            )
        self.assertEqual(result["reason"], "unavailable")
        self.assertEqual(market_calendar.load_holiday_dates(self.connection_factory), {date(2026, 1, 1)})

    def test_binary_download_enforces_declared_and_effective_size(self):
        too_large = str(market_calendar.MAX_ANBIMA_XLS_BYTES + 1)
        with self.assertRaises(ValueError):
            market_calendar.download_anbima_xls(opener=lambda *_args, **_kwargs: Response(b"x", too_large))
        with self.assertRaises(ValueError):
            market_calendar.download_anbima_xls(
                opener=lambda *_args, **_kwargs: Response(b"x" * (market_calendar.MAX_ANBIMA_XLS_BYTES + 1), "")
            )

    def test_next_business_day_skips_weekend_and_anbima_holiday(self):
        result = market_calendar.next_business_day(date(2026, 4, 2), {date(2026, 4, 3)})
        self.assertEqual(result, date(2026, 4, 6))


if __name__ == "__main__":
    unittest.main()
