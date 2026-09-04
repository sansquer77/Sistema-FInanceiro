from datetime import date, datetime, timezone
import unittest

from financeiro import portfolio_events


class ProviderError(Exception):
    pass


class PortfolioEventsTest(unittest.TestCase):
    def test_assets_are_limited_to_open_stock_positions_and_deduplicated(self):
        positions = [
            {"asset_type": "stock", "asset_identifier": "PETR4", "asset_name": "Petrobras", "currency": "BRL", "first_operation_date": "2025-04-10"},
            {"asset_type": "stock", "asset_identifier": "PETR4", "asset_name": "Petrobras", "currency": "BRL", "first_operation_date": "2024-01-15"},
            {"asset_type": "crypto", "asset_identifier": "BTC", "currency": "BRL", "first_operation_date": "2024-01-01"},
        ]
        assets = portfolio_events.build_event_assets(positions, lambda position: f"{position['asset_identifier']}.SA")
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["symbol"], "PETR4.SA")
        self.assertEqual(assets[0]["acquired_at"], "2024-01-15")

    def test_assets_keep_all_portfolios_for_the_same_symbol(self):
        positions = [
            {"asset_type": "stock", "asset_identifier": "PETR4", "currency": "BRL", "account_name": "Carteira A", "first_operation_date": "2025-01-01"},
            {"asset_type": "stock", "asset_identifier": "PETR4", "currency": "BRL", "account_name": "Carteira B", "first_operation_date": "2025-02-01"},
        ]
        assets = portfolio_events.build_event_assets(positions, lambda position: f"{position['asset_identifier']}.SA")
        self.assertEqual(assets[0]["portfolio_names"], ["Carteira A", "Carteira B"])

    def test_yahoo_dividends_keep_unit_amount_and_provider_confirmation(self):
        timestamp = int(datetime(2026, 8, 20, tzinfo=timezone.utc).timestamp())
        events = portfolio_events.parse_yahoo_events({
            "chart": {"result": [{"events": {"dividends": {
                str(timestamp): {"amount": 0.357891, "date": timestamp},
            }}}]},
        }, {"asset_identifier": "PETR4", "asset_name": "Petrobras", "currency": "BRL"})
        self.assertEqual(events[0]["amount_per_share_micros"], 357891)
        self.assertEqual(events[0]["event_label"], "Dividendo/JCP")
        self.assertEqual(events[0]["confirmation_label"], "Detectado pelo provedor")
        self.assertIsNone(events[0]["payment_date"])
        self.assertNotIn("estimated", events[0])
        self.assertNotIn("total", events[0])

    def test_failure_is_partial_and_cache_receives_bounded_period(self):
        calls = []

        def cached_json(url, message, cache_key, ttl, force_refresh=False):
            calls.append((url, cache_key, ttl, force_refresh))
            if "FAIL3" in url:
                raise ProviderError(message)
            timestamp = int(datetime(2026, 9, 2, tzinfo=timezone.utc).timestamp())
            return {"chart": {"result": [{"events": {"dividends": {
                str(timestamp): {"amount": "1.25", "date": timestamp},
            }}}]}}

        assets = [
            {"symbol": "OK3.SA", "asset_identifier": "OK3", "asset_name": "Ok", "currency": "BRL", "acquired_at": "2026-01-01"},
            {"symbol": "FAIL3.SA", "asset_identifier": "FAIL3", "asset_name": "Falha", "currency": "BRL", "acquired_at": "2026-01-01"},
        ]
        result = portfolio_events.get_events(assets, cached_json=cached_json, error_type=ProviderError,
                                              today=date(2026, 9, 4), force_refresh=True,
                                              start_date=date(2026, 9, 1))
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["unavailable"][0]["asset_identifier"], "FAIL3")
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call[3] for call in calls))
        self.assertTrue(all("period1=" in call[0] and "period2=" in call[0] for call in calls))
        self.assertTrue(all(call[1].endswith(":2026-09-01") for call in calls))

    def test_payment_date_is_optional_and_kept_only_when_valid(self):
        event_timestamp = int(datetime(2026, 8, 20, tzinfo=timezone.utc).timestamp())
        payment_timestamp = int(datetime(2026, 9, 5, tzinfo=timezone.utc).timestamp())
        events = portfolio_events.parse_yahoo_events({
            "chart": {"result": [{"events": {"dividends": {
                str(event_timestamp): {
                    "amount": "0.42", "date": event_timestamp, "paymentDate": payment_timestamp,
                },
            }}}]},
        }, {"asset_identifier": "ITUB4", "asset_name": "Itaú", "currency": "BRL"})
        self.assertEqual(events[0]["date"], "2026-08-20")
        self.assertEqual(events[0]["payment_date"], "2026-09-05")

    def test_invalid_provider_scalars_and_out_of_window_events_are_discarded_individually(self):
        valid = int(datetime(2026, 9, 2, tzinfo=timezone.utc).timestamp())
        old = int(datetime(2026, 8, 20, tzinfo=timezone.utc).timestamp())
        payload = {"chart": {"result": [{"events": {"dividends": {
            "valid": {"amount": "1.25", "date": valid},
            "huge_amount": {"amount": "9" * 100, "date": valid},
            "huge_timestamp": {"amount": "1", "date": "9" * 100},
            "old": {"amount": "2", "date": old},
        }}}]}}
        events = portfolio_events.parse_yahoo_events(
            payload,
            {"asset_identifier": "OK3", "asset_name": "Ok", "currency": "BRL"},
            minimum_date=date(2026, 9, 1),
            maximum_date=date(2026, 9, 4),
        )
        self.assertEqual([(item["date"], item["amount_per_share_micros"]) for item in events], [
            ("2026-09-02", 1_250_000),
        ])

    def test_malformed_dividend_collection_is_an_empty_partial_result(self):
        payload = {"chart": {"result": [{"events": {"dividends": ["invalid"]}}]}}
        events = portfolio_events.parse_yahoo_events(
            payload, {"asset_identifier": "OK3", "asset_name": "Ok", "currency": "BRL"},
        )
        self.assertEqual(events, [])

    def test_calendar_events_are_limited_to_current_month_plus_two(self):
        def epoch(day):
            return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
        payload = {"quoteSummary": {"result": [{"calendarEvents": {
            "exDividendDate": {"raw": epoch("2026-10-01")},
            "dividendDate": {"raw": epoch("2026-10-08")},
        }}]}}
        events = portfolio_events.parse_yahoo_calendar_events(
            payload,
            {"asset_identifier": "ITUB4", "asset_name": "Itaú", "currency": "BRL", "portfolio_names": ["Carteira"]},
            minimum_date=date(2026, 9, 4), maximum_date=date(2026, 11, 30),
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["date"], "2026-10-01")
        self.assertEqual(events[0]["payment_date"], "2026-10-08")
        self.assertIsNone(events[0]["amount_per_share_micros"])


if __name__ == "__main__":
    unittest.main()
