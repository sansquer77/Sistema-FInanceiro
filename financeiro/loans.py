from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from http import HTTPStatus

from financeiro.database import begin_immediate, get_connection
from financeiro.accounts import money_to_cents
from financeiro.accounts import SUPPORTED_CURRENCIES
from financeiro.calendar_rules import add_months


class LoanError(ValueError):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


def invalidate_loan_payment_links(conn: sqlite3.Connection, user_id: int, transaction_id: int) -> None:
    conn.execute(
        """UPDATE loan_payment_links SET valid=0 WHERE user_id=? AND transaction_id=? AND valid=1""",
        (user_id, transaction_id),
    )
    conn.execute(
        """UPDATE loans SET review_required=1, updated_at=CURRENT_TIMESTAMP
           WHERE user_id=? AND id IN (SELECT loan_id FROM loan_payment_links WHERE user_id=? AND transaction_id=? AND valid=0)""",
        (user_id, user_id, transaction_id),
    )


def _loan_payload(data: dict) -> dict:
    name = str(data.get("name") or "").strip()
    currency = str(data.get("currency") or "BRL").strip().upper()
    loan_type = str(data.get("loan_type") or "other").strip().lower()
    if not name:
        raise LoanError("Informe o nome do empréstimo.")
    if currency not in SUPPORTED_CURRENCIES:
        raise LoanError("Informe uma moeda válida.")
    try:
        count = int(data.get("remaining_installments"))
        installment = money_to_cents(data.get("installment_amount"))
        commitment = money_to_cents(data.get("remaining_commitment")) if data.get("remaining_commitment") not in (None, "") else installment * count
        rate_value = data.get("monthly_rate_percent")
        annual_value = data.get("annual_cet_percent")
        if rate_value not in (None, ""):
            rate_micros = round(float(str(rate_value).replace(",", ".")) * 10000)
            annual_rate_micros = None
        elif annual_value not in (None, ""):
            annual_rate = float(str(annual_value).replace(",", ".")) / 100
            if annual_rate < 0:
                raise ValueError("negative CET")
            # spec: emprestimos-quitacao/emprestimos-quitacao v0.25 — critério 6
            rate_micros = round(((1 + annual_rate) ** (1 / 12) - 1) * 1_000_000)
            annual_rate_micros = round(annual_rate * 1_000_000)
        else:
            rate_micros = None
            annual_rate_micros = None
        due = date.fromisoformat(str(data.get("next_due_date") or ""))
    except (TypeError, ValueError, OverflowError) as exc:
        raise LoanError("Confira parcelas, taxa e data do próximo vencimento.") from exc
    if count < 1 or installment < 1 or commitment < 1:
        raise LoanError("Informe parcelas e compromisso restantes maiores que zero.")
    if rate_micros is not None and rate_micros < 0:
        raise LoanError("A taxa não pode ser negativa.")
    return {"name": name, "currency": currency, "loan_type": loan_type, "count": count,
            "installment": installment, "commitment": commitment, "rate": rate_micros,
            "annual_cet": annual_rate_micros, "due": due.isoformat()}


def list_loans(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""SELECT l.*,
            (SELECT COUNT(*) FROM loan_payment_links p WHERE p.user_id=l.user_id AND p.loan_id=l.id AND p.valid=1) paid_count,
            (SELECT MAX(t.date) FROM loan_payment_links p JOIN transactions t ON t.id=p.transaction_id AND t.user_id=p.user_id WHERE p.user_id=l.user_id AND p.loan_id=l.id AND p.valid=1) latest_payment_date,
            CASE WHEN l.review_required=0 AND DATE('now','localtime') > DATE(l.next_due_date,'start of month','+1 month','-1 day')
              AND COALESCE((SELECT MAX(t.date) FROM loan_payment_links p JOIN transactions t ON t.id=p.transaction_id AND t.user_id=p.user_id WHERE p.user_id=l.user_id AND p.loan_id=l.id AND p.valid=1),'') < l.next_due_date
              THEN 1 ELSE 0 END missed_payment_review
            FROM loans l WHERE l.user_id=? AND l.archived_at IS NULL ORDER BY l.currency, l.name""", (user_id,)).fetchall()
        loans = [dict(row) for row in rows]
        for loan in loans:
            payments = conn.execute(
                """SELECT t.id, t.description, t.amount_cents, t.date, a.currency
                   FROM loan_payment_links p JOIN transactions t ON t.id=p.transaction_id AND t.user_id=p.user_id
                   JOIN checking_accounts a ON a.id=t.account_id AND a.user_id=t.user_id
                   WHERE p.user_id=? AND p.loan_id=? AND p.valid=1
                   ORDER BY t.date DESC, t.id DESC""",
                (user_id, loan["id"]),
            ).fetchall()
            loan["payments"] = [dict(payment) for payment in payments]
            loan["total_paid_cents"] = sum(int(payment["amount_cents"]) for payment in loan["payments"])
            loan["paid_installments"] = len(loan["payments"])
            # spec: emprestimos-quitacao/emprestimos-quitacao v0.25 — critério 26
            # A base de 100% é o compromisso nominal reconstruído pelo que foi pago mais o que resta.
            loan["total_nominal_cents"] = loan["total_paid_cents"] + int(loan["remaining_commitment_cents"])
            loan["paid_percentage_basis_points"] = (
                (loan["total_paid_cents"] * 10_000 + loan["total_nominal_cents"] // 2) // loan["total_nominal_cents"]
                if loan["total_nominal_cents"] > 0 else 0
            )
            loan["remaining_percentage_basis_points"] = max(0, 10_000 - loan["paid_percentage_basis_points"])
        return loans


def create_loan(user_id: int, data: dict) -> dict:
    item = _loan_payload(data)
    with get_connection() as conn:
        cursor = conn.execute("""INSERT INTO loans(user_id,name,loan_type,currency,installment_cents,remaining_installments,remaining_commitment_cents,monthly_rate_micros,annual_cet_micros,next_due_date) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (user_id,item['name'],item['loan_type'],item['currency'],item['installment'],item['count'],item['commitment'],item['rate'],item['annual_cet'],item['due']))
        return dict(conn.execute("SELECT * FROM loans WHERE id=? AND user_id=?", (cursor.lastrowid,user_id)).fetchone())


def update_loan(user_id: int, loan_id: int, data: dict) -> dict:
    item = _loan_payload(data)
    with get_connection() as conn:
        conn.execute("""UPDATE loans SET name=?,loan_type=?,currency=?,installment_cents=?,remaining_installments=?,remaining_commitment_cents=?,monthly_rate_micros=?,annual_cet_micros=?,next_due_date=?,review_required=0,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND archived_at IS NULL""",
            (item['name'],item['loan_type'],item['currency'],item['installment'],item['count'],item['commitment'],item['rate'],item['annual_cet'],item['due'],loan_id,user_id))
        row=conn.execute("SELECT * FROM loans WHERE id=? AND user_id=?",(loan_id,user_id)).fetchone()
        if not row: raise LoanError("Empréstimo não encontrado.",HTTPStatus.NOT_FOUND)
        return dict(row)


def archive_loan(user_id: int, loan_id: int) -> None:
    with get_connection() as conn:
        cur=conn.execute("UPDATE loans SET archived_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND archived_at IS NULL",(loan_id,user_id))
        if cur.rowcount==0: raise LoanError("Empréstimo não encontrado.",HTTPStatus.NOT_FOUND)


def link_payment(user_id: int, loan_id: int, transaction_id: int) -> dict:
    with get_connection() as conn:
        begin_immediate(conn)
        return link_payment_with_conn(conn, user_id, loan_id, transaction_id)


def link_payment_with_conn(conn: sqlite3.Connection, user_id: int, loan_id: int, transaction_id: int) -> dict:
        loan=conn.execute("SELECT * FROM loans WHERE id=? AND user_id=? AND archived_at IS NULL",(loan_id,user_id)).fetchone()
        tx=conn.execute("""SELECT t.*, a.currency, c.system_key category_system_key, c.group_type category_group_type FROM transactions t JOIN checking_accounts a ON a.id=t.account_id AND a.user_id=t.user_id LEFT JOIN categories c ON c.id=t.category_id AND c.user_id=t.user_id WHERE t.id=? AND t.user_id=? AND t.archived_at IS NULL""",(transaction_id,user_id)).fetchone()
        if not loan or not tx: raise LoanError("Empréstimo ou lançamento não encontrado.",HTTPStatus.NOT_FOUND)
        # spec: emprestimos-quitacao/emprestimos-quitacao v0.25 — critério 16
        if tx['type']!='expense' or tx['category_group_type']!='expense' or tx['category_system_key']!='loan_payment': raise LoanError("Selecione uma despesa vinculada à categoria de empréstimos e financiamentos.")
        if str(tx['currency']).upper()!=str(loan['currency']).upper(): raise LoanError("A moeda do lançamento deve ser igual à do empréstimo.")
        previous=conn.execute("SELECT loan_id,valid FROM loan_payment_links WHERE user_id=? AND transaction_id=?",(user_id,transaction_id)).fetchone()
        if previous and previous['valid']:
            raise LoanError("Esse lançamento já está associado a um empréstimo.")
        if previous:
            conn.execute("UPDATE loan_payment_links SET loan_id=?,valid=1,linked_at=CURRENT_TIMESTAMP WHERE user_id=? AND transaction_id=?",(loan_id,user_id,transaction_id))
        else:
            conn.execute("INSERT INTO loan_payment_links(user_id,loan_id,transaction_id) VALUES(?,?,?)",(user_id,loan_id,transaction_id))
        # spec: emprestimos-quitacao/emprestimos-quitacao v0.25 — critérios 17–18
        # O lançamento existente amortiza o compromisso e não cria movimento duplicado.
        same_loan=bool(previous and int(previous['loan_id'])==loan_id)
        next_count=int(loan['remaining_installments']) if same_loan else max(0,int(loan['remaining_installments'])-1)
        next_commitment=max(0,int(loan['remaining_commitment_cents']) + (0 if same_loan else -int(tx['amount_cents'])))
        next_due=loan['next_due_date'] if same_loan else add_months(date.fromisoformat(loan['next_due_date']),1).isoformat()
        conn.execute("UPDATE loans SET remaining_installments=?,remaining_commitment_cents=?,next_due_date=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
                     (next_count,next_commitment,next_due,loan_id,user_id))
        return {"loan_id":loan_id,"transaction_id":transaction_id}


def project_payment_plan(installment_cents: int, count: int, monthly_rate_micros: int | None, extra_cents: int=0,
                         extraordinary_cents: int=0, amortization_mode: str="reduce_term") -> dict:
    rate = Decimal(monthly_rate_micros or 0) / Decimal(1_000_000)
    # spec: emprestimos-quitacao/emprestimos-quitacao v0.25 — critérios 5, 22 e 30–31
    def present_value() -> int:
        if not rate:
            return installment_cents * count
        value = Decimal(installment_cents) * (1 - (1 + rate) ** (-count)) / rate
        return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    def amortize(monthly_extra: int, balance: int, payment_cents: int, max_months: int) -> tuple[int, int, int]:
        remaining = balance
        nominal_paid=interest_paid=months_paid=0
        while remaining>0 and months_paid<max_months:
            months_paid+=1
            period_interest=int((Decimal(remaining)*rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            payment=min(remaining+period_interest,payment_cents+max(monthly_extra,0))
            principal=max(0,payment-period_interest)
            remaining=max(0,remaining-principal)
            nominal_paid+=payment; interest_paid+=period_interest
        return months_paid, nominal_paid, interest_paid
    estimated_principal = present_value()
    base_months, base_nominal, base_interest = amortize(0, estimated_principal, installment_cents, max(count, 1))
    scenario_balance=max(0,estimated_principal-max(extraordinary_cents,0))
    if amortization_mode not in {"reduce_term", "reduce_payment"}:
        raise LoanError("Escolha redução do prazo ou da parcela.")
    scenario_payment=installment_cents
    scenario_months_limit=1200
    if amortization_mode == "reduce_payment":
        scenario_months_limit=max(count,1)
        if rate:
            payment=Decimal(scenario_balance)*rate/(1-(1+rate)**(-scenario_months_limit))
        else:
            payment=Decimal(scenario_balance)/scenario_months_limit
        scenario_payment=max(1,int(payment.quantize(Decimal("1"),rounding=ROUND_HALF_UP))) if scenario_balance else 0
    months, nominal, interest = amortize(extra_cents, scenario_balance, scenario_payment, scenario_months_limit)
    return {"months":months,"total_payment_cents":nominal,"interest_cents":interest,
            "estimated_principal_cents":estimated_principal,"baseline_months":base_months,
            "baseline_interest_cents":base_interest,"months_saved":max(0,base_months-months),
            "interest_saved_cents":max(0,base_interest-interest),"amortization_mode":amortization_mode,
            "new_installment_cents":scenario_payment,"extraordinary_cents":max(extraordinary_cents,0)}


def project_payoff_strategy(loans: list[dict], strategy: str, monthly_budget_cents: int) -> dict:
    # spec: emprestimos-quitacao/emprestimos-quitacao v0.25 — critérios 3, 28–29
    if strategy not in {"avalanche", "snowball"} or not loans:
        raise LoanError("Selecione uma estratégia e ao menos um empréstimo ativo.")
    currencies = {str(loan["currency"]).upper() for loan in loans}
    if len(currencies) != 1:
        raise LoanError("Simule uma moeda por vez.")
    if strategy == "avalanche" and any(loan.get("monthly_rate_micros") is None for loan in loans):
        raise LoanError("Informe as taxas mensais de todos os empréstimos desta moeda para ordenar avalanche.")

    interest_available = all(loan.get("monthly_rate_micros") is not None for loan in loans)
    plans = []
    for loan in loans:
        count = int(loan["remaining_installments"])
        rate_micros = loan.get("monthly_rate_micros")
        rate = Decimal(rate_micros or 0) / Decimal(1_000_000)
        payment = int(loan["installment_cents"])
        if rate and rate_micros is not None:
            balance = int((Decimal(payment) * (1 - (1 + rate) ** (-count)) / rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        else:
            balance = int(loan["remaining_commitment_cents"])
        plans.append({"id": loan["id"], "name": loan["name"], "payment": payment, "rate": rate,
                      "balance": balance, "priority": rate_micros or 0,
                      "snowball": balance})
    if strategy == "avalanche":
        plans.sort(key=lambda item: (-item["priority"], item["balance"], item["id"]))
    else:
        plans.sort(key=lambda item: (item["snowball"], item["id"]))

    def run(budget: int) -> tuple[int, int]:
        balances = [item["balance"] for item in plans]
        months = total_interest = 0
        while any(balance > 0 for balance in balances) and months < 1200:
            months += 1
            period_interest = [int((Decimal(balance) * item["rate"]).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if balance > 0 else 0 for balance, item in zip(balances, plans)]
            balances = [balance + interest for balance, interest in zip(balances, period_interest)]
            total_interest += sum(period_interest)
            pool = max(0, budget)
            for index, item in enumerate(plans):
                if balances[index] <= 0:
                    pool += item["payment"]
                    continue
                due = balances[index]
                paid = min(item["payment"], due)
                balances[index] -= paid
                pool += item["payment"] - paid
            for index, _item in enumerate(plans):
                if pool <= 0:
                    break
                paid = min(pool, balances[index])
                balances[index] -= paid
                pool -= paid
        return months, total_interest

    base_months, base_interest = run(0)
    months, interest = run(monthly_budget_cents)
    return {"currency": next(iter(currencies)), "strategy": strategy, "months": months,
            "interest_cents": interest if interest_available else None, "baseline_months": base_months,
            "baseline_interest_cents": base_interest if interest_available else None, "months_saved": max(0, base_months - months),
            "interest_saved_cents": max(0, base_interest - interest) if interest_available else None,
            "priority_order": [item["id"] for item in plans]}
