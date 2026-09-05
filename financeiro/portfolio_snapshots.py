"""Persistência local de snapshots mensais do Portfólio.

O módulo não calcula valores nem consulta provedores externos. Recebe uma
conexão SQLite já aberta pela composição do domínio e mantém a captura
idempotente por usuário, competência, conta e ativo.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterable


SNAPSHOT_COLUMNS = (
    "user_id", "snapshot_month", "as_of_date", "account_id", "currency",
    "asset_type", "asset_identifier", "asset_name", "quantity_micros",
    "unit_price_cents", "market_value_cents", "cost_basis_cents",
    "contribution_cents", "redemption_cents", "dividend_cents",
    "quote_source", "valuation_status",
)


def upsert_snapshots(conn: sqlite3.Connection, snapshots: Iterable[dict]) -> int:
    """Grava um lote idempotente e retorna a quantidade de linhas recebidas."""
    rows = [snapshot_row(snapshot) for snapshot in snapshots]
    if not rows:
        return 0
    placeholders = ", ".join("?" for _ in SNAPSHOT_COLUMNS)
    assignments = ", ".join(
        f"{column} = excluded.{column}"
        for column in SNAPSHOT_COLUMNS
        if column not in {"user_id", "snapshot_month", "account_id", "currency", "asset_type", "asset_identifier", "asset_name"}
    )
    conn.executemany(
        f"""
        INSERT INTO investment_monthly_snapshots ({', '.join(SNAPSHOT_COLUMNS)})
        VALUES ({placeholders})
        ON CONFLICT (user_id, snapshot_month, account_id, currency, asset_type, asset_identifier, asset_name)
        DO UPDATE SET {assignments}, updated_at = CURRENT_TIMESTAMP
        """,
        [tuple(row[column] for column in SNAPSHOT_COLUMNS) for row in rows],
    )
    return len(rows)


def list_snapshots(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    snapshot_month: str | None = None,
    currency: str | None = None,
) -> list[dict]:
    """Lê snapshots ordenados para alimentar a série de rentabilidade."""
    clauses = ["user_id = ?"]
    params: list[object] = [user_id]
    if snapshot_month:
        clauses.append("snapshot_month = ?")
        params.append(snapshot_month)
    if currency:
        clauses.append("currency = ?")
        params.append(currency.upper())
    rows = conn.execute(
        f"""
        SELECT * FROM investment_monthly_snapshots
        WHERE {' AND '.join(clauses)}
        ORDER BY snapshot_month, currency, asset_type, asset_identifier, asset_name
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def snapshot_row(snapshot: dict) -> dict:
    """Normaliza um snapshot antes de persistir, sem converter valores monetários."""
    row = {column: snapshot.get(column) for column in SNAPSHOT_COLUMNS}
    row["snapshot_month"] = str(row["snapshot_month"] or "")
    row["as_of_date"] = str(row["as_of_date"] or "")
    row["currency"] = str(row["currency"] or "BRL").upper()
    row["asset_type"] = str(row["asset_type"] or "other")
    row["asset_identifier"] = str(row["asset_identifier"] or "")
    row["asset_name"] = str(row["asset_name"] or "")
    row["quote_source"] = str(row["quote_source"] or "not_available")
    row["valuation_status"] = str(row["valuation_status"] or "approximate")
    for column in (
        "user_id", "account_id", "quantity_micros", "unit_price_cents", "market_value_cents",
        "cost_basis_cents", "contribution_cents", "redemption_cents", "dividend_cents",
    ):
        row[column] = int(row[column] or 0)
    if not row["user_id"] or not row["account_id"] or not row["snapshot_month"] or not row["as_of_date"]:
        raise ValueError("Snapshot mensal requer usuário, conta, competência e data de referência.")
    if row["valuation_status"] not in {"observed", "approximate"}:
        raise ValueError("Status de valorização inválido.")
    return row
