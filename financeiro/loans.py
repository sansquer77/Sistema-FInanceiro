from __future__ import annotations

import sqlite3
from datetime import date, timedelta
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


AMORTIZATION_SYSTEMS = {"price", "sac"}
LOAN_INDEXERS = {"none", "TR", "IPCA", "POUPANCA"}


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
    amortization_system = str(data.get("amortization_system") or "").strip().lower()
    indexer = str(data.get("indexer") or "none").strip().upper()
    if indexer == "NONE":
        indexer = "none"
    if not name:
        raise LoanError("Informe o nome do empréstimo.")
    if currency not in SUPPORTED_CURRENCIES:
        raise LoanError("Informe uma moeda válida.")
    if amortization_system not in AMORTIZATION_SYSTEMS:
        raise LoanError("Escolha o sistema de amortização Price ou SAC.")
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
            # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 6
            rate_micros = None if indexer != "none" else round(((1 + annual_rate) ** (1 / 12) - 1) * 1_000_000)
            annual_rate_micros = round(annual_rate * 1_000_000)
        else:
            rate_micros = None
            annual_rate_micros = None
        principal = money_to_cents(data.get("principal_balance")) if data.get("principal_balance") not in (None, "") else None
        remuneratory_value = data.get("remuneratory_rate_percent")
        remuneratory_rate_micros = (
            round(float(str(remuneratory_value).replace(",", ".")) * 10000)
            if remuneratory_value not in (None, "") else None
        )
        principal_date = str(data.get("principal_balance_date") or "").strip() or None
        if principal_date:
            principal_date = date.fromisoformat(principal_date).isoformat()
        due = date.fromisoformat(str(data.get("next_due_date") or ""))
    except (TypeError, ValueError, OverflowError) as exc:
        raise LoanError("Confira parcelas, taxa e data do próximo vencimento.") from exc
    if count < 1 or installment < 1 or commitment < 1:
        raise LoanError("Informe parcelas e compromisso restantes maiores que zero.")
    if rate_micros is not None and rate_micros < 0:
        raise LoanError("A taxa não pode ser negativa.")
    if indexer not in LOAN_INDEXERS:
        raise LoanError("Escolha nenhum indexador, TR, IPCA ou poupança.")
    if remuneratory_rate_micros is not None and remuneratory_rate_micros < 0:
        raise LoanError("A taxa remuneratória não pode ser negativa.")
    if indexer != "none" and (principal is None or principal <= 0 or not principal_date or remuneratory_rate_micros is None):
        raise LoanError("Para contrato indexado, informe saldo principal, data-base e taxa remuneratória mensal do contrato.")
    if indexer != "none" and rate_value not in (None, ""):
        raise LoanError("Em contrato indexado, informe a taxa no campo de juros remuneratórios; o CET fica apenas como referência.")
    # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 56
    # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 68
    if amortization_system == "sac" and indexer == "none" and rate_micros is None:
        raise LoanError("Para cadastrar SAC prefixado, informe a taxa efetiva mensal ou o CET efetivo anual do contrato.")
    return {"name": name, "currency": currency, "loan_type": loan_type,
            "amortization_system": amortization_system, "count": count,
            "installment": installment, "commitment": commitment, "rate": rate_micros,
            "annual_cet": annual_rate_micros, "due": due.isoformat(), "indexer": indexer,
            "principal_balance": principal, "principal_balance_date": principal_date,
            "remuneratory_rate": remuneratory_rate_micros}


def list_loans(user_id: int, include_archived: bool = False) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""SELECT l.*,
            (SELECT COUNT(*) FROM loan_payment_links p JOIN transactions t ON t.id=p.transaction_id AND t.user_id=p.user_id WHERE p.user_id=l.user_id AND p.loan_id=l.id AND p.valid=1 AND p.recognized=1 AND t.reconciled_at IS NOT NULL) paid_count,
            (SELECT MAX(t.date) FROM loan_payment_links p JOIN transactions t ON t.id=p.transaction_id AND t.user_id=p.user_id WHERE p.user_id=l.user_id AND p.loan_id=l.id AND p.valid=1 AND p.recognized=1 AND t.reconciled_at IS NOT NULL) latest_payment_date,
            CASE WHEN l.review_required=0 AND DATE('now','localtime') > DATE(l.next_due_date,'start of month','+1 month','-1 day')
              AND COALESCE((SELECT MAX(t.date) FROM loan_payment_links p JOIN transactions t ON t.id=p.transaction_id AND t.user_id=p.user_id WHERE p.user_id=l.user_id AND p.loan_id=l.id AND p.valid=1 AND p.recognized=1 AND t.reconciled_at IS NOT NULL),'') < l.next_due_date
              THEN 1 ELSE 0 END missed_payment_review
            FROM loans l WHERE l.user_id=? AND (l.archived_at IS NULL OR ?=1) ORDER BY l.currency, l.name""", (user_id, int(include_archived))).fetchall()
        loans = [dict(row) for row in rows]
        for loan in loans:
            payments = conn.execute(
                """SELECT t.id, t.description, t.amount_cents, t.date, a.currency,
                          t.reconciled_at, p.recognized
                   FROM loan_payment_links p JOIN transactions t ON t.id=p.transaction_id AND t.user_id=p.user_id
                   JOIN checking_accounts a ON a.id=t.account_id AND a.user_id=t.user_id
                   WHERE p.user_id=? AND p.loan_id=? AND p.valid=1
                   ORDER BY t.date DESC, t.id DESC""",
                (user_id, loan["id"]),
            ).fetchall()
            loan["payments"] = [dict(payment) for payment in payments if payment["recognized"] and payment["reconciled_at"]]
            loan["pending_payments"] = [dict(payment) for payment in payments if not payment["recognized"] or not payment["reconciled_at"]]
            loan["total_paid_cents"] = sum(int(payment["amount_cents"]) for payment in loan["payments"])
            loan["paid_installments"] = len(loan["payments"])
            indexed = str(loan.get("indexer") or "none").upper() not in {"NONE", ""}
            principal_date = str(loan.get("principal_balance_date") or "")
            latest_payment_date = str(loan.get("latest_payment_date") or "")
            loan["principal_review_required"] = bool(
                indexed and principal_date and latest_payment_date and latest_payment_date >= principal_date
            )
            principal_cents, future_interest_cents = estimate_remaining_price_values(
                int(loan["installment_cents"]),
                int(loan["remaining_installments"]),
                loan["monthly_rate_micros"],
                int(loan["remaining_commitment_cents"]),
                str(loan.get("amortization_system") or "price"),
            )
            loan["estimated_principal_cents"] = principal_cents
            loan["estimated_future_interest_cents"] = future_interest_cents
            if loan["principal_review_required"]:
                # Keep the creditor-provided value in SQLite, but never return it as a current balance.
                loan["principal_balance_cents"] = None
            # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 26
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
        cursor = conn.execute("""INSERT INTO loans(user_id,name,loan_type,amortization_system,currency,installment_cents,remaining_installments,remaining_commitment_cents,monthly_rate_micros,annual_cet_micros,next_due_date,indexer,principal_balance_cents,principal_balance_date,remuneratory_rate_micros) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id,item['name'],item['loan_type'],item['amortization_system'],item['currency'],item['installment'],item['count'],item['commitment'],item['rate'],item['annual_cet'],item['due'],item['indexer'],item['principal_balance'],item['principal_balance_date'],item['remuneratory_rate']))
        return dict(conn.execute("SELECT * FROM loans WHERE id=? AND user_id=?", (cursor.lastrowid,user_id)).fetchone())


def update_loan(user_id: int, loan_id: int, data: dict) -> dict:
    item = _loan_payload(data)
    with get_connection() as conn:
        conn.execute("""UPDATE loans SET name=?,loan_type=?,amortization_system=?,currency=?,installment_cents=?,remaining_installments=?,remaining_commitment_cents=?,monthly_rate_micros=?,annual_cet_micros=?,next_due_date=?,indexer=?,principal_balance_cents=?,principal_balance_date=?,remuneratory_rate_micros=?,review_required=0,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND archived_at IS NULL""",
            (item['name'],item['loan_type'],item['amortization_system'],item['currency'],item['installment'],item['count'],item['commitment'],item['rate'],item['annual_cet'],item['due'],item['indexer'],item['principal_balance'],item['principal_balance_date'],item['remuneratory_rate'],loan_id,user_id))
        row=conn.execute("SELECT * FROM loans WHERE id=? AND user_id=?",(loan_id,user_id)).fetchone()
        if not row: raise LoanError("Empréstimo não encontrado.",HTTPStatus.NOT_FOUND)
        return dict(row)


def archive_loan(user_id: int, loan_id: int) -> None:
    with get_connection() as conn:
        cur=conn.execute("UPDATE loans SET archived_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND archived_at IS NULL",(loan_id,user_id))
        if cur.rowcount==0: raise LoanError("Empréstimo não encontrado.",HTTPStatus.NOT_FOUND)


def delete_loan(user_id: int, loan_id: int) -> None:
    with get_connection() as conn:
        begin_immediate(conn)
        row = conn.execute("SELECT id FROM loans WHERE id=? AND user_id=?", (loan_id, user_id)).fetchone()
        if not row:
            raise LoanError("Empréstimo não encontrado.", HTTPStatus.NOT_FOUND)
        # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério de exclusão
        # Remover apenas os vínculos preserva integralmente os lançamentos da conta.
        conn.execute("DELETE FROM loan_payment_links WHERE user_id=? AND loan_id=?", (user_id, loan_id))
        conn.execute("DELETE FROM loans WHERE user_id=? AND id=?", (user_id, loan_id))


def link_payment(user_id: int, loan_id: int, transaction_id: int) -> dict:
    with get_connection() as conn:
        begin_immediate(conn)
        return link_payment_with_conn(conn, user_id, loan_id, transaction_id)


def link_payment_with_conn(conn: sqlite3.Connection, user_id: int, loan_id: int, transaction_id: int) -> dict:
        loan=conn.execute("SELECT * FROM loans WHERE id=? AND user_id=? AND archived_at IS NULL",(loan_id,user_id)).fetchone()
        tx=conn.execute("""SELECT t.*, a.currency, c.system_key category_system_key, c.group_type category_group_type FROM transactions t JOIN checking_accounts a ON a.id=t.account_id AND a.user_id=t.user_id LEFT JOIN categories c ON c.id=t.category_id AND c.user_id=t.user_id WHERE t.id=? AND t.user_id=? AND t.archived_at IS NULL""",(transaction_id,user_id)).fetchone()
        if not loan or not tx: raise LoanError("Empréstimo ou lançamento não encontrado.",HTTPStatus.NOT_FOUND)
        # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 16
        if tx['type']!='expense' or tx['category_group_type']!='expense' or tx['category_system_key']!='loan_payment': raise LoanError("Selecione uma despesa vinculada à categoria de empréstimos e financiamentos.")
        if str(tx['currency']).upper()!=str(loan['currency']).upper(): raise LoanError("A moeda do lançamento deve ser igual à do empréstimo.")
        previous=conn.execute("SELECT loan_id,valid FROM loan_payment_links WHERE user_id=? AND transaction_id=?",(user_id,transaction_id)).fetchone()
        if previous and previous['valid']:
            raise LoanError("Esse lançamento já está associado a um empréstimo.")
        if previous:
            conn.execute("UPDATE loan_payment_links SET loan_id=?,valid=1,linked_at=CURRENT_TIMESTAMP WHERE user_id=? AND transaction_id=?",(loan_id,user_id,transaction_id))
        else:
            conn.execute("INSERT INTO loan_payment_links(user_id,loan_id,transaction_id) VALUES(?,?,?)",(user_id,loan_id,transaction_id))
        # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 41
        # Lançamentos associados só reduzem o compromisso depois da conciliação.
        if tx["reconciled_at"]:
            recognize_loan_payment_with_conn(conn, user_id, transaction_id)
        return {"loan_id":loan_id,"transaction_id":transaction_id}


def recognize_loan_payment_with_conn(conn: sqlite3.Connection, user_id: int, transaction_id: int) -> None:
    row = conn.execute(
        """SELECT p.loan_id, p.recognized, t.amount_cents, t.date, t.reconciled_at,
                  l.remaining_installments, l.remaining_commitment_cents, l.next_due_date,
                  l.review_required, l.amortization_system, l.installment_cents,
                  l.monthly_rate_micros
           FROM loan_payment_links p
           JOIN transactions t ON t.id=p.transaction_id AND t.user_id=p.user_id
           JOIN loans l ON l.id=p.loan_id AND l.user_id=p.user_id
           WHERE p.user_id=? AND p.transaction_id=? AND p.valid=1 AND l.archived_at IS NULL""",
        (user_id, transaction_id),
    ).fetchone()
    if not row or not row["reconciled_at"] or row["recognized"]:
        return
    if not row["review_required"]:
        # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 42
        due_date = date.fromisoformat(row["next_due_date"])
        next_due = add_months(due_date, 1).isoformat()
        remaining_installments = max(0, int(row["remaining_installments"]) - 1)
        next_installment = int(row["installment_cents"])
        # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 58
        # O valor salvo em SAC acompanha a próxima prestação calculada após a amortização regular.
        if (row["amortization_system"] == "sac" and row["monthly_rate_micros"] is not None
                and remaining_installments > 0):
            rate = Decimal(row["monthly_rate_micros"]) / Decimal(1_000_000)
            principal = _estimate_principal(
                int(row["installment_cents"]), int(row["remaining_installments"]), rate, "sac"
            )
            regular_amortization = _round_cents(Decimal(principal) / int(row["remaining_installments"]))
            principal_after_payment = max(0, principal - regular_amortization)
            next_installment = _sac_installment(principal_after_payment, regular_amortization, rate)
        conn.execute(
            """UPDATE loans SET remaining_installments=?, remaining_commitment_cents=?,
                      installment_cents=?, next_due_date=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?""",
            (
                remaining_installments,
                max(0, int(row["remaining_commitment_cents"]) - int(row["amount_cents"])),
                next_installment,
                next_due,
                row["loan_id"],
                user_id,
            ),
        )
    conn.execute(
        "UPDATE loan_payment_links SET recognized=1 WHERE user_id=? AND transaction_id=? AND valid=1",
        (user_id, transaction_id),
    )


def project_payment_plan(installment_cents: int, count: int, monthly_rate_micros: int | None, extra_cents: int=0,
                         extraordinary_cents: int=0, amortization_mode: str="reduce_term",
                         amortization_system: str="price") -> dict:
    if amortization_system not in AMORTIZATION_SYSTEMS:
        raise LoanError("Escolha o sistema de amortização Price ou SAC.")
    if amortization_system == "sac" and monthly_rate_micros is None:
        raise LoanError("Informe uma taxa para projetar o sistema SAC.")
    rate = Decimal(monthly_rate_micros or 0) / Decimal(1_000_000)
    # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 58
    estimated_principal = _estimate_principal(installment_cents, count, rate, amortization_system)

    def amortize_price(monthly_extra: int, balance: int, payment_cents: int,
                       max_months: int) -> tuple[int, int, int]:
        remaining = balance
        nominal_paid=interest_paid=months_paid=0
        while remaining>0 and months_paid<max_months:
            months_paid+=1
            period_interest=_round_cents(Decimal(remaining)*rate)
            payment=min(remaining+period_interest,payment_cents+max(monthly_extra,0))
            principal=max(0,payment-period_interest)
            remaining=max(0,remaining-principal)
            nominal_paid+=payment; interest_paid+=period_interest
        return months_paid, nominal_paid, interest_paid

    initial_amortization = _round_cents(Decimal(estimated_principal) / max(count, 1))

    def amortize_sac(monthly_extra: int, balance: int, principal_amortization_cents: int,
                     max_months: int) -> tuple[int, int, int]:
        remaining = balance
        nominal_paid=interest_paid=months_paid=0
        while remaining>0 and months_paid<max_months:
            months_paid+=1
            period_interest=_round_cents(Decimal(remaining)*rate)
            principal_paid=min(remaining, max(0, principal_amortization_cents) + max(0, monthly_extra))
            payment=principal_paid+period_interest
            remaining=max(0,remaining-principal_paid)
            nominal_paid+=payment; interest_paid+=period_interest
        return months_paid, nominal_paid, interest_paid

    if amortization_system == "sac":
        base_months, base_nominal, base_interest = amortize_sac(
            0, estimated_principal, initial_amortization, max(count, 1)
        )
    else:
        base_months, base_nominal, base_interest = amortize_price(
            0, estimated_principal, installment_cents, max(count, 1)
        )
    scenario_balance=max(0,estimated_principal-max(extraordinary_cents,0))
    if amortization_mode not in {"reduce_term", "reduce_payment"}:
        raise LoanError("Escolha redução do prazo ou da parcela.")
    scenario_payment=installment_cents
    scenario_months_limit=1200
    if amortization_system == "sac":
        scenario_amortization=initial_amortization
        if amortization_mode == "reduce_payment":
            scenario_months_limit=max(count,1)
            scenario_amortization=(
                _round_cents(Decimal(scenario_balance)/scenario_months_limit) if scenario_balance else 0
            )
        scenario_payment=_sac_installment(scenario_balance, scenario_amortization, rate)
        months, nominal, interest = amortize_sac(
            extra_cents, scenario_balance, scenario_amortization, scenario_months_limit
        )
    else:
        if amortization_mode == "reduce_payment":
            scenario_months_limit=max(count,1)
            if rate:
                payment=Decimal(scenario_balance)*rate/(1-(1+rate)**(-scenario_months_limit))
            else:
                payment=Decimal(scenario_balance)/scenario_months_limit
            scenario_payment=max(1,int(payment.quantize(Decimal("1"),rounding=ROUND_HALF_UP))) if scenario_balance else 0
        months, nominal, interest = amortize_price(
            extra_cents, scenario_balance, scenario_payment, scenario_months_limit
        )
    return {"months":months,"total_payment_cents":nominal,"interest_cents":interest,
            "estimated_principal_cents":estimated_principal,"baseline_months":base_months,
            "baseline_interest_cents":base_interest,"months_saved":max(0,base_months-months),
            "interest_saved_cents":max(0,base_interest-interest),"amortization_mode":amortization_mode,
            "new_installment_cents":scenario_payment,"extraordinary_cents":max(extraordinary_cents,0),
            "amortization_system":amortization_system}


# spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critérios 78–81
def project_payoff_vs_cdi(result: dict, extra_monthly_cents: int, extraordinary_cents: int) -> dict:
    """Compare nominal interest savings with gross CDI earnings on the same hypothetical contributions."""
    if extra_monthly_cents <= 0 and extraordinary_cents <= 0:
        return {"available": False, "message": "Informe um adicional mensal ou uma amortização extraordinária para comparar."}
    horizon_months = int(result.get("baseline_months") or 0)
    if horizon_months <= 0:
        return {"available": False, "message": "Não foi possível determinar o prazo-base do contrato."}

    from financeiro import portfolio

    try:
        observed = portfolio.fetch_latest_cdi_assumption()
        monthly_rate = Decimal(str(observed["monthly_rate"]))
        daily_rate = Decimal(str(observed["daily_rate"]))
        annual_rate = Decimal(str(observed["annual_rate"]))
        if monthly_rate < 0 or daily_rate < 0 or annual_rate < 0:
            raise ValueError("CDI rates must not be negative")
    except Exception:
        return {
            "available": False,
            "message": "O CDI não está disponível para comparação agora; a simulação de quitação continua válida.",
        }

    monthly_factor = Decimal("1") + monthly_rate
    investment_balance = Decimal(max(0, extraordinary_cents)) * (monthly_factor ** horizon_months)
    for month in range(1, horizon_months + 1):
        investment_balance += Decimal(max(0, extra_monthly_cents)) * (monthly_factor ** (horizon_months - month))
    invested_cents = max(0, extraordinary_cents) + max(0, extra_monthly_cents) * horizon_months
    ending_balance_cents = _round_cents(investment_balance)
    gross_gain_cents = ending_balance_cents - invested_cents
    interest_saved_cents = int(result.get("interest_saved_cents") or 0)
    indexation_saved_cents = max(
        0,
        int(result.get("baseline_indexation_cents") or 0) - int(result.get("indexation_cents") or 0),
    )
    financing_cost_saved_cents = interest_saved_cents + indexation_saved_cents
    return {
        "available": True,
        "horizon_months": horizon_months,
        "invested_cents": invested_cents,
        "ending_balance_cents": ending_balance_cents,
        "gross_gain_cents": gross_gain_cents,
        "interest_saved_cents": interest_saved_cents,
        "indexation_saved_cents": indexation_saved_cents,
        "financing_cost_saved_cents": financing_cost_saved_cents,
        "advantage_cents": financing_cost_saved_cents - gross_gain_cents,
        "daily_rate_micros": _round_cents(daily_rate * Decimal("1000000")),
        "annual_rate_micros": _round_cents(annual_rate * Decimal("1000000")),
        "monthly_rate_micros": _round_cents(monthly_rate * Decimal("1000000")),
        "rate_date": observed["rate_date"],
    }


# spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 63
def _latest_indexer_projection_assumption(indexer: str, as_of_date: date | None = None) -> dict:
    """Return the effective accumulated factor from the latest twelve-month window and its monthly equivalent."""
    from financeiro import portfolio

    as_of = as_of_date or date.today()
    try:
        observed = portfolio.fetch_trailing_twelve_month_indexer_factor(indexer, as_of)
    except Exception as exc:
        raise LoanError(
            "Não foi possível consultar os últimos índices publicados para estimar a taxa futura. Tente novamente quando o serviço estiver disponível."
        ) from exc
    factor = observed["factor"]
    if factor <= 0:
        raise LoanError("O histórico publicado do indexador não permite calcular uma taxa equivalente.")
    accumulated_rate = factor - Decimal("1")
    monthly_equivalent = factor ** (Decimal("1") / Decimal("12")) - Decimal("1")
    return {
        "factor": factor,
        "accumulated_rate_micros": _round_cents(accumulated_rate * Decimal("1000000")),
        "monthly_rate": monthly_equivalent,
        "monthly_rate_micros": _round_cents(monthly_equivalent * Decimal("1000000")),
        "period_start": observed["period_start"],
        "period_end": observed["period_end"],
    }


def project_indexed_payment_plan(loan: dict, extra_cents: int = 0, extraordinary_cents: int = 0,
                                 amortization_mode: str = "reduce_term") -> dict:
    """Project an indexed loan from its lender-reported principal and reference date."""
    indexer = str(loan.get("indexer") or "none").upper()
    if indexer not in {"TR", "IPCA", "POUPANCA"}:
        raise LoanError("Escolha TR, IPCA ou poupança para projetar o contrato indexado.")
    if amortization_mode not in {"reduce_term", "reduce_payment"}:
        raise LoanError("Escolha redução do prazo ou da parcela.")
    if loan.get("principal_review_required"):
        raise LoanError("Atualize o principal e a data-base com o demonstrativo do credor antes de simular este contrato.")
    count = int(loan["remaining_installments"])
    principal = int(loan.get("principal_balance_cents") or 0)
    monthly_rate = loan.get("remuneratory_rate_micros")
    if principal <= 0 or count <= 0 or monthly_rate is None:
        raise LoanError("Revise saldo principal, prazo e juros remuneratórios do contrato.")
    rate = Decimal(int(monthly_rate)) / Decimal(1_000_000)
    base_date = date.fromisoformat(str(loan["principal_balance_date"]))
    first_due = date.fromisoformat(str(loan["next_due_date"]))
    if first_due < base_date:
        raise LoanError("O próximo vencimento não pode ser anterior à data-base do saldo principal.")

    # Buscar fatores antes de qualquer escrita. O cache local evita consultar duas
    # vezes os mesmos períodos ao comparar plano-base e cenário adicional.
    factor_cache: dict[tuple[str, date, date], Decimal] = {}
    assumption_holder: dict[str, dict] = {}
    from financeiro import portfolio

    def period_factor(start: date, end: date) -> Decimal:
        key = (indexer, start, end)
        if key in factor_cache:
            return factor_cache[key]
        today = date.today()
        actual_end = min(end, today)
        factor = Decimal("1")
        if actual_end >= start:
            try:
                if indexer == "POUPANCA":
                    monthly_savings_rate = portfolio.savings_additional_monthly_rate()
                    factor = portfolio.savings_factor_for_anniversary(start, actual_end, monthly_savings_rate)
                else:
                    factor = portfolio.fetch_accumulated_indexer_factor(indexer, start, actual_end)
            except Exception as exc:
                raise LoanError("Não foi possível consultar o histórico oficial do indexador. Tente novamente quando o serviço estiver disponível.") from exc
        future_start = max(start, today + timedelta(days=1))
        if end >= future_start:
            if "value" not in assumption_holder:
                nonlocal_assumption = _latest_indexer_projection_assumption(indexer, today)
                # Cache this window for all future periods in this study.
                assumption_holder["value"] = nonlocal_assumption
            days = (end - future_start).days + 1
            factor *= (Decimal("1") + assumption_holder["value"]["monthly_rate"]) ** (
                Decimal(days) / Decimal("30.436875")
            )
        factor_cache[key] = factor
        return factor

    from financeiro.calendar_rules import add_months
    factors: list[Decimal] = []
    previous_date = base_date
    scenario_month_limit = count if amortization_mode == "reduce_payment" or (extra_cents <= 0 and extraordinary_cents <= 0) else 1200
    factor_month_limit = max(count, scenario_month_limit)
    for month_index in range(1, factor_month_limit + 1):
        due = add_months(first_due, month_index - 1)
        factors.append(period_factor(previous_date + timedelta(days=1), due))
        previous_date = due

    system = str(loan.get("amortization_system") or "price")
    scheduled = int(loan["installment_cents"])

    def run(extra: int, upfront: int, mode: str, baseline: bool = False) -> tuple[int, int, int, int, int]:
        upfront_applied = min(principal, max(0, upfront))
        balance = principal - upfront_applied
        if mode == "reduce_payment":
            if system == "sac":
                base_amortization = _round_cents(Decimal(balance) / max(1, count))
                base_payment = 0
            else:
                base_payment = (_round_cents(Decimal(balance) / count) if not rate else
                    _round_cents(Decimal(balance) * rate / (Decimal(1) - (Decimal(1) + rate) ** (-count))))
                base_amortization = 0
        else:
            base_payment = scheduled
            base_amortization = _round_cents(Decimal(principal) / count) if system == "sac" else 0
        total_paid = upfront_applied
        total_interest = total_indexation = months = first_installment = 0
        month_limit = count if baseline or mode == "reduce_payment" or (extra <= 0 and upfront <= 0) else len(factors)
        for index, factor in enumerate(factors[:month_limit]):
            if balance <= 0:
                break
            previous = balance
            balance = _round_cents(Decimal(balance) * factor)
            total_indexation += balance - previous
            if system == "price":
                base_payment = _round_cents(Decimal(base_payment) * factor)
            else:
                base_amortization = _round_cents(Decimal(base_amortization) * factor)
            interest = _round_cents(Decimal(balance) * rate)
            if system == "sac":
                amortization = min(balance, base_amortization)
                payment = amortization + interest
            else:
                payment = max(0, base_payment)
                amortization = max(0, payment - interest)
            regular_payment = min(balance + interest, payment)
            if months == 0:
                first_installment = regular_payment
            if not baseline:
                amortization += max(0, extra)
                payment += max(0, extra)
            payment = min(balance + interest, payment)
            amortization = min(balance, max(0, payment - interest))
            balance = max(0, balance - amortization)
            total_paid += payment
            total_interest += interest
            months = index + 1
            if mode == "reduce_payment" and months >= count:
                break
        return months, total_paid, total_interest, total_indexation, first_installment

    baseline_months, baseline_paid, baseline_interest, baseline_indexation, _baseline_installment = run(0, 0, "reduce_term", True)
    scenario_months, scenario_paid, scenario_interest, scenario_indexation, scenario_installment = run(
        max(0, extra_cents), max(0, extraordinary_cents), amortization_mode
    )
    return {"months": scenario_months, "total_payment_cents": scenario_paid,
            "interest_cents": scenario_interest, "indexation_cents": scenario_indexation,
            "estimated_principal_cents": principal, "baseline_months": baseline_months,
            "baseline_interest_cents": baseline_interest, "baseline_indexation_cents": baseline_indexation,
            "months_saved": max(0, baseline_months - scenario_months),
            "interest_saved_cents": max(0, baseline_interest - scenario_interest),
            "amortization_mode": amortization_mode, "new_installment_cents": scenario_installment,
            "extraordinary_cents": max(0, extraordinary_cents), "amortization_system": system,
            "indexer": indexer,
            "future_index_accumulated_rate_micros": assumption_holder.get("value", {}).get("accumulated_rate_micros"),
            "future_index_monthly_rate_micros": assumption_holder.get("value", {}).get("monthly_rate_micros"),
            "future_index_period_start": assumption_holder.get("value", {}).get("period_start"),
            "future_index_period_end": assumption_holder.get("value", {}).get("period_end")}


# spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critérios 84–90
def project_full_payoff(loan: dict) -> dict:
    """Compare a full payoff today with investing the estimated payoff amount at 100% CDI."""
    if loan.get("principal_review_required"):
        raise LoanError("Atualize o saldo principal e a data-base do contrato antes de estudar a quitação.")
    indexer = str(loan.get("indexer") or "none").upper()
    if indexer not in {"NONE", ""}:
        if indexer not in {"TR", "IPCA", "POUPANCA"}:
            raise LoanError("Este indexador não está disponível para o estudo de quitação.")
        payoff_amount = loan.get("principal_balance_cents")
        if payoff_amount is None:
            raise LoanError("Revise o saldo principal e a data-base do contrato antes de estudar a quitação.")
    else:
        payoff_amount = loan.get("estimated_principal_cents")
        if payoff_amount is None or loan.get("monthly_rate_micros") is None:
            raise LoanError("Informe a taxa do contrato para estimar o valor de quitação e os juros futuros.")
    if int(payoff_amount) <= 0:
        raise LoanError("O valor estimado de quitação precisa ser maior que zero.")
    if indexer not in {"NONE", ""}:
        result = project_indexed_payment_plan(loan, extraordinary_cents=int(payoff_amount))
    else:
        result = project_payment_plan(
            int(loan["installment_cents"]),
            int(loan["remaining_installments"]),
            int(loan["monthly_rate_micros"]),
            extraordinary_cents=int(payoff_amount),
            amortization_system=str(loan.get("amortization_system") or "price"),
        )
    result["study_type"] = "payoff"
    result["payoff_amount_cents"] = int(payoff_amount)
    result["payoff_cost_avoided_cents"] = (
        int(result.get("interest_saved_cents") or 0)
        + max(0, int(result.get("baseline_indexation_cents") or 0) - int(result.get("indexation_cents") or 0))
    )
    result["cdi_comparison"] = project_payoff_vs_cdi(result, 0, int(payoff_amount))
    return result


def estimate_remaining_price_values(installment_cents: int, count: int, monthly_rate_micros: int | None,
                                    nominal_commitment_cents: int,
                                    amortization_system: str="price") -> tuple[int | None, int | None]:
    """Return estimated principal and future finance cost for Price or fixed-rate SAC."""
    if count <= 0 and nominal_commitment_cents <= 0:
        return 0, 0
    if monthly_rate_micros is None:
        return None, None
    rate = Decimal(monthly_rate_micros) / Decimal(1_000_000)
    principal_cents = _estimate_principal(installment_cents, count, rate, amortization_system)
    # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 77
    future_cost_cents = nominal_commitment_cents - principal_cents
    return principal_cents, future_cost_cents if future_cost_cents >= 0 else None


def _estimate_price_principal(installment_cents: int, count: int, rate: Decimal) -> int:
    if not rate or count <= 0:
        return installment_cents * max(0, count)
    value = Decimal(installment_cents) * (1 - (1 + rate) ** (-count)) / rate
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _estimate_principal(installment_cents: int, count: int, rate: Decimal, amortization_system: str) -> int:
    if amortization_system == "sac":
        if count <= 0:
            return 0
        return _round_cents(Decimal(installment_cents) / (rate + Decimal(1) / count))
    return _estimate_price_principal(installment_cents, count, rate)


def _round_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _sac_installment(balance_cents: int, principal_amortization_cents: int, rate: Decimal) -> int:
    principal = min(max(0, balance_cents), max(0, principal_amortization_cents))
    interest = _round_cents(Decimal(max(0, balance_cents)) * rate)
    return principal + interest


def project_payoff_strategy(loans: list[dict], strategy: str, monthly_budget_cents: int,
                            revolving_loans: list[dict] | None = None) -> dict:
    # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 59
    revolving_loans = list(revolving_loans or [])
    if strategy not in {"avalanche", "snowball"} or not (loans or revolving_loans):
        raise LoanError("Selecione uma estratégia e ao menos um empréstimo ativo.")
    currencies = {str(loan["currency"]).upper() for loan in [*loans, *revolving_loans]}
    if len(currencies) != 1:
        raise LoanError("Simule uma moeda por vez.")
    if monthly_budget_cents < 0:
        raise LoanError("O orçamento adicional não pode ser negativo.")
    if revolving_loans and monthly_budget_cents <= 0:
        raise LoanError("Informe um orçamento mensal adicional para incluir dívidas rotativas na estratégia.")
    if strategy == "avalanche" and any(
        loan.get("monthly_rate_micros") is None and loan.get("remuneratory_rate_micros") is None
        for loan in loans
    ):
        raise LoanError("Informe as taxas de todos os empréstimos desta moeda para ordenar avalanche.")
    if any(loan.get("amortization_system") == "sac" and
           loan.get("monthly_rate_micros") is None and loan.get("remuneratory_rate_micros") is None
           for loan in loans):
        raise LoanError("Informe a taxa mensal dos contratos SAC desta moeda para simular a estratégia.")

    interest_available = (all(loan.get("monthly_rate_micros") is not None or
                              loan.get("remuneratory_rate_micros") is not None for loan in loans)
                          and all(loan.get("rate_micros") is not None for loan in revolving_loans))
    indexed = any(str(loan.get("indexer") or "none").upper() not in {"NONE", ""} for loan in loans)
    assumptions_by_indexer: dict[str, dict] = {}
    if indexed:
        # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 73
        # Index factors are fetched before any database writes and then applied month by month.
        factor_cache: dict[tuple[str, date, date], Decimal] = {}
        from financeiro import portfolio

        def period_factor(indexer: str, start: date, end: date) -> Decimal:
            key = (indexer, start, end)
            if key in factor_cache:
                return factor_cache[key]
            today = date.today()
            actual_end = min(end, today)
            factor = Decimal("1")
            if actual_end >= start:
                try:
                    if indexer == "POUPANCA":
                        factor = portfolio.savings_factor_for_anniversary(
                            start, actual_end, portfolio.savings_additional_monthly_rate())
                    else:
                        factor = portfolio.fetch_accumulated_indexer_factor(indexer, start, actual_end)
                except Exception as exc:
                    raise LoanError("Não foi possível consultar o histórico oficial do indexador. Tente novamente quando o serviço estiver disponível.") from exc
            future_start = max(start, today + timedelta(days=1))
            if end >= future_start:
                if indexer not in assumptions_by_indexer:
                    assumptions_by_indexer[indexer] = _latest_indexer_projection_assumption(indexer, today)
                days = (end - future_start).days + 1
                factor *= (Decimal("1") + assumptions_by_indexer[indexer]["monthly_rate"]) ** (
                    Decimal(days) / Decimal("30.436875")
                )
            factor_cache[key] = factor
            return factor

    plans = []
    for loan in loans:
        count = int(loan["remaining_installments"])
        indexer = str(loan.get("indexer") or "none").upper()
        is_indexed = indexer not in {"NONE", ""}
        if is_indexed and loan.get("principal_review_required"):
            raise LoanError(f"Atualize o principal e a data-base de {loan.get('name') or 'um contrato indexado'} com o demonstrativo do credor antes de simular a estratégia.")
        rate_micros = loan.get("remuneratory_rate_micros") if is_indexed else loan.get("monthly_rate_micros")
        if is_indexed and indexer not in {"TR", "IPCA", "POUPANCA"}:
            raise LoanError("A estratégia aceita apenas contratos indexados por TR, IPCA ou poupança.")
        if is_indexed and (not loan.get("principal_balance_cents") or not loan.get("principal_balance_date")
                           or not loan.get("next_due_date")):
            raise LoanError("Revise o saldo principal, a data-base e o próximo vencimento do contrato indexado.")
        rate = Decimal(rate_micros or 0) / Decimal(1_000_000)
        payment = int(loan["installment_cents"])
        system = str(loan.get("amortization_system") or "price")
        balance = (int(loan["principal_balance_cents"]) if is_indexed else
            _estimate_principal(payment, count, rate, system)
            if rate_micros is not None else int(loan["remaining_commitment_cents"]))
        principal_payment = _round_cents(Decimal(balance) / max(1, count)) if system == "sac" else 0
        factors = []
        if is_indexed:
            previous_date = date.fromisoformat(str(loan["principal_balance_date"]))
            due_date = date.fromisoformat(str(loan["next_due_date"]))
            if due_date < previous_date:
                raise LoanError("O próximo vencimento não pode ser anterior à data-base do saldo principal.")
            for month in range(1, 1201):
                due = add_months(due_date, month - 1)
                factors.append(period_factor(indexer, previous_date + timedelta(days=1), due))
                previous_date = due
        else:
            factors = [Decimal("1")] * 1200
        # Avalanche orders by the contracted monthly rate; where present, the stated index assumption
        # contributes to a comparable approximate effective rate for indexed contracts.
        priority = rate_micros or 0
        if is_indexed:
            if indexer not in assumptions_by_indexer:
                assumptions_by_indexer[indexer] = _latest_indexer_projection_assumption(indexer)
            priority += assumptions_by_indexer[indexer]["monthly_rate_micros"]
        plans.append({"id": loan["id"], "name": loan["name"], "payment": payment, "rate": rate,
                      "system": system, "principal_payment": principal_payment,
                      "balance": balance, "priority": priority,
                      "snowball": balance, "indexer": indexer, "factors": factors,
                      "is_revolving": False})
    today = date.today()
    for loan in revolving_loans:
        balance = int(loan["balance_cents"])
        rate_micros = loan.get("rate_micros")
        rate_period = loan.get("rate_period")
        priority = 0
        if rate_micros is not None:
            from financeiro.revolving_loans import effective_daily_rate
            daily_rate = effective_daily_rate(int(rate_micros), str(rate_period))
            priority = round(float(((Decimal(1) + daily_rate) ** Decimal(30) - 1) * 1_000_000))
        plans.append({"id": loan["id"], "name": loan["name"], "payment": 0,
                      "rate": Decimal(0), "system": "revolving", "principal_payment": 0,
                      "balance": balance, "priority": priority, "snowball": balance,
                      "indexer": "NONE", "factors": [Decimal(1)] * 1200,
                      "is_revolving": True, "rate_micros": rate_micros,
                      "rate_period": rate_period, "capitalization": loan.get("capitalization", "daily"),
                      "balance_date": date.fromisoformat(str(loan["balance_date"])),
                      "start_balance_date": date.fromisoformat(str(loan["balance_date"]))})
    if strategy == "avalanche":
        plans.sort(key=lambda item: (not item["is_revolving"],
                                     item["rate_micros"] is None if item["is_revolving"] else False,
                                     -item["priority"], item["balance"], item["id"]))
    else:
        plans.sort(key=lambda item: (not item["is_revolving"], item["snowball"], item["id"]))

    has_revolving = bool(revolving_loans)

    def run(budget: int) -> tuple[int, int, int]:
        balances = [item["balance"] for item in plans]
        for item in plans:
            if item["is_revolving"]:
                item["balance_date"] = item["start_balance_date"]
        scheduled_payments = [item["payment"] for item in plans]
        principal_amortizations = [item["principal_payment"] for item in plans]
        months = total_interest = total_indexation = 0
        while any(balance > 0 for balance in balances) and months < 1200:
            months += 1
            period_end = add_months(today, months)
            period_interest = [0] * len(plans)
            for index, item in enumerate(plans):
                if not item["is_revolving"] or balances[index] <= 0 or item["rate_micros"] is None:
                    continue
                start = item["balance_date"]
                if period_end > start:
                    from financeiro.revolving_loans import project_revolving_balance
                    projection = project_revolving_balance(
                        balances[index], start.isoformat(), int(item["rate_micros"]),
                        str(item["rate_period"]), str(item["capitalization"]), [], period_end.isoformat())
                    balances[index] = int(projection["balance_cents"])
                    period_interest[index] = int(projection["interest_cents"])
                item["balance_date"] = period_end
            factors = [item["factors"][months - 1] for item in plans]
            corrections = [_round_cents(Decimal(balance) * (factor - 1)) if balance > 0 else 0
                           for balance, factor in zip(balances, factors)]
            balances = [balance + correction for balance, correction in zip(balances, corrections)]
            total_indexation += sum(corrections)
            for index, item in enumerate(plans):
                if item["indexer"] not in {"NONE", ""}:
                    scheduled_payments[index] = _round_cents(Decimal(scheduled_payments[index]) * factors[index])
                    principal_amortizations[index] = _round_cents(Decimal(principal_amortizations[index]) * factors[index])
            for index, (balance, item) in enumerate(zip(balances, plans)):
                if balance > 0 and not item["is_revolving"]:
                    period_interest[index] = _round_cents(Decimal(balance) * item["rate"])
                    balances[index] += period_interest[index]
            total_interest += sum(period_interest)
            pool = max(0, budget)
            for index, (item, interest) in enumerate(zip(plans, period_interest)):
                if balances[index] <= 0:
                    pool += item["payment"]
                    continue
                planned_payment = 0 if item["is_revolving"] else (
                    principal_amortizations[index] + interest
                    if item["system"] == "sac" else scheduled_payments[index]
                )
                scheduled_due = min(balances[index], planned_payment)
                balances[index] -= scheduled_due
                if balances[index] == 0:
                    pool += max(0, planned_payment - scheduled_due)
            for index, _item in enumerate(plans):
                if pool <= 0:
                    break
                paid = min(pool, balances[index])
                balances[index] -= paid
                pool -= paid
        return months, total_interest, total_indexation

    # A zero-payment baseline is not displayed for revolving debts. Avoid
    # compounding a deliberately unpaid high-rate balance for the full horizon.
    if has_revolving:
        base_months = base_interest = base_indexation = None
    else:
        base_months, base_interest, base_indexation = run(0)
    months, interest, indexation = run(monthly_budget_cents)
    return {"currency": next(iter(currencies)), "strategy": strategy, "months": months,
            "interest_cents": interest if interest_available else None,
            "baseline_months": base_months,
            "baseline_interest_cents": base_interest if interest_available and not has_revolving else None,
            "months_saved": None if has_revolving else max(0, base_months - months),
            "interest_saved_cents": max(0, base_interest - interest) if interest_available and not has_revolving else None,
            "priority_order": ([{"kind": "revolving" if item["is_revolving"] else "loan", "id": item["id"], "name": item["name"]} for item in plans]
                               if revolving_loans else [item["id"] for item in plans]),
            "indexation_cents": indexation if indexed else None,
            "baseline_indexation_cents": base_indexation if indexed else None,
            "future_index_assumptions": {
                indexer: {
                    "accumulated_rate_micros": item["accumulated_rate_micros"],
                    "monthly_rate_micros": item["monthly_rate_micros"],
                    "period_start": item["period_start"],
                    "period_end": item["period_end"],
                }
                for indexer, item in assumptions_by_indexer.items()
            }}
