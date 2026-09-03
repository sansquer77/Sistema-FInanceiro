from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable, Iterable

from financeiro.balance_projections import build_currency_totals_for_user
from financeiro.calendar import get_cockpit_calendar
from financeiro.database import get_connection
from financeiro.money import cents_to_money, decimal_to_cents
from financeiro.portfolio_positions import load_open_fixed_income_maturities
from financeiro.spending_limits import list_spending_limits_with_consumption


def build_cockpit_notifications(
    user_id: int,
    *,
    reference_date: date | None = None,
    portfolio_events: Iterable[dict] | None = None,
    limits_loader: Callable = list_spending_limits_with_consumption,
    calendar_loader: Callable = get_cockpit_calendar,
    totals_loader: Callable = build_currency_totals_for_user,
    portfolio_positions_loader: Callable | None = None,
) -> dict:
    """Compila notificações financeiras sem depender do snapshot mensal do Cockpit."""
    reference_date = reference_date or date.today()
    month = reference_date.strftime("%Y-%m")

    # spec: cockpit/alertas-cockpit v0.8 — critérios 1, 3, 4, 5, 6 e 11
    critical = _limit_notifications(limits_loader(user_id, month), month)
    critical.extend(_negative_balance_notifications(totals_loader(user_id, month), month))

    try:
        positions = list(
            (portfolio_positions_loader or _load_local_maturity_positions)(user_id) or []
        )
    except Exception:
        # Dados de mercado/maturidade são informativos e nunca viram alerta crítico.
        positions = []
    calendar = calendar_loader(user_id, reference_date=reference_date, portfolio_positions=positions)
    critical.extend(_overdue_account_notifications(calendar.get("overdue_payables") or []))
    critical.extend(_overdue_invoice_notifications(user_id, reference_date))

    informational = _maturity_notifications(calendar.get("maturity_30_days") or [], reference_date)
    informational.extend(_portfolio_event_notifications(portfolio_events or [], reference_date))
    _apply_seen_state(user_id, informational)

    critical.sort(key=lambda item: (item["date_or_period"], item["id"]))
    informational.sort(key=lambda item: (item["date_or_period"], item["id"]))
    return {
        "critical": critical,
        "informational": informational,
        "critical_count": len(critical),
        "informational_count": sum(not item["seen"] for item in informational),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def mark_informational_seen(user_id: int, notification_ids: Iterable[str]) -> int:
    ids = sorted({str(item or "").strip() for item in notification_ids if str(item or "").strip()})
    if len(ids) > 500 or any(len(item) > 200 for item in ids):
        raise ValueError("Lista de notificações inválida.")
    if not ids:
        return 0
    with get_connection() as conn:
        before = conn.total_changes
        conn.executemany(
            "INSERT OR IGNORE INTO notification_reads (user_id, notification_id) VALUES (?, ?)",
            ((user_id, item) for item in ids),
        )
        return conn.total_changes - before


def _limit_notifications(rows: Iterable[dict], month: str) -> list[dict]:
    result = []
    for row in rows:
        spent = int(row.get("spent_amount_cents") or 0)
        limit = int(row.get("limit_amount_cents") or 0)
        if limit <= 0 or spent <= limit:
            continue
        label = row.get("subcategory_name") or row.get("category_name") or "categoria"
        percent = (spent * 100) // limit
        result.append(_item(
            f"limit_exceeded:{row['id']}:{month}", "limit_exceeded", "limits",
            f"Limite de {label} excedido",
            f"Gastos atingiram R$ {cents_to_money(spent)} de R$ {cents_to_money(limit)} planejados ({percent}%).",
            month, "Ver limites", "limits", {"month": month},
        ))
    return result


def _negative_balance_notifications(rows: Iterable[dict], month: str) -> list[dict]:
    result = []
    for row in rows:
        amount = Decimal(str(row.get("current") or "0"))
        if amount >= 0:
            continue
        cents = decimal_to_cents(abs(amount))
        currency = str(row.get("currency") or "BRL")
        result.append(_item(
            f"projected_negative_balance:{currency}:{month}", "projected_negative_balance", "cashflow",
            f"Saldo projetado negativo em {currency}",
            f"A projeção do mês indica saldo negativo de {currency} {cents_to_money(cents)}.",
            month, "Ver extrato", "transactions", {"month": month},
        ))
    return result


def _overdue_account_notifications(rows: Iterable[dict]) -> list[dict]:
    return [
        _item(
            f"overdue_payable:{row['id']}:{row['date']}", "overdue_payable", "cashflow",
            "Conta vencida não conciliada",
            f"{row.get('description') or 'Despesa'} venceu em {row['date']} na conta {row.get('account_name') or ''}.",
            row["date"], "Ver extrato", "transactions", {"account_id": row.get("account_id")},
        )
        for row in rows
    ]


def _overdue_invoice_notifications(user_id: int, reference_date: date) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.currency, c.due_day, t.invoice_month,
                   SUM(CASE WHEN t.type = 'expense' THEN t.amount_cents
                            WHEN t.type = 'income' THEN -t.amount_cents ELSE 0 END) AS amount_cents
            FROM credit_card_transactions t
            JOIN credit_cards c ON c.id = t.credit_card_id AND c.user_id = t.user_id
            WHERE t.user_id = ? AND t.archived_at IS NULL AND c.archived_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM credit_card_payments p
                  WHERE p.user_id = t.user_id AND p.credit_card_id = t.credit_card_id
                    AND p.invoice_month = t.invoice_month
              )
            GROUP BY c.id, t.invoice_month
            """,
            (user_id,),
        ).fetchall()
    result = []
    for row in rows:
        year, month = map(int, str(row["invoice_month"]).split("-"))
        due = date(year, month, min(int(row["due_day"]), monthrange(year, month)[1]))
        amount = int(row["amount_cents"] or 0)
        if due >= reference_date or amount <= 0:
            continue
        result.append(_item(
            f"overdue_invoice:{row['id']}:{row['invoice_month']}", "overdue_invoice", "invoices",
            f"Fatura vencida: {row['name']}",
            f"Fatura de {row['invoice_month']} venceu em {due.isoformat()}.",
            due.isoformat(), "Ver cartões", "cards", {"card_id": row["id"], "month": row["invoice_month"]},
        ))
    return result


def _load_local_maturity_positions(user_id: int) -> list[dict]:
    """Adapta a leitura compartilhada para a assinatura injetável do agregador."""
    with get_connection() as conn:
        return load_open_fixed_income_maturities(conn, user_id)


def _maturity_notifications(rows: Iterable[dict], reference_date: date) -> list[dict]:
    result = []
    for row in rows:
        maturity = date.fromisoformat(str(row["maturity_date"]))
        if not (reference_date <= maturity <= reference_date + timedelta(days=14)):
            continue
        identifier = row.get("position_id") or row.get("asset_identifier") or row["maturity_date"]
        result.append(_item(
            f"maturity_upcoming:{identifier}:{row['maturity_date']}", "maturity_upcoming", "portfolio",
            f"Vencimento: {row.get('asset_name') or 'Renda fixa'}",
            f"O investimento vence em {row['maturity_date']}.", row["maturity_date"],
            "Abrir calendário", "calendar", {}, seen=False,
        ))
    return result


def _portfolio_event_notifications(rows: Iterable[dict], reference_date: date) -> list[dict]:
    week_start = reference_date - timedelta(days=reference_date.weekday())
    week_end = week_start + timedelta(days=6)
    result = []
    for row in rows:
        event_date_text = str(row.get("payment_date") or row.get("event_date") or "")
        try:
            event_date = date.fromisoformat(event_date_text)
        except ValueError:
            continue
        if not (week_start <= event_date <= week_end):
            continue
        identifier = str(row.get("asset_identifier") or row.get("asset_name") or "ativo")
        event_id = row.get("id") or f"{identifier}:{event_date_text}"
        source = str(row.get("source") or "fonte externa")
        confidence = str(row.get("confirmation_level") or "detectado")
        result.append(_item(
            f"dividend_week:{event_id}", "dividend_incoming", "portfolio",
            f"Provento {identifier} detectado",
            f"Evento informado para {event_date_text}. Fonte: {source}; confirmação: {confidence}.",
            event_date_text, "Ver eventos", "portfolio", {"tab": "events"}, seen=False,
        ))
    return result


def _apply_seen_state(user_id: int, rows: list[dict]) -> None:
    if not rows:
        return
    ids = [row["id"] for row in rows]
    placeholders = ",".join("?" for _ in ids)
    with get_connection() as conn:
        seen = {row["notification_id"] for row in conn.execute(
            f"SELECT notification_id FROM notification_reads WHERE user_id = ? AND notification_id IN ({placeholders})",
            (user_id, *ids),
        ).fetchall()}
    for row in rows:
        row["seen"] = row["id"] in seen


def _item(item_id, item_type, category, title, description, date_or_period, label, route, params, seen=None):
    item = {
        "id": str(item_id), "type": item_type, "category": category,
        "title": str(title)[:45], "description": str(description),
        "date_or_period": str(date_or_period),
        "action": {"label": label, "route": route, "params": params},
    }
    if seen is not None:
        item["seen"] = bool(seen)
    return item
