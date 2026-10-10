from __future__ import annotations

import json
import sqlite3

from financeiro.classification_suggestions import normalize_description


# spec: importacao/importacao-dados v1.16 — critérios 14 a 17
LEARNABLE_IMPORT_FIELDS = {"descricao", "categoria", "subcategoria", "tags"}


def find_import_adjustment(
    conn: sqlite3.Connection,
    user_id: int,
    source_type: str,
    source_id: int,
    original_description: object,
    transaction_type: str,
) -> dict | None:
    normalized_description = normalize_description(original_description)
    if not normalized_description or transaction_type not in {"income", "expense"}:
        return None
    source_column = "account_id" if source_type == "account" else "credit_card_id"
    if source_type not in {"account", "credit_card"}:
        return None
    row = conn.execute(
        f"""
        SELECT corrected_description, category, subcategory, tags_json
        FROM import_adjustments
        WHERE user_id = ? AND {source_column} = ?
            AND (normalized_description = ? OR normalized_corrected_description = ?)
            AND transaction_type = ?
        ORDER BY (normalized_description = ?) DESC, updated_at DESC, id DESC
        LIMIT 1
        """,
        (user_id, source_id, normalized_description, normalized_description, transaction_type, normalized_description),
    ).fetchone()
    if row is None:
        legacy_alias_rows = conn.execute(
            f"""
            SELECT corrected_description, category, subcategory, tags_json
            FROM import_adjustments
            WHERE user_id = ? AND {source_column} = ?
                AND normalized_corrected_description IS NULL AND transaction_type = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (user_id, source_id, transaction_type),
        ).fetchall()
        row = next(
            (
                candidate
                for candidate in legacy_alias_rows
                if normalize_description(candidate["corrected_description"]) == normalized_description
            ),
            None,
        )
    if row is None:
        return None
    try:
        tags = json.loads(row["tags_json"])
    except (TypeError, json.JSONDecodeError):
        tags = []
    return {
        "description": row["corrected_description"],
        "category": row["category"],
        "subcategory": row["subcategory"] or "",
        "tags": tags if isinstance(tags, list) else [],
    }


def save_import_adjustment(
    conn: sqlite3.Connection,
    user_id: int,
    source_type: str,
    source_id: int,
    original_description: object,
    transaction_type: str,
    corrected_description: object,
    category: object,
    subcategory: object,
    tags: list[str],
) -> None:
    normalized_description = normalize_description(original_description)
    if (
        not normalized_description
        or source_type not in {"account", "credit_card"}
        or transaction_type not in {"income", "expense"}
    ):
        return
    source_column = "account_id" if source_type == "account" else "credit_card_id"
    other_column = "credit_card_id" if source_column == "account_id" else "account_id"
    conn.execute(
        f"""
        INSERT INTO import_adjustments (
            user_id, {source_column}, normalized_description, normalized_corrected_description, transaction_type,
            corrected_description, category, subcategory, tags_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, {source_column}, normalized_description, transaction_type)
        WHERE {source_column} IS NOT NULL
        DO UPDATE SET
            corrected_description = excluded.corrected_description,
            normalized_corrected_description = excluded.normalized_corrected_description,
            category = excluded.category,
            subcategory = excluded.subcategory,
            tags_json = excluded.tags_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            user_id,
            source_id,
            normalized_description,
            normalize_description(corrected_description),
            transaction_type,
            " ".join(str(corrected_description or "").split()),
            " ".join(str(category or "").split()),
            " ".join(str(subcategory or "").split()) or None,
            json.dumps(tags, ensure_ascii=False),
        ),
    )
