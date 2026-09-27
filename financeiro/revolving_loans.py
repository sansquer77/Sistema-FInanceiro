from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from http import HTTPStatus

from financeiro.accounts import SUPPORTED_CURRENCIES, money_to_cents
from financeiro.database import begin_immediate, get_connection
from financeiro.calendar_rules import add_months


class RevolvingLoanError(ValueError):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


RATE_PERIODS = {"daily", "monthly"}
CAPITALIZATIONS = {"daily", "monthly"}
DEBT_TYPES = {"overdraft", "card_revolving"}
MAX_RATE_MICROS = 10_000_000  # 1,000% effective per entered period.
MAX_PROJECTED_BALANCE_CENTS = 9_000_000_000_000_000_000


def round_cents(value: Decimal) -> int:
    if value > MAX_PROJECTED_BALANCE_CENTS:
        raise RevolvingLoanError(
            "O saldo projetado excedeu o limite numérico. Aumente o orçamento mensal ou revise a taxa e a data-base."
        )
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def effective_daily_rate(rate_micros: int, rate_period: str) -> Decimal:
    """Convert an effective monthly quote with the documented 30-day basis."""
    rate = Decimal(int(rate_micros)) / Decimal(1_000_000)
    if rate_period == "daily":
        return rate
    if rate_period != "monthly" or rate < 0:
        raise RevolvingLoanError("Confira a unidade e o valor da taxa.")
    return (Decimal(1) + rate) ** (Decimal(1) / Decimal(30)) - Decimal(1)


def _accrue_interval(balance: int, start: date, end: date, rate_micros: int,
                     rate_period: str, capitalization: str) -> tuple[int, int]:
    if end <= start or balance <= 0:
        return balance, 0
    daily_rate = effective_daily_rate(rate_micros, rate_period)
    total_interest = 0
    cursor = start
    if capitalization == "daily":
        while cursor < end:
            interest = round_cents(Decimal(balance) * daily_rate)
            balance += interest
            total_interest += interest
            cursor = date.fromordinal(cursor.toordinal() + 1)
        return balance, total_interest

    monthly_rate = Decimal(rate_micros) / Decimal(1_000_000)
    while cursor < end:
        boundary = add_months(cursor, 1)
        if boundary <= end:
            if rate_period == "monthly":
                interest = round_cents(Decimal(balance) * monthly_rate)
            else:
                days = (boundary - cursor).days
                interest = round_cents(Decimal(balance) * ((Decimal(1) + daily_rate) ** days - Decimal(1)))
            balance += interest
            total_interest += interest
            cursor = boundary
            continue
        days = (end - cursor).days
        # An incomplete monthly period follows the documented 30-day daily
        # equivalent, capitalized once per elapsed calendar day.
        while days > 0:
            interest = round_cents(Decimal(balance) * daily_rate)
            balance += interest
            total_interest += interest
            cursor = date.fromordinal(cursor.toordinal() + 1)
            days -= 1
    return balance, total_interest


def project_revolving_balance(
    balance_cents: int,
    balance_date: str,
    rate_micros: int | None,
    rate_period: str | None,
    capitalization: str,
    payments: list[dict],
    through_date: str,
) -> dict:
    """Project an open balance, applying each payment at the start of its date.

    Monetary inputs and outputs are cents. The balance is considered current at
    the beginning of balance_date; elapsed calendar days accrue before the next
    payment date. A monthly quote with daily capitalization uses the 30-day
    equivalent described in the loans spec.
    """
    try:
        current_date = date.fromisoformat(balance_date)
        final_date = date.fromisoformat(through_date)
        normalized = []
        for item in payments:
            payment_date = date.fromisoformat(str(item["date"]))
            amount = int(item["amount_cents"])
            if amount < 0:
                raise ValueError("negative payment")
            if payment_date > final_date:
                continue
            normalized.append((payment_date, amount))
    except (TypeError, ValueError, KeyError) as exc:
        raise RevolvingLoanError("Confira as datas e os pagamentos do contrato rotativo.") from exc
    if balance_cents < 0 or final_date < current_date:
        raise RevolvingLoanError("A data final deve ser igual ou posterior à data-base.")
    if capitalization not in CAPITALIZATIONS:
        raise RevolvingLoanError("Escolha capitalização diária ou mensal.")
    if rate_micros is None:
        if normalized:
            raise RevolvingLoanError("Informe a taxa para projetar juros do contrato.")
        return {"balance_cents": int(balance_cents), "interest_cents": 0,
                "payments_cents": 0, "days": (final_date - current_date).days,
                "estimated": True}
    if rate_period not in RATE_PERIODS:
        raise RevolvingLoanError("Informe se a taxa efetiva é diária ou mensal.")
    rate = Decimal(int(rate_micros)) / Decimal(1_000_000)
    if rate < 0 or int(rate_micros) > MAX_RATE_MICROS:
        raise RevolvingLoanError("A taxa informada está fora do intervalo aceito.")

    normalized.sort(key=lambda item: item[0])
    balance = int(balance_cents)
    interest_total = 0
    payments_total = 0
    cursor_date = current_date

    for payment_date, amount in normalized:
        if payment_date < current_date:
            continue
        accrued_balance, accrued = _accrue_interval(
            balance, cursor_date, payment_date, int(rate_micros), str(rate_period), capitalization
        )
        balance = accrued_balance
        interest_total += accrued
        applied = min(balance, amount)
        balance -= applied
        payments_total += applied
        cursor_date = payment_date

    accrued_balance, accrued = _accrue_interval(
        balance, cursor_date, final_date, int(rate_micros), str(rate_period), capitalization
    )
    balance = accrued_balance
    interest_total += accrued
    return {"balance_cents": balance, "interest_cents": interest_total,
            "payments_cents": payments_total, "days": (final_date - current_date).days,
            "estimated": bool(rate_period == "monthly" or capitalization == "monthly")}


def _price_offer(principal_cents: int, rate_micros: int, installments: int) -> dict:
    if principal_cents <= 0 or not 1 <= installments <= 1200 or not 0 <= rate_micros <= MAX_RATE_MICROS:
        raise RevolvingLoanError("Confira principal, taxa mensal e prazo da proposta Price.")
    rate = Decimal(rate_micros) / Decimal(1_000_000)
    if rate == 0:
        payment = round_cents(Decimal(principal_cents) / installments)
    else:
        factor = (Decimal(1) + rate) ** installments
        payment = round_cents(Decimal(principal_cents) * rate * factor / (factor - 1))
    balance = principal_cents
    total_paid = interest_total = 0
    for index in range(installments):
        interest = round_cents(Decimal(balance) * rate)
        due = balance + interest
        paid = due if index == installments - 1 else min(due, payment)
        balance = max(0, due - paid)
        interest_total += interest
        total_paid += paid
    if balance:
        raise RevolvingLoanError("A proposta Price não quita o principal no prazo informado.")
    return {"installment_cents": payment, "installments": installments,
            "total_paid_cents": total_paid, "interest_cents": interest_total,
            "principal_cents": principal_cents}


def simulate_revolving_repayment(
    loan: dict,
    monthly_payment_cents: int,
    first_payment_date: str,
    extraordinary_payment_cents: int = 0,
    extraordinary_payment_date: str | None = None,
    price_principal_cents: int | None = None,
    price_rate_micros: int | None = None,
    price_installments: int | None = None,
) -> dict:
    """Compare a dated payment plan and optional Price offer without persistence."""
    try:
        balance = int(loan["balance_cents"])
        balance_date = date.fromisoformat(str(loan["balance_date"]))
        first_due = date.fromisoformat(first_payment_date)
        monthly_payment = int(monthly_payment_cents)
        extraordinary = int(extraordinary_payment_cents)
    except (KeyError, TypeError, ValueError) as exc:
        raise RevolvingLoanError("Confira o saldo e as datas do estudo.") from exc
    rate_micros = loan.get("rate_micros")
    rate_period = loan.get("rate_period")
    capitalization = str(loan.get("capitalization") or "daily")
    if rate_micros is None:
        raise RevolvingLoanError("Informe a taxa do contrato antes de estudar juros e quitação.")
    if first_due < balance_date or monthly_payment <= 0 or extraordinary < 0:
        raise RevolvingLoanError("A primeira data deve ser igual ou posterior à data-base e o pagamento mensal deve ser positivo.")
    extra_date = None
    if extraordinary:
        try:
            extra_date = date.fromisoformat(str(extraordinary_payment_date or ""))
        except ValueError as exc:
            raise RevolvingLoanError("Informe a data da amortização extraordinária.") from exc
        if extra_date < balance_date:
            raise RevolvingLoanError("A data da amortização não pode ser anterior à data-base.")

    schedule: dict[date, int] = {}
    max_months = 120
    for month in range(max_months):
        due = add_months(first_due, month)
        schedule[due] = monthly_payment
    if extra_date is not None:
        schedule[extra_date] = schedule.get(extra_date, 0) + extraordinary

    cursor = balance_date
    processed_events: set[date] = set()
    balance_after_plan = balance
    interest_total = paid_total = 0
    payoff_month = payoff_date = None
    horizon_date = add_months(first_due, max_months - 1)
    if extra_date is not None and extra_date > horizon_date:
        raise RevolvingLoanError("A data da amortização extraordinária deve estar dentro do horizonte de 120 meses.")
    for month in range(1, max_months + 1):
        due = add_months(first_due, month - 1)
        due_events = sorted(event_date for event_date in schedule
                            if event_date not in processed_events and cursor <= event_date <= due)
        for event_date in due_events:
            projection = project_revolving_balance(
                balance_after_plan, cursor.isoformat(), int(rate_micros), str(rate_period),
                capitalization, [{"date": event_date.isoformat(), "amount_cents": schedule[event_date]}],
                event_date.isoformat(),
            )
            balance_after_plan = int(projection["balance_cents"])
            interest_total += int(projection["interest_cents"])
            paid_total += int(projection["payments_cents"])
            cursor = event_date
            processed_events.add(event_date)
            if balance_after_plan == 0:
                payoff_month, payoff_date = month, event_date
                break
        if payoff_date is not None:
            break
        if cursor < due:
            # Every regular due date is in schedule. This branch handles only an
            # extraordinary payment on a non-due date before that installment.
            projection = project_revolving_balance(
                balance_after_plan, cursor.isoformat(), int(rate_micros), str(rate_period),
                capitalization, [{"date": due.isoformat(), "amount_cents": schedule[due]}], due.isoformat(),
            )
            balance_after_plan = int(projection["balance_cents"])
            interest_total += int(projection["interest_cents"])
            paid_total += int(projection["payments_cents"])
            cursor = due
            if balance_after_plan == 0:
                payoff_month, payoff_date = month, due
                break
    if payoff_date is not None:
        horizon_date = payoff_date
    baseline = project_revolving_balance(
        balance, balance_date.isoformat(), int(rate_micros), str(rate_period), capitalization,
        [], horizon_date.isoformat(),
    )
    price_offer = None
    provided_price = (price_principal_cents is not None, price_rate_micros is not None,
                      price_installments is not None)
    if any(provided_price) and not all(provided_price):
        raise RevolvingLoanError("Para comparar a proposta Price, informe principal, taxa mensal e prazo.")
    if all(provided_price):
        price_offer = _price_offer(int(price_principal_cents), int(price_rate_micros), int(price_installments))
        price_offer["cheaper"] = (None if payoff_date is None
                                  else price_offer["total_paid_cents"] < paid_total)
    return {
        "currency": loan["currency"], "estimated": True,
        "horizon_months": payoff_month if payoff_month is not None else max_months,
        "revolving": {"paid_off": payoff_date is not None, "months": payoff_month,
                      "payoff_date": payoff_date.isoformat() if payoff_date else None,
                      "total_paid_cents": paid_total, "interest_cents": interest_total,
                      "ending_balance_cents": balance_after_plan},
        "no_payment": {"horizon_date": horizon_date.isoformat(),
                       "interest_cents": int(baseline["interest_cents"]),
                       "ending_balance_cents": int(baseline["balance_cents"])},
        "price_offer": price_offer,
    }


def _normalize_payload(data: dict) -> dict:
    name = str(data.get("name") or "").strip()
    debt_type = str(data.get("debt_type") or "overdraft").strip().lower()
    currency = str(data.get("currency") or "BRL").strip().upper()
    balance_date = str(data.get("balance_date") or "").strip()
    rate_period = str(data.get("rate_period") or "").strip().lower() or None
    capitalization = str(data.get("capitalization") or "daily").strip().lower()
    try:
        date.fromisoformat(balance_date)
        balance_cents = money_to_cents(data.get("balance"))
        raw_rate = data.get("rate_percent")
        rate_micros = round(float(str(raw_rate).replace(",", ".")) * 10_000) if raw_rate not in (None, "") else None
    except (TypeError, ValueError, OverflowError) as exc:
        raise RevolvingLoanError("Confira o saldo, a taxa e a data-base.") from exc
    if not name:
        raise RevolvingLoanError("Informe o nome da dívida.")
    if debt_type not in DEBT_TYPES or currency not in SUPPORTED_CURRENCIES:
        raise RevolvingLoanError("Confira a modalidade e a moeda da dívida.")
    if balance_cents < 0:
        raise RevolvingLoanError("O saldo não pode ser negativo.")
    if capitalization not in CAPITALIZATIONS:
        raise RevolvingLoanError("Escolha capitalização diária ou mensal.")
    if rate_micros is not None and (rate_period not in RATE_PERIODS or not 0 <= rate_micros <= MAX_RATE_MICROS):
        raise RevolvingLoanError("Informe uma taxa válida e sua unidade diária ou mensal.")
    if rate_micros is None:
        rate_period = None
    source_card_id = data.get("source_card_id")
    try:
        source_card_id = int(source_card_id) if source_card_id not in (None, "") else None
    except (TypeError, ValueError) as exc:
        raise RevolvingLoanError("Cartão de origem inválido.") from exc
    if (debt_type == "card_revolving") != (source_card_id is not None):
        raise RevolvingLoanError("Selecione o cartão de origem da dívida rotativa.")
    return {"name": name, "debt_type": debt_type, "currency": currency,
            "balance_cents": balance_cents, "balance_date": balance_date,
            "rate_micros": rate_micros, "rate_period": rate_period,
            "capitalization": capitalization, "source_card_id": source_card_id}


def _record_terms(conn: sqlite3.Connection, user_id: int, loan_id: int, item: dict) -> None:
    conn.execute(
        """INSERT INTO revolving_loan_terms_history
           (user_id, revolving_loan_id, effective_date, balance_cents, rate_micros, rate_period, capitalization)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, loan_id, item["balance_date"], item["balance_cents"],
         item["rate_micros"], item["rate_period"], item["capitalization"]),
    )


def create_revolving_loan(user_id: int, data: dict) -> dict:
    with get_connection() as conn:
        begin_immediate(conn)
        return create_revolving_loan_with_conn(conn, user_id, data)


def create_revolving_loan_with_conn(conn: sqlite3.Connection, user_id: int, data: dict) -> dict:
    item = _normalize_payload(data)
    if item["debt_type"] == "card_revolving":
        raise RevolvingLoanError("O rotativo do cartão é acompanhado a partir do pagamento parcial da fatura.")
    if item["source_card_id"] is not None:
        card = conn.execute("SELECT id, name, currency FROM credit_cards WHERE id=? AND user_id=? AND archived_at IS NULL",
                            (item["source_card_id"], user_id)).fetchone()
        if not card:
            raise RevolvingLoanError("Cartão de origem não encontrado.", HTTPStatus.NOT_FOUND)
        if str(card["currency"]).upper() != item["currency"]:
            raise RevolvingLoanError("A moeda do contrato deve ser igual à do cartão.")
    cursor = conn.execute(
        """INSERT INTO revolving_loans
           (user_id, name, debt_type, currency, balance_cents, balance_date,
            rate_micros, rate_period, capitalization, source_card_id, review_required)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, item["name"], item["debt_type"], item["currency"], item["balance_cents"],
         item["balance_date"], item["rate_micros"], item["rate_period"], item["capitalization"],
         item["source_card_id"], int(item["rate_micros"] is None)),
    )
    _record_terms(conn, user_id, int(cursor.lastrowid), item)
    return dict(conn.execute("SELECT * FROM revolving_loans WHERE id=? AND user_id=?",
                             (cursor.lastrowid, user_id)).fetchone())


def list_revolving_loans(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.*, c.name source_card_name FROM revolving_loans r
               LEFT JOIN credit_cards c ON c.id=r.source_card_id AND c.user_id=r.user_id
               WHERE r.user_id=? ORDER BY CASE r.status WHEN 'active' THEN 0 ELSE 1 END, r.currency, r.name""",
            (user_id,),
        ).fetchall()
        result = [dict(row) for row in rows]
        for item in result:
            item["terms_history"] = [dict(row) for row in conn.execute(
                """SELECT effective_date, balance_cents, rate_micros, rate_period, capitalization
                   FROM revolving_loan_terms_history WHERE user_id=? AND revolving_loan_id=?
                   ORDER BY effective_date DESC, id DESC""", (user_id, item["id"]))]
            linked_payments = [dict(row) for row in conn.execute(
                """SELECT t.id transaction_id, t.amount_cents, t.date, t.description, t.reconciled_at, p.recognized
                   FROM revolving_loan_payment_links p JOIN transactions t
                     ON t.id=p.transaction_id AND t.user_id=p.user_id
                   WHERE p.user_id=? AND p.revolving_loan_id=? AND p.valid=1
                   ORDER BY t.date, t.id""", (user_id, item["id"]))]
            item["payments"] = [payment for payment in linked_payments if payment["recognized"] and payment["reconciled_at"]]
            item["pending_payments"] = [payment for payment in linked_payments if not payment["recognized"] or not payment["reconciled_at"]]
        return result


def update_revolving_loan(user_id: int, loan_id: int, data: dict) -> dict:
    with get_connection() as conn:
        begin_immediate(conn)
        return update_revolving_loan_with_conn(conn, user_id, loan_id, data)


def update_revolving_loan_with_conn(conn: sqlite3.Connection, user_id: int, loan_id: int, data: dict) -> dict:
    item = _normalize_payload(data)
    existing = conn.execute("SELECT * FROM revolving_loans WHERE id=? AND user_id=? AND status='active'",
                            (loan_id, user_id)).fetchone()
    if not existing:
        raise RevolvingLoanError("Dívida rotativa ativa não encontrada.", HTTPStatus.NOT_FOUND)
    if item["source_card_id"] != existing["source_card_id"]:
        raise RevolvingLoanError("O cartão de origem não pode ser alterado neste contrato.")
    if item["balance_date"] < str(existing["balance_date"]):
        raise RevolvingLoanError("A data da revisão não pode ser anterior à data-base atual.")
    conn.execute(
        """UPDATE revolving_loans SET name=?, balance_cents=?, balance_date=?, rate_micros=?,
           rate_period=?, capitalization=?, review_required=?, updated_at=CURRENT_TIMESTAMP
           WHERE id=? AND user_id=?""",
        (item["name"], item["balance_cents"], item["balance_date"], item["rate_micros"],
         item["rate_period"], item["capitalization"], int(item["rate_micros"] is None), loan_id, user_id),
    )
    _record_terms(conn, user_id, loan_id, item)
    return dict(conn.execute("SELECT * FROM revolving_loans WHERE id=? AND user_id=?", (loan_id, user_id)).fetchone())


def sync_card_partial_payment_with_conn(conn: sqlite3.Connection, user_id: int, card: dict,
                                        residual_transaction_id: int, balance_cents: int,
                                        balance_date: str) -> int:
    """Attach the residual already created by Card to one monitoring contract."""
    existing = conn.execute("SELECT * FROM revolving_loans WHERE user_id=? AND source_card_id=? AND status='active'",
                            (user_id, card["id"])).fetchone()
    if existing:
        conn.execute("""UPDATE revolving_loans SET balance_cents=?, balance_date=?,
                   source_residual_transaction_id=?, review_required=1, updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND user_id=?""",
                     (balance_cents, balance_date, residual_transaction_id, existing["id"], user_id))
        conn.execute(
            """INSERT INTO revolving_loan_terms_history
               (user_id,revolving_loan_id,effective_date,balance_cents,capitalization)
               VALUES(?,?,?,?, 'daily')""",
            (user_id, existing["id"], balance_date, balance_cents),
        )
        return int(existing["id"])
    cursor = conn.execute(
        """INSERT INTO revolving_loans
           (user_id,name,debt_type,currency,balance_cents,balance_date,source_card_id,
            source_residual_transaction_id,review_required)
           VALUES(?,?,'card_revolving',?,?,?,?,?,1)""",
        (user_id, f"Rotativo do cartão {card['name']}", card["currency"], balance_cents, balance_date,
         card["id"], residual_transaction_id),
    )
    loan_id = int(cursor.lastrowid)
    conn.execute(
        """INSERT INTO revolving_loan_terms_history
           (user_id,revolving_loan_id,effective_date,balance_cents,capitalization)
           VALUES(?,?,?,?, 'daily')""",
        (user_id, loan_id, balance_date, balance_cents),
    )
    return loan_id


def close_card_revolving_with_conn(conn: sqlite3.Connection, user_id: int, card_id: int, resolution: str | None) -> int | None:
    row = conn.execute("SELECT * FROM revolving_loans WHERE user_id=? AND source_card_id=? AND status='active'",
                       (user_id, card_id)).fetchone()
    if not row:
        return None
    if resolution not in {"paid", "swapped"}:
        raise RevolvingLoanError("Informe se o rotativo foi quitado ou trocado por outra dívida.")
    conn.execute("""UPDATE revolving_loans SET status=?, closure_reason=?,
               balance_cents=CASE WHEN ?='paid' THEN 0 ELSE balance_cents END,
               updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?""",
                 (resolution, resolution, resolution, row["id"], user_id))
    return int(row["id"])


def close_revolving_loan(user_id: int, loan_id: int, resolution: str) -> None:
    with get_connection() as conn:
        begin_immediate(conn)
        close_revolving_loan_with_conn(conn, user_id, loan_id, resolution)


def close_revolving_loan_with_conn(conn: sqlite3.Connection, user_id: int, loan_id: int, resolution: str) -> None:
    if resolution not in {"paid", "swapped", "archived"}:
        raise RevolvingLoanError("Escolha quitação definitiva, troca de dívida ou arquivamento.")
    cursor = conn.execute(
        """UPDATE revolving_loans SET status=?, closure_reason=?, updated_at=CURRENT_TIMESTAMP
           ,balance_cents=CASE WHEN ?='paid' THEN 0 ELSE balance_cents END
           WHERE id=? AND user_id=? AND status='active'""",
        (resolution if resolution != "archived" else "archived",
         resolution if resolution in {"paid", "swapped"} else None,
         resolution, loan_id, user_id),
    )
    if cursor.rowcount == 0:
        raise RevolvingLoanError("Dívida rotativa ativa não encontrada.", HTTPStatus.NOT_FOUND)


def link_payment_with_conn(conn: sqlite3.Connection, user_id: int, loan_id: int, transaction_id: int) -> dict:
    loan = conn.execute("SELECT * FROM revolving_loans WHERE id=? AND user_id=? AND status='active'",
                        (loan_id, user_id)).fetchone()
    tx = conn.execute(
        """SELECT t.*, a.currency, c.group_type category_group_type, c.system_key category_system_key
           FROM transactions t JOIN checking_accounts a ON a.id=t.account_id AND a.user_id=t.user_id
           LEFT JOIN categories c ON c.id=t.category_id AND c.user_id=t.user_id
           WHERE t.id=? AND t.user_id=? AND t.archived_at IS NULL""", (transaction_id, user_id)
    ).fetchone()
    if not loan or not tx:
        raise RevolvingLoanError("Dívida rotativa ou lançamento não encontrado.", HTTPStatus.NOT_FOUND)
    if tx["type"] != "expense" or tx["category_group_type"] != "expense" or tx["category_system_key"] != "loan_payment":
        raise RevolvingLoanError("Associe uma despesa da categoria Empréstimos e Financiamentos.")
    if str(tx["currency"]).upper() != str(loan["currency"]).upper():
        raise RevolvingLoanError("A moeda do lançamento deve ser igual à da dívida rotativa.")
    standard_link = conn.execute("SELECT valid FROM loan_payment_links WHERE user_id=? AND transaction_id=?",
                                 (user_id, transaction_id)).fetchone()
    if standard_link and standard_link["valid"]:
        raise RevolvingLoanError("Esse lançamento já está associado a um empréstimo programado.")
    existing = conn.execute("SELECT * FROM revolving_loan_payment_links WHERE user_id=? AND transaction_id=?",
                            (user_id, transaction_id)).fetchone()
    if existing and existing["valid"]:
        if int(existing["revolving_loan_id"]) != loan_id:
            raise RevolvingLoanError("Esse lançamento já está associado a outra dívida.")
        return {"revolving_loan_id": loan_id, "transaction_id": transaction_id}
    if existing:
        conn.execute("""UPDATE revolving_loan_payment_links SET revolving_loan_id=?,valid=1,
                   linked_at=CURRENT_TIMESTAMP WHERE user_id=? AND transaction_id=?""",
                     (loan_id, user_id, transaction_id))
    else:
        conn.execute("INSERT INTO revolving_loan_payment_links(user_id,revolving_loan_id,transaction_id) VALUES(?,?,?)",
                     (user_id, loan_id, transaction_id))
    if tx["reconciled_at"]:
        recognize_payment_with_conn(conn, user_id, transaction_id)
    return {"revolving_loan_id": loan_id, "transaction_id": transaction_id}


def recognize_payment_with_conn(conn: sqlite3.Connection, user_id: int, transaction_id: int) -> None:
    link = conn.execute(
        """SELECT p.*, r.balance_cents, r.balance_date, r.rate_micros, r.rate_period, r.capitalization,
                  t.amount_cents, t.date
           FROM revolving_loan_payment_links p JOIN revolving_loans r
             ON r.id=p.revolving_loan_id AND r.user_id=p.user_id
           JOIN transactions t ON t.id=p.transaction_id AND t.user_id=p.user_id
           WHERE p.user_id=? AND p.transaction_id=? AND p.valid=1 AND p.recognized=0 AND r.status='active'""",
        (user_id, transaction_id),
    ).fetchone()
    if not link:
        return
    payment_date = str(link["date"])
    if payment_date < str(link["balance_date"]):
        conn.execute("UPDATE revolving_loans SET review_required=1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
                     (link["revolving_loan_id"], user_id))
        conn.execute("UPDATE revolving_loan_payment_links SET recognized=1 WHERE id=? AND user_id=?",
                     (link["id"], user_id))
        return
    projection = project_revolving_balance(
        int(link["balance_cents"]), str(link["balance_date"]), link["rate_micros"], link["rate_period"],
        str(link["capitalization"]), [], payment_date,
    )
    accrued_balance = int(projection["balance_cents"])
    amount = int(link["amount_cents"])
    review = amount > accrued_balance
    remaining = max(0, accrued_balance - amount)
    conn.execute("""UPDATE revolving_loans SET balance_cents=?,balance_date=?,review_required=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?""",
                 (remaining, payment_date, int(review), link["revolving_loan_id"], user_id))
    conn.execute("UPDATE revolving_loan_payment_links SET recognized=1 WHERE id=? AND user_id=?",
                 (link["id"], user_id))
    conn.execute(
        """INSERT INTO revolving_loan_terms_history
           (user_id,revolving_loan_id,effective_date,balance_cents,rate_micros,rate_period,capitalization)
           SELECT ?,id,?,balance_cents,rate_micros,rate_period,capitalization
           FROM revolving_loans WHERE id=? AND user_id=?""",
        (user_id, payment_date, link["revolving_loan_id"], user_id),
    )


def invalidate_payment_links_with_conn(conn: sqlite3.Connection, user_id: int, transaction_id: int) -> None:
    cursor = conn.execute("UPDATE revolving_loan_payment_links SET valid=0 WHERE user_id=? AND transaction_id=? AND valid=1",
                          (user_id, transaction_id))
    if cursor.rowcount:
        conn.execute("""UPDATE revolving_loans SET review_required=1,updated_at=CURRENT_TIMESTAMP
                   WHERE user_id=? AND id IN (SELECT revolving_loan_id FROM revolving_loan_payment_links
                                              WHERE user_id=? AND transaction_id=? AND valid=0)""",
                     (user_id, user_id, transaction_id))


def link_payment(user_id: int, loan_id: int, transaction_id: int) -> dict:
    with get_connection() as conn:
        from financeiro.database import begin_immediate
        begin_immediate(conn)
        return link_payment_with_conn(conn, user_id, loan_id, transaction_id)
