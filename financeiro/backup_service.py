from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import zipfile
import base64
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from contextlib import closing
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.exceptions import InvalidTag

from financeiro import database
from financeiro.app_metadata import APP_VERSION
from financeiro.backup_settings import (
    backup_is_due,
    BackupSettingsError,
    get_backup_settings,
    load_remembered_password,
    record_backup_result,
    require_backup_manager,
    validate_backup_directory,
    validate_backup_password,
)
from financeiro.database_schema import SCHEMA_VERSION
from financeiro.secure_config import (
    CONFIG_KEY_ENV,
    SecureConfigError,
    config_key_path,
    decrypt_json_from_storage,
    load_or_create_key_material,
)

PACKAGE_FORMAT_VERSION = 1
PACKAGE_SUFFIX = ".sfbackup"
ENVELOPE_NAME = "envelope.json"
PAYLOAD_NAME = "payload.enc"
README_NAME = "LEIA-ME.txt"
SALT_BYTES = 16
NONCE_BYTES = 12
SCRYPT_N = 32768
SCRYPT_R = 8
SCRYPT_P = 1
KEY_BYTES = 32
CHUNK_BYTES = 1024 * 1024
MAX_PACKAGE_BYTES = 5 * 1024 * 1024 * 1024
MAX_INNER_FILES = 256
MAX_INNER_TOTAL_BYTES = 8 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
RESTORE_TOKEN_TTL = timedelta(minutes=10)
_BACKUP_LOCK = threading.Lock()
_RESTORE_LOCK = threading.Lock()
_RESTORE_TOKENS: dict[str, dict] = {}


class BackupError(RuntimeError):
    pass


def create_backup(
    password: str,
    *,
    now: datetime | None = None,
    destination_override: Path | None = None,
    record_status: bool = True,
) -> dict:
    validate_backup_password(str(password or ""))
    settings = get_backup_settings()
    if destination_override is None:
        if not settings["configured"]:
            raise BackupError("Configure o diretorio de backup antes de gerar o pacote.")
        destination = validate_backup_directory(settings["backup_directory"])
    else:
        destination_override.mkdir(parents=True, exist_ok=True)
        destination = validate_backup_directory(destination_override)
    if not _BACKUP_LOCK.acquire(blocking=False):
        raise BackupError("Ja existe um backup em andamento nesta instalacao.")

    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    filename = f"sistema-financeiro-{timestamp.strftime('%Y%m%d-%H%M%S-%f')}{PACKAGE_SUFFIX}"
    final_path = destination / filename
    temporary_package = destination / f".{filename}.tmp"
    work_root = database.DATA_DIR / ".backup-work"
    work_root.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(work_root, 0o700)
        with tempfile.TemporaryDirectory(prefix="create-", dir=work_root) as temp_name:
            temp_dir = Path(temp_name)
            database_copy = temp_dir / "finance.db"
            inner_zip = temp_dir / "payload.zip"
            encrypted_payload = temp_dir / PAYLOAD_NAME
            _online_database_copy(database_copy)
            integrity = _database_integrity(database_copy)
            if integrity != "ok":
                raise BackupError("A copia do banco nao passou na verificacao de integridade.")
            manifest = _build_inner_payload(inner_zip, database_copy, integrity, timestamp)
            envelope = _encrypt_payload(inner_zip, encrypted_payload, password)
            _write_outer_package(temporary_package, encrypted_payload, envelope)
            _validate_created_package(temporary_package, envelope, encrypted_payload.stat().st_size)
            os.replace(temporary_package, final_path)
            os.chmod(final_path, 0o600)
        if record_status:
            record_backup_result(success=True, filename=filename)
            apply_retention(destination, int(settings["retention_count"]), str(password))
        return {
            "status": "success",
            "package_filename": filename,
            "package_path": str(final_path),
            "created_at": timestamp.isoformat(),
            "schema_version": manifest["schema_version"],
            "files_count": len(manifest["files"]),
        }
    except (OSError, sqlite3.DatabaseError, zipfile.BadZipFile, BackupSettingsError, BackupError) as exc:
        try:
            temporary_package.unlink(missing_ok=True)
        except OSError:
            pass
        message = (
            str(exc)
            if isinstance(exc, BackupError)
            else "Nao foi possivel gerar o backup completo."
        )
        if record_status:
            record_backup_result(success=False, error=message)
        if isinstance(exc, BackupError):
            raise
        raise BackupError("Nao foi possivel gerar o backup completo.") from exc
    finally:
        _BACKUP_LOCK.release()


def _online_database_copy(destination: Path) -> None:
    # spec: backup-restauracao v1.0 — critérios 1 e 2
    with database.get_connection(database.DB_PATH) as source:
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target, pages=256, sleep=0.01)


def _database_integrity(path: Path) -> str:
    uri = path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        rows = [str(row[0]) for row in conn.execute("PRAGMA integrity_check")]
        foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if rows != ["ok"] or foreign_keys or version != SCHEMA_VERSION:
        return "failed"
    return "ok"


def _build_inner_payload(
    inner_zip: Path,
    database_copy: Path,
    integrity: str,
    timestamp: datetime,
) -> dict:
    key_material = load_or_create_key_material()
    files: list[dict] = []
    with zipfile.ZipFile(inner_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        _add_path(archive, database_copy, "data/finance.db", files)
        _add_bytes(archive, key_material, "secure/config.key.raw", files)
        for legacy_path in sorted(database.DATA_DIR.glob("*_config_user_*.enc")):
            if legacy_path.is_file():
                _add_path(archive, legacy_path, f"legacy/{legacy_path.name}", files)
        legacy_key = database.DATA_DIR / "email_config.key"
        if legacy_key.is_file():
            _add_path(archive, legacy_key, "legacy/email_config.key", files)
        manifest = {
            "format_version": PACKAGE_FORMAT_VERSION,
            "app_version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "created_at": timestamp.isoformat(),
            "integrity_check": integrity,
            "files": files,
        }
        manifest_bytes = _canonical_json(manifest)
        archive.writestr("manifest.json", manifest_bytes)
    return manifest


def _add_path(archive: zipfile.ZipFile, source: Path, name: str, files: list[dict]) -> None:
    content_hash = _sha256_path(source)
    size = source.stat().st_size
    archive.write(source, name)
    files.append({"path": name, "size": size, "sha256": content_hash})


def _add_bytes(archive: zipfile.ZipFile, content: bytes, name: str, files: list[dict]) -> None:
    archive.writestr(name, content)
    files.append({"path": name, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()})


def _encrypt_payload(source: Path, destination: Path, password: str) -> dict:
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    envelope = {
        "format_version": PACKAGE_FORMAT_VERSION,
        "cipher": "AES-256-GCM",
        "kdf": "scrypt",
        "scrypt": {"n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P, "length": KEY_BYTES},
        "salt": salt.hex(),
        "nonce": nonce.hex(),
        "payload_size": source.stat().st_size,
    }
    aad = _canonical_json(envelope)
    key = _derive_key(password, salt)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(aad)
    with source.open("rb") as reader, destination.open("wb") as writer:
        while chunk := reader.read(CHUNK_BYTES):
            writer.write(encryptor.update(chunk))
        writer.write(encryptor.finalize())
    envelope["tag"] = encryptor.tag.hex()
    return envelope


def _derive_key(password: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=KEY_BYTES, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P).derive(
        password.encode("utf-8")
    )


def _write_outer_package(path: Path, encrypted_payload: Path, envelope: dict) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(ENVELOPE_NAME, _canonical_json(envelope))
        archive.write(encrypted_payload, PAYLOAD_NAME)
        archive.writestr(
            README_NAME,
            "Backup criptografado do Sistema Financeiro. Restaure-o pelo proprio aplicativo.\n",
        )


def _validate_created_package(path: Path, envelope: dict, encrypted_size: int) -> None:
    with zipfile.ZipFile(path, "r") as archive:
        if set(archive.namelist()) != {ENVELOPE_NAME, PAYLOAD_NAME, README_NAME}:
            raise BackupError("O pacote gerado possui estrutura inesperada.")
        stored = json.loads(archive.read(ENVELOPE_NAME))
        payload_info = archive.getinfo(PAYLOAD_NAME)
    if stored != envelope or payload_info.file_size != encrypted_size:
        raise BackupError("O pacote gerado nao passou na validacao estrutural.")


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_restore_package(user_id: int, package_path: object, password: str) -> dict:
    require_backup_manager(user_id)
    validate_backup_password(str(password or ""))
    path = _validate_package_path(package_path)
    if not _RESTORE_LOCK.acquire(blocking=False):
        raise BackupError("Ja existe uma restauracao em andamento nesta instalacao.")
    _cleanup_restore_tokens()
    work_root = database.DATA_DIR / ".backup-work"
    work_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="restore-", dir=work_root))
    try:
        os.chmod(temp_dir, 0o700)
        envelope, encrypted_path = _read_outer_package(path, temp_dir)
        inner_zip = temp_dir / "payload.zip"
        _decrypt_payload(encrypted_path, inner_zip, str(password), envelope)
        manifest = _extract_and_validate_inner(inner_zip, temp_dir / "restored")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + RESTORE_TOKEN_TTL
        _RESTORE_TOKENS[token] = {
            "user_id": int(user_id),
            "temp_dir": temp_dir,
            "package_path": path,
            "manifest": manifest,
            "expires_at": expires_at,
        }
        return {
            "status": "valid",
            "confirmation_token": token,
            "expires_at": expires_at.isoformat(),
            "app_version": manifest["app_version"],
            "schema_version": manifest["schema_version"],
            "created_at": manifest["created_at"],
            "files_count": len(manifest["files"]),
        }
    except (
        OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile,
        InvalidTag, SecureConfigError, BackupError,
    ) as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if isinstance(exc, BackupError):
            raise
        raise BackupError("Senha incorreta ou pacote de backup invalido.") from exc
    finally:
        _RESTORE_LOCK.release()


def restore_validated_package(user_id: int, token: object, password: str) -> dict:
    require_backup_manager(user_id)
    validate_backup_password(str(password or ""))
    _cleanup_restore_tokens()
    token_text = str(token or "")
    record = _RESTORE_TOKENS.get(token_text)
    if not record or record["user_id"] != int(user_id):
        raise BackupError("A validacao da restauracao expirou. Valide o pacote novamente.")
    if not _RESTORE_LOCK.acquire(blocking=False):
        raise BackupError("Ja existe uma restauracao em andamento nesta instalacao.")
    try:
        # Reauthenticate the original package so a validation token alone never
        # authorizes a destructive operation.
        verification_dir = Path(record["temp_dir"]) / "confirmation"
        verification_dir.mkdir()
        envelope, encrypted = _read_outer_package(Path(record["package_path"]), verification_dir)
        verification_zip = verification_dir / "payload.zip"
        _decrypt_payload(encrypted, verification_zip, str(password), envelope)

        safety_dir = database.DATA_DIR.parent / "restore-safety"
        safety = create_backup(
            str(password), destination_override=safety_dir, record_status=False
        )
        restored_root = Path(record["temp_dir"]) / "restored"
        _promote_restored_environment(restored_root)
        _RESTORE_TOKENS.pop(token_text, None)
        shutil.rmtree(Path(record["temp_dir"]), ignore_errors=True)
        return {
            "status": "restored",
            "restart_required": True,
            "safety_backup_path": safety["package_path"],
        }
    except InvalidTag as exc:
        raise BackupError("Senha incorreta ou pacote de backup invalido.") from exc
    except (
        OSError,
        sqlite3.DatabaseError,
        zipfile.BadZipFile,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        raise BackupError("A restauracao falhou; o ambiente ativo foi preservado ou revertido.") from exc
    finally:
        _RESTORE_LOCK.release()


def _validate_package_path(value: object) -> Path:
    raw = str(value or "").strip()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute() or candidate.suffix != PACKAGE_SUFFIX:
        raise BackupError("Selecione um pacote .sfbackup por caminho absoluto.")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise BackupError("O pacote de backup nao foi encontrado.") from exc
    if not resolved.is_file() or resolved.stat().st_size > MAX_PACKAGE_BYTES:
        raise BackupError("O pacote de backup e invalido ou excede o limite permitido.")
    return resolved


def _read_outer_package(path: Path, temp_dir: Path) -> tuple[dict, Path]:
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        if len(infos) != 3 or {info.filename for info in infos} != {ENVELOPE_NAME, PAYLOAD_NAME, README_NAME}:
            raise BackupError("O pacote possui estrutura inesperada.")
        if any(info.file_size > MAX_PACKAGE_BYTES for info in infos):
            raise BackupError("O pacote excede o limite permitido.")
        by_name = {info.filename: info for info in infos}
        if by_name[ENVELOPE_NAME].file_size > 64 * 1024 or by_name[README_NAME].file_size > 64 * 1024:
            raise BackupError("Os metadados externos do pacote excedem o limite permitido.")
        if by_name[PAYLOAD_NAME].compress_type != zipfile.ZIP_STORED:
            raise BackupError("O payload externo deve estar armazenado sem compressao adicional.")
        envelope = json.loads(archive.read(ENVELOPE_NAME))
        encrypted_path = temp_dir / PAYLOAD_NAME
        with archive.open(PAYLOAD_NAME) as reader, encrypted_path.open("wb") as writer:
            shutil.copyfileobj(reader, writer, CHUNK_BYTES)
    _validate_envelope(envelope, encrypted_path.stat().st_size)
    return envelope, encrypted_path


def _validate_envelope(envelope: dict, encrypted_size: int) -> None:
    expected = {
        "format_version": PACKAGE_FORMAT_VERSION,
        "cipher": "AES-256-GCM",
        "kdf": "scrypt",
        "scrypt": {"n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P, "length": KEY_BYTES},
    }
    if any(envelope.get(key) != value for key, value in expected.items()):
        raise BackupError("O formato criptografico do pacote nao e compativel.")
    if int(envelope.get("payload_size", -1)) != encrypted_size:
        raise BackupError("O tamanho autenticado do payload diverge do pacote.")
    if len(bytes.fromhex(str(envelope.get("salt") or ""))) != SALT_BYTES:
        raise BackupError("O salt do pacote e invalido.")
    if len(bytes.fromhex(str(envelope.get("nonce") or ""))) != NONCE_BYTES:
        raise BackupError("O nonce do pacote e invalido.")
    if len(bytes.fromhex(str(envelope.get("tag") or ""))) != 16:
        raise BackupError("A tag do pacote e invalida.")


def _decrypt_payload(source: Path, destination: Path, password: str, envelope: dict) -> None:
    aad_envelope = {key: value for key, value in envelope.items() if key != "tag"}
    key = _derive_key(password, bytes.fromhex(envelope["salt"]))
    decryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(bytes.fromhex(envelope["nonce"]), bytes.fromhex(envelope["tag"])),
    ).decryptor()
    decryptor.authenticate_additional_data(_canonical_json(aad_envelope))
    with source.open("rb") as reader, destination.open("wb") as writer:
        while chunk := reader.read(CHUNK_BYTES):
            writer.write(decryptor.update(chunk))
        writer.write(decryptor.finalize())


def _extract_and_validate_inner(inner_zip: Path, destination: Path) -> dict:
    destination.mkdir(mode=0o700)
    with zipfile.ZipFile(inner_zip, "r") as archive:
        infos = archive.infolist()
        if len(infos) > MAX_INNER_FILES:
            raise BackupError("O backup contem arquivos demais.")
        if sum(info.file_size for info in infos) > MAX_INNER_TOTAL_BYTES:
            raise BackupError("O conteudo descompactado excede o limite permitido.")
        names = {info.filename for info in infos}
        if "manifest.json" not in names:
            raise BackupError("O manifesto protegido nao foi encontrado.")
        manifest_info = archive.getinfo("manifest.json")
        if manifest_info.file_size > MAX_MANIFEST_BYTES:
            raise BackupError("O manifesto protegido excede o limite permitido.")
        manifest = json.loads(archive.read("manifest.json"))
        expected_names = {str(item["path"]) for item in manifest.get("files", [])} | {"manifest.json"}
        if len(expected_names) != len(manifest.get("files", [])) + 1 or names != expected_names:
            raise BackupError("Os arquivos do pacote divergem do manifesto.")
        for info in infos:
            if info.filename == "manifest.json":
                continue
            target = destination / info.filename
            resolved = target.resolve()
            if not _is_inside(resolved, destination.resolve()) or info.is_dir():
                raise BackupError("O pacote contem um caminho de arquivo invalido.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as reader, target.open("wb") as writer:
                shutil.copyfileobj(reader, writer, CHUNK_BYTES)
    _validate_manifest(manifest, destination)
    return manifest


def _validate_manifest(manifest: dict, root: Path) -> None:
    if (
        manifest.get("format_version") != PACKAGE_FORMAT_VERSION
        or int(manifest.get("schema_version", -1)) != SCHEMA_VERSION
        or manifest.get("integrity_check") != "ok"
    ):
        raise BackupError("O manifesto nao e compativel com esta versao do aplicativo.")
    paths = {str(item.get("path")) for item in manifest.get("files", [])}
    if not {"data/finance.db", "secure/config.key.raw"}.issubset(paths):
        raise BackupError("O backup nao contem o banco e a chave obrigatorios.")
    for item in manifest["files"]:
        path = root / str(item["path"])
        if not path.is_file() or path.stat().st_size != int(item["size"]):
            raise BackupError("Um arquivo do backup diverge do manifesto.")
        if _sha256_path(path) != str(item["sha256"]):
            raise BackupError("A verificacao criptografica de um arquivo falhou.")
    if _database_integrity(root / "data/finance.db") != "ok":
        raise BackupError("O banco restaurado nao passou na verificacao de integridade.")
    _validate_restored_secure_configs(root)


def _validate_restored_secure_configs(root: Path) -> None:
    raw_key = (root / "secure/config.key.raw").read_bytes()
    if len(raw_key) != 32:
        raise BackupError("A chave mestra restaurada e invalida.")
    temp_key = root / "secure/config.key"
    temp_key.write_text(base64.b64encode(raw_key).decode("ascii"), encoding="ascii")
    with closing(sqlite3.connect(root / "data/finance.db")) as conn:
        payloads = [str(row[0]) for row in conn.execute("SELECT payload_enc FROM secure_configs")]
    for payload in payloads:
        decrypt_json_from_storage(payload, temp_key)


def _promote_restored_environment(root: Path) -> None:
    restored_db = root / "data/finance.db"
    restored_key_raw = (root / "secure/config.key.raw").read_bytes()
    env_key = os.environ.get(CONFIG_KEY_ENV)
    if env_key and env_key.encode("utf-8") != restored_key_raw:
        raise BackupError("A chave configurada pelo ambiente diverge da chave do backup.")

    with closing(sqlite3.connect(database.DB_PATH, timeout=5)) as conn:
        checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if checkpoint and int(checkpoint[0]) != 0:
            raise BackupError("O banco esta ocupado; tente restaurar quando nao houver outras operacoes.")
    active_db = database.DB_PATH
    previous_db = active_db.with_name(".finance-before-restore.db")
    active_key = config_key_path()
    previous_key = active_key.with_name(".config-before-restore.key")
    previous_db.unlink(missing_ok=True)
    previous_key.unlink(missing_ok=True)
    key_moved = False
    db_moved = False
    try:
        os.replace(active_db, previous_db)
        db_moved = True
        if not env_key and active_key.exists():
            os.replace(active_key, previous_key)
            key_moved = True
        os.replace(restored_db, active_db)
        if not env_key:
            active_key.parent.mkdir(parents=True, exist_ok=True)
            active_key.write_text(base64.b64encode(restored_key_raw).decode("ascii"), encoding="ascii")
            os.chmod(active_key, 0o600)
        if _database_integrity(active_db) != "ok":
            raise BackupError("O ambiente promovido nao passou na verificacao final.")
    except Exception:
        active_db.unlink(missing_ok=True)
        if db_moved and previous_db.exists():
            os.replace(previous_db, active_db)
        if not env_key:
            active_key.unlink(missing_ok=True)
            if key_moved and previous_key.exists():
                os.replace(previous_key, active_key)
        raise
    previous_db.unlink(missing_ok=True)
    previous_key.unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        Path(f"{active_db}{suffix}").unlink(missing_ok=True)
    for legacy in (root / "legacy").glob("*") if (root / "legacy").exists() else ():
        shutil.copy2(legacy, database.DATA_DIR / legacy.name)


def _cleanup_restore_tokens() -> None:
    now = datetime.now(timezone.utc)
    for token, record in list(_RESTORE_TOKENS.items()):
        if record["expires_at"] <= now:
            shutil.rmtree(Path(record["temp_dir"]), ignore_errors=True)
            _RESTORE_TOKENS.pop(token, None)


def apply_retention(directory: Path, retention_count: int, password: str) -> list[str]:
    """Remove only authenticated app backups beyond the configured retention."""
    valid: list[Path] = []
    for package in sorted(directory.glob(f"sistema-financeiro-*{PACKAGE_SUFFIX}"), reverse=True):
        if _package_is_valid(package, password):
            valid.append(package)
    removed: list[str] = []
    for package in valid[max(1, int(retention_count)):]:
        package.unlink()
        removed.append(package.name)
    return removed


def run_scheduled_backup_if_due() -> dict:
    if not backup_is_due():
        return {"status": "not_due"}
    password = load_remembered_password()
    if not password:
        record_backup_result(success=False, error="Senha lembrada indisponivel para o backup automatico.")
        return {"status": "failed"}
    try:
        return create_backup(password)
    except BackupError:
        return {"status": "failed"}


def _package_is_valid(path: Path, password: str) -> bool:
    work_root = database.DATA_DIR / ".backup-work"
    work_root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="retention-", dir=work_root) as temp_name:
            temp_dir = Path(temp_name)
            envelope, encrypted = _read_outer_package(path, temp_dir)
            inner = temp_dir / "payload.zip"
            _decrypt_payload(encrypted, inner, password, envelope)
            _extract_and_validate_inner(inner, temp_dir / "restored")
        return True
    except (BackupError, OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile, InvalidTag, SecureConfigError):
        return False


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
