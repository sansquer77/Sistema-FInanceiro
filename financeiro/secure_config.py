from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from financeiro import database

CONFIG_KEY_ENV = "SISTEMA_FINANCEIRO_CONFIG_KEY"
CONFIG_KEY_PATH_ENV = "SISTEMA_FINANCEIRO_CONFIG_KEY_PATH"
KDF_ITERATIONS = 310_000
EMAIL_PROVIDER_PRESETS = {
    "gmail": {
        "label": "Gmail",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
    },
    "outlook": {
        "label": "Outlook / Microsoft",
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "use_tls": True,
    },
}
AI_PROVIDER_PRESETS = {
    "openai": {
        "label": "OpenAI / ChatGPT",
        "base_url": "https://api.openai.com/v1",
        "auth_type": "bearer",
    },
    "anthropic": {
        "label": "Anthropic / Claude",
        "base_url": "https://api.anthropic.com/v1",
        "auth_type": "bearer",
    },
    "google": {
        "label": "Google / Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "auth_type": "bearer",
    },
    "custom": {
        "label": "Custom / Local",
        "base_url": "",
        "auth_type": "bearer",
    },
    "local": {
        "label": "Local",
        "base_url": "",
        "auth_type": "none",
    },
}


class SecureConfigError(Exception):
    pass


def email_config_path(user_id: int) -> Path:
    return database.DATA_DIR / f"email_config_user_{int(user_id)}.enc"


def email_config_key_path() -> Path:
    return database.DATA_DIR / "email_config.key"


def config_key_path() -> Path:
    configured = str(os.environ.get(CONFIG_KEY_PATH_ENV) or "").strip()
    if configured:
        return Path(configured).expanduser()
    return database.DATA_DIR.parent / "secure" / "config.key"


def ai_secret_config_path(user_id: int) -> Path:
    return database.DATA_DIR / f"ai_config_user_{int(user_id)}.enc"


def mais_retorno_config_path(user_id: int) -> Path:
    return database.DATA_DIR / f"mais_retorno_config_user_{int(user_id)}.enc"


def load_encrypted_config(path: Path, key_path: Path | None = None) -> dict:
    if not path.exists():
        raise SecureConfigError("Configuracao criptografada nao encontrada.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return decrypt_config_payload(payload, key_path)


def decrypt_config_payload(payload: dict, key_path: Path | None = None) -> dict:
    key_material = load_key_material(key_path)
    salt = decode_field(payload, "salt")
    nonce = decode_field(payload, "nonce")
    ciphertext = decode_field(payload, "ciphertext")
    expected_tag = decode_field(payload, "tag")
    iterations = int(payload.get("iterations") or KDF_ITERATIONS)
    encryption_key, signing_key = derive_keys(key_material, salt, iterations)
    actual_tag = sign_payload(signing_key, nonce, ciphertext)
    if not hmac.compare_digest(actual_tag, expected_tag):
        raise SecureConfigError("Configuracao criptografada invalida ou chave incorreta.")
    plain = xor_bytes(ciphertext, key_stream(encryption_key, nonce, len(ciphertext)))
    return json.loads(plain.decode("utf-8"))


def encrypt_config_payload(config: dict, key_path: Path | None = None) -> dict:
    key_material = load_or_create_key_material(key_path)
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    encryption_key, signing_key = derive_keys(key_material, salt, KDF_ITERATIONS)
    plain = json.dumps(config, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ciphertext = xor_bytes(plain, key_stream(encryption_key, nonce, len(plain)))
    return {
        "version": 1,
        "kdf": "pbkdf2_hmac_sha256",
        "iterations": KDF_ITERATIONS,
        "salt": encode_bytes(salt),
        "nonce": encode_bytes(nonce),
        "ciphertext": encode_bytes(ciphertext),
        "tag": encode_bytes(sign_payload(signing_key, nonce, ciphertext)),
    }


def save_encrypted_config(config: dict, path: Path, key_path: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = encrypt_config_payload(config, key_path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(path, 0o600)


def encrypt_json_for_storage(config: dict, key_path: Path | None = None) -> str:
    # spec: consultor/consultor v0.29 - criterio 23
    return json.dumps(encrypt_config_payload(config, key_path), indent=2, sort_keys=True)


def decrypt_json_from_storage(payload_text: str, key_path: Path | None = None) -> dict:
    # spec: consultor/consultor v0.29 - criterio 23
    if not str(payload_text or "").strip():
        raise SecureConfigError("Configuracao criptografada nao encontrada.")
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise SecureConfigError("Configuracao criptografada invalida.") from exc
    return decrypt_config_payload(payload, key_path)


def email_config_status(user_id: int) -> dict:
    configured = secure_config_exists(user_id, "email")
    status = {
        "configured": configured,
        "provider": "",
        "sender": "",
        "smtp_server": "",
        "smtp_port": "",
        "use_tls": True,
        "presets": email_provider_presets(),
    }
    if not configured:
        return status
    try:
        config = load_email_config(user_id)
    except SecureConfigError:
        status["configured"] = False
        return status
    return {
        **status,
        "configured": True,
        "provider": str(config.get("provider") or ""),
        "sender": str(config.get("sender") or ""),
        "smtp_server": str(config.get("smtp_server") or ""),
        "smtp_port": int(config.get("smtp_port") or 587),
        "use_tls": bool(config.get("use_tls", True)),
    }


def save_email_config(user_id: int, data: dict) -> dict:
    provider = str(data.get("provider") or "gmail").strip().lower()
    sender = str(data.get("sender") or "").strip()
    password = str(data.get("password") or "")
    if not sender or "@" not in sender:
        raise SecureConfigError("Informe o email remetente.")
    if not password:
        raise SecureConfigError("Informe a senha de app.")
    if provider in EMAIL_PROVIDER_PRESETS:
        preset = EMAIL_PROVIDER_PRESETS[provider]
        smtp_server = str(preset["smtp_server"])
        smtp_port = int(preset["smtp_port"])
        use_tls = bool(preset["use_tls"])
    elif provider == "manual":
        smtp_server = str(data.get("smtp_server") or "").strip()
        try:
            smtp_port = int(data.get("smtp_port") or 587)
        except (TypeError, ValueError) as exc:
            raise SecureConfigError("Informe uma porta SMTP valida.") from exc
        use_tls = bool(data.get("use_tls", True))
        if not smtp_server:
            raise SecureConfigError("Informe o servidor SMTP.")
    else:
        raise SecureConfigError("Provedor de email invalido.")
    save_secure_config(user_id, "email", {
        "provider": provider,
        "sender": sender,
        "password": password,
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "use_tls": use_tls,
    })
    return email_config_status(user_id)


def load_email_config(user_id: int) -> dict:
    return load_secure_config(user_id, "email")


def mais_retorno_config_status(user_id: int) -> dict:
    if not secure_config_exists(user_id, "mais_retorno"):
        return {"configured": False, "enabled": False, "has_api_key": False}
    try:
        config = load_secure_config(user_id, "mais_retorno")
    except SecureConfigError:
        return {"configured": False, "enabled": False, "has_api_key": False}
    return {
        "configured": True,
        "enabled": bool(config.get("enabled")),
        "has_api_key": bool(config.get("api_key")),
    }


def save_mais_retorno_settings(user_id: int, data: dict) -> dict:
    # spec: preferencias-abas v0.8 — criterios 7, 8 e 13
    # (chave criptografada por usuario no SQLite; desligar mantem a chave para reativacao sem nova)
    enabled = bool(data.get("enabled", False))
    api_key = str(data.get("api_key") or "").strip()
    existing_key = ""
    if secure_config_exists(user_id, "mais_retorno"):
        try:
            existing_key = str(load_secure_config(user_id, "mais_retorno").get("api_key") or "")
        except SecureConfigError:
            existing_key = ""
    effective_key = api_key or existing_key
    if enabled and not effective_key:
        raise SecureConfigError("Informe a chave de API da Mais Retorno para ativar as cotas de fundos.")
    if effective_key:
        save_secure_config(user_id, "mais_retorno", {"enabled": enabled, "api_key": effective_key})
    else:
        delete_secure_config(user_id, "mais_retorno")
    return mais_retorno_config_status(user_id)


def load_mais_retorno_api_key(user_id: int) -> str:
    status = mais_retorno_config_status(user_id)
    if not status["enabled"]:
        return ""
    try:
        config = load_secure_config(user_id, "mais_retorno")
    except SecureConfigError:
        return ""
    return str(config.get("api_key") or "")


def ai_provider_presets() -> list[dict]:
    return [
        {
            "provider": key,
            "label": str(value["label"]),
            "base_url": str(value["base_url"]),
            "auth_type": str(value["auth_type"]),
        }
        for key, value in AI_PROVIDER_PRESETS.items()
    ]


def ai_settings_status(user_id: int) -> dict:
    with database.get_connection() as conn:
        row = conn.execute(
            """
            SELECT enabled, provider, base_url, model, auth_type, timeout_seconds,
                   temperature_micros, max_tokens, secret_config_path
            FROM user_ai_settings
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        return default_ai_settings_status()
    has_secret = secure_config_exists(user_id, "ai")
    return {
        "configured": bool(row["model"]) and (str(row["auth_type"]) == "none" or has_secret),
        "enabled": bool(row["enabled"]),
        "provider": str(row["provider"] or "custom"),
        "base_url": str(row["base_url"] or ""),
        "model": str(row["model"] or ""),
        "auth_type": str(row["auth_type"] or "bearer"),
        "has_api_key": has_secret,
        "timeout_seconds": int(row["timeout_seconds"] or 10),
        "temperature": micros_to_decimal(row["temperature_micros"], "0.2"),
        "max_tokens": int(row["max_tokens"] or 700),
        "presets": ai_provider_presets(),
        "contract": "openai_chat_completions",
    }


def default_ai_settings_status() -> dict:
    return {
        "configured": False,
        "enabled": False,
        "provider": "custom",
        "base_url": "",
        "model": "",
        "auth_type": "bearer",
        "has_api_key": False,
        "timeout_seconds": 10,
        "temperature": 0.2,
        "max_tokens": 700,
        "presets": ai_provider_presets(),
        "contract": "openai_chat_completions",
    }


def save_ai_settings(user_id: int, data: dict) -> dict:
    provider = normalize_ai_provider(data.get("provider"))
    preset = AI_PROVIDER_PRESETS[provider]
    enabled = bool(data.get("enabled", False))
    base_url = str(data.get("base_url") or preset["base_url"]).strip().rstrip("/")
    model = str(data.get("model") or "").strip()
    auth_type = str(data.get("auth_type") or preset["auth_type"]).strip().lower()
    api_key = str(data.get("api_key") or "").strip()
    timeout_seconds = normalize_int(data.get("timeout_seconds"), 10, 1, 60, "Timeout invalido.")
    temperature_micros = normalize_temperature_micros(data.get("temperature"))
    max_tokens = normalize_int(data.get("max_tokens"), 700, 1, 4000, "Limite de tokens invalido.")
    if auth_type not in {"none", "bearer"}:
        raise SecureConfigError("Tipo de autenticacao de IA invalido.")
    if provider in {"custom", "local"} and not base_url:
        raise SecureConfigError("Informe a URL base da IA customizada/local.")
    if provider in {"openai", "anthropic", "google"} and not base_url:
        raise SecureConfigError("URL base do provedor de IA invalida.")
    if enabled and not model:
        raise SecureConfigError("Informe o modelo de IA.")

    existing_key = ""
    if secure_config_exists(user_id, "ai"):
        try:
            existing_key = str(load_secure_config(user_id, "ai").get("api_key") or "")
        except SecureConfigError:
            existing_key = ""
    effective_key = api_key or existing_key
    if enabled and auth_type == "bearer" and not effective_key:
        raise SecureConfigError("Informe a chave de API para ativar a IA.")
    if auth_type == "bearer" and effective_key:
        save_secure_config(user_id, "ai", {"api_key": effective_key})
    elif auth_type == "none":
        delete_secure_config(user_id, "ai")

    # spec: tendencias-saude-financeira v2.13 — critérios 17, 21, 23, 27 e 28
    with database.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_ai_settings (
                user_id, enabled, provider, base_url, model, auth_type,
                timeout_seconds, temperature_micros, max_tokens, secret_config_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                enabled = excluded.enabled,
                provider = excluded.provider,
                base_url = excluded.base_url,
                model = excluded.model,
                auth_type = excluded.auth_type,
                timeout_seconds = excluded.timeout_seconds,
                temperature_micros = excluded.temperature_micros,
                max_tokens = excluded.max_tokens,
                secret_config_path = excluded.secret_config_path,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                1 if enabled else 0,
                provider,
                base_url,
                model,
                auth_type,
                timeout_seconds,
                temperature_micros,
                max_tokens,
                "secure_configs:ai",
            ),
        )
    return ai_settings_status(user_id)


def load_ai_settings(user_id: int) -> dict:
    status = ai_settings_status(user_id)
    api_key = ""
    if status["has_api_key"]:
        api_key = str(load_secure_config(user_id, "ai").get("api_key") or "")
    return {**status, "api_key": api_key}


def normalize_ai_provider(value: object) -> str:
    provider = str(value or "custom").strip().lower()
    if provider not in AI_PROVIDER_PRESETS:
        raise SecureConfigError("Provedor de IA invalido.")
    return provider


def normalize_int(value: object, default: int, minimum: int, maximum: int, message: str) -> int:
    try:
        normalized = int(value if value not in (None, "") else default)
    except (TypeError, ValueError) as exc:
        raise SecureConfigError(message) from exc
    if normalized < minimum or normalized > maximum:
        raise SecureConfigError(message)
    return normalized


def normalize_temperature_micros(value: object) -> int:
    raw = str(value if value not in (None, "") else "0.2").strip().replace(",", ".")
    try:
        parsed = float(raw)
    except ValueError as exc:
        raise SecureConfigError("Temperatura de IA invalida.") from exc
    if parsed < 0 or parsed > 2:
        raise SecureConfigError("Temperatura de IA invalida.")
    return int(round(parsed * 1_000_000))


def micros_to_decimal(value: object, default: str) -> float:
    try:
        return round(int(value) / 1_000_000, 4)
    except (TypeError, ValueError):
        return float(default)


def email_provider_presets() -> list[dict]:
    return [
        {
            "provider": key,
            "label": str(value["label"]),
            "smtp_server": str(value["smtp_server"]),
            "smtp_port": int(value["smtp_port"]),
            "use_tls": bool(value["use_tls"]),
        }
        for key, value in EMAIL_PROVIDER_PRESETS.items()
    ]


def secure_config_legacy_path(user_id: int, config_type: str) -> Path:
    if config_type == "email":
        return email_config_path(user_id)
    if config_type == "ai":
        return ai_secret_config_path(user_id)
    if config_type == "mais_retorno":
        return mais_retorno_config_path(user_id)
    raise SecureConfigError("Tipo de configuracao segura invalido.")


def secure_config_payload(user_id: int, config_type: str) -> str | None:
    with database.get_connection() as conn:
        row = conn.execute(
            """
            SELECT payload_enc
            FROM secure_configs
            WHERE user_id = ? AND config_type = ?
            """,
            (user_id, config_type),
        ).fetchone()
    if row is not None:
        return str(row["payload_enc"] or "")

    legacy_path = secure_config_legacy_path(user_id, config_type)
    if config_type == "ai":
        with database.get_connection() as conn:
            settings_row = conn.execute(
                "SELECT secret_config_path FROM user_ai_settings WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        configured_path = str(settings_row["secret_config_path"] or "") if settings_row is not None else ""
        if configured_path and not configured_path.startswith("secure_configs:"):
            legacy_path = Path(configured_path)
    if not legacy_path.exists():
        return None
    payload_text = legacy_path.read_text(encoding="utf-8")
    with database.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO secure_configs (user_id, config_type, payload_enc, source_path)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, config_type) DO UPDATE SET
                payload_enc = excluded.payload_enc,
                source_path = excluded.source_path,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, config_type, payload_text, str(legacy_path)),
        )
    return payload_text


def secure_config_exists(user_id: int, config_type: str) -> bool:
    return secure_config_payload(user_id, config_type) is not None


def load_secure_config(user_id: int, config_type: str) -> dict:
    payload_text = secure_config_payload(user_id, config_type)
    if payload_text is None:
        raise SecureConfigError("Configuracao criptografada nao encontrada.")
    return decrypt_json_from_storage(payload_text)


def save_secure_config(user_id: int, config_type: str, config: dict) -> None:
    payload_text = encrypt_json_for_storage(config)
    with database.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO secure_configs (user_id, config_type, payload_enc, source_path)
            VALUES (?, ?, ?, '')
            ON CONFLICT(user_id, config_type) DO UPDATE SET
                payload_enc = excluded.payload_enc,
                source_path = '',
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, config_type, payload_text),
        )


def delete_secure_config(user_id: int, config_type: str) -> None:
    with database.get_connection() as conn:
        conn.execute(
            "DELETE FROM secure_configs WHERE user_id = ? AND config_type = ?",
            (user_id, config_type),
        )
    legacy_path = secure_config_legacy_path(user_id, config_type)
    if legacy_path.exists():
        legacy_path.unlink()


def preferred_key_path(key_path: Path | None = None) -> Path:
    return Path(key_path) if key_path is not None else config_key_path()


def migrate_legacy_key_material() -> None:
    preferred = config_key_path()
    legacy = email_config_key_path()
    if preferred.exists() or not legacy.exists() or preferred == legacy:
        return
    preferred.parent.mkdir(parents=True, exist_ok=True)
    preferred.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
    os.chmod(preferred, 0o600)


def load_key_material(key_path: Path | None = None) -> bytes:
    env_value = os.environ.get(CONFIG_KEY_ENV)
    if env_value:
        return env_value.encode("utf-8")
    if key_path is None:
        migrate_legacy_key_material()
    key_path = preferred_key_path(key_path)
    if not key_path.exists():
        raise SecureConfigError("Chave local da configuracao criptografada nao encontrada.")
    return base64.b64decode(key_path.read_text(encoding="utf-8").strip().encode("ascii"))


def load_or_create_key_material(key_path: Path | None = None) -> bytes:
    env_value = os.environ.get(CONFIG_KEY_ENV)
    if env_value:
        return env_value.encode("utf-8")
    if key_path is None:
        migrate_legacy_key_material()
    key_path = preferred_key_path(key_path)
    if key_path.exists():
        return load_key_material(key_path)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_material = secrets.token_bytes(32)
    key_path.write_text(base64.b64encode(key_material).decode("ascii"), encoding="utf-8")
    os.chmod(key_path, 0o600)
    return key_material


def derive_keys(key_material: bytes, salt: bytes, iterations: int) -> tuple[bytes, bytes]:
    derived = hashlib.pbkdf2_hmac("sha256", key_material, salt, iterations, dklen=64)
    return derived[:32], derived[32:]


def key_stream(key: bytes, nonce: bytes, length: int) -> bytes:
    blocks = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        counter_bytes = counter.to_bytes(8, "big")
        blocks.append(hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(left_byte ^ right_byte for left_byte, right_byte in zip(left, right))


def sign_payload(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    return hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()


def encode_bytes(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def decode_field(payload: dict, field: str) -> bytes:
    try:
        return base64.b64decode(str(payload[field]).encode("ascii"))
    except Exception as exc:
        raise SecureConfigError("Configuracao criptografada invalida.") from exc
