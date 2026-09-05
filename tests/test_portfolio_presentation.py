from copy import deepcopy
import unittest
from financeiro import portfolio_presentation as presentation
from financeiro.portfolio import PortfolioError
from financeiro.portfolio_calculations import summarize_positions
from financeiro.http_routes import EXACT_ROUTES


def position(currency='BRL', current=12000, brl=12000):
    return dict(account_id=1, account_name='Carteira', currency=currency, asset_type='stock',
                asset_type_label='Renda variável', asset_identifier='ABC', asset_name='Ativo',
                quantity='2', average_price='50.00', total_cost='100.00', total_cost_cents=10000,
                total_cost_brl='100.00', total_cost_brl_cents=10000, day_result='1.00',
                day_result_cents=100, day_result_brl_cents=100,
                current_value=presentation.cents_to_money(current), current_value_cents=current,
                current_value_brl=presentation.cents_to_money(brl), current_value_brl_cents=brl)


class PortfolioPresentationTest(unittest.TestCase):
    def test_position_results_and_fractional_quantity(self):
        p = presentation.decorate_position(position())
        self.assertEqual(p['result'], '20.00')
        self.assertEqual(p['result_percent'], '20.00')
        self.assertEqual(p['day_result_percent'], '0.84')
        self.assertEqual(p['redemption_unit_price'], '60.00')
        p.update(quantity='0', total_cost='0', current_value_cents=0)
        presentation.decorate_position(p)
        self.assertEqual(p['result_percent'], '0.00')
        self.assertEqual(p['redemption_unit_price'], '0.00')

    def test_groups_never_add_different_native_currencies(self):
        positions = [position(), position('USD', current=20000, brl=100000)]
        summary = summarize_positions(positions)
        original = deepcopy(summary)
        model = presentation.build_presentation(positions, summary, [])
        self.assertEqual(summary, original)
        self.assertEqual(model['sections']['["account_name","Carteira"]']['current'], '1120.00')
        self.assertEqual(model['sections']['["currency","USD"]']['current'], '200.00')
        members = model['compositions']['["asset_type_label","Renda variável","USD"]']
        self.assertEqual(members['total'], '1000.00')
        self.assertEqual(members['members'][0]['percent'], '100.00')

    def test_aggregate_keeps_cents_and_custody_fees(self):
        a, b = position(), position(current=12001)
        a['fixed_income_custody_fee'] = '0.01'
        b['fixed_income_custody_fee'] = '0.02'
        model = presentation.build_presentation([a, b], summarize_positions([a, b]), [])
        parent = model['asset_groups']['[0,1]']
        self.assertEqual(parent['current_value_cents'], 24001)
        self.assertEqual(parent['average_price'], '50.00')
        self.assertEqual(parent['fixed_income_custody_fee'], '0.03')

    def test_goals_keep_empty_class_and_stock_usd_distinct(self):
        positions = [position(), position('USD', brl=48000)]
        goals = [dict(asset_type='stock', label='Renda variável', target_percent='20'),
                 dict(asset_type='stock_usd', label='Renda variável - USD', target_percent='70'),
                 dict(asset_type='fund', label='Fundos', target_percent='10')]
        model = presentation.build_presentation(positions, summarize_positions(positions), goals)
        rows = {(r['label'], r['currency']): r for r in model['allocation']}
        usd = rows[('Renda variável', 'USD')]
        self.assertEqual(usd['target_percent'], '70')
        self.assertEqual(usd['participation_percent'], '80')
        self.assertEqual(usd['deviation_value'], '60.00')
        self.assertEqual(rows[('Fundos', 'BRL')]['count'], 0)
        self.assertEqual(rows[('Fundos', 'BRL')]['deviation_level'], 'under')

    def test_asset_aggregation_respects_active_section_partition(self):
        positions = [position(), position(), position(current=30000)]
        positions[0]['fixed_income_indexer'] = 'CDI'
        positions[1]['fixed_income_indexer'] = 'CDI'
        positions[2]['fixed_income_indexer'] = 'IPCA'
        model = presentation.build_presentation(positions, summarize_positions(positions), [])
        self.assertEqual(model['asset_groups']['[0,1]']['current_value'], '240.00')
        self.assertEqual(model['asset_groups']['[0,1,2]']['current_value'], '540.00')

    def test_preview_rounds_like_redemption_and_rejects_invalid_numbers(self):
        data = dict(kind='redemption', quantity='0,333333', available_quantity='2', unit_price='10,00', fees='0,03')
        result = presentation.preview(data, PortfolioError)
        self.assertEqual(result['gross_amount'], '3.33')
        self.assertEqual(result['amount'], '3.30')
        self.assertEqual(result['remaining_quantity'], '1.666667')
        invalid = presentation.preview({**data, 'quantity': '3', 'fees': '99'}, PortfolioError)
        self.assertTrue(invalid['errors']['quantity'])
        self.assertTrue(invalid['errors']['fees'])
        for invalid_value in ('NaN', 'Infinity', 'xxx'):
            with self.assertRaises(PortfolioError):
                presentation.preview({**data, 'quantity': invalid_value}, PortfolioError)

    def test_goals_preview_exact_total_and_route(self):
        result = presentation.preview(dict(kind='goals', goals=[{'target_percent': '33,33'}, {'target_percent': '66,67'}]), PortfolioError)
        self.assertTrue(result['valid'])
        self.assertEqual(result['total_percent'], '100.00')
        self.assertEqual(EXACT_ROUTES['POST']['/api/portfolio/preview'], 'handle_portfolio_preview')
        self.assertEqual(presentation.build_presentation([], summarize_positions([]), [])['asset_groups'], {})
