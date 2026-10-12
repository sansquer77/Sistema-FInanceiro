"""Política única de seleção entre IA local, remota e resumo determinístico."""
from __future__ import annotations

from financeiro.database import get_connection
from financeiro.secure_config import ai_settings_status


PRIORITIES = {"local_primeiro", "remota_primeiro", "somente_local", "somente_remota"}
DEFAULT_PRIORITY = "local_primeiro"


class AIExecutionError(ValueError):
    pass


def get_ai_execution_settings(user_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT execution_priority, data_access_consent, consented_at FROM ai_execution_settings WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
    remote = ai_settings_status(int(user_id))
    priority = str(row["execution_priority"] if row else DEFAULT_PRIORITY)
    consent = bool(row["data_access_consent"]) if row else False
    remote_ready = bool(remote["configured"] and remote["enabled"])
    return {
        "execution_priority": priority,
        "data_access_consent": consent,
        "consented_at": str(row["consented_at"] or "") if row else "",
        "remote_ready": remote_ready,
        "order": execution_order(priority, remote_ready=remote_ready, data_access_consent=consent),
    }


def save_ai_execution_settings(user_id: int, data: dict) -> dict:
    current = get_ai_execution_settings(int(user_id))
    priority = str(data.get("execution_priority", current["execution_priority"]))
    consent = bool(data.get("data_access_consent", current["data_access_consent"]))
    if priority not in PRIORITIES:
        raise AIExecutionError("Prioridade de IA inválida.")
    # spec: tendencias-saude-financeira v2.26 — critério 2
    # Fallback remoto também é envio de dados e só entra na política consentida.
    if priority != "somente_local" and current["remote_ready"] and not consent:
        raise AIExecutionError("Aceite o consentimento antes de habilitar o uso de IA remota ou fallback remoto.")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_execution_settings (user_id, execution_priority, data_access_consent, consented_at)
            VALUES (?, ?, ?, CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END)
            ON CONFLICT(user_id) DO UPDATE SET
                execution_priority = excluded.execution_priority,
                data_access_consent = excluded.data_access_consent,
                consented_at = CASE WHEN excluded.data_access_consent = 1
                    THEN COALESCE(ai_execution_settings.consented_at, CURRENT_TIMESTAMP) ELSE NULL END,
                updated_at = CURRENT_TIMESTAMP
            """,
            (int(user_id), priority, 1 if consent else 0, 1 if consent else 0),
        )
    return get_ai_execution_settings(int(user_id))


def execution_order(priority: str, *, remote_ready: bool, data_access_consent: bool) -> list[str]:
    remote_allowed = remote_ready and data_access_consent
    if priority == "somente_local":
        return ["local", "deterministica"]
    if priority == "somente_remota":
        return (["remota"] if remote_allowed else []) + ["deterministica"]
    if priority == "remota_primeiro":
        return (["remota"] if remote_allowed else []) + ["local", "deterministica"]
    return ["local"] + (["remota"] if remote_allowed else []) + ["deterministica"]
