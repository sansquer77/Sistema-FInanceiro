from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from financeiro.credit_cards import list_credit_card_transactions
from financeiro.transactions import list_transactions
from financeiro.database import get_connection
from financeiro.money import cents_to_money
from financeiro.open_debts import get_open_debts, parse_ids
from financeiro.calendar_rules import shift_month


def build_evolution_presentation(evolution):
    # spec: relatorios/relatorios v2.20 — evolução: total, tendência e SMA recursiva
    values = [int(point['total_cents']) for point in evolution]
    trend = None
    if len(values) > 1 and values[0] != 0:
        trend = (values[-1] - values[0]) / abs(values[0]) * 100
    forecast = []
    if values:
        window_size = min(3, len(values))
        window = values[-window_size:]
        for index in range(12):
            # Equivalent to Math.round(mean), without monetary floating point.
            amount = (2 * sum(window) + window_size) // (2 * window_size)
            forecast.append(dict(month=shift_month(evolution[-1]['month'], index + 1), total_cents=amount))
            window = (window + [amount])[-window_size:]
    return dict(evolution=evolution, total_cents=sum(values), trend_percent=trend, forecast=forecast)


def build_statement_report(user_id, month=None, account_ids=None, card_ids=None, currency=None, *, today=None):
    """Monthly expense statement, retaining original currencies and invoice competence."""
    today = today or date.today()
    debts = get_open_debts(user_id, month, account_ids, card_ids, currency, today=today)
    month = debts['month']
    selected_accounts, selected_cards = parse_ids(account_ids), parse_ids(card_ids)
    with get_connection() as conn:
        active_accounts = {row['id'] for row in conn.execute(
            'SELECT id FROM checking_accounts WHERE user_id = ? AND archived_at IS NULL', (user_id,))}
        active_cards = {row['id'] for row in conn.execute(
            'SELECT id FROM credit_cards WHERE user_id = ? AND archived_at IS NULL', (user_id,))}
    owners = {
        'account': active_accounts & set(selected_accounts) if selected_accounts else active_accounts,
        'card': active_cards & set(selected_cards) if selected_cards else active_cards,
    }
    sections = {}
    # spec: relatorios/relatorios v2.20 — demonstrativo mensal e filtros por moeda
    for origin, transactions in (
        ('account', list_transactions(user_id, month=month)),
        ('card', list_credit_card_transactions(user_id, invoice_month=month)),
    ):
        for tx in transactions:
            owner_key = 'account_id' if origin == 'account' else 'credit_card_id'
            if tx['type'] != 'expense' or tx.get('is_credit_card_payment') or tx[owner_key] not in owners[origin]:
                continue
            unit = tx.get('account_currency' if origin == 'account' else 'card_currency') or 'BRL'
            if currency and currency != 'all' and currency != unit:
                continue
            amount = int(Decimal(tx['amount']) * 100)
            item = dict(date=tx['date'], amount_cents=amount, amount=cents_to_money(amount), currency=unit,
                        description=tx.get('description') or '', category=tx.get('category_name') or 'Sem categoria',
                        subcategory=str(tx.get('subcategory_name') or '').strip(), tags=tx.get('tags') or [],
                        source='Conta' if origin == 'account' else 'Cartão',
                        accountName=tx.get('account_name' if origin == 'account' else 'credit_card_name') or '',
                        origin=origin)
            sections.setdefault(unit, []).append(item)
    return dict(month=month, observed_on=today.isoformat(), sections=[
        _statement_section(unit, items, debts['by_currency_cents'].get(unit, 0), month, today)
        for unit, items in sorted(sections.items())
    ])


def _statement_groups(items, total, *, subcategory=False):
    groups = {}
    for item in items:
        label = item['category']
        if subcategory:
            label += ' / ' + (item['subcategory'] or 'Sem subcategoria')
        groups[label] = groups.get(label, 0) + item['amount_cents']
    return [dict(label=label, amount_cents=amount, amount=cents_to_money(amount), share=amount / total if total else 0)
            for label, amount in sorted(groups.items(), key=lambda entry: (-entry[1], entry[0]))]


def _statement_section(currency, items, debt_cents, month, today):
    # spec: relatorios/relatorios v2.20 — média, composição e série diária do demonstrativo
    total = sum(item['amount_cents'] for item in items)
    days = monthrange(*map(int, month.split('-')))[1]
    current_month = today.strftime('%Y-%m')
    divisor = today.day if month == current_month else days if month < current_month else 1
    average = int((Decimal(total) / divisor).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    origins = {origin: [item for item in items if item['origin'] == origin] for origin in ('account', 'card')}
    categories = _statement_groups(items, total)
    distribution = categories[:5]
    remainder = total - sum(row['amount_cents'] for row in distribution)
    if remainder:
        distribution.append(dict(label='Outros', amount_cents=remainder, amount=cents_to_money(remainder), share=remainder / total))
    daily_totals = {}
    for item in items:
        daily_totals[item['date']] = daily_totals.get(item['date'], 0) + item['amount_cents']
    maximum = max(100, *daily_totals.values())
    daily = []
    for number in range(1, days + 1):
        day = f'{month}-{number:02d}'
        amount = daily_totals.get(day, 0)
        daily.append(dict(date=day, amount=cents_to_money(amount), amount_cents=amount, ratio=amount / maximum))
    return dict(currency=currency, total=cents_to_money(total), total_cents=total,
                average=cents_to_money(average), average_cents=average,
                account_total=cents_to_money(sum(item['amount_cents'] for item in origins['account'])),
                card_total=cents_to_money(sum(item['amount_cents'] for item in origins['card'])),
                open_debts=cents_to_money(debt_cents),
                top_category=categories[0] if categories else None,
                top_transaction=max(items, key=lambda item: item['amount_cents'], default=None),
                distribution=distribution, daily=daily,
                composition={origin: _statement_groups(rows, total, subcategory=True) for origin, rows in origins.items()},
                items=sorted(items, key=lambda item: (item['date'], -item['amount_cents'])))


def build_tag_report(user_id: int, month: str | None = None) -> dict:
    # spec: relatorios/relatorios v2.20 — relatório de tags agrupado por tag com
    # Receitas, Despesas, Saldo e Investimentos, separados por moeda.
    transactions = list_transactions(user_id, month=month)
    card_transactions = list_credit_card_transactions(user_id, invoice_month=month)
    groups: dict[str, dict] = {}
    for transaction in transactions:
        if transaction.get("is_credit_card_payment"):
            continue
        _accumulate_tag_groups(groups, transaction, "account")
    for transaction in card_transactions:
        _accumulate_tag_groups(groups, transaction, "card")
    rows = sorted(
        groups.values(),
        key=lambda row: (
            -(row["expense_cents"] + row["investment_cents"]),
            row["tag"],
        ),
    )
    return {
        "month": month,
        "tags": [_serialize_tag_row(row) for row in rows],
    }


def _accumulate_tag_groups(
    groups: dict[str, dict],
    transaction: dict,
    source: str,
) -> None:
    report_type = _report_type_for(transaction)
    if not report_type:
        return
    tags = transaction.get("tags") or []
    if not tags:
        return
    amount_cents = int(Decimal(transaction.get("amount") or "0") * 100)
    currency = (
        transaction.get("currency")
        or transaction.get("card_currency")
        or transaction.get("account_currency")
        or "BRL"
    )
    for tag in tags:
        if tag not in groups:
            groups[tag] = {
                "tag": tag,
                "income_cents": 0,
                "expense_cents": 0,
                "investment_cents": 0,
                "income_by_currency": {},
                "expense_by_currency": {},
                "investment_by_currency": {},
                "count": 0,
            }
        group = groups[tag]
        group["count"] += 1
        if report_type == "income":
            group["income_cents"] += amount_cents
            group["income_by_currency"][currency] = group["income_by_currency"].get(currency, 0) + amount_cents
        elif report_type == "expense":
            group["expense_cents"] += amount_cents
            group["expense_by_currency"][currency] = group["expense_by_currency"].get(currency, 0) + amount_cents
        elif report_type == "investment":
            group["investment_cents"] += amount_cents
            group["investment_by_currency"][currency] = group["investment_by_currency"].get(currency, 0) + amount_cents


def _report_type_for(transaction: dict) -> str:
    tx_type = transaction.get("type")
    if tx_type == "income":
        return "income"
    if tx_type == "expense":
        return "expense"
    if tx_type == "investment":
        return "investment"
    return ""


def _serialize_tag_row(row: dict) -> dict:
    return {
        "tag": row["tag"],
        "count": row["count"],
        "income_cents": row["income_cents"],
        "expense_cents": row["expense_cents"],
        "investment_cents": row["investment_cents"],
        "balance_cents": row["income_cents"] - row["expense_cents"],
        "income_by_currency": row["income_by_currency"],
        "expense_by_currency": row["expense_by_currency"],
        "investment_by_currency": row["investment_by_currency"],
    }
