"""Configurações, consentimento e perfil complementar criptografado do Consultor."""
from __future__ import annotations

from financeiro import consultor_history as history_store
from financeiro.consultor_catalog import validate_investor_profile
from financeiro.consultor_errors import ConsultorError
from financeiro.database import get_connection
from financeiro.secure_config import (
    SecureConfigError,
    ai_settings_status,
    decrypt_json_from_storage,
    encrypt_json_for_storage,
)


COMPLEMENTARY_PROFILE_SCHEMA_VERSION = 1
COMPLEMENTARY_PROFILE_FIELDS = (
    "idade",
    "possui_imovel_proprio",
    "possui_dependentes",
    "numero_dependentes",
    "objetivo_financeiro_principal",
    "horizonte_investimento_principal",
    "renda_mensal_aproximada",
    "tolerancia_perdas",
)
COMPLEMENTARY_PROFILE_ENUMS = {
    "objetivo_financeiro_principal": {
        "aposentadoria",
        "compra_de_imovel",
        "reserva_de_emergencia",
        "educacao_dos_filhos",
        "independencia_financeira",
        "outro",
    },
    "horizonte_investimento_principal": {
        "curto_prazo",
        "medio_prazo",
        "longo_prazo",
    },
    "renda_mensal_aproximada": {
        "ate_3k",
        "de_3k_a_8k",
        "de_8k_a_15k",
        "acima_de_15k",
    },
    "tolerancia_perdas": {
        "baixa",
        "moderada",
        "alta",
    },
}


DEFAULT_SETTINGS = {
    "consultor_enabled": False,
    "investor_profile": "moderado",
    "data_access_consent": False,
    "consented_at": "",
    "available": False,
    "blocked_reason": "ai_not_configured",
}


def get_consultor_settings(user_id: int) -> dict:
    sync_consultor_with_ai_settings(user_id)
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT consultor_enabled, investor_profile, data_access_consent, consented_at
            FROM consultor_settings
            WHERE user_id = ?
            """,
            (int(user_id),),
        ).fetchone()
    status = ai_settings_status(int(user_id))
    if row is None:
        settings = dict(DEFAULT_SETTINGS)
        settings["ai_configured"] = bool(status["configured"])
        settings["ai_enabled"] = bool(status["enabled"])
        settings["available"] = False
        settings["blocked_reason"] = consultor_blocked_reason(settings)
        return settings
    settings = {
        "consultor_enabled": bool(row["consultor_enabled"]),
        "investor_profile": validate_investor_profile(row["investor_profile"]),
        "data_access_consent": bool(row["data_access_consent"]),
        "consented_at": str(row["consented_at"] or ""),
        "ai_configured": bool(status["configured"]),
        "ai_enabled": bool(status["enabled"]),
    }
    settings["available"] = (
        settings["consultor_enabled"]
        and settings["data_access_consent"]
        and settings["ai_configured"]
        and settings["ai_enabled"]
    )
    settings["blocked_reason"] = consultor_blocked_reason(settings)
    return settings


def consultor_blocked_reason(settings: dict) -> str:
    if not bool(settings.get("ai_configured")) or not bool(settings.get("ai_enabled")):
        return "ai_not_configured"
    if not bool(settings.get("consultor_enabled")):
        return "consultor_disabled"
    if not bool(settings.get("data_access_consent")):
        return "consent_required"
    return ""


def save_consultor_settings(user_id: int, data: dict) -> dict:
    # spec: consultor/consultor v2.0 - criterios 1, 2, 3, 25, 26 e 32
    normalized_user_id = int(user_id)
    current = get_consultor_settings(normalized_user_id)
    consultor_enabled = bool(data.get("consultor_enabled", current["consultor_enabled"]))
    investor_profile = validate_investor_profile(data.get("investor_profile", current["investor_profile"]))
    data_access_consent = bool(data.get("data_access_consent", current["data_access_consent"]))
    ai_status = ai_settings_status(normalized_user_id)
    if consultor_enabled and (not ai_status["configured"] or not ai_status["enabled"]):
        raise ConsultorError("Conclua e habilite a configuracao de IA antes de ativar o Consultor.")
    if consultor_enabled and not data_access_consent:
        raise ConsultorError("Aceite o consentimento de acesso aos dados para ativar o Consultor.")
    should_purge_history = (
        (current["consultor_enabled"] and not consultor_enabled)
        or (current["data_access_consent"] and not data_access_consent)
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO consultor_settings (
                user_id, consultor_enabled, investor_profile, data_access_consent, consented_at
            )
            VALUES (
                ?, ?, ?, ?,
                CASE WHEN ? = 1 THEN COALESCE(
                    (SELECT consented_at FROM consultor_settings WHERE user_id = ?),
                    CURRENT_TIMESTAMP
                ) ELSE NULL END
            )
            ON CONFLICT(user_id) DO UPDATE SET
                consultor_enabled = excluded.consultor_enabled,
                investor_profile = excluded.investor_profile,
                data_access_consent = excluded.data_access_consent,
                consented_at = CASE
                    WHEN excluded.data_access_consent = 1 THEN COALESCE(consultor_settings.consented_at, CURRENT_TIMESTAMP)
                    ELSE NULL
                END,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                normalized_user_id,
                1 if consultor_enabled else 0,
                investor_profile,
                1 if data_access_consent else 0,
                1 if data_access_consent else 0,
                normalized_user_id,
            ),
        )
    if should_purge_history:
        history_store.delete_history(normalized_user_id)
    return get_consultor_settings(normalized_user_id)


def sync_consultor_with_ai_settings(user_id: int) -> None:
    status = ai_settings_status(int(user_id))
    if status["configured"] and status["enabled"]:
        return
    history_store.delete_history(int(user_id))


def get_complementary_profile(user_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT payload_enc, schema_version, atualizado_em
            FROM consultor_perfil_complementar
            WHERE user_id = ?
            """,
            (int(user_id),),
        ).fetchone()
    if row is None:
        return {
            "configured": False,
            "schema_version": COMPLEMENTARY_PROFILE_SCHEMA_VERSION,
            "atualizado_em": "",
            "profile": {},
        }
    try:
        profile = decrypt_json_from_storage(str(row["payload_enc"] or ""))
    except SecureConfigError as exc:
        raise ConsultorError("Perfil Complementar criptografado invalido.") from exc
    return {
        "configured": True,
        "schema_version": int(row["schema_version"] or COMPLEMENTARY_PROFILE_SCHEMA_VERSION),
        "atualizado_em": str(row["atualizado_em"] or ""),
        "profile": normalize_complementary_profile(profile, partial=False),
    }


def save_complementary_profile(user_id: int, data: dict) -> dict:
    # spec: consultor/consultor v2.0 - criterios 22, 23, 24, 25 e 33
    current = get_complementary_profile(int(user_id))["profile"]
    normalized_patch = normalize_complementary_profile(data, partial=True)
    merged = {**current, **normalized_patch}
    payload = encrypt_json_for_storage(merged)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO consultor_perfil_complementar (
                user_id, payload_enc, schema_version, atualizado_em
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                payload_enc = excluded.payload_enc,
                schema_version = excluded.schema_version,
                atualizado_em = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            """,
            (int(user_id), payload, COMPLEMENTARY_PROFILE_SCHEMA_VERSION),
        )
    return get_complementary_profile(int(user_id))


def delete_complementary_profile(user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM consultor_perfil_complementar WHERE user_id = ?",
            (int(user_id),),
        )
        return int(cursor.rowcount or 0) > 0


def normalize_complementary_profile(data: dict, *, partial: bool) -> dict:
    if not isinstance(data, dict):
        raise ConsultorError("Perfil Complementar invalido.")
    normalized: dict = {}
    fields = data.keys() if partial else COMPLEMENTARY_PROFILE_FIELDS
    for field in fields:
        if field not in COMPLEMENTARY_PROFILE_FIELDS:
            continue
        value = data.get(field)
        if value in (None, ""):
            if not partial:
                continue
            normalized.pop(field, None)
            continue
        if field in {"idade", "numero_dependentes"}:
            normalized[field] = normalize_optional_int(value, field)
        elif field in {"possui_imovel_proprio", "possui_dependentes"}:
            normalized[field] = bool(value)
        elif field in COMPLEMENTARY_PROFILE_ENUMS:
            normalized[field] = normalize_profile_enum(field, value)
    if normalized.get("possui_dependentes") is False:
        normalized.pop("numero_dependentes", None)
    return normalized


def normalize_optional_int(value: object, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConsultorError("Campo numerico do Perfil Complementar invalido.") from exc
    if field == "idade" and (parsed < 0 or parsed > 120):
        raise ConsultorError("Idade do Perfil Complementar invalida.")
    if field == "numero_dependentes" and (parsed < 0 or parsed > 30):
        raise ConsultorError("Numero de dependentes invalido.")
    return parsed


def normalize_profile_enum(field: str, value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in COMPLEMENTARY_PROFILE_ENUMS[field]:
        raise ConsultorError("Opcao do Perfil Complementar invalida.")
    return normalized
