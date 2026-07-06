from __future__ import annotations

from datetime import date, timedelta
from http import HTTPStatus

from financeiro.accounts import money_to_cents
from financeiro.database import get_connection, row_to_dict
from financeiro.transactions import add_months, normalize_date, normalize_id

SIMULATION_TYPES = {"income", "expense"}
SERIES_KINDS = {"single", "installment", "recurring"}
RECURRENCE_FREQUENCIES = {"monthly"}


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
        "virtual_items": virtual_items,
        "warnings": warnings,
    }


def normalize_simulation_payload(data: dict) -> dict:
    simulation_type = str(data.get("type", "")).strip().lower()
    if simulation_type not in SIMULATION_TYPES:
        raise SimulationError("Tipo de simulacao invalido.")
    description = str(data.get("description", "")).strip()
    if not description:
        raise SimulationError("Informe a descricao do cenário.")
    amount_cents = money_to_cents(data.get("amount", "0"))
    if amount_cents <= 0:
        raise SimulationError("Informe um valor maior que zero.")
    simulation_date = normalize_date(data.get("date"))
    account_id = normalize_id(data.get("account_id"), "Informe a conta.")
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
        recurrence_count = normalize_count(data.get("recurrence_count"), "Informe a quantidade de ocorrencias.")
    return {
        "type": simulation_type,
        "amount_cents": amount_cents,
        "date": simulation_date,
        "description": description,
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
    text = str(value or "").strip()
    if not text:
        return None
    return normalize_id(text, "Identificador invalido.")


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
    if payload["type"] == "expense" and not payload["category_id"]:
        raise SimulationError("Escolha uma categoria para despesas.")
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
    current_month = payload["date"][:7]
    current_month_impact_cents = sum(item["impact_cents"] for item in virtual_items if item["month"] == current_month)
    projected_balance_cents = base_balance_cents + sum(item["impact_cents"] for item in virtual_items)
    return {
        "current_balance_cents": base_balance_cents + current_month_impact_cents,
        "projected_balance_cents": projected_balance_cents,
        "difference_cents": projected_balance_cents - base_balance_cents,
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
    items = []
    months = sorted({item["month"] for item in virtual_items})
    for month in months:
        if category_id is not None:
            limit_rows = conn.execute(
                """
                SELECT id, month, category_id, subcategory_id, limit_amount_cents
                FROM spending_limits
                WHERE user_id = ? AND month = ? AND category_id = ?
                """,
                (user_id, month, category_id),
            ).fetchall()
        else:
            limit_rows = conn.execute(
                """
                SELECT id, month, category_id, subcategory_id, limit_amount_cents
                FROM spending_limits
                WHERE user_id = ? AND month = ?
                """,
                (user_id, month),
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
    base_date = (date.fromisoformat(f"{months[0]}-01") - timedelta(days=1)).isoformat()
    last_month_end_date = month_end_date(months[-1])
    transactions = fetch_account_transactions_until(conn, user_id, account["id"], last_month_end_date)
    real_deltas_by_month = account_transaction_deltas_by_month(transactions, account["id"])
    simulated_deltas_by_month = simulation_deltas_by_month(virtual_items)
    series = []
    running_real_balance_cents = fetch_account_balance_until(conn, user_id, account["id"], base_date, reconciled_only=False)
    running_simulated_delta_cents = 0
    for month in months:
        real_total_cents = real_deltas_by_month.get(month, 0)
        simulated_total_cents = simulated_deltas_by_month.get(month, 0)
        running_real_balance_cents += real_total_cents
        running_simulated_delta_cents += simulated_total_cents
        series.append({
            "month": month,
            "real_total_cents": real_total_cents,
            "simulated_total_cents": simulated_total_cents,
            "result_cents": real_total_cents + simulated_total_cents,
            "real_balance_cents": running_real_balance_cents,
            "projected_balance_cents": running_real_balance_cents + running_simulated_delta_cents,
        })
    return series


def account_transaction_deltas_by_month(transactions: list, account_id: int) -> dict[str, int]:
    deltas: dict[str, int] = {}
    for row in transactions:
        month = str(row["date"])[:7]
        deltas[month] = deltas.get(month, 0) + transaction_balance_delta(row, account_id)
    return deltas


def simulation_deltas_by_month(virtual_items: list[dict]) -> dict[str, int]:
    deltas: dict[str, int] = {}
    for item in virtual_items:
        month = item["month"]
        deltas[month] = deltas.get(month, 0) + int(item["impact_cents"] or 0)
    return deltas


def build_forecast_months(payload: dict, virtual_items: list[dict]) -> list[str]:
    start_month = payload["date"][:7]
    last_virtual_month = max((item["month"] for item in virtual_items), default=start_month)
    start = date.fromisoformat(f"{start_month}-01")
    last_virtual = date.fromisoformat(f"{last_virtual_month}-01")
    months_until_last_virtual = (last_virtual.year - start.year) * 12 + (last_virtual.month - start.month) + 1
    horizon_months = max(6, months_until_last_virtual)
    current = date.fromisoformat(f"{start_month}-01")
    generated = []
    for offset in range(horizon_months):
        month_date = add_months(current, offset)
        generated.append(month_date.strftime("%Y-%m"))
    return generated


def month_end_date(month: str) -> str:
    start_date = date.fromisoformat(f"{month}-01")
    return ((start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)).isoformat()


def build_warnings(account_impact: dict, limit_impact: dict) -> list[str]:
    warnings = []
    if account_impact["projected_balance_cents"] < 0:
        warnings.append("Saldo projetado negativo.")
    for item in limit_impact.get("items", []):
        if item["status"] == "exceeded":
            warnings.append(f"Limite ultrapassado para o mês {item['month']}.")
    return warnings
