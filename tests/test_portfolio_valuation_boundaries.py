"""Contracts for valuation/history separation (architecture v2, criteria 18–20)."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from decimal import Decimal
import inspect
import unittest
from unittest.mock import Mock, patch

from financeiro import portfolio, portfolio_returns, portfolio_valuation


class ValuationBoundariesTest(unittest.TestCase):
    def engine(self):
        return portfolio_valuation.PositionValuation(
            today=lambda: date(2026, 8, 31), error_type=portfolio.PortfolioError,
            fetch_accumulated_indexer_factor=lambda *a, **k: Decimal('1.01'),
            fetch_indexer_rate=lambda *a, **k: Decimal('0.15'),
            value_to_brl=lambda value, currency: value,
            fallback_indexer_annual_rate=lambda indexer: Decimal('0.15'),
            parse_rate_decimal=lambda value: Decimal(str(value or 0)),
            format_decimal_percent=str,
        )

    def position(self, **changes):
        return dict({
            'asset_type': 'fixed_income', 'currency': 'BRL',
            'first_operation_date': '2026-01-01', 'total_cost_cents': 100000,
            'fixed_income_mode': 'pre', 'fixed_income_indexer': 'CDI',
            'fixed_income_rate': '12', 'source_type': 'opening',
            'apply_tax_estimate': True,
        }, **changes)

    def test_current_value_reuses_date_valuation_and_integer_taxes(self):
        engine = self.engine()
        position = self.position()
        expected = engine.fixed_income_value_as_of(position, date(2026, 8, 31))
        engine.apply_fixed_income_value(position)
        self.assertEqual(position['current_value_cents'], expected[0])
        self.assertEqual(expected[0], expected[1] - expected[2] - expected[3] - expected[4])
        self.assertTrue(all(isinstance(value, int) for value in expected[:5]))
        self.assertEqual(engine.fixed_income_value_as_of(position, date(2025, 12, 31))[:5], (0, 0, 0, 0, 0))

    def test_savings_anniversary_and_maturity_are_preserved(self):
        engine = self.engine()
        savings = self.position(asset_type='savings', first_operation_date='2026-01-31')
        self.assertEqual(engine.savings_value_as_of(savings, date(2026, 2, 27)), 100000)
        self.assertGreater(engine.savings_value_as_of(savings, date(2026, 2, 28)), 100000)
        fixed = self.position(fixed_income_maturity_date='2026-06-01')
        self.assertEqual(engine.fixed_income_value_as_of(fixed, date(2026, 6, 1)),
                         engine.fixed_income_value_as_of(fixed, date(2026, 8, 31)))

    def test_history_reuses_supplied_positions_and_keeps_request_cache_local(self):
        engine = self.engine()
        load = Mock(side_effect=AssertionError('Must not reload positions'))
        caches = []
        def value_at(position, as_of, **kwargs):
            caches.append(kwargs['factor_cache'])
            return engine._position_value_native_as_of(position, as_of, **kwargs)
        history = portfolio_returns.PortfolioReturns(
            today=engine.today, error_type=portfolio.PortfolioError,
            get_portfolio=load, _position_value_native_as_of=value_at,
            fetch_accumulated_indexer_factor=engine.fetch_accumulated_indexer_factor,
            fetch_indexer_rate=engine.fetch_indexer_rate,
            compound_annual_factor=engine.compound_annual_factor,
        )
        positions = [self.position(), self.position(currency='USD', asset_type='other', current_value_cents=110000)]
        original = deepcopy(positions)
        first = history.get_portfolio_returns(1, positions=positions)
        first_cache = caches[0]
        self.assertTrue(all(cache is first_cache for cache in caches))
        caches.clear()
        second = history.get_portfolio_returns(2, positions=positions)
        self.assertIsNot(caches[0], first_cache)
        self.assertEqual(first, second)
        self.assertEqual(positions, original)
        self.assertTrue(first['has_historical_approximation'])
        self.assertEqual(first['series'][0]['BRL_return_pct'], 0)
        self.assertIn('USD_return_pct', first['series'][0])
        load.assert_not_called()

    def test_facade_injection_remains_late_and_parallel_calls_isolated(self):
        with patch.object(portfolio, 'fetch_accumulated_indexer_factor', return_value=Decimal('1.01')):
            positions = [self.position(fixed_income_mode='post') for _ in range(12)]
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(lambda p: portfolio.fixed_income_value_as_of(p, date(2026, 8, 31), factor_cache={}), positions))
            self.assertTrue(all(result == results[0] for result in results))
            self.assertGreater(results[0][0], 100000)

    def test_internal_modules_do_not_import_facade_or_access_storage_transport(self):
        for module in (portfolio_returns, portfolio_valuation):
            source = inspect.getsource(module)
            for forbidden in ('from financeiro.portfolio import', 'import portfolio', 'get_connection', 'urlopen', 'sqlite3'):
                self.assertNotIn(forbidden, source)


if __name__ == '__main__':
    unittest.main()
