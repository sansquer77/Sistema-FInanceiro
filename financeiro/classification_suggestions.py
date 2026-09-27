from __future__ import annotations

from http import HTTPStatus
import re
import unicodedata

from financeiro.database import get_connection
from financeiro.identifiers import optional_positive_int_id

SUPPORTED_GROUP_TYPES = {"income", "expense", "investment"}
MIN_AUTO_SUPPORT = 2
MIN_AUTO_CONFIDENCE = 0.80


class ClassificationSuggestionError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def normalize_description(value: object) -> str:
    text = " ".join(str(value or "").strip().split()).casefold()
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", without_marks).strip()


def get_classification_suggestion(
    user_id: int,
    description: object,
    group_type: object,
    source: object = None,
    source_id: object = None,
) -> dict:
    normalized_description = normalize_description(description)
    normalized_group = str(group_type or "").strip().lower()
    if not normalized_description:
        return {"suggestion": None}
    if normalized_group not in SUPPORTED_GROUP_TYPES:
        raise ClassificationSuggestionError("Grupo de classificacao invalido.")
    normalized_source = str(source or "").strip().lower()
    if normalized_source and normalized_source not in {"account", "credit_card"}:
        raise ClassificationSuggestionError("Origem de classificacao invalida.")
    try:
        normalized_source_id = optional_positive_int_id(source_id)
    except ValueError as exc:
        raise ClassificationSuggestionError("Origem de classificacao invalida.") from exc
    if bool(normalized_source) != bool(normalized_source_id):
        raise ClassificationSuggestionError("Origem de classificacao invalida.")

    with get_connection() as conn:
        rows = conn.execute(
            """
            WITH matching_classifications AS (
                SELECT category_id, subcategory_id, date AS used_at,
                    CASE WHEN ? = 'account' AND account_id = ? THEN 1 ELSE 0 END AS context_match
                FROM transactions
                WHERE user_id = ?
                    AND type = ?
                    AND normalized_description = ?
                    AND archived_at IS NULL
                    AND category_id IS NOT NULL
                UNION ALL
                SELECT category_id, subcategory_id, date AS used_at,
                    CASE WHEN ? = 'credit_card' AND credit_card_id = ? THEN 1 ELSE 0 END AS context_match
                FROM credit_card_transactions
                WHERE user_id = ?
                    AND type = ?
                    AND normalized_description = ?
                    AND archived_at IS NULL
                    AND category_id IS NOT NULL
            )
            SELECT
                matching_classifications.category_id,
                matching_classifications.subcategory_id,
                categories.name AS category_name,
                subcategories.name AS subcategory_name,
                COUNT(*) AS support,
                MAX(matching_classifications.used_at) AS last_used_at,
                SUM(matching_classifications.context_match) AS context_support,
                MAX(CASE WHEN matching_classifications.context_match = 1 THEN matching_classifications.used_at END) AS context_last_used_at
            FROM matching_classifications
            JOIN categories
                ON categories.id = matching_classifications.category_id
                AND categories.user_id = ?
                AND categories.group_type = ?
            LEFT JOIN subcategories
                ON subcategories.id = matching_classifications.subcategory_id
                AND subcategories.user_id = categories.user_id
                AND subcategories.category_id = categories.id
            GROUP BY
                matching_classifications.category_id,
                matching_classifications.subcategory_id,
                categories.name,
                subcategories.name
            ORDER BY support DESC, last_used_at DESC, matching_classifications.category_id DESC
            """,
            (
                normalized_source,
                normalized_source_id or 0,
                user_id,
                normalized_group,
                normalized_description,
                normalized_source,
                normalized_source_id or 0,
                user_id,
                normalized_group,
                normalized_description,
                user_id,
                normalized_group,
            ),
        ).fetchall()

    total_support = sum(row["support"] for row in rows)
    total_context_support = sum(row["context_support"] for row in rows)
    if not rows or total_support == 0:
        return {"suggestion": None}
    use_context = bool(normalized_source_id and total_context_support >= MIN_AUTO_SUPPORT)
    if use_context:
        best = max(rows, key=lambda row: (
            row["context_support"], row["context_last_used_at"] or "", row["category_id"]
        ))
        support = best["context_support"]
        confidence = support / total_context_support
    else:
        best = rows[0]
        support = best["support"]
        confidence = support / total_support
    if support < MIN_AUTO_SUPPORT or confidence < MIN_AUTO_CONFIDENCE:
        return {"suggestion": None}
    return {
        "suggestion": {
            "category_id": best["category_id"],
            "category_name": best["category_name"],
            "subcategory_id": best["subcategory_id"],
            "subcategory_name": best["subcategory_name"],
            "confidence": round(confidence, 4),
            "support": support,
            "reason": "historico_contextual" if use_context else "historico_exato",
        }
    }
