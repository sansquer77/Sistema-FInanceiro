from datetime import date, datetime, timezone
import unittest
from urllib.parse import urlparse

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
        self.assertEqual(events[0]["confirmation_label"], "Detectado · Yahoo Finance")
        self.assertIsNone(events[0]["payment_date"])
        self.assertNotIn("estimated", events[0])
        self.assertNotIn("total", events[0])

    def test_failure_is_partial_and_cache_receives_bounded_period(self):
        calls = []

        def cached_json(url, message, cache_key, ttl, force_refresh=False, headers=None):
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
        yahoo_calls = [
            call for call in calls
            if (urlparse(call[0]).hostname or "").endswith(".query1.finance.yahoo.com")
            or (urlparse(call[0]).hostname or "") == "query1.finance.yahoo.com"
        ]
        self.assertEqual(len(yahoo_calls), 2)
        self.assertTrue(all(call[3] for call in calls))
        self.assertTrue(all("period1=" in call[0] and "period2=" in call[0] for call in yahoo_calls))
        self.assertTrue(all(call[1].endswith(":2026-09-01") for call in yahoo_calls))

    def test_b3_future_dividends_are_filtered_by_share_type_and_normalized(self):
        payload = [{"cashDividends": [
            {"assetIssued": "BRPETRACNOR9", "lastDatePrior": "18/09/2026", "paymentDate": "25/09/2026", "rate": "0,47156696000", "label": "DIVIDENDO"},
            {"assetIssued": "BRPETRACNPR6", "lastDatePrior": "18/09/2026", "paymentDate": "25/09/2026", "rate": "0,67407131000", "label": "JRS CAP PROPRIO"},
        ]}]
        events = portfolio_events.parse_b3_events(
            payload,
            {"asset_identifier": "PETR4", "asset_name": "Petrobras", "currency": "BRL", "portfolio_names": ["Carteira"]},
            minimum_date=date(2026, 9, 1), maximum_date=date(2026, 11, 30),
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["date"], "2026-09-21")
        self.assertEqual(events[0]["payment_date"], "2026-09-25")
        self.assertEqual(events[0]["amount_per_share_micros"], 674071)
        self.assertEqual(events[0]["event_label"], "JCP")
        self.assertEqual(events[0]["source"], "B3")
        self.assertEqual(events[0]["confirmation_label"], "Anunciado · B3")

    def test_b3_ex_date_skips_anbima_holiday(self):
        events = portfolio_events.parse_b3_events(
            [{"cashDividends": [{
                "assetIssued": "BRPETRACNPR6", "lastDatePrior": "02/04/2026",
                "paymentDate": "10/04/2026", "rate": "0,50", "label": "DIVIDENDO",
            }]}],
            {"asset_identifier": "PETR4", "asset_name": "Petrobras", "currency": "BRL"},
            minimum_date=date(2026, 4, 1), maximum_date=date(2026, 4, 30),
            holidays={date(2026, 4, 3)},
        )
        self.assertEqual(events[0]["date"], "2026-04-06")

    def test_b3_corporate_events_include_bonus_split_and_reverse_split(self):
        payload = [{"stockDividends": [
            {"assetIssued": "BRITUBACNPR1", "lastDatePrior": "30/09/2026", "label": "BONIFICACAO", "factor": "3,00000000000"},
            {"assetIssued": "BRITUBACNPR1", "lastDatePrior": "30/09/2026", "label": "DESDOBRAMENTO", "factor": "50,00000000000"},
            {"assetIssued": "BRITUBACNPR1", "lastDatePrior": "30/09/2026", "label": "GRUPAMENTO", "factor": "0,01000000000"},
            {"assetIssued": "BRITUBACNOR4", "lastDatePrior": "30/09/2026", "label": "BONIFICACAO", "factor": "3,00000000000"},
        ]}]
        events = portfolio_events.parse_b3_events(
            payload,
            {"asset_identifier": "ITUB4", "asset_name": "Itaú", "currency": "BRL", "portfolio_names": ["Carteira"]},
            minimum_date=date(2026, 9, 1), maximum_date=date(2026, 11, 30),
        )
        self.assertEqual(
            [(event["event_type"], event["event_label"]) for event in events],
            [
                ("stock_bonus", "Bonificação"),
                ("stock_split", "Desdobramento"),
                ("reverse_stock_split", "Grupamento"),
            ],
        )
        self.assertTrue(all(event["date"] == "2026-10-01" for event in events))
        self.assertTrue(all(event["amount_per_share_micros"] is None for event in events))
        self.assertTrue(all(event["source"] == "B3" for event in events))

    def test_nasdaq_future_dividend_uses_decimal_without_float(self):
        payload = {"data": {"dividends": {"rows": [{
            "exOrEffDate": "10/15/2026", "paymentDate": "10/20/2026",
            "amount": "$1.009719", "currency": "USD",
        }]}}}
        events = portfolio_events.parse_nasdaq_events(
            payload,
            {"asset_identifier": "ACWI", "asset_name": "ACWI", "currency": "USD", "portfolio_names": ["Exterior"]},
            minimum_date=date(2026, 9, 1), maximum_date=date(2026, 11, 30),
        )
        self.assertEqual(events[0]["amount_per_share_micros"], 1_009_719)
        self.assertEqual(events[0]["payment_date"], "2026-10-20")
        self.assertEqual(events[0]["source"], "Nasdaq")
        self.assertEqual(events[0]["confirmation_label"], "Detectado · Nasdaq")

    def test_b3_is_primary_for_brazilian_asset_and_uses_daily_cache(self):
        calls = []

        def cached_json(url, message, cache_key, ttl, force_refresh=False, headers=None):
            calls.append((url, cache_key, ttl, headers))
            return [{"cashDividends": [{
                "assetIssued": "BRPETRACNPR6", "lastDatePrior": "30/09/2026",
                "paymentDate": "15/10/2026", "rate": "0,50", "label": "DIVIDENDO",
            }]}]

        result = portfolio_events.get_events(
            [{"symbol": "PETR4.SA", "asset_identifier": "PETR4", "asset_name": "Petrobras", "currency": "BRL", "acquired_at": "2025-01-01", "portfolio_names": ["Carteira"]}],
            cached_json=cached_json,
            cached_calendar=lambda *args, **kwargs: self.fail("Yahoo não deve ser consultado quando a B3 retorna evento"),
            error_type=ProviderError,
            today=date(2026, 9, 4),
        )
        self.assertEqual(result["events"][0]["source"], "B3")
        self.assertEqual(calls[0][1], "b3-events:PETR")
        self.assertEqual(calls[0][2], 24 * 60 * 60)
        self.assertIn("Origin", calls[0][3])

    def test_b3_event_from_earlier_in_current_month_does_not_fall_back(self):
        calls = []

        def cached_json(url, message, cache_key, ttl, force_refresh=False, headers=None):
            calls.append(cache_key)
            return [{"cashDividends": [{
                "assetIssued": "BRITUBACNPR1", "lastDatePrior": "31/08/2026",
                "paymentDate": "01/10/2026", "rate": "0,01818200000",
                "label": "JRS CAP PROPRIO",
            }]}]

        result = portfolio_events.get_events(
            [{"symbol": "ITUB4.SA", "asset_identifier": "ITUB4", "asset_name": "Itaú Unibanco", "currency": "BRL", "acquired_at": "2025-01-01", "portfolio_names": ["Personnalité"]}],
            cached_json=cached_json,
            cached_calendar=lambda *args, **kwargs: self.fail("Yahoo não deve receber evento B3 do mês vigente"),
            error_type=ProviderError,
            today=date(2026, 9, 4),
        )
        self.assertEqual(calls, ["b3-events:ITUB"])
        self.assertEqual(result["events"][0]["date"], "2026-09-01")
        self.assertEqual(result["events"][0]["payment_date"], "2026-10-01")
        self.assertEqual(result["events"][0]["amount_per_share_micros"], 18_182)
        self.assertEqual(result["events"][0]["source"], "B3")

    def test_nasdaq_is_primary_for_international_asset(self):
        calls = []

        def cached_json(url, message, cache_key, ttl, force_refresh=False, headers=None):
            calls.append((url, cache_key))
            return {"data": {"dividends": {"rows": [{
                "exOrEffDate": "10/15/2026", "paymentDate": "10/20/2026",
                "amount": "$0.75", "currency": "USD",
            }]}}}

        result = portfolio_events.get_events(
            [{"symbol": "ACWI", "asset_identifier": "ACWI", "asset_name": "ACWI", "currency": "USD", "acquired_at": "2025-01-01", "portfolio_names": ["Exterior"]}],
            cached_json=cached_json,
            cached_calendar=lambda *args, **kwargs: self.fail("Yahoo não deve ser consultado quando a Nasdaq retorna evento"),
            error_type=ProviderError,
            today=date(2026, 9, 4),
        )
        self.assertEqual(result["events"][0]["source"], "Nasdaq")
        self.assertEqual(calls, [(portfolio_events.NASDAQ_DIVIDENDS_URL.format(symbol="ACWI", asset_class="stocks"), "nasdaq-events:ACWI:stocks")])

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
