from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Iterable

from financeiro.balance_projections import build_projected_negative_balances_for_user
from financeiro.calendar import get_cockpit_calendar
from financeiro.database import get_connection
from financeiro.money import cents_to_money
from financeiro.portfolio_positions import load_open_fixed_income_maturities
from financeiro.secure_config import SecureConfigError, load_email_config
from financeiro.spending_limits import list_spending_limits_with_consumption


def build_cockpit_notifications(
    user_id: int,
    *,
    reference_date: date | None = None,
    portfolio_events: Iterable[dict] | None = None,
    limits_loader: Callable = list_spending_limits_with_consumption,
    calendar_loader: Callable = get_cockpit_calendar,
    totals_loader: Callable | None = None,
    negative_balance_loader: Callable = build_projected_negative_balances_for_user,
    portfolio_positions_loader: Callable | None = None,
) -> dict:
    """Compila notificações financeiras sem depender do snapshot mensal do Cockpit."""
    reference_date = reference_date or date.today()
    month = reference_date.strftime("%Y-%m")

    # spec: cockpit/alertas-cockpit v1.12 — critérios 1, 3, 4, 5, 6, 11 e 22
    critical = _limit_notifications(limits_loader(user_id, month), month)
    # totals_loader permanece como ponto de compatibilidade para integrações que
    # já injetavam o agregador do Cockpit; o formato esperado agora é o evento
    # diário produzido por negative_balance_loader.
    negative_rows = (totals_loader or negative_balance_loader)(user_id, month)
    critical.extend(_negative_balance_notifications(negative_rows, month))

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
    critical.extend(_loan_due_notifications(user_id, reference_date))
    critical.extend(_revolving_zero_balance_notifications(user_id))
    critical.extend(_backup_failure_notifications(user_id))
    critical.extend(_password_recovery_notifications(user_id, reference_date))

    informational = _maturity_notifications(calendar.get("maturity_30_days") or [], reference_date)
    informational.extend(_portfolio_event_notifications(portfolio_events or [], reference_date))
    informational.extend(_revolving_swap_notifications(user_id))
    monthly_close = _monthly_close_notification(user_id, reference_date)
    if monthly_close:
        informational.append(monthly_close)
    _apply_seen_state(user_id, informational)
    for item in informational:
        if item["type"] == "revolving_swap" and item["seen"]:
            item["action"] = None

    critical.sort(key=lambda item: (item["date_or_period"], item["id"]))
    informational.sort(key=lambda item: (item["date_or_period"], item["id"]))
    return {
        "critical": critical,
        "informational": informational,
        "critical_count": len(critical),
        "informational_count": sum(not item["seen"] for item in informational),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _loan_due_notifications(user_id: int, reference_date: date) -> list[dict]:
    due_date = reference_date.isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, name, currency FROM loans
               WHERE user_id=? AND archived_at IS NULL AND next_due_date=?
                 AND remaining_installments > 0""",
            (user_id, due_date),
        ).fetchall()
    return [
        _item(
            f"loan_due:{row['id']}:{due_date}", "loan_due", "loans",
            f"Parcela de {row['name']} vence hoje",
            f"Confira o pagamento do empréstimo em {row['currency']} e associe o lançamento da conta.",
            due_date, "Ver empréstimo", "loans", {"loan_id": row["id"]},
        )
        for row in rows
    ]


def _revolving_zero_balance_notifications(user_id: int) -> list[dict]:
    # spec: emprestimos-quitacao/emprestimos-quitacao v0.61 — critério 97
    # Saldo zerado não encerra o rotativo sozinho; o alerta pede a decisão do usuário.
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, name, currency, balance_date FROM revolving_loans
               WHERE user_id=? AND status='active' AND balance_cents<=0
               ORDER BY name, id""",
            (user_id,),
        ).fetchall()
    return [
        _item(
            f"revolving_zero_balance:{row['id']}", "revolving_zero_balance", "loans",
            f"Saldo zerado: {row['name']}",
            f"O saldo do rotativo em {row['currency']} está zerado. Encerre o acompanhamento como quitação definitiva ou troca de dívida.",
            str(row["balance_date"]), "Encerrar acompanhamento", "loans",
            {"revolving_loan_id": row["id"], "action": "close_revolving"},
        )
        for row in rows
    ]


def _backup_failure_notifications(user_id: int) -> list[dict]:
    # spec: cockpit/alertas-cockpit v1.12 — critério 15
    # Backup policy is installation-wide; only its responsible user can resolve settings.
    with get_connection() as conn:
        row = conn.execute(
            """SELECT updated_at FROM backup_settings
               WHERE id=1 AND configured_by_user_id=? AND last_backup_status='failed'""",
            (user_id,),
        ).fetchone()
    if not row:
        return []
    failed_at = str(row["updated_at"] or "")[:10] or date.today().isoformat()
    return [_item(
        "backup_failure", "backup_failure", "backup",
        "Backup automático não concluído",
        "Revise o destino e a política em Preferências > Backup. O sistema continua disponível.",
        failed_at, "Revisar backup", "user", {"tab": "backup"},
    )]


def _password_recovery_notifications(user_id: int, reference_date: date) -> list[dict]:
    # spec: seguranca/recuperacao-senha v1.2 — critério 8
    try:
        config = load_email_config(user_id)
    except SecureConfigError:
        config = {}
    if all(str(config.get(field) or "").strip() for field in ("sender", "password", "smtp_server")):
        return []
    return [_item(
        "password_recovery_unconfigured", "password_recovery_unconfigured", "security",
        "Configure a recuperação por e-mail",
        "Sem uma senha de app SMTP configurada, você não poderá recuperar o acesso à conta se esquecer sua senha.",
        reference_date.isoformat(), "Configurar recuperação", "user", {"tab": "geral", "section": "email-recovery"},
    )]


def _revolving_swap_notifications(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, name, currency, updated_at FROM revolving_loans
               WHERE user_id=? AND status='swapped' ORDER BY updated_at DESC""", (user_id,)
        ).fetchall()
    return [
        _item(
            f"revolving_swap:{row['id']}", "revolving_swap", "loans",
            f"Cadastre o novo contrato de {row['name']}",
            f"A dívida rotativa em {row['currency']} foi marcada como troca. Confira o demonstrativo do credor e cadastre manualmente o novo contrato Price em Empréstimos e Financiamentos.",
            str(row["updated_at"] or date.today().isoformat())[:10],
            "Cadastrar contrato", "loans", {"revolving_loan_id": row["id"]},
        )
        for row in rows
    ]


def _monthly_close_notification(user_id: int, reference_date: date) -> dict | None:
    previous_month_date = reference_date.replace(day=1) - timedelta(days=1)
    previous_month = previous_month_date.strftime("%Y-%m")
    with get_connection() as conn:
        account_pending = conn.execute(
            """SELECT COUNT(*) AS total, COUNT(DISTINCT t.account_id) AS owners
               FROM transactions t
               JOIN checking_accounts a ON a.id = t.account_id AND a.user_id = t.user_id
               WHERE t.user_id = ? AND t.archived_at IS NULL AND a.archived_at IS NULL
                 AND substr(t.date, 1, 7) = ? AND (t.reconciled_at IS NULL OR t.reconciled_at = '')""",
            (user_id, previous_month),
        ).fetchone()
        card_pending = conn.execute(
            """SELECT COUNT(*) AS total, COUNT(DISTINCT t.credit_card_id) AS owners
               FROM credit_card_transactions t
               JOIN credit_cards c ON c.id = t.credit_card_id AND c.user_id = t.user_id
               WHERE t.user_id = ? AND t.archived_at IS NULL AND c.archived_at IS NULL
                 AND t.invoice_month = ? AND (t.reconciled_at IS NULL OR t.reconciled_at = '')""",
            (user_id, previous_month),
        ).fetchone()
        account_unclassified = conn.execute(
            """SELECT COUNT(*) AS total
               FROM transactions t
               JOIN checking_accounts a ON a.id = t.account_id AND a.user_id = t.user_id
               WHERE t.user_id = ? AND t.archived_at IS NULL AND a.archived_at IS NULL
                 AND substr(t.date, 1, 7) = ? AND t.type IN ('income', 'expense')
                 AND t.category_id IS NULL
                 -- spec: cockpit/alertas-cockpit v1.12 — critérios 23 e 24
                 -- Resgates e créditos de encerramento do Portfólio já têm
                 -- classificação pela origem financeira, mesmo sem categoria.
                 AND NOT EXISTS (
                     SELECT 1 FROM investment_redemptions r
                     WHERE r.user_id = t.user_id AND r.transaction_id = t.id
                 )
                 AND NOT (
                     t.type = 'income'
                     AND t.description LIKE 'Encerramento - %'
                     AND EXISTS (
                         SELECT 1
                         FROM investment_closed_positions p
                         WHERE p.user_id = t.user_id
                           AND p.account_id = t.account_id
                           AND substr(p.closed_at, 1, 10) = t.date
                           AND p.closing_value_cents = t.amount_cents
                     )
                 )""",
            (user_id, previous_month),
        ).fetchone()
        card_unclassified = conn.execute(
            """SELECT COUNT(*) AS total
               FROM credit_card_transactions t
               JOIN credit_cards c ON c.id = t.credit_card_id AND c.user_id = t.user_id
               WHERE t.user_id = ? AND t.archived_at IS NULL AND c.archived_at IS NULL
                 AND t.invoice_month = ? AND t.category_id IS NULL""",
            (user_id, previous_month),
        ).fetchone()
    pending = int(account_pending["total"] or 0) + int(card_pending["total"] or 0)
    owners = int(account_pending["owners"] or 0) + int(card_pending["owners"] or 0)
    unclassified = int(account_unclassified["total"] or 0) + int(card_unclassified["total"] or 0)
    if pending == 0 and unclassified == 0:
        return None
    month_label = _month_label(previous_month)
    details = []
    if pending:
        pending_label = "lançamento" if pending == 1 else "lançamentos"
        details.append(f"{pending} {pending_label} não conciliado(s)")
    if owners:
        details.append(f"{owners} conta(s)/cartão(ões) com pendências")
    if unclassified:
        unclassified_label = "lançamento" if unclassified == 1 else "lançamentos"
        details.append(f"{unclassified} {unclassified_label} sem classificação")
    description = (
        f"{month_label} tem {', '.join(details)}. "
        "Revise o demonstrativo antes de iniciar o novo mês."
    )
    return _item(
        f"monthly_close:{previous_month}", "monthly_close", "cashflow",
        f"Feche {month_label}", description, previous_month,
        "Abrir demonstrativo", "reports", {"month": previous_month, "tab": "statement"}, seen=False,
        actions=[
            {"label": "Abrir demonstrativo", "route": "reports", "params": {"month": previous_month, "tab": "statement"}},
            {"label": "Ver conciliação pendente", "route": "transactions", "params": {"month": previous_month, "status": "pending"}},
            {"label": "Ver sem classificação", "route": "reports", "params": {"month": previous_month, "tab": "unclassified"}},
        ],
    )


def _month_label(month: str) -> str:
    year, month_number = month.split("-")
    names = (
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    )
    return f"{names[int(month_number) - 1]} de {year}"


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
        negative_cents = int(row.get("negative_cents") or 0)
        negative_date = str(row.get("first_negative_date") or "")
        if negative_cents <= 0 or not negative_date:
            continue
        currency = str(row.get("currency") or "BRL")
        account_id = row.get("account_id")
        account_name = str(row.get("account_name") or "Conta")
        formatted_date = _short_date(negative_date)
        causes = list(dict.fromkeys(str(item) for item in (row.get("causes") or []) if str(item).strip()))
        cause_text = _join_causes(causes or ["compromissos previstos"])
        result.append(_item(
            f"projected_negative_balance:{account_id}:{negative_date}", "projected_negative_balance", "cashflow",
            f"Saldo previsto ficará negativo em {formatted_date}",
            f"Conta: {account_name}. Estimativa de -{_localized_money(negative_cents, currency)} após {cause_text}.",
            negative_date, "Ver extrato", "transactions", {"month": month, "account_id": account_id},
        ))
    return result


def _short_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%d/%m")


def _localized_money(cents: int, currency: str) -> str:
    symbol = {"BRL": "R$", "USD": "US$", "EUR": "€"}.get(currency, currency)
    raw = cents_to_money(abs(int(cents)))
    integer, fraction = raw.split(".", 1)
    grouped = f"{int(integer):,}".replace(",", ".")
    return f"{symbol} {grouped},{fraction}"


def _join_causes(causes: list[str]) -> str:
    if len(causes) == 1:
        return causes[0]
    if len(causes) == 2:
        return f"{causes[0]} e {causes[1]}"
    return f"{', '.join(causes[:-1])} e {causes[-1]}"


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
        event_date_text = str(row.get("date") or row.get("event_date") or row.get("payment_date") or "")
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


def _item(item_id, item_type, category, title, description, date_or_period, label, route, params, seen=None, actions=None):
    item = {
        "id": str(item_id), "type": item_type, "category": category,
        "title": str(title)[:45], "description": str(description),
        "date_or_period": str(date_or_period),
        "action": {"label": label, "route": route, "params": params},
    }
    if actions is not None:
        item["actions"] = actions
    if seen is not None:
        item["seen"] = bool(seen)
    return item
