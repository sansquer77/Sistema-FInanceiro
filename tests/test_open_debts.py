import tempfile
import unittest
from unittest.mock import Mock, patch
from datetime import date
from pathlib import Path

from financeiro import database
from financeiro.auth import create_user
from financeiro.accounts import create_checking_account
from financeiro.credit_cards import create_credit_card, pay_credit_card_invoice
from financeiro.open_debts import get_open_debts


class OpenDebtsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = database.DATA_DIR, database.DB_PATH
        database.DATA_DIR = Path(self.temp.name)
        database.DB_PATH = database.DATA_DIR / 'test.db'
        database.initialize_database()
        self.uid = create_user('Alice', 'alice@example.com', 'correct-password')['id']
        self.account = create_checking_account(self.uid, dict(name='Conta', bank_name='Banco', currency='BRL', initial_balance='5000,00'))['id']
        self.card = create_credit_card(self.uid, dict(name='Cartão', issuer='Banco', currency='BRL', limit='5000,00', closing_day='20', due_day='31'))['id']

    def tearDown(self):
        database.DATA_DIR, database.DB_PATH = self.old
        self.temp.cleanup()

    def item(self, card=False, **changes):
        values = dict(user_id=self.uid, type='expense', description='Compra', amount_cents=10001,
                      date='2026-02-10', series_kind='installment', series_id='series')
        values.update(dict(credit_card_id=self.card, invoice_month='2026-02') if card else dict(account_id=self.account))
        values.update(changes)
        table = 'credit_card_transactions' if card else 'transactions'
        with database.get_connection() as conn:
            return conn.execute(f'INSERT INTO {table} ({",".join(values)}) VALUES ({",".join("?" for _ in values)})', tuple(values.values())).lastrowid

    def read(self, **kwargs):
        return get_open_debts(self.uid, '2026-02', today=date(2026, 3, 1), **kwargs)

    def test_accounts_include_overdue_but_not_reconciled_future_or_noninstallments(self):
        self.item(date='2026-01-10')
        self.item(date='2026-04-10', reconciled_at='2026-02-01')
        self.item(series_kind='single')
        self.item(type='income')
        self.item(archived_at='2026-02-01')
        debt = self.read()['groups'][0]['debts'][0]
        self.assertEqual(debt['total_cents'], 10001)
        self.assertEqual(debt['overdue_count'], 1)
        self.assertEqual(debt['month_total_cents'], 0)

    def test_card_reconciliation_is_not_payment_and_competence_controls_due_date(self):
        self.item(card=True, date='2025-12-01', reconciled_at='2026-01-01')
        debt = self.read()['groups'][0]['debts'][0]
        self.assertEqual(debt['month_total_cents'], 10001)
        self.assertEqual(debt['overdue_count'], 1)  # February due day 31 clamps to 28.
        before_due = get_open_debts(self.uid, '2026-02', today=date(2026, 2, 27))
        self.assertEqual(before_due['groups'][0]['debts'][0]['overdue_count'], 0)

    def test_full_and_partial_payments_close_original_invoice_only(self):
        for amount in (None, '50,00'):
            with self.subTest(amount=amount):
                with database.get_connection() as conn:
                    conn.execute('DELETE FROM credit_card_payments')
                    conn.execute('DELETE FROM credit_card_transactions')
                self.item(card=True)
                self.item(card=True, invoice_month='2026-04')
                payload = dict(credit_card_id=str(self.card), invoice_month='2026-02', account_id=str(self.account), payment_date='2026-02-28')
                if amount:
                    payload['amount'] = amount
                pay_credit_card_invoice(self.uid, payload)
                result = self.read()
                self.assertEqual(result['by_currency_cents'], {'BRL': 10001})
                self.assertEqual(result['groups'][0]['debts'][0]['count'], 1)
                self.assertEqual(result['groups'][0]['debts'][0]['month_total_cents'], 0)

    def test_currency_filters_scope_and_legacy_installments(self):
        usd = create_checking_account(self.uid, dict(name='USD', bank_name='Banco', currency='USD', initial_balance='0,00'))['id']
        self.item()
        self.item(account_id=usd, amount_cents=7, series_kind='single', installment_index=1, installment_count=3)
        self.assertEqual(self.read()['by_currency_cents'], {'BRL': 10001, 'USD': 7})
        self.assertEqual(self.read(currency='USD')['by_currency'], {'USD': '0.07'})
        self.assertEqual(self.read(account_ids=str(usd))['by_currency_cents'], {'USD': 7})

    def test_archived_owners_and_other_users_are_excluded(self):
        other = create_user('Bob', 'bob@example.com', 'correct-password')['id']
        foreign = create_checking_account(other, dict(name='Outra', bank_name='Banco', currency='BRL', initial_balance='0,00'))['id']
        self.item(user_id=other, account_id=foreign)
        self.item()
        with database.get_connection() as conn:
            conn.execute('UPDATE checking_accounts SET archived_at = CURRENT_TIMESTAMP WHERE id = ?', (self.account,))
        self.assertEqual(self.read()['groups'], [])
        for ids in (str(foreign), str(self.account), 'oops', '-1'):
            with self.assertRaises(ValueError):
                self.read(account_ids=ids)

    def test_equal_descriptions_without_series_are_not_merged(self):
        self.item(series_id=None)
        self.item(series_id=None)
        self.assertEqual(len(self.read()['groups'][0]['debts']), 2)

    def test_handlers_share_service_and_report_requires_authentication(self):
        from app import AppHandler
        import app
        handler = Mock(path='/api/reports/open-debts?month=2026-02&currency=BRL')
        handler.require_user.return_value = {'id': self.uid}
        with patch.object(app, 'get_open_debts', return_value={'groups': []}) as service:
            AppHandler.handle_open_debts(handler)
            service.assert_called_once_with(self.uid, month='2026-02', currency='BRL')
            handler.send_json.assert_called_once_with({'groups': []})
            service.reset_mock()
            handler.require_user.side_effect = PermissionError('Sem sessão')
            with self.assertRaises(PermissionError):
                AppHandler.handle_open_debts(handler)
            service.assert_not_called()
        handler.require_user.side_effect = None
        handler.path = '/api/cockpit?month=2026-02'
        with patch.object(app, 'get_open_debts', return_value={'groups': []}) as service:
            AppHandler.handle_cockpit(handler)
            service.assert_called_once_with(self.uid, '2026-02')
            self.assertEqual(handler.send_json.call_args.args[0]['open_debts'], {'groups': []})

    def test_invalid_month_and_currency_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'mês válido'):
            get_open_debts(self.uid, '2026-13')
        with self.assertRaisesRegex(ValueError, 'Moeda inválida'):
            self.read(currency='invalid')


if __name__ == '__main__':
    unittest.main()
