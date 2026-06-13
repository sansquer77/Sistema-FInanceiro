from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from financeiro.database import DATA_DIR

EMAIL_CONFIG_PATH = DATA_DIR / "email_config.enc"
EMAIL_CONFIG_KEY_PATH = DATA_DIR / "email_config.key"
CONFIG_KEY_ENV = "SISTEMA_FINANCEIRO_CONFIG_KEY"
KDF_ITERATIONS = 310_000


class SecureConfigError(Exception):
    pass


def load_encrypted_config(path: Path = EMAIL_CONFIG_PATH, key_path: Path = EMAIL_CONFIG_KEY_PATH) -> dict:
    if not path.exists():
        raise SecureConfigError("Configuracao de email criptografada nao encontrada.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    key_material = load_key_material(key_path)
    salt = decode_field(payload, "salt")
    nonce = decode_field(payload, "nonce")
    ciphertext = decode_field(payload, "ciphertext")
    expected_tag = decode_field(payload, "tag")
    iterations = int(payload.get("iterations") or KDF_ITERATIONS)
    encryption_key, signing_key = derive_keys(key_material, salt, iterations)
    actual_tag = sign_payload(signing_key, nonce, ciphertext)
    if not hmac.compare_digest(actual_tag, expected_tag):
        raise SecureConfigError("Configuracao de email invalida ou chave incorreta.")
    plain = xor_bytes(ciphertext, key_stream(encryption_key, nonce, len(ciphertext)))
    return json.loads(plain.decode("utf-8"))


def save_encrypted_config(config: dict, path: Path = EMAIL_CONFIG_PATH, key_path: Path = EMAIL_CONFIG_KEY_PATH) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    key_material = load_or_create_key_material(key_path)
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    encryption_key, signing_key = derive_keys(key_material, salt, KDF_ITERATIONS)
    plain = json.dumps(config, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ciphertext = xor_bytes(plain, key_stream(encryption_key, nonce, len(plain)))
    payload = {
        "version": 1,
        "kdf": "pbkdf2_hmac_sha256",
        "iterations": KDF_ITERATIONS,
        "salt": encode_bytes(salt),
        "nonce": encode_bytes(nonce),
        "ciphertext": encode_bytes(ciphertext),
        "tag": encode_bytes(sign_payload(signing_key, nonce, ciphertext)),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(path, 0o600)


def load_key_material(key_path: Path) -> bytes:
    env_value = os.environ.get(CONFIG_KEY_ENV)
    if env_value:
        return env_value.encode("utf-8")
    if not key_path.exists():
        raise SecureConfigError("Chave local da configuracao de email nao encontrada.")
    return base64.b64decode(key_path.read_text(encoding="utf-8").strip().encode("ascii"))


def load_or_create_key_material(key_path: Path) -> bytes:
    env_value = os.environ.get(CONFIG_KEY_ENV)
    if env_value:
        return env_value.encode("utf-8")
    if key_path.exists():
        return load_key_material(key_path)
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
        raise SecureConfigError("Configuracao de email criptografada invalida.") from exc
