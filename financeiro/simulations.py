from __future__ import annotations

from datetime import date, timedelta
from http import HTTPStatus

from financeiro.accounts import AccountError, money_to_cents
from financeiro.categories import ClassificationError
from financeiro.database import get_connection, row_to_dict
from financeiro.transactions import TransactionError, add_months, normalize_date, normalize_id

SIMULATION_TYPES = {"income", "expense"}
SERIES_KINDS = {"single", "installment", "recurring"}
RECURRENCE_FREQUENCIES = {"monthly", "quarterly", "semiannual", "annual"}


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
        SELECT id, currency, current_balance_cents
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
                "impact_cents": payload["type"] == "income" and current_amount or -current_amount,
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
                "impact_cents": payload["type"] == "income" and amount_cents or -amount_cents,
                "impact_sign": "+" if payload["type"] == "income" else "-",
            })
        return items
    return [{
        "month": start_date.strftime("%Y-%m"),
        "date": start_date.isoformat(),
        "description": payload["description"],
        "occurrence_index": 1,
        "occurrence_total": 1,
        "impact_cents": payload["type"] == "income" and amount_cents or -amount_cents,
        "impact_sign": "+" if payload["type"] == "income" else "-",
    }]


def build_account_impact(conn, user_id: int, account: dict, payload: dict, virtual_items: list[dict]) -> dict:
    current_balance_cents = fetch_reconciled_balance_until(conn, user_id, account["id"], payload["date"])
    projected_balance_cents = current_balance_cents + sum(item["impact_cents"] for item in virtual_items)
    return {
        "current_balance_cents": current_balance_cents,
        "projected_balance_cents": projected_balance_cents,
        "difference_cents": projected_balance_cents - current_balance_cents,
    }


def fetch_reconciled_balance_until(conn, user_id: int, account_id: int, limit_date: str) -> int:
    start_date = None
    rows = conn.execute(
        """
        SELECT amount_cents, type, date, reconciled_at, destination_account_id, destination_amount_cents
        FROM transactions
        WHERE user_id = ? AND archived_at IS NULL AND account_id = ? AND date <= ?
        ORDER BY date ASC, id ASC
        """,
        (user_id, account_id, limit_date),
    ).fetchall()
    balance_cents = int(conn.execute(
        """
        SELECT initial_balance_cents
        FROM checking_accounts
        WHERE id = ? AND user_id = ? AND archived_at IS NULL
        """,
        (account_id, user_id),
    ).fetchone()["initial_balance_cents"] or 0)
    for row in rows:
        if not row["reconciled_at"]:
            continue
        amount_cents = int(row["amount_cents"] or 0)
        if row["type"] == "income":
            balance_cents += amount_cents
        elif row["type"] == "expense":
            balance_cents -= amount_cents
        elif row["type"] == "transfer":
            balance_cents -= amount_cents
            if row["destination_account_id"] and row["destination_amount_cents"]:
                balance_cents += int(row["destination_amount_cents"] or 0)
    return balance_cents


def build_month_impact(conn, user_id: int, account: dict, payload: dict, virtual_items: list[dict]) -> dict:
    month = payload["date"][:7]
    real_total_cents = fetch_month_real_spend(conn, user_id, account["id"], month)
    simulated_total_cents = sum(item["impact_cents"] for item in virtual_items if item["month"] == month)
    return {
        "month": month,
        "real_total_cents": real_total_cents,
        "simulated_total_cents": simulated_total_cents,
        "projected_total_cents": real_total_cents + simulated_total_cents,
    }


def fetch_month_real_spend(conn, user_id: int, account_id: int, month: str) -> int:
    start_date = f"{month}-01"
    end_date = (date.fromisoformat(start_date) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    row = conn.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN type = 'income' THEN amount_cents ELSE amount_cents END), 0) AS spent_cents
        FROM transactions
        WHERE user_id = ? AND archived_at IS NULL AND account_id = ? AND date >= ? AND date <= ?
        """,
        (user_id, account_id, start_date, end_date.isoformat()),
    ).fetchone()
    return int(row["spent_cents"] or 0)


def build_limit_impact(conn, user_id: int, account: dict, payload: dict, virtual_items: list[dict], category_id: int | None, subcategory_id: int | None) -> dict:
    items = []
    months = sorted({item["month"] for item in virtual_items})
    for month in months:
        limit_rows = conn.execute(
            """
            SELECT id, month, category_id, subcategory_id, limit_amount_cents
            FROM spending_limits
            WHERE user_id = ? AND month = ? AND category_id = ?
            """,
            (user_id, month, category_id) if category_id is not None else (user_id, month),
        ).fetchall()
        for row in limit_rows:
            if subcategory_id is not None and row["subcategory_id"] not in {None, subcategory_id}:
                continue
            real_spent_cents = fetch_limit_real_spend(conn, user_id, account["id"], month, row["category_id"], row["subcategory_id"])
            simulated_spent_cents = sum(
                item["impact_cents"] * -1 if item["impact_cents"] < 0 else item["impact_cents"]
                for item in virtual_items
                if item["month"] == month
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
    months = sorted({item["month"] for item in virtual_items})
    series = []
    for month in months:
        real_total_cents = fetch_month_real_spend(conn, user_id, account["id"], month)
        simulated_total_cents = sum(item["impact_cents"] for item in virtual_items if item["month"] == month)
        series.append({
            "month": month,
            "real_total_cents": real_total_cents,
            "simulated_total_cents": simulated_total_cents,
            "result_cents": real_total_cents + simulated_total_cents,
        })
    return series


def build_warnings(account_impact: dict, limit_impact: dict) -> list[str]:
    warnings = []
    if account_impact["projected_balance_cents"] < 0:
        warnings.append("Saldo projetado negativo.")
    for item in limit_impact.get("items", []):
        if item["status"] == "exceeded":
            warnings.append(f"Limite ultrapassado para o mês {item['month']}.")
    return warnings
