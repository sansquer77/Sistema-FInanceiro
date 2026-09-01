"""Current outstanding installments shared by reports and Cockpit."""
from calendar import monthrange
from datetime import date
import re

from financeiro.accounts import cents_to_money
from financeiro.calendar_rules import normalize_iso_month
from financeiro.database import get_connection


def parse_ids(value):
    if value is None or value == '':
        return []
    values = value.split(',') if isinstance(value, str) else value
    if not isinstance(values, (list, tuple)) or len(values) > 500:
        raise ValueError('Seleção de contas/cartões inválida.')
    try:
        ids = {int(item) for item in values}
        if any(item <= 0 for item in ids):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('Seleção de contas/cartões inválida.') from None
    return sorted(ids)


def get_open_debts(user_id, month=None, account_ids=None, card_ids=None, currency=None, *, today=None):
    today = today or date.today()
    try:
        month = normalize_iso_month(month or today.strftime('%Y-%m'))
    except ValueError:
        raise ValueError('Informe um mês válido no formato AAAA-MM.') from None
    accounts = parse_ids(account_ids)
    cards = parse_ids(card_ids)
    currency = str(currency or 'all').strip()
    if currency != 'all' and not re.fullmatch('[A-Z]{3}', currency):
        raise ValueError('Moeda inválida.')
    with get_connection() as conn:
        conn.execute('BEGIN')
        for table, ids in (('checking_accounts', accounts), ('credit_cards', cards)):
            if ids:
                available = {row['id'] for row in conn.execute(
                    f'SELECT id FROM {table} WHERE user_id = ? AND archived_at IS NULL', (user_id,))}
                if not set(ids) <= available:
                    raise ValueError('Seleção de contas/cartões inválida.')
        rows = []
        for origin, table, owner_table, owner_key, ids in (
            ('account', 'transactions', 'checking_accounts', 'account_id', accounts),
            ('card', 'credit_card_transactions', 'credit_cards', 'credit_card_id', cards),
        ):
            # spec: relatorios/relatorios v2.20 — critérios complementares de dívida aberta
            # Card reconciliation verifies consumption; only invoice settlement closes it.
            settled = ("t.reconciled_at IS NULL AND NOT EXISTS (SELECT 1 FROM credit_card_payments p WHERE p.user_id = t.user_id AND p.transaction_id = t.id)"
                       if origin == 'account' else
                       "NOT EXISTS (SELECT 1 FROM credit_card_payments p WHERE p.user_id = t.user_id AND p.credit_card_id = t.credit_card_id AND p.invoice_month = t.invoice_month)")
            competence = "substr(t.date, 1, 7)" if origin == 'account' else 't.invoice_month'
            due_day = 'NULL' if origin == 'account' else 'o.due_day'
            params = [user_id]
            extra = ''
            if ids:
                extra += f' AND o.id IN ({",".join("?" for _ in ids)})'
                params.extend(ids)
            if currency != 'all':
                extra += ' AND o.currency = ?'
                params.append(currency)
            records = conn.execute(f'''
                SELECT t.id, t.series_id, t.description, t.amount_cents, t.date,
                       {competence} AS competence, {due_day} AS due_day,
                       o.id AS owner_id, o.name AS owner_name, o.currency
                FROM {table} t JOIN {owner_table} o ON o.id = t.{owner_key} AND o.user_id = t.user_id
                WHERE t.user_id = ? AND t.archived_at IS NULL AND o.archived_at IS NULL
                  AND t.type = 'expense'
                  AND (t.series_kind = 'installment' OR (t.installment_index > 0 AND t.installment_count > 0))
                  AND {settled} {extra}
                ORDER BY o.id, t.id
            ''', params).fetchall()
            rows.extend(dict(row) | {'origin': origin} for row in records)
    return summarize_open_debts(rows, month, today)


def summarize_open_debts(rows, month, today):
    groups, totals = {}, {}
    for row in rows:
        origin, currency = row['origin'], row['currency']
        group_key = (origin, row['owner_id'])
        group = groups.setdefault(group_key, dict(label=row['owner_name'], detail='Conta' if origin == 'account' else 'Cartão',
            currency=currency, origin=origin, owner_id=row['owner_id'], total_cents=0, debts={}))
        # A missing series must not merge unrelated purchases with the same description.
        debt_key = ('series', row['series_id']) if row['series_id'] else ('item', row['id'])
        debt = group['debts'].setdefault(debt_key, dict(description=row['description'], total_cents=0, count=0, overdue_count=0, month_total_cents=0))
        due = row['date']
        if origin == 'card':
            year, number = map(int, row['competence'].split('-'))
            due = date(year, number, min(row['due_day'], monthrange(year, number)[1])).isoformat()
        amount = int(row['amount_cents'])
        debt['total_cents'] += amount
        debt['count'] += 1
        debt['overdue_count'] += int(due < today.isoformat())
        if row['competence'] == month:
            debt['month_total_cents'] += amount
        group['total_cents'] += amount
        totals[currency] = totals.get(currency, 0) + amount
    result = []
    for group in sorted(groups.values(), key=lambda row: (row['currency'], -row['total_cents'], row['label'], row['owner_id'])):
        debts = sorted(group['debts'].values(), key=lambda row: (-row['total_cents'], row['description']))
        group['debts'] = [debt | {'total': cents_to_money(debt['total_cents'])} for debt in debts]
        group['total'] = cents_to_money(group['total_cents'])
        result.append(group)
    return dict(month=month, observed_on=today.isoformat(), groups=result,
                by_currency={key: cents_to_money(value) for key, value in sorted(totals.items())},
                by_currency_cents=dict(sorted(totals.items())))
