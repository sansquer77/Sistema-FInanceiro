from __future__ import annotations

from http import HTTPStatus
import re
import unicodedata

from financeiro.database import get_connection

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


def get_classification_suggestion(user_id: int, description: object, group_type: object) -> dict:
    normalized_description = normalize_description(description)
    normalized_group = str(group_type or "").strip().lower()
    if not normalized_description:
        return {"suggestion": None}
    if normalized_group not in SUPPORTED_GROUP_TYPES:
        raise ClassificationSuggestionError("Grupo de classificacao invalido.")

    with get_connection() as conn:
        rows = conn.execute(
            """
            WITH matching_classifications AS (
                SELECT category_id, subcategory_id, date AS used_at
                FROM transactions
                WHERE user_id = ?
                    AND type = ?
                    AND normalized_description = ?
                    AND archived_at IS NULL
                    AND category_id IS NOT NULL
                UNION ALL
                SELECT category_id, subcategory_id, date AS used_at
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
                MAX(matching_classifications.used_at) AS last_used_at
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
                user_id,
                normalized_group,
                normalized_description,
                user_id,
                normalized_group,
                normalized_description,
                user_id,
                normalized_group,
            ),
        ).fetchall()

    total_support = sum(row["support"] for row in rows)
    if not rows or total_support == 0:
        return {"suggestion": None}
    best = rows[0]
    confidence = best["support"] / total_support
    if best["support"] < MIN_AUTO_SUPPORT or confidence < MIN_AUTO_CONFIDENCE:
        return {"suggestion": None}
    return {
        "suggestion": {
            "category_id": best["category_id"],
            "category_name": best["category_name"],
            "subcategory_id": best["subcategory_id"],
            "subcategory_name": best["subcategory_name"],
            "confidence": round(confidence, 4),
            "support": best["support"],
            "reason": "historico_exato",
        }
    }
