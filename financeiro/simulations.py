from __future__ import annotations

from datetime import date, timedelta
from http import HTTPStatus

from financeiro.accounts import money_to_cents
from financeiro.calendar_rules import add_months, month_end_date, normalize_iso_date
from financeiro.database import get_connection, row_to_dict
from financeiro.identifiers import optional_positive_int_id, positive_int_id
from financeiro.recurrence import MONTHLY_RECURRENCE_FREQUENCIES as RECURRENCE_FREQUENCIES
from financeiro.recurrence import SERIES_KINDS

SIMULATION_TYPES = {"income", "expense"}
class SimulationError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def simulate_butterfly_effect(user_id: int, data: dict) -> dict:
    payload = normalize_simulation_payload(data)
    with get_connection() as conn:
        account = fetch_account(conn, user_id, payload["account_id"])
        category_id, subcategory_id = resolve_category(conn, user_id, payload)
        virtual_items = build_virtual_items(payload)
        account_impact = build_account_impact(conn, user_id, account, payload, virtual_items)
        month_impact = build_month_impact(conn, user_id, account, payload, virtual_items)
        limit_impact = build_limit_impact(conn, user_id, account, payload, virtual_items, category_id, subcategory_id)
        chart_series = build_chart_series(conn, user_id, account, payload, virtual_items)
        daily_projection = build_daily_projection(conn, user_id, account, payload, virtual_items)
        daily_projection_summary = summarize_daily_projection(daily_projection)
        warnings = build_warnings(account_impact, limit_impact)
    return {
        "scenario": {
            "type": payload["type"],
            "amount_cents": payload["amount_cents"],
            "date": payload["date"],
            "description": payload["description"],
            "account_id": payload["account_id"],
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "series_kind": payload["series_kind"],
            "installment_count": payload["installment_count"],
            "recurrence_frequency": payload["recurrence_frequency"],
            "recurrence_count": payload["recurrence_count"],
        },
        "account_impact": account_impact,
        "month_impact": month_impact,
        "limit_impact": limit_impact,
        "chart_series": chart_series,
        "daily_projection": daily_projection,
        "daily_projection_summary": daily_projection_summary,
        "weekly_projection": daily_projection,
        "virtual_items": virtual_items,
        "warnings": warnings,
    }


def normalize_simulation_payload(data: dict) -> dict:
    simulation_type = str(data.get("type", "")).strip().lower()
    if simulation_type not in SIMULATION_TYPES:
        raise SimulationError("Tipo de simulacao invalido.")
    amount_cents = money_to_cents(data.get("amount", "0"))
    if amount_cents <= 0:
        raise SimulationError("Informe um valor maior que zero.")
    try:
        simulation_date = normalize_iso_date(data.get("date"))
    except ValueError as exc:
        raise SimulationError("Informe uma data valida.") from exc
    try:
        account_id = positive_int_id(data.get("account_id"))
    except ValueError as exc:
        raise SimulationError("Informe a conta.") from exc
    series_kind = str(data.get("series_kind") or "single").strip().lower()
    if series_kind not in SERIES_KINDS:
        raise SimulationError("Tipo de repeticao invalido.")
    installment_count = None
    recurrence_frequency = None
    recurrence_count = None
    if series_kind == "installment":
        installment_count = normalize_count(data.get("installment_count"), "Informe a quantidade de parcelas.")
    if series_kind == "recurring":
        recurrence_frequency = str(data.get("recurrence_frequency") or "monthly").strip().lower()
        if recurrence_frequency not in RECURRENCE_FREQUENCIES:
            raise SimulationError("Informe a frequencia da recorrencia.")
        # spec: efeito-borboleta v1.8 — critério 16
        # (recorrentes usam 120 ocorrencias automaticamente quando o campo nao e enviado)
        raw_count = str(data.get("recurrence_count") or "").strip()
        recurrence_count = normalize_count(raw_count, "Informe a quantidade de ocorrencias.") if raw_count else 120
    return {
        "type": simulation_type,
        "amount_cents": amount_cents,
        "date": simulation_date,
        "description": normalize_description(data.get("description"), simulation_type),
        "account_id": account_id,
        "category_id": normalize_optional_id(data.get("category_id")),
        "subcategory_id": normalize_optional_id(data.get("subcategory_id")),
        "series_kind": series_kind,
        "installment_count": installment_count,
        "recurrence_frequency": recurrence_frequency,
        "recurrence_count": recurrence_count,
    }


def normalize_count(value: object, message: str) -> int:
    try:
        count = int(str(value or "").strip())
    except ValueError as exc:
        raise SimulationError(message) from exc
    if count < 2:
        raise SimulationError(message)
    if count > 240:
        raise SimulationError("Quantidade de repeticoes muito alta.")
    return count


def normalize_optional_id(value: object) -> int | None:
    try:
        return optional_positive_int_id(value)
    except ValueError as exc:
        raise SimulationError("Identificador invalido.") from exc


def normalize_description(value: object, simulation_type: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    return "Receita simulada" if simulation_type == "income" else "Despesa simulada"


def fetch_account(conn, user_id: int, account_id: int) -> dict:
    row = conn.execute(
        """
        SELECT id, currency
        FROM checking_accounts
        WHERE id = ? AND user_id = ? AND archived_at IS NULL
        """,
        (account_id, user_id),
    ).fetchone()
    if not row:
        raise SimulationError("Conta nao encontrada.", HTTPStatus.NOT_FOUND)
    return row_to_dict(row)


def resolve_category(conn, user_id: int, payload: dict) -> tuple[int | None, int | None]:
    if payload["category_id"] is None:
        return None, None
    row = conn.execute(
        """
        SELECT id, group_type
        FROM categories
        WHERE id = ? AND user_id = ?
        """,
        (payload["category_id"], user_id),
    ).fetchone()
    if not row:
        raise SimulationError("Categoria nao encontrada.", HTTPStatus.NOT_FOUND)
    if payload["type"] == "expense" and row["group_type"] != "expense":
        raise SimulationError("Escolha uma categoria de despesa.")
    if payload["type"] == "income" and row["group_type"] != "income":
        raise SimulationError("Escolha uma categoria de receita.")
    if payload["subcategory_id"] is not None:
        subcategory = conn.execute(
            """
            SELECT id
            FROM subcategories
            WHERE id = ? AND user_id = ? AND category_id = ?
            """,
            (payload["subcategory_id"], user_id, payload["category_id"]),
        ).fetchone()
        if not subcategory:
            raise SimulationError("Subcategoria nao pertence a categoria escolhida.")
        return payload["category_id"], payload["subcategory_id"]
    return payload["category_id"], None


def build_virtual_items(payload: dict) -> list[dict]:
    amount_cents = payload["amount_cents"]
    start_date = date.fromisoformat(payload["date"])
    if payload["series_kind"] == "installment":
        item_count = payload["installment_count"]
        amount_per_item = amount_cents // item_count
        remainder = amount_cents % item_count
        items = []
        for index in range(item_count):
            current_amount = amount_per_item + (1 if index < remainder else 0)
            items.append({
                "month": add_months(start_date, index).strftime("%Y-%m"),
                "date": add_months(start_date, index).isoformat(),
                "description": f"{payload['description']} ({index + 1}/{item_count})",
                "occurrence_index": index + 1,
                "occurrence_total": item_count,
                "impact_cents": signed_impact_cents(payload["type"], current_amount),
                "impact_sign": "+" if payload["type"] == "income" else "-",
            })
        return items
    if payload["series_kind"] == "recurring":
        items = []
        for index in range(payload["recurrence_count"]):
            occurrence_date = add_months(start_date, index)
            items.append({
                "month": occurrence_date.strftime("%Y-%m"),
                "date": occurrence_date.isoformat(),
                "description": payload["description"],
                "occurrence_index": index + 1,
                "occurrence_total": payload["recurrence_count"],
                "impact_cents": signed_impact_cents(payload["type"], amount_cents),
                "impact_sign": "+" if payload["type"] == "income" else "-",
            })
        return items
    return [{
        "month": start_date.strftime("%Y-%m"),
        "date": start_date.isoformat(),
        "description": payload["description"],
        "occurrence_index": 1,
        "occurrence_total": 1,
        "impact_cents": signed_impact_cents(payload["type"], amount_cents),
        "impact_sign": "+" if payload["type"] == "income" else "-",
    }]


def signed_impact_cents(simulation_type: str, amount_cents: int) -> int:
    return amount_cents if simulation_type == "income" else -amount_cents


def build_account_impact(conn, user_id: int, account: dict, payload: dict, virtual_items: list[dict]) -> dict:
    base_balance_cents = fetch_account_balance_until(conn, user_id, account["id"], payload["date"], reconciled_only=True)
    projected_base_cents = account_projected_balance_until(conn, user_id, account, month_end_date(payload["date"][:7]))
    # spec: efeito-borboleta v1.8 — critério 18
    # (o card "Saldo projetado no mês" soma apenas o impacto virtual do mês da simulação,
    # não as ocorrências de meses futuros da série)
    month = payload["date"][:7]
    simulated_month_total_cents = sum(item["impact_cents"] for item in virtual_items if item["month"] == month)
    projected_balance_cents = projected_base_cents + simulated_month_total_cents
    return {
        "month": month,
        "current_balance_cents": base_balance_cents,
        "projected_balance_cents": projected_balance_cents,
        "difference_cents": projected_balance_cents - base_balance_cents,
        "simulated_month_total_cents": simulated_month_total_cents,
    }


def fetch_account_balance_until(conn, user_id: int, account_id: int, limit_date: str, reconciled_only: bool) -> int:
    rows = fetch_account_transactions_until(conn, user_id, account_id, limit_date)
    balance_cents = fetch_account_initial_balance(conn, user_id, account_id)
    for row in rows:
        if reconciled_only and not row["reconciled_at"]:
            continue
        balance_cents += transaction_balance_delta(row, account_id)
    return balance_cents


def fetch_account_initial_balance(conn, user_id: int, account_id: int) -> int:
    row = conn.execute(
        """
        SELECT initial_balance_cents
        FROM checking_accounts
        WHERE id = ? AND user_id = ? AND archived_at IS NULL
        """,
        (account_id, user_id),
    ).fetchone()
    return int(row["initial_balance_cents"] or 0)


def fetch_account_transactions_until(conn, user_id: int, account_id: int, limit_date: str) -> list:
    return conn.execute(
        """
        SELECT amount_cents, type, date, reconciled_at, destination_account_id, destination_amount_cents
        FROM transactions
        WHERE user_id = ? AND archived_at IS NULL AND date <= ?
            AND (account_id = ? OR destination_account_id = ?)
        ORDER BY date ASC, id ASC
        """,
        (user_id, limit_date, account_id, account_id),
    ).fetchall()


def transaction_balance_delta(row: dict, account_id: int) -> int:
    amount_cents = int(row["amount_cents"] or 0)
    if row["type"] in {"transfer", "exchange"} and int(row["destination_account_id"] or 0) == account_id:
        return int(row["destination_amount_cents"] or amount_cents)
    if row["type"] == "income":
        return amount_cents
    if row["type"] in {"expense", "investment", "transfer", "exchange"}:
        return -amount_cents
    return 0


def build_month_impact(conn, user_id: int, account: dict, payload: dict, virtual_items: list[dict]) -> dict:
    month = payload["date"][:7]
    projection = build_month_projection(conn, user_id, account, month, virtual_items)
    return {
        "month": month,
        "real_total_cents": projection["real_total_cents"],
        "simulated_total_cents": projection["simulated_total_cents"],
        "projected_total_cents": projection["projected_total_cents"],
    }


def build_month_projection(conn, user_id: int, account: dict, month: str, virtual_items: list[dict]) -> dict:
    real_total_cents = fetch_month_real_balance_delta(conn, user_id, account["id"], month)
    simulated_total_cents = sum(item["impact_cents"] for item in virtual_items if item["month"] == month)
    return {
        "month": month,
        "real_total_cents": real_total_cents,
        "simulated_total_cents": simulated_total_cents,
        "projected_total_cents": real_total_cents + simulated_total_cents,
    }


def fetch_month_real_balance_delta(conn, user_id: int, account_id: int, month: str) -> int:
    start_date = f"{month}-01"
    end_date = (date.fromisoformat(start_date) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    rows = conn.execute(
        """
        SELECT type, amount_cents, account_id, destination_account_id, destination_amount_cents
        FROM transactions
        WHERE user_id = ? AND archived_at IS NULL
            AND (account_id = ? OR destination_account_id = ?)
            AND reconciled_at IS NOT NULL
            AND date >= ? AND date <= ?
        """,
        (user_id, account_id, account_id, start_date, end_date.isoformat()),
    ).fetchall()
    return sum(transaction_balance_delta(row, account_id) for row in rows)


def build_limit_impact(conn, user_id: int, account: dict, payload: dict, virtual_items: list[dict], category_id: int | None, subcategory_id: int | None) -> dict:
    if category_id is None:
        return {"items": []}
    items = []
    months = sorted({item["month"] for item in virtual_items})
    for month in months:
        limit_rows = conn.execute(
            """
            SELECT id, month, category_id, subcategory_id, limit_amount_cents
            FROM spending_limits
            WHERE user_id = ? AND month = ? AND category_id = ?
            """,
            (user_id, month, category_id),
        ).fetchall()
        for row in limit_rows:
            if subcategory_id is not None and row["subcategory_id"] not in {None, subcategory_id}:
                continue
            real_spent_cents = fetch_limit_real_spend(conn, user_id, account["id"], month, row["category_id"], row["subcategory_id"])
            simulated_spent_cents = 0
            if payload["type"] == "expense":
                simulated_spent_cents = sum(
                    -item["impact_cents"]
                    for item in virtual_items
                    if item["month"] == month and item["impact_cents"] < 0
                )
            projected_spent_cents = real_spent_cents + simulated_spent_cents
            items.append({
                "month": month,
                "category_id": row["category_id"],
                "subcategory_id": row["subcategory_id"],
                "limit_cents": int(row["limit_amount_cents"] or 0),
                "real_spent_cents": real_spent_cents,
                "projected_spent_cents": projected_spent_cents,
                "remaining_cents": int(row["limit_amount_cents"] or 0) - projected_spent_cents,
                "status": "exceeded" if projected_spent_cents > int(row["limit_amount_cents"] or 0) else "ok",
            })
    return {"items": items}


def fetch_limit_real_spend(conn, user_id: int, account_id: int, month: str, category_id: int | None, subcategory_id: int | None) -> int:
    start_date = f"{month}-01"
    end_date = (date.fromisoformat(start_date) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    query = """
        SELECT COALESCE(SUM(amount_cents), 0) AS spent_cents
        FROM transactions
        WHERE user_id = ? AND archived_at IS NULL AND account_id = ? AND type = 'expense' AND date >= ? AND date <= ?
    """
    params: list[object] = [user_id, account_id, start_date, end_date.isoformat()]
    if category_id is not None:
        query += " AND category_id = ?"
        params.append(category_id)
    if subcategory_id is not None:
        query += " AND subcategory_id = ?"
        params.append(subcategory_id)
    row = conn.execute(query, tuple(params)).fetchone()
    return int(row["spent_cents"] or 0)


def build_chart_series(conn, user_id: int, account: dict, payload: dict, virtual_items: list[dict]) -> list[dict]:
    months = build_forecast_months(payload, virtual_items)
    simulated_deltas_by_month = simulation_deltas_by_month(virtual_items)
    series = []
    running_simulated_delta_cents = 0
    for month in months:
        previous_real_balance_cents = account_projected_balance_until(
            conn,
            user_id,
            account,
            (date.fromisoformat(f"{month}-01") - timedelta(days=1)).isoformat(),
        )
        real_balance_cents = account_projected_balance_until(conn, user_id, account, month_end_date(month))
        real_total_cents = real_balance_cents - previous_real_balance_cents
        simulated_total_cents = simulated_deltas_by_month.get(month, 0)
        running_simulated_delta_cents += simulated_total_cents
        series.append({
            "month": month,
            "real_total_cents": real_total_cents,
            "simulated_total_cents": simulated_total_cents,
            "result_cents": real_total_cents + simulated_total_cents,
            "real_balance_cents": real_balance_cents,
            "projected_balance_cents": real_balance_cents + running_simulated_delta_cents,
        })
    return series


def build_daily_projection(conn, user_id: int, account: dict, payload: dict, virtual_items: list[dict]) -> list[dict]:
    # spec: efeito-borboleta v1.8 — critérios 19 a 24
    start_date = daily_projection_start_date(date.fromisoformat(payload["date"]))
    projection = []
    for day_index in range(15):
        cutoff_date = (start_date + timedelta(days=day_index)).isoformat()
        forecast_balance_cents = account_projected_balance_until(conn, user_id, account, cutoff_date)
        simulated_impact_cents = sum(
            item["impact_cents"]
            for item in virtual_items
            if item["date"] <= cutoff_date
        )
        simulated_balance_cents = forecast_balance_cents + simulated_impact_cents
        projection.append({
            "day_index": day_index,
            "date": cutoff_date,
            "forecast_balance_cents": forecast_balance_cents,
            "simulated_balance_cents": simulated_balance_cents,
            "difference_cents": simulated_balance_cents - forecast_balance_cents,
        })
    return projection


def daily_projection_start_date(scenario_date: date, reference_date: date | None = None) -> date:
    today = reference_date or date.today()
    if scenario_date > today + timedelta(days=14):
        return scenario_date - timedelta(days=7)
    return today


def summarize_daily_projection(projection: list[dict]) -> dict:
    forecast_first_negative_date = next(
        (row["date"] for row in projection if row["forecast_balance_cents"] < 0),
        None,
    )
    simulated_first_negative_date = next(
        (row["date"] for row in projection if row["simulated_balance_cents"] < 0),
        None,
    )
    effect = "unchanged"
    if simulated_first_negative_date and (
        forecast_first_negative_date is None
        or simulated_first_negative_date < forecast_first_negative_date
    ):
        effect = "causes_negative"
    elif forecast_first_negative_date and (
        simulated_first_negative_date is None
        or simulated_first_negative_date > forecast_first_negative_date
    ):
        effect = "avoids_negative"
    return {
        "forecast_first_negative_date": forecast_first_negative_date,
        "simulated_first_negative_date": simulated_first_negative_date,
        "effect": effect,
    }


def account_projected_balance_until(conn, user_id: int, account: dict, limit_date: str) -> int:
    balance_cents = fetch_account_balance_until(conn, user_id, account["id"], limit_date, reconciled_only=False)
    return balance_cents - preferred_card_forecast_for_account(conn, user_id, account, limit_date)


def preferred_card_forecast_for_account(conn, user_id: int, account: dict, limit_date: str) -> int:
    rows = conn.execute(
        """
        SELECT
            credit_cards.id AS card_id,
            credit_cards.due_day,
            credit_card_transactions.invoice_month,
            credit_card_transactions.type,
            credit_card_transactions.amount_cents
        FROM credit_cards
        JOIN credit_card_transactions
            ON credit_card_transactions.credit_card_id = credit_cards.id
            AND credit_card_transactions.user_id = credit_cards.user_id
        LEFT JOIN credit_card_payments
            ON credit_card_payments.credit_card_id = credit_card_transactions.credit_card_id
            AND credit_card_payments.invoice_month = credit_card_transactions.invoice_month
            AND credit_card_payments.user_id = credit_card_transactions.user_id
        WHERE credit_cards.user_id = ?
            AND credit_cards.archived_at IS NULL
            AND credit_cards.preferred_payment_account_id = ?
            AND credit_cards.currency = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.reconciled_at IS NOT NULL
            AND credit_card_payments.id IS NULL
        """,
        (user_id, account["id"], account["currency"]),
    ).fetchall()
    invoice_totals: dict[tuple[int, str], int] = {}
    for row in rows:
        due_date = card_invoice_due_date(row["invoice_month"], row["due_day"])
        if due_date > limit_date:
            continue
        key = (int(row["card_id"]), str(row["invoice_month"]))
        amount_cents = int(row["amount_cents"] or 0)
        delta_cents = amount_cents if row["type"] == "expense" else -amount_cents
        invoice_totals[key] = invoice_totals.get(key, 0) + delta_cents
    return sum(max(total, 0) for total in invoice_totals.values())


def card_invoice_due_date(invoice_month: str, due_day: int) -> str:
    year, month = map(int, str(invoice_month).split("-"))
    last_day = (date(year, month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    day = min(max(int(due_day or 1), 1), last_day.day)
    return date(year, month, day).isoformat()


def simulation_deltas_by_month(virtual_items: list[dict]) -> dict[str, int]:
    deltas: dict[str, int] = {}
    for item in virtual_items:
        month = item["month"]
        deltas[month] = deltas.get(month, 0) + int(item["impact_cents"] or 0)
    return deltas


def build_forecast_months(payload: dict, virtual_items: list[dict]) -> list[str]:
    start_month = payload["date"][:7]
    current = date.fromisoformat(f"{start_month}-01")
    generated = []
    for offset in range(5):
        month_date = add_months(current, offset)
        generated.append(month_date.strftime("%Y-%m"))
    return generated


def build_warnings(account_impact: dict, limit_impact: dict) -> list[str]:
    warnings = []
    if account_impact["projected_balance_cents"] < 0:
        warnings.append("Saldo projetado negativo.")
    for item in limit_impact.get("items", []):
        if item["status"] == "exceeded":
            warnings.append(f"Limite ultrapassado para o mês {item['month']}.")
    return warnings
