"""Financial read models for the portfolio UI; no persistence or external I/O."""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json

from financeiro.accounts import cents_to_money, money_to_cents
from financeiro.portfolio_calculations import percent, portfolio_group_label


def decimal(value):
    return Decimal(str(value or 0))


def cents(value):
    return int((decimal(value) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def key(values):
    return json.dumps(values, ensure_ascii=False, separators=(',', ':'))


def asset_key(position):
    return key([position['account_id'], position['currency'], position['asset_type'],
                position.get('asset_name') or position.get('asset_identifier') or 'Sem nome', position.get('cnpj') or ''])


def decorate_position(position):
    # spec: investimentos-portfolio v2.53 — resultados por moeda, sem cálculo no cliente
    current = int(position['current_value_cents'])
    cost = cents(position.get('total_cost'))
    day = cents(position.get('day_result'))
    quantity = decimal(position.get('quantity'))
    position.update(result=cents_to_money(current - cost),
                    result_percent=percent(current - cost, cost) if cost > 0 else '0.00',
                    day_result_percent=percent(day, current - day) if current - day > 0 else '0.00',
                    redemption_unit_price=cents_to_money(int((Decimal(current) / quantity).quantize(Decimal('1'), rounding=ROUND_HALF_UP))) if quantity > 0 else '0.00')
    for source in position.get('sources', []):
        source['day_result'] = '0.00'
        decorate_position(source)
    return position


def aggregate(positions):
    base = {**positions[0], 'sources': []}
    fields = ('invested', 'costs', 'total_cost', 'total_cost_brl', 'current_value',
              'current_value_brl', 'day_result', 'day_result_brl', 'fixed_income_gross_value',
              'fixed_income_iof_tax', 'fixed_income_income_tax', 'fixed_income_custody_fee', 'fixed_income_net_value')
    for field in fields:
        base[field] = cents_to_money(sum(cents(p.get(field)) for p in positions))
    quantity = sum((decimal(p.get('quantity')) for p in positions), Decimal(0))
    base.update(quantity=str(quantity), current_value_cents=cents(base['current_value']),
                current_value_brl_cents=cents(base['current_value_brl']),
                average_price=cents_to_money(int((Decimal(cents(base['total_cost'])) / quantity).quantize(Decimal('1'), rounding=ROUND_HALF_UP))) if quantity > 0 else base['average_price'],
                apply_tax_estimate=all(p.get('apply_tax_estimate') for p in positions),
                source_type='aggregate', source_id=None, source_transaction_id=None,
                operations_count=len(positions))
    return decorate_position(base)


def build_presentation(positions, summary, goals):
    """Enrich serialized positions/summary once, without quoting again."""
    summary = deepcopy(summary)
    assets = {}
    sections = {}
    for position in positions:
        decorate_position(position)
    def add_aggregates(members):
        groups = defaultdict(list)
        for index in members:
            groups[asset_key(positions[index])].append(index)
        for indices in groups.values():
            if len(indices) > 1 and key(indices) not in assets:
                assets[key(indices)] = aggregate([positions[index] for index in indices])
    add_aggregates(range(len(positions)))
    currency_totals = defaultdict(int)
    for row in summary['by_type']:
        currency_totals[row['currency']] += cents(row['current_brl'])
    for row in summary['by_type']:
        total = currency_totals[row['currency']]
        row['currency_participation_percent'] = percent(cents(row['current_brl']), total) if total > 0 else '0.00'
    for field in ('asset_type_label', 'fixed_income_indexer', 'account_name', 'currency'):
        groups = defaultdict(list)
        for index, position in enumerate(positions):
            groups[position.get(field) or 'Nao informado'].append(index)
        for label, indices in groups.items():
            add_aggregates(indices)
            members = [positions[index] for index in indices]
            currencies = {p['currency'] for p in members}
            currency = next(iter(currencies)) if len(currencies) == 1 else 'BRL'
            suffix = '' if len(currencies) == 1 else '_brl'
            current = sum(cents(p.get('current_value' + suffix)) for p in members)
            cost = sum(cents(p.get('total_cost' + suffix)) for p in members)
            sections[key([field, label])] = dict(currency=currency, current=cents_to_money(current),
                                                 result=cents_to_money(current-cost), result_percent=percent(current-cost, cost) if cost > 0 else '0.00')
    allocation = [dict(row) for row in summary['by_type']]
    goal_keys = {goal['label']: goal['asset_type'] for goal in goals}
    for goal in goals:
        label = 'Renda variável' if goal['asset_type'] == 'stock_usd' else goal['label']
        currency = 'USD' if goal['asset_type'] == 'stock_usd' else 'BRL'
        exists = any(row['label'] == label and (row['currency'] == currency if goal['asset_type'] in ('stock', 'stock_usd') else True) for row in allocation)
        if decimal(goal['target_percent']) > 0 and not exists:
            allocation.append(dict(label=label, currency=currency, count=0, current_brl='0.00', chart_current_brl='0.00', result_brl='0.00', result_percent='0.00'))
    compositions = {}
    for field, rows in [('asset_type_label', allocation), ('fixed_income_indexer', summary['by_indexer']), ('currency', summary['by_currency']), ('account_name', summary['by_account'])]:
        total = sum(max(cents(row['chart_current_brl']), 0) for row in rows)
        for row in rows:
            value = cents(row['chart_current_brl'])
            actual = Decimal(value) * 100 / total if total > 0 else Decimal(0)
            goal_key = 'stock_usd' if row['label'] == 'Renda variável' and row['currency'] == 'USD' else goal_keys.get(row['label'])
            target = next((decimal(g['target_percent']) for g in goals if g['asset_type'] == goal_key), Decimal(0))
            deviation = actual-target
            target_cents = int((Decimal(total)*target/100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
            row.update(participation_percent=str(actual), target_percent=str(target), deviation_percent=str(deviation),
                       deviation_value=cents_to_money(abs(value-target_cents)),
                       deviation_level='over' if deviation > Decimal('0.005') else 'under' if deviation < Decimal('-0.005') else 'equal')
            members = [p for p in positions if portfolio_group_label(p, field) == row['label'] and p['currency'] == row['currency']]
            group_total = sum(p['current_value_brl_cents'] for p in members)
            compositions[key([field, row['label'], row['currency']])] = dict(total=cents_to_money(group_total), members=[dict(
                name=p.get('asset_name') or p.get('asset_identifier') or 'Ativo sem nome',
                identifier=p.get('asset_identifier') or p.get('account_name') or 'Sem código', currency=p['currency'],
                value=p['current_value_brl'], percent=percent(p['current_value_brl_cents'], group_total) if group_total > 0 else '0.00') for p in members])
    return dict(asset_groups=assets, sections=sections,
                allocation=allocation, compositions=compositions, analysis=summary)


def preview(data, error_type):
    """Advisory arithmetic only; the mutation validates actual ownership/balances."""
    def number(value):
        raw = str(value or '0').strip()
        if ',' in raw:
            raw = raw.replace('.', '').replace(',', '.')
        try:
            result = Decimal(raw)
            if not result.is_finite() or abs(result) > Decimal('1e15'):
                raise ValueError
            return max(result, Decimal(0))
        except (ValueError, InvalidOperation):
            raise error_type('Informe um valor numérico válido.') from None
    if data.get('kind') == 'goals':
        goals = data.get('goals')
        if not isinstance(goals, list) or len(goals) > 50 or any(not isinstance(goal, dict) for goal in goals):
            raise error_type('Metas inválidas.')
        total = sum((number(goal.get('target_percent')) for goal in goals), Decimal(0))
        return dict(total_percent=str(total), valid=total == 100)
    if data.get('kind') != 'redemption':
        raise error_type('Prévia inválida.')
    quantity = number(data.get('quantity')).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    available = number(data.get('available_quantity'))
    unit = money_to_cents(str(number(data.get('unit_price'))).replace('.', ','))
    fees = money_to_cents(str(number(data.get('fees'))).replace('.', ','))
    gross = int((quantity*unit).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    errors = dict(quantity='A quantidade excede o saldo disponível.' if quantity > available else '',
                  fees='As taxas não podem superar o valor bruto.' if fees > gross else '')
    return dict(gross_amount=cents_to_money(gross), amount=cents_to_money(max(gross-fees, 0)),
                remaining_quantity=str(max(available-quantity, Decimal(0))), errors=errors)
