from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeadCodeAuditTest(unittest.TestCase):
    def test_evidenced_production_residues_stay_removed(self):
        ai = (ROOT / 'financeiro/ai_summary.py').read_text(encoding='utf-8')
        version = (ROOT / 'financeiro/version_check.py').read_text(encoding='utf-8')
        portfolio = (ROOT / 'financeiro/portfolio.py').read_text(encoding='utf-8')
        transactions = (ROOT / 'financeiro/transactions.py').read_text(encoding='utf-8')

        self.assertNotIn('\nimport os\n', ai)
        self.assertNotIn('from financeiro import database', ai)
        self.assertNotIn('datetime, timedelta, timezone', version)
        self.assertNotIn('defaultdict, OrderedDict', portfolio)
        update_prefix = transactions[transactions.index('def update_transaction('):transactions.index('def delete_transaction(')]
        discarded_conversion = update_prefix[
            update_prefix.index('exchange_rate_micros = resolve_exchange_rate_micros'):
            update_prefix.index('category_id, subcategory_id = resolve_transaction_category')
        ]
        self.assertNotIn('convert_to_brl_cents(', discarded_conversion)
        self.assertIn('current_amount_brl_cents = convert_to_brl_cents(', update_prefix)

    def test_consultor_compatibility_reexports_are_not_misclassified(self):
        facade = (ROOT / 'financeiro/consultor.py').read_text(encoding='utf-8')
        self.assertIn('from financeiro.consultor_context import (', facade)
        self.assertIn('from financeiro.consultor_catalog import (', facade)
        self.assertIn('from financeiro.consultor_settings import (', facade)


if __name__ == '__main__':
    unittest.main()
