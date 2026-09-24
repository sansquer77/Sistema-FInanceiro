from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus
import sqlite3

from financeiro.accounts import cents_to_money, empty_to_none, money_to_cents
from financeiro.categories import normalize_item_id
from financeiro.database import get_connection, row_to_dict
from financeiro.portfolio_calculations import effective_asset_type, normalize_asset_identifier, normalize_indexer


OBJECTIVE_TYPES = {"target", "annual_provision", "continuous_reserve"}
GOAL_STATUSES = {"active", "paused", "completed"}
YIELD_MODES = {"none", "cdi_percentage", "custom_annual_rate"}
TAX_TREATMENTS = {"conservative", "taxable", "exempt"}
MOVEMENT_TYPES = {"contribution", "withdrawal", "adjustment"}
FUNDING_SOURCE_TYPES = {"investment_opening", "investment_operation"}


class FinancialGoalError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def list_financial_goals(user_id: int, include_archived: bool = False) -> list[dict]:
    archived_filter = "" if include_archived else "AND goals.archived_at IS NULL"
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT goals.*, COALESCE(SUM(movements.amount_cents), 0) AS reserved_balance_cents
            FROM financial_goals goals
            LEFT JOIN financial_goal_movements movements
                ON movements.goal_id = goals.id AND movements.user_id = goals.user_id
            WHERE goals.user_id = ? {archived_filter}
            GROUP BY goals.id
            ORDER BY goals.status = 'completed', goals.target_date IS NULL, goals.target_date, goals.name COLLATE NOCASE
            """,
            (user_id,),
        ).fetchall()
        goals = [row_to_dict(row) for row in rows]
        sources_by_goal = funding_sources_by_goal(conn, user_id, [goal["id"] for goal in goals])
    positions = None
    if any(sources_by_goal.values()):
        from financeiro.portfolio import current_portfolio_positions

        positions = current_portfolio_positions(user_id, force_refresh=False)
    return [hydrate_goal(goal, sources_by_goal.get(goal["id"], []), user_id, positions) for goal in goals]


def create_financial_goal(user_id: int, data: dict) -> dict:
    goal = normalize_goal_payload(data)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO financial_goals (
                user_id, name, objective_type, target_amount_cents, target_date, start_date,
                status, yield_mode, yield_percentage_micros, tax_treatment,
                safety_margin_bps, preferred_contribution_day, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, goal["name"], goal["objective_type"], goal["target_amount_cents"],
                goal["target_date"], goal["start_date"], goal["status"], goal["yield_mode"],
                goal["yield_percentage_micros"], goal["tax_treatment"], goal["safety_margin_bps"],
                goal["preferred_contribution_day"], goal["notes"],
            ),
        )
        goal_id = int(cursor.lastrowid)
    return fetch_goal(user_id, goal_id)


def update_financial_goal(user_id: int, goal_id: object, data: dict) -> dict:
    normalized_id = normalize_item_id(goal_id, "Objetivo nao encontrado.")
    goal = normalize_goal_payload(data)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE financial_goals
            SET name = ?, objective_type = ?, target_amount_cents = ?, target_date = ?,
                start_date = ?, status = ?, yield_mode = ?, yield_percentage_micros = ?,
                tax_treatment = ?, safety_margin_bps = ?, preferred_contribution_day = ?,
                notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (
                goal["name"], goal["objective_type"], goal["target_amount_cents"], goal["target_date"],
                goal["start_date"], goal["status"], goal["yield_mode"], goal["yield_percentage_micros"],
                goal["tax_treatment"], goal["safety_margin_bps"], goal["preferred_contribution_day"],
                goal["notes"], normalized_id, user_id,
            ),
        )
        if cursor.rowcount == 0:
            raise FinancialGoalError("Objetivo nao encontrado.", HTTPStatus.NOT_FOUND)
    return fetch_goal(user_id, normalized_id)


def archive_financial_goal(user_id: int, goal_id: object) -> None:
    normalized_id = normalize_item_id(goal_id, "Objetivo nao encontrado.")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE financial_goals
            SET status = 'archived', archived_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND archived_at IS NULL
            """,
            (normalized_id, user_id),
        )
        if cursor.rowcount == 0:
            raise FinancialGoalError("Objetivo nao encontrado.", HTTPStatus.NOT_FOUND)
        conn.execute(
            "DELETE FROM financial_goal_funding_sources WHERE goal_id = ? AND user_id = ?",
            (normalized_id, user_id),
        )


def list_goal_movements(user_id: int, goal_id: object) -> list[dict]:
    normalized_id = normalize_item_id(goal_id, "Objetivo nao encontrado.")
    with get_connection() as conn:
        ensure_goal_owner(conn, user_id, normalized_id)
        rows = conn.execute(
            """
            SELECT * FROM financial_goal_movements
            WHERE user_id = ? AND goal_id = ?
            ORDER BY movement_date DESC, id DESC
            """,
            (user_id, normalized_id),
        ).fetchall()
    return [format_movement(row_to_dict(row)) for row in rows]


def create_goal_movement(user_id: int, goal_id: object, data: dict) -> dict:
    normalized_id = normalize_item_id(goal_id, "Objetivo nao encontrado.")
    movement = normalize_movement_payload(data)
    with get_connection() as conn:
        ensure_goal_owner(conn, user_id, normalized_id)
        current_balance = goal_balance(conn, user_id, normalized_id)
        signed_amount = movement["amount_cents"]
        if movement["movement_type"] == "withdrawal":
            if signed_amount > current_balance:
                raise FinancialGoalError("A retirada nao pode ser maior que o saldo manual do objetivo.")
            signed_amount = -signed_amount
        elif movement["movement_type"] == "adjustment":
            signed_amount -= current_balance
        cursor = conn.execute(
            """
            INSERT INTO financial_goal_movements (
                user_id, goal_id, movement_type, amount_cents, movement_date, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, normalized_id, movement["movement_type"], signed_amount,
                movement["movement_date"], movement["notes"],
            ),
        )
        row = conn.execute(
            "SELECT * FROM financial_goal_movements WHERE id = ? AND user_id = ?",
            (cursor.lastrowid, user_id),
        ).fetchone()
    return format_movement(row_to_dict(row))


def list_goal_funding_sources(user_id: int, goal_id: object) -> list[dict]:
    normalized_id = normalize_item_id(goal_id, "Objetivo nao encontrado.")
    with get_connection() as conn:
        ensure_goal_owner(conn, user_id, normalized_id)
        sources = funding_sources_by_goal(conn, user_id, [normalized_id]).get(normalized_id, [])
    return enrich_funding_source_values(sources, user_id)


def link_goal_funding_source(user_id: int, goal_id: object, data: dict) -> dict:
    normalized_goal_id = normalize_item_id(goal_id, "Objetivo nao encontrado.")
    source_type = normalize_choice(
        data.get("source_type"), FUNDING_SOURCE_TYPES, "Tipo de origem de recurso invalido."
    )
    source_id = normalize_item_id(data.get("source_id"), "Origem de recurso nao encontrada.")
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        ensure_goal_owner(conn, user_id, normalized_goal_id)
        source = fetch_funding_source(conn, user_id, source_type, source_id)
        if source.get("archived_at"):
            raise FinancialGoalError("Uma origem arquivada nao pode ser vinculada ao objetivo.")
        identity = investment_asset_identity(source)
        members = matching_investment_sources(conn, user_id, identity)
        if not members:
            raise FinancialGoalError("Investimento nao encontrado na carteira.", HTTPStatus.NOT_FOUND)
        # spec: objetivos-financeiros v0.10 — critérios 29 a 32
        if any(member.get("emergency_reserve_eligible") for member in members):
            raise FinancialGoalError(
                "Este investimento compoe a Reserva de Emergencia e nao pode financiar outro objetivo."
            )
        for row in conn.execute(
            "SELECT source_type, source_id FROM financial_goal_funding_sources WHERE user_id = ?",
            (user_id,),
        ).fetchall():
            if row["source_type"] not in FUNDING_SOURCE_TYPES:
                continue
            existing = fetch_funding_source(conn, user_id, row["source_type"], row["source_id"])
            if investment_asset_identity(existing) == identity:
                raise FinancialGoalError("Este investimento ja esta vinculado a outro objetivo ativo.")
        canonical = min(members, key=lambda member: (0 if member["source_type"] == "investment_opening" else 1, int(member["id"])))
        canonical["label"] = canonical.get("asset_name") or canonical.get("asset_identifier") or "Investimento"
        try:
            cursor = conn.execute(
                """
                INSERT INTO financial_goal_funding_sources (user_id, goal_id, source_type, source_id)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, normalized_goal_id, canonical["source_type"], canonical["id"]),
            )
        except sqlite3.IntegrityError as exc:
            raise FinancialGoalError("Esta origem de recurso ja esta vinculada a outro objetivo ativo.") from exc
        link = conn.execute(
            "SELECT * FROM financial_goal_funding_sources WHERE id = ? AND user_id = ?",
            (cursor.lastrowid, user_id),
        ).fetchone()
        result = format_funding_source(row_to_dict(link), canonical)
    return enrich_funding_source_values([result], user_id)[0]


def unlink_goal_funding_source(user_id: int, goal_id: object, link_id: object) -> None:
    normalized_goal_id = normalize_item_id(goal_id, "Objetivo nao encontrado.")
    normalized_link_id = normalize_item_id(link_id, "Vinculo de recurso nao encontrado.")
    with get_connection() as conn:
        ensure_goal_owner(conn, user_id, normalized_goal_id)
        cursor = conn.execute(
            "DELETE FROM financial_goal_funding_sources WHERE id = ? AND goal_id = ? AND user_id = ?",
            (normalized_link_id, normalized_goal_id, user_id),
        )
        if cursor.rowcount == 0:
            raise FinancialGoalError("Vinculo de recurso nao encontrado.", HTTPStatus.NOT_FOUND)


def ensure_not_linked_to_financial_goal(conn, user_id: int, source_type: str, source_id: int) -> None:
    """Impede que uma fonte alocada seja reaproveitada na Reserva de Emergência."""
    # spec: objetivos-financeiros v0.10 — critérios 31 e 32
    source = fetch_funding_source(conn, user_id, source_type, source_id)
    identity = investment_asset_identity(source)
    rows = conn.execute(
        """
        SELECT sources.source_type, sources.source_id, goals.name
        FROM financial_goal_funding_sources sources
        JOIN financial_goals goals
          ON goals.id = sources.goal_id AND goals.user_id = sources.user_id
        WHERE sources.user_id = ? AND sources.source_type IN ('investment_opening', 'investment_operation')
          AND goals.archived_at IS NULL
        """,
        (user_id,),
    ).fetchall()
    for row in rows:
        linked = fetch_funding_source(conn, user_id, row["source_type"], row["source_id"])
        if investment_asset_identity(linked) != identity:
            continue
        raise FinancialGoalError(
            f'Este investimento esta vinculado ao objetivo "{row["name"]}" e nao pode compor a Reserva de Emergencia.'
        )


def emergency_reserve_summary(user_id: int, positions: list[dict] | None = None) -> dict:
    if positions is None:
        from financeiro.portfolio import current_portfolio_positions

        positions = current_portfolio_positions(user_id, force_refresh=False)
    components = []
    total_brl_cents = 0
    portfolios = {}
    for position in positions:
        if not position.get("emergency_reserve_eligible"):
            continue
        value_brl_cents = int(position.get("current_value_brl_cents") or 0)
        total_brl_cents += value_brl_cents
        component = {
            "account_id": position.get("account_id"),
            "asset_name": position.get("asset_name") or position.get("asset_identifier") or "Investimento",
            "asset_identifier": position.get("asset_identifier") or "",
            "asset_type": position.get("asset_type") or "",
            "asset_type_label": position.get("asset_type_label") or position.get("asset_type") or "",
            "account_name": position.get("account_name") or "",
            "currency": position.get("currency") or "BRL",
            "current_value": cents_to_money(int(position.get("current_value_cents") or 0)),
            "current_value_brl": cents_to_money(value_brl_cents),
            "current_value_brl_cents": value_brl_cents,
            "maturity_date": position.get("fixed_income_maturity_date") or None,
            "quote_source": position.get("quote_source") or "",
            "quote_date": position.get("quote_date") or None,
        }
        components.append(component)
        portfolio_key = position.get("account_id") or f"name:{component['account_name'] or 'unknown'}"
        portfolio = portfolios.setdefault(portfolio_key, {
            "account_id": component["account_id"],
            "account_name": component["account_name"] or "Carteira não identificada",
            "total_brl_cents": 0,
            "components": [],
        })
        portfolio["total_brl_cents"] += value_brl_cents
        portfolio["components"].append(component)
    portfolio_groups = sorted(portfolios.values(), key=lambda item: item["account_name"].casefold())
    for portfolio in portfolio_groups:
        portfolio["total_brl"] = cents_to_money(portfolio["total_brl_cents"])
    return {
        "total_brl": cents_to_money(total_brl_cents),
        "total_brl_cents": total_brl_cents,
        "components": components,
        "portfolios": portfolio_groups,
    }


def fetch_goal(user_id: int, goal_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT goals.*, COALESCE(SUM(movements.amount_cents), 0) AS reserved_balance_cents
            FROM financial_goals goals
            LEFT JOIN financial_goal_movements movements
                ON movements.goal_id = goals.id AND movements.user_id = goals.user_id
            WHERE goals.id = ? AND goals.user_id = ?
            GROUP BY goals.id
            """,
            (goal_id, user_id),
        ).fetchone()
        if not row:
            raise FinancialGoalError("Objetivo nao encontrado.", HTTPStatus.NOT_FOUND)
        goal = row_to_dict(row)
        sources = funding_sources_by_goal(conn, user_id, [goal_id]).get(goal_id, [])
    return hydrate_goal(goal, sources, user_id)


def funding_sources_by_goal(conn, user_id: int, goal_ids: list[int]) -> dict[int, list[dict]]:
    if not goal_ids:
        return {}
    placeholders = ", ".join("?" for _ in goal_ids)
    rows = conn.execute(
        f"""
        SELECT * FROM financial_goal_funding_sources
        WHERE user_id = ? AND goal_id IN ({placeholders})
        ORDER BY id
        """,
        (user_id, *goal_ids),
    ).fetchall()
    result: dict[int, list[dict]] = {}
    for row in rows:
        link = row_to_dict(row)
        # Links antigos a contas correntes não são mais uma cobertura válida.
        if link["source_type"] not in FUNDING_SOURCE_TYPES:
            continue
        source = fetch_funding_source(conn, user_id, link["source_type"], link["source_id"])
        result.setdefault(link["goal_id"], []).append(format_funding_source(link, source))
    return result


def fetch_funding_source(conn, user_id: int, source_type: str, source_id: int) -> dict:
    if source_type == "investment_opening":
        row = conn.execute(
            """
            SELECT positions.id, positions.account_id, positions.asset_type, positions.asset_name,
                   positions.asset_identifier, positions.cnpj, positions.fixed_income_indexer,
                   positions.fixed_income_maturity_date, positions.emergency_reserve_eligible,
                   accounts.currency, accounts.name AS account_name, accounts.archived_at
            FROM investment_opening_positions positions
            JOIN checking_accounts accounts ON accounts.id = positions.account_id AND accounts.user_id = positions.user_id
            WHERE positions.id = ? AND positions.user_id = ?
            """,
            (source_id, user_id),
        ).fetchone()
        source = row_to_dict(row)
        if source:
            source["label"] = source.get("asset_name") or source.get("asset_identifier") or "Investimento"
    else:
        row = conn.execute(
            """
            SELECT operations.id, operations.account_id, operations.asset_type, operations.asset_name,
                   operations.asset_identifier, operations.cnpj, operations.fixed_income_indexer,
                   operations.fixed_income_maturity_date, operations.emergency_reserve_eligible,
                   accounts.currency, accounts.name AS account_name, accounts.archived_at
            FROM investment_operations operations
            JOIN checking_accounts accounts ON accounts.id = operations.account_id AND accounts.user_id = operations.user_id
            WHERE operations.id = ? AND operations.user_id = ?
            """,
            (source_id, user_id),
        ).fetchone()
        source = row_to_dict(row)
        if source:
            source["label"] = source.get("asset_name") or source.get("asset_identifier") or "Investimento"
    if not source:
        raise FinancialGoalError("Origem de recurso nao encontrada.", HTTPStatus.NOT_FOUND)
    return source


def format_funding_source(link: dict, source: dict) -> dict:
    return {
        "id": link["id"],
        "goal_id": link["goal_id"],
        "source_type": link["source_type"],
        "source_id": link["source_id"],
        "label": source.get("label") or "Origem de recurso",
        "account_name": source.get("account_name") or source.get("name") or "",
        "account_id": source.get("account_id"),
        "currency": source.get("currency") or "BRL",
        "asset_type": source.get("asset_type") or "",
        "asset_identifier": source.get("asset_identifier") or "",
        "asset_name": source.get("asset_name") or source.get("asset_identifier") or "Investimento",
        "cnpj": source.get("cnpj") or "",
        "fixed_income_indexer": source.get("fixed_income_indexer") or "",
        "fixed_income_maturity_date": source.get("fixed_income_maturity_date") or "",
        "created_at": link["created_at"],
    }


def hydrate_goal(goal: dict, sources: list[dict], user_id: int, positions: list[dict] | None = None) -> dict:
    # spec: objetivos-financeiros v0.10 — critério 30
    manual_balance_cents = int(goal.get("reserved_balance_cents") or 0)
    sources = enrich_funding_source_values(sources, user_id, positions)
    linked_balance_cents = sum(int(source.get("current_value_brl_cents") or 0) for source in sources)
    goal["manual_reserved_balance_cents"] = manual_balance_cents
    goal["linked_reserved_balance_cents"] = linked_balance_cents
    goal["reserved_balance_cents"] = manual_balance_cents + linked_balance_cents
    goal = format_goal(goal)
    goal["funding_sources"] = sources
    goal["coverage_status"] = "linked" if sources else "unlinked"
    return goal


def enrich_funding_source_values(
    sources: list[dict], user_id: int, positions: list[dict] | None = None
) -> list[dict]:
    if not sources:
        return sources
    if positions is None:
        from financeiro.portfolio import current_portfolio_positions

        positions = current_portfolio_positions(user_id, force_refresh=False)
    for source in sources:
        identity = investment_asset_identity(source)
        value_cents = sum(
            int(position.get("current_value_brl_cents") or 0)
            for position in positions
            if investment_asset_identity(position) == identity
        )
        source["current_value_brl_cents"] = value_cents
        source["current_value_brl"] = cents_to_money(value_cents)
    return sources


def investment_asset_identity(source: dict) -> tuple:
    asset_type = effective_asset_type(source.get("asset_type"), source.get("asset_identifier"))
    fixed_income = asset_type == "fixed_income"
    return (
        int(source.get("account_id") or 0),
        str(source.get("currency") or "BRL").strip().upper(),
        asset_type,
        normalize_asset_identifier(source.get("asset_identifier"), asset_type),
        str(source.get("asset_name") or source.get("asset_identifier") or "").strip().casefold(),
        "".join(char for char in str(source.get("cnpj") or "") if char.isdigit()),
        normalize_indexer(source.get("fixed_income_indexer")) if fixed_income else "",
        str(source.get("fixed_income_maturity_date") or "").strip() if fixed_income else "",
    )


def matching_investment_sources(conn, user_id: int, identity: tuple) -> list[dict]:
    rows = conn.execute(
        """
        SELECT * FROM (
            SELECT 'investment_opening' AS source_type, positions.id, positions.user_id,
                   positions.account_id, positions.asset_type, positions.asset_identifier,
                   positions.asset_name, positions.cnpj, positions.fixed_income_indexer,
                   positions.fixed_income_maturity_date, positions.emergency_reserve_eligible,
                   accounts.currency, accounts.name AS account_name, accounts.archived_at
            FROM investment_opening_positions positions
            JOIN checking_accounts accounts ON accounts.id = positions.account_id
                AND accounts.user_id = positions.user_id
            WHERE positions.user_id = ?
            UNION ALL
            SELECT 'investment_operation' AS source_type, operations.id, operations.user_id,
                   operations.account_id, operations.asset_type, operations.asset_identifier,
                   operations.asset_name, operations.cnpj, operations.fixed_income_indexer,
                   operations.fixed_income_maturity_date, operations.emergency_reserve_eligible,
                   accounts.currency, accounts.name AS account_name, accounts.archived_at
            FROM investment_operations operations
            JOIN checking_accounts accounts ON accounts.id = operations.account_id
                AND accounts.user_id = operations.user_id
            WHERE operations.user_id = ?
        )
        """,
        (user_id, user_id),
    ).fetchall()
    return [
        item for row in rows
        if investment_asset_identity(item := row_to_dict(row)) == identity
    ]


def ensure_goal_owner(conn, user_id: int, goal_id: int) -> None:
    row = conn.execute(
        "SELECT id FROM financial_goals WHERE id = ? AND user_id = ? AND archived_at IS NULL",
        (goal_id, user_id),
    ).fetchone()
    if not row:
        raise FinancialGoalError("Objetivo nao encontrado.", HTTPStatus.NOT_FOUND)


def goal_balance(conn, user_id: int, goal_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) AS balance FROM financial_goal_movements WHERE user_id = ? AND goal_id = ?",
        (user_id, goal_id),
    ).fetchone()
    return int(row["balance"] or 0)


def normalize_goal_payload(data: dict) -> dict:
    name = str(data.get("name") or "").strip()
    if not name:
        raise FinancialGoalError("Informe o nome do objetivo.")
    objective_type = normalize_choice(data.get("objective_type"), OBJECTIVE_TYPES, "Tipo de objetivo invalido.")
    target_amount_cents = money_to_cents(data.get("target_amount", "0"))
    if target_amount_cents <= 0:
        raise FinancialGoalError("Informe um valor-alvo maior que zero.")
    start_date = normalize_date(data.get("start_date") or date.today().isoformat(), "Data inicial invalida.")
    target_date = normalize_optional_date(data.get("target_date"), "Data desejada invalida.")
    if objective_type != "continuous_reserve" and not target_date:
        raise FinancialGoalError("Informe a data desejada.")
    if target_date and target_date < start_date:
        raise FinancialGoalError("A data desejada deve ser igual ou posterior a data inicial.")
    status = normalize_choice(data.get("status") or "active", GOAL_STATUSES, "Estado do objetivo invalido.")
    yield_mode = normalize_choice(data.get("yield_mode") or "none", YIELD_MODES, "Forma de rendimento invalida.")
    tax_treatment = normalize_choice(data.get("tax_treatment") or "conservative", TAX_TREATMENTS, "Tratamento tributario invalido.")
    yield_percentage_micros = decimal_to_micros(data.get("yield_percentage") or (100 if yield_mode == "cdi_percentage" else 0))
    safety_margin_bps = normalize_int(data.get("safety_margin_bps") or 0, 0, 10000, "Margem de seguranca invalida.")
    contribution_day = data.get("preferred_contribution_day")
    preferred_contribution_day = None if str(contribution_day or "").strip() == "" else normalize_int(contribution_day, 1, 28, "Dia de aporte invalido.")
    return {
        "name": name,
        "objective_type": objective_type,
        "target_amount_cents": target_amount_cents,
        "target_date": target_date,
        "start_date": start_date,
        "status": status,
        "yield_mode": yield_mode,
        "yield_percentage_micros": yield_percentage_micros,
        "tax_treatment": tax_treatment,
        "safety_margin_bps": safety_margin_bps,
        "preferred_contribution_day": preferred_contribution_day,
        "notes": empty_to_none(data.get("notes")),
    }


def normalize_movement_payload(data: dict) -> dict:
    movement_type = normalize_choice(data.get("movement_type"), MOVEMENT_TYPES, "Tipo de movimentacao invalido.")
    amount_cents = money_to_cents(data.get("amount", "0"))
    if amount_cents < 0 or (movement_type != "adjustment" and amount_cents <= 0):
        raise FinancialGoalError("Informe um valor valido para a movimentacao.")
    return {
        "movement_type": movement_type,
        "amount_cents": amount_cents,
        "movement_date": normalize_date(data.get("movement_date") or date.today().isoformat(), "Data da movimentacao invalida."),
        "notes": empty_to_none(data.get("notes")),
    }


def format_goal(goal: dict) -> dict:
    reserved = int(goal.get("reserved_balance_cents") or 0)
    manual_reserved = int(goal.get("manual_reserved_balance_cents", reserved) or 0)
    linked_reserved = int(goal.get("linked_reserved_balance_cents") or 0)
    target = int(goal["target_amount_cents"])
    effective_target = int((Decimal(target) * (Decimal(10000 + int(goal["safety_margin_bps"] or 0)) / Decimal(10000))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    remaining = max(effective_target - reserved, 0)
    months = contribution_months(goal.get("start_date"), goal.get("target_date"))
    recommended = (remaining + months - 1) // months if months > 0 else remaining
    pace_status = calculate_pace_status(goal, reserved, effective_target)
    goal["target_amount"] = cents_to_money(target)
    goal["effective_target_amount"] = cents_to_money(effective_target)
    goal["reserved_balance"] = cents_to_money(reserved)
    goal["manual_reserved_balance"] = cents_to_money(manual_reserved)
    goal["linked_reserved_balance"] = cents_to_money(linked_reserved)
    goal["remaining_amount"] = cents_to_money(remaining)
    goal["recommended_monthly_contribution"] = cents_to_money(recommended)
    goal["progress_percentage"] = round((reserved / effective_target * 100) if effective_target else 0, 2)
    goal["pace_status"] = pace_status
    goal["yield_percentage"] = str(Decimal(int(goal["yield_percentage_micros"])) / Decimal(1_000_000))
    goal["projection"] = build_goal_projection(goal, reserved, effective_target, months)
    return goal


def build_goal_projection(goal: dict, reserved: int, effective_target: int, months: int) -> dict:
    """Build conservative and yield scenarios without changing the reserved balance."""
    # spec: objetivos-financeiros v0.10 — critérios 7, 8, 9, 11, 27, 28 e 30
    remaining = max(effective_target - reserved, 0)
    conservative_monthly = (remaining + months - 1) // months if months > 0 else remaining
    conservative_contributions = remaining
    annual_rate, rate_label = projection_annual_rate(goal)
    if months <= 0 or annual_rate <= 0 or remaining <= 0:
        yield_contributions = conservative_contributions
        projected_yield = 0
    else:
        monthly_factor = (Decimal("1") + annual_rate) ** (Decimal("1") / Decimal("12"))
        reserved_future = Decimal(reserved) * (monthly_factor ** months)
        annuity_factor = sum((monthly_factor ** period for period in range(1, months + 1)), Decimal("0"))
        required = max(Decimal(effective_target) - reserved_future, Decimal("0"))
        yield_monthly = int((required / annuity_factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if annuity_factor else 0
        yield_contributions = max(yield_monthly, 0) * months
        projected_total = reserved_future + Decimal(yield_contributions) / Decimal(months) * annuity_factor if months else reserved_future
        projected_yield = max(int(projected_total.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) - reserved - yield_contributions, 0)
    yield_total = reserved + yield_contributions + projected_yield
    uncovered = max(effective_target - yield_total, 0)
    return {
        "reference_date": date.today().isoformat(),
        "rate_label": rate_label,
        "annual_rate_percentage": str((annual_rate * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "conservative": projection_scenario(reserved, conservative_contributions, 0, max(effective_target - reserved - conservative_contributions, 0), conservative_monthly),
        "with_yield": projection_scenario(reserved, yield_contributions, projected_yield, uncovered, (yield_contributions + months - 1) // months if months else yield_contributions),
    }


def projection_annual_rate(goal: dict) -> tuple[Decimal, str]:
    mode = goal.get("yield_mode") or "none"
    percentage = Decimal(int(goal.get("yield_percentage_micros") or 0)) / Decimal(1_000_000)
    percentage_label = f"{percentage:f}"
    if "." in percentage_label:
        percentage_label = percentage_label.rstrip("0").rstrip(".")
    if mode == "custom_annual_rate":
        return percentage / Decimal("100"), f"{percentage_label}% a.a."
    if mode == "cdi_percentage":
        from financeiro.portfolio import fallback_indexer_annual_rate

        cdi_rate = fallback_indexer_annual_rate("CDI")
        return cdi_rate * percentage / Decimal("100"), f"{percentage_label}% do CDI"
    return Decimal("0"), "Sem rendimento"


def projection_scenario(reserved: int, contributions: int, projected_yield: int, uncovered: int, monthly: int) -> dict:
    return {
        "reserved": cents_to_money(reserved),
        "future_contributions": cents_to_money(contributions),
        "projected_yield": cents_to_money(projected_yield),
        "uncovered": cents_to_money(uncovered),
        "monthly_contribution": cents_to_money(monthly),
        "projected_total": cents_to_money(reserved + contributions + projected_yield),
    }


def format_movement(movement: dict) -> dict:
    movement["amount"] = cents_to_money(abs(int(movement["amount_cents"])))
    movement["signed_amount"] = cents_to_money(int(movement["amount_cents"]))
    return movement


def calculate_pace_status(goal: dict, reserved: int, effective_target: int) -> str:
    if goal.get("status") == "paused":
        return "paused"
    if reserved >= effective_target:
        return "completed"
    target_date = goal.get("target_date")
    if target_date and target_date < date.today().isoformat():
        return "overdue"
    return "on_track"


def contribution_months(start_value: str | None, target_value: str | None) -> int:
    if not target_value:
        return 0
    start = date.fromisoformat(start_value or date.today().isoformat())
    target = date.fromisoformat(target_value)
    return max((target.year - start.year) * 12 + target.month - start.month + 1, 1)


def normalize_choice(value: object, choices: set[str], message: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in choices:
        raise FinancialGoalError(message)
    return normalized


def normalize_date(value: object, message: str) -> str:
    try:
        return date.fromisoformat(str(value or "").strip()).isoformat()
    except ValueError as exc:
        raise FinancialGoalError(message) from exc


def normalize_optional_date(value: object, message: str) -> str | None:
    if not str(value or "").strip():
        return None
    return normalize_date(value, message)


def normalize_int(value: object, minimum: int, maximum: int, message: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise FinancialGoalError(message) from exc
    if normalized < minimum or normalized > maximum:
        raise FinancialGoalError(message)
    return normalized


def decimal_to_micros(value: object) -> int:
    raw = str(value or "0").strip().replace(",", ".")
    try:
        normalized = Decimal(raw)
    except InvalidOperation as exc:
        raise FinancialGoalError("Percentual de rendimento invalido.") from exc
    if normalized < 0:
        raise FinancialGoalError("Percentual de rendimento invalido.")
    return int((normalized * Decimal(1_000_000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
