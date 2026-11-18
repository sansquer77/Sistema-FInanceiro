"""Política única de seleção entre IA local, remota e resumo determinístico."""
from __future__ import annotations

from financeiro.database import get_connection
from financeiro.secure_config import ai_settings_status


PRIORITIES = {"local_primeiro", "remota_primeiro", "somente_local", "somente_remota"}
DEFAULT_PRIORITY = "local_primeiro"
DEFAULT_LOCAL_MODEL_ID = "Qwen2.5-1.5B-Instruct-q4f16_1-MLC"
LOCAL_MODEL_CATALOG = (
    {
        "id": DEFAULT_LOCAL_MODEL_ID,
        "label": "Qwen 2.5 1.5B Instruct",
        "description": "Equilíbrio recomendado entre qualidade e memória.",
        "estimated_vram": "1,6 GB",
        "recommended": True,
    },
    {
        "id": "Qwen3-0.6B-q4f16_1-MLC",
        "label": "Qwen 3 0.6B",
        "description": "Opção mais leve para Macs com pouca memória gráfica.",
        "estimated_vram": "1,4 GB",
    },
    {
        "id": "gemma3-1b-it-q4f16_1-MLC",
        "label": "Gemma 3 1B",
        "description": "Modelo compacto para reduzir o uso de memória.",
        "estimated_vram": "711 MB",
    },
    {
        "id": "Llama-3.2-1B-Instruct-q4f16_1-MLC",
        "label": "Llama 3.2 1B Instruct",
        "description": "Alternativa compacta para dispositivos com menos memória.",
        "estimated_vram": "879 MB",
    },
    {
        "id": "Qwen3-1.7B-q4f16_1-MLC",
        "label": "Qwen 3 1.7B",
        "description": "Mais capacidade, com maior uso de memória.",
        "estimated_vram": "2,0 GB",
    },
    {
        "id": "Qwen2.5-3B-Instruct-q4f16_1-MLC",
        "label": "Qwen 2.5 3B Instruct",
        "description": "Modelo mais forte para Macs com mais memória disponível.",
        "estimated_vram": "2,4 GB",
    },
    {
        "id": "Qwen3-4B-q4f16_1-MLC",
        "label": "Qwen 3 4B",
        "description": "Maior capacidade; indicado para Macs com bastante memória.",
        "estimated_vram": "3,4 GB",
    },
)
LOCAL_MODEL_IDS = {item["id"] for item in LOCAL_MODEL_CATALOG}


class AIExecutionError(ValueError):
    pass


def local_model_catalog() -> list[dict]:
    return [dict(item) for item in LOCAL_MODEL_CATALOG]


def normalize_local_model_id(value: object) -> str:
    model_id = str(value or DEFAULT_LOCAL_MODEL_ID).strip()
    if model_id not in LOCAL_MODEL_IDS:
        raise AIExecutionError("Modelo local inválido.")
    return model_id


def get_ai_execution_settings(user_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT execution_priority, local_model_id, data_access_consent, consented_at FROM ai_execution_settings WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
    remote = ai_settings_status(int(user_id))
    priority = str(row["execution_priority"] if row else DEFAULT_PRIORITY)
    local_model_id = normalize_local_model_id(row["local_model_id"] if row else DEFAULT_LOCAL_MODEL_ID)
    consent = bool(row["data_access_consent"]) if row else False
    remote_ready = bool(remote["configured"] and remote["enabled"])
    return {
        "execution_priority": priority,
        "local_model_id": local_model_id,
        "local_models": local_model_catalog(),
        "data_access_consent": consent,
        "consented_at": str(row["consented_at"] or "") if row else "",
        "remote_ready": remote_ready,
        "order": execution_order(priority, remote_ready=remote_ready, data_access_consent=consent),
    }


def save_ai_execution_settings(user_id: int, data: dict) -> dict:
    current = get_ai_execution_settings(int(user_id))
    priority = str(data.get("execution_priority", current["execution_priority"]))
    local_model_id = normalize_local_model_id(data.get("local_model_id", current["local_model_id"]))
    consent = bool(data.get("data_access_consent", current["data_access_consent"]))
    if priority not in PRIORITIES:
        raise AIExecutionError("Prioridade de IA inválida.")
    # spec: consultor/consultor v2.44 — critério 93
    # Fallback remoto também é envio de dados e só entra na política consentida.
    # A revogação explícita deve ser permitida sem forçar a prioridade para local;
    # a mesma prioridade poderá voltar a usar a API quando o consentimento retornar.
    if priority != "somente_local" and current["remote_ready"] and not consent and not current["data_access_consent"]:
        raise AIExecutionError("Aceite o consentimento antes de habilitar o uso de IA remota ou fallback remoto.")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_execution_settings (user_id, execution_priority, local_model_id, data_access_consent, consented_at)
            VALUES (?, ?, ?, ?, CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END)
            ON CONFLICT(user_id) DO UPDATE SET
                execution_priority = excluded.execution_priority,
                local_model_id = excluded.local_model_id,
                data_access_consent = excluded.data_access_consent,
                consented_at = CASE WHEN excluded.data_access_consent = 1
                    THEN COALESCE(ai_execution_settings.consented_at, CURRENT_TIMESTAMP) ELSE NULL END,
                updated_at = CURRENT_TIMESTAMP
            """,
            (int(user_id), priority, local_model_id, 1 if consent else 0, 1 if consent else 0),
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
