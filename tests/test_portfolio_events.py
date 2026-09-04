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
        self.assertNotIn("estimated", events[0])
        self.assertNotIn("total", events[0])

    def test_failure_is_partial_and_cache_receives_bounded_period(self):
        calls = []

        def cached_json(url, message, cache_key, ttl, force_refresh=False):
            calls.append((url, cache_key, ttl, force_refresh))
            if "FAIL3" in url:
                raise ProviderError(message)
            timestamp = int(datetime(2026, 7, 10, tzinfo=timezone.utc).timestamp())
            return {"chart": {"result": [{"events": {"dividends": {
                str(timestamp): {"amount": "1.25", "date": timestamp},
            }}}]}}

        assets = [
            {"symbol": "OK3.SA", "asset_identifier": "OK3", "asset_name": "Ok", "currency": "BRL", "acquired_at": "2026-01-01"},
            {"symbol": "FAIL3.SA", "asset_identifier": "FAIL3", "asset_name": "Falha", "currency": "BRL", "acquired_at": "2026-01-01"},
        ]
        result = portfolio_events.get_events(assets, cached_json=cached_json, error_type=ProviderError,
                                              today=date(2026, 9, 4), force_refresh=True)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["unavailable"][0]["asset_identifier"], "FAIL3")
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call[3] for call in calls))
        self.assertTrue(all("period1=" in call[0] and "period2=" in call[0] for call in calls))


if __name__ == "__main__":
    unittest.main()
