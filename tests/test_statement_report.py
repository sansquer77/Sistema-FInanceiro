import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.credit_cards import create_credit_card, pay_credit_card_invoice
from financeiro.reports import build_statement_report, _statement_section


class StatementReportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = database.DATA_DIR, database.DB_PATH
        database.DATA_DIR = Path(self.temp.name)
        database.DB_PATH = database.DATA_DIR / 'test.db'
        database.initialize_database()
        self.uid = create_user('Alice', 'alice@example.com', 'correct-password')['id']
        self.account = self.make_account(self.uid, 'BRL')
        self.card = create_credit_card(self.uid, dict(name='Cartão', issuer='Banco', currency='BRL', limit='5000,00', closing_day='20', due_day='10'))['id']

    def tearDown(self):
        database.DATA_DIR, database.DB_PATH = self.old
        self.temp.cleanup()

    def make_account(self, uid, currency):
        return create_checking_account(uid, dict(name=currency, bank_name='Banco', currency=currency, initial_balance='5000,00'))['id']

    def item(self, card=False, **changes):
        values = dict(user_id=self.uid, type='expense', description='Compra', amount_cents=10001, date='2026-02-10')
        values.update(dict(credit_card_id=self.card, invoice_month='2026-02') if card else dict(account_id=self.account))
        values.update(changes)
        table = 'credit_card_transactions' if card else 'transactions'
        with database.get_connection() as conn:
            return conn.execute(f'INSERT INTO {table} ({",".join(values)}) VALUES ({",".join("?" for _ in values)})', tuple(values.values())).lastrowid

    def read(self, **filters):
        return build_statement_report(self.uid, '2026-02', today=date(2026, 2, 20), **filters)

    def test_native_currency_totals_and_filters(self):
        usd = self.make_account(self.uid, 'USD')
        self.item(amount_cents=10)
        self.item(amount_cents=20)
        self.item(account_id=usd, amount_cents=7)
        self.item(card=True, amount_cents=40)
        result = self.read()['sections']
        self.assertEqual([(s['currency'], s['total_cents']) for s in result], [('BRL', 70), ('USD', 7)])
        self.assertEqual(result[0]['account_total'], '0.30')
        self.assertEqual(result[0]['card_total'], '0.40')
        self.assertEqual(self.read(currency='USD')['sections'][0]['total'], '0.07')
        self.assertEqual([s['total_cents'] for s in self.read(account_ids=str(usd))['sections']], [40, 7])
        self.assertEqual(self.read(account_ids='', card_ids=''), self.read())

    def test_competence_payment_and_nonexpense_exclusions(self):
        self.item(card=True, date='2026-01-15', series_kind='installment')
        self.item(date='2026-01-15')
        self.item(type='income')
        self.item(type='investment')
        self.item(type='transfer')
        self.item(archived_at='2026-02-01')
        pay_credit_card_invoice(self.uid, dict(credit_card_id=str(self.card), invoice_month='2026-02', account_id=str(self.account), payment_date='2026-02-10'))
        section = self.read()['sections'][0]
        self.assertEqual(section['total_cents'], 10001)
        self.assertEqual(section['open_debts'], '0.00')
        self.assertEqual(section['items'][0]['date'], '2026-01-15')
        self.assertEqual(sum(day['amount_cents'] for day in section['daily']), 0)

    def test_scope_rejects_foreign_ids_and_excludes_archived_owners(self):
        other = create_user('Bob', 'bob@example.com', 'correct-password')['id']
        foreign = self.make_account(other, 'USD')
        self.item(user_id=other, account_id=foreign)
        self.item()
        self.item(card=True)
        with database.get_connection() as conn:
            conn.execute('UPDATE checking_accounts SET archived_at = CURRENT_TIMESTAMP WHERE id = ?', (self.account,))
            conn.execute('UPDATE credit_cards SET archived_at = CURRENT_TIMESTAMP WHERE id = ?', (self.card,))
        self.assertEqual(self.read()['sections'], [])
        for filters in ({'account_ids': str(foreign)}, {'card_ids': str(self.card)}, {'currency': 'wrong'}, {'account_ids': 'bad'}):
            with self.assertRaises(ValueError):
                self.read(**filters)

    def test_aggregation_ranking_others_daily_composition_and_precision(self):
        items = [dict(amount_cents=amount, amount=f'{amount / 100:.2f}', category=f'C{index}', subcategory='', date='2026-02-10', origin='account' if index < 3 else 'card')
                 for index, amount in enumerate([101, 200, 300, 400, 500, 600, 700])]
        section = _statement_section('BRL', items, 555, '2026-02', date(2026, 2, 20))
        self.assertEqual(section['total_cents'], 2801)
        self.assertEqual(section['average_cents'], 140)
        self.assertEqual(section['top_category']['label'], 'C6')
        self.assertEqual(section['distribution'][-1]['amount_cents'], 301)
        self.assertEqual(section['distribution'][-1]['label'], 'Outros')
        self.assertAlmostEqual(sum(row['share'] for row in section['distribution']), 1)
        self.assertEqual(section['daily'][9]['amount_cents'], 2801)
        self.assertEqual(section['daily'][9]['ratio'], 1)
        self.assertEqual(section['items'][0]['amount_cents'], 700)
        self.assertAlmostEqual(section['composition']['account'][0]['share'], 300 / 2801)
        self.assertEqual(section['composition']['account'][0]['label'], 'C2 / Sem subcategoria')
        self.assertEqual(section['open_debts'], '5.55')
        self.assertEqual(_statement_section('BRL', items, 0, '2026-02', date(2026, 3, 1))['average_cents'], 100)
        self.assertEqual(_statement_section('BRL', items, 0, '2026-02', date(2026, 1, 1))['average_cents'], 2801)

    def test_endpoint_authentication_and_parameters(self):
        import app
        handler = Mock(path='/api/reports/statement?month=2026-02&currency=USD&account_ids=1,2')
        handler.require_user.return_value = {'id': self.uid}
        with patch.object(app, 'build_statement_report', return_value={'sections': []}) as service:
            app.AppHandler.handle_statement_report(handler)
            service.assert_called_once_with(self.uid, month='2026-02', currency='USD', account_ids='1,2')
            handler.send_json.assert_called_once_with({'sections': []})
            service.reset_mock()
            handler.require_user.side_effect = PermissionError('Sem sessão')
            with self.assertRaises(PermissionError):
                app.AppHandler.handle_statement_report(handler)
            service.assert_not_called()


if __name__ == '__main__':
    unittest.main()
