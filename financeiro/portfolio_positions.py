from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def allocation_goal_key(position: dict) -> str:
    if position.get("asset_type") == "stock" and str(position.get("currency") or "BRL").upper() == "USD":
        return "stock_usd"
    return str(position.get("asset_type") or "other")


def consume_savings_anniversaries_fifo(entries: list[dict], redeemed_cost_cents: int) -> list[dict]:
    remaining = max(int(redeemed_cost_cents or 0), 0)
    result = []
    for entry in sorted(entries, key=lambda item: str(item.get("date") or "")):
        amount = max(int(entry.get("amount_cents") or 0), 0)
        consumed = min(amount, remaining)
        remaining -= consumed
        if amount > consumed:
            result.append({**entry, "amount_cents": amount - consumed})
    return result


def aggregate_savings_anniversaries(entries: list[dict]) -> list[dict]:
    grouped: dict[str, int] = {}
    for entry in entries:
        key = str(entry.get("date") or "").strip()
        try:
            date.fromisoformat(key)
        except ValueError:
            continue
        grouped[key] = grouped.get(key, 0) + int(entry.get("amount_cents") or 0)
    return [{"date": key, "amount_cents": amount} for key, amount in sorted(grouped.items()) if key and amount > 0]


def decimal_to_micros_value(value: Decimal) -> int:
    return int((value * Decimal("1000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def load_position_inputs(conn, user_id: int) -> dict:
    """Lê apenas dados locais pela conexão recebida; não abre conexão nem consulta rede."""
    operation_rows_raw = conn.execute(
        """
        SELECT investment_operations.*, 'operation' AS source_type, investment_operations.id AS source_id,
            1 AS apply_tax_estimate, transactions.date, transactions.description, transactions.amount_cents,
            transactions.exchange_rate_micros, transactions.amount_brl_cents,
            checking_accounts.name AS account_name, checking_accounts.currency AS account_currency, checking_accounts.archived_at AS account_archived_at
        FROM investment_operations
        JOIN transactions ON transactions.id = investment_operations.transaction_id
            AND transactions.user_id = investment_operations.user_id
            AND transactions.archived_at IS NULL
            AND (
                transactions.reconciled_at IS NOT NULL
                OR (
                    transactions.series_kind = 'single'
                    AND transactions.date <= DATE('now', 'localtime')
                )
            )
        JOIN checking_accounts ON checking_accounts.id = investment_operations.account_id
            AND checking_accounts.user_id = investment_operations.user_id
        WHERE investment_operations.user_id = ?
        """,
        (user_id,),
    ).fetchall()
    opening_rows_raw = conn.execute(
        """
        SELECT investment_opening_positions.id, 'opening' AS source_type,
            investment_opening_positions.id AS source_id, investment_opening_positions.user_id,
            NULL AS transaction_id, investment_opening_positions.account_id,
            investment_opening_positions.asset_type, investment_opening_positions.asset_identifier,
            investment_opening_positions.asset_name, investment_opening_positions.cnpj,
            investment_opening_positions.quantity_micros, investment_opening_positions.unit_price_cents,
            investment_opening_positions.total_cost_cents AS invested_amount_cents,
            0 AS brokerage_fee_cents, 0 AS exchange_fee_cents, 0 AS tax_cents, 0 AS other_costs_cents,
            investment_opening_positions.fixed_income_mode, investment_opening_positions.fixed_income_indexer,
            investment_opening_positions.fixed_income_rate_micros, investment_opening_positions.fixed_income_maturity_date,
            investment_opening_positions.apply_tax_estimate, investment_opening_positions.emergency_reserve_eligible,
            investment_opening_positions.savings_anniversaries_json,
            investment_opening_positions.acquisition_date AS date,
            'Posicao inicial' AS description, investment_opening_positions.total_cost_cents AS amount_cents,
            investment_opening_positions.exchange_rate_micros, 0 AS amount_brl_cents,
            checking_accounts.name AS account_name, checking_accounts.currency AS account_currency, checking_accounts.archived_at AS account_archived_at
        FROM investment_opening_positions
        JOIN checking_accounts ON checking_accounts.id = investment_opening_positions.account_id
            AND checking_accounts.user_id = investment_opening_positions.user_id
        WHERE investment_opening_positions.user_id = ?
        """,
        (user_id,),
    ).fetchall()
    redemption_rows = conn.execute(
        """
        SELECT source_type, source_id, SUM(redeemed_cost_cents) AS redeemed_cost_cents,
            SUM(redeemed_quantity_micros) AS redeemed_quantity_micros
        FROM investment_redemptions
        WHERE user_id = ?
        GROUP BY source_type, source_id
        """,
        (user_id,),
    ).fetchall()
    closed_rows = conn.execute(
        "SELECT * FROM investment_closed_positions WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    override_rows = conn.execute(
        "SELECT * FROM investment_value_overrides WHERE user_id = ?", (user_id,)
    ).fetchall()
    def ordered(rows):
        return sorted((dict(row) for row in rows), key=lambda row: json.dumps(row, sort_keys=True))
    return {
        "reference_date": date.today().isoformat(),
        "operations": ordered(operation_rows_raw),
        "openings": ordered(opening_rows_raw),
        "redemptions": ordered(redemption_rows),
        "closed": ordered(closed_rows),
        "overrides": ordered(override_rows),
    }
