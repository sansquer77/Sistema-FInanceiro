from __future__ import annotations

import struct
import zipfile
from http import HTTPStatus
from pathlib import PurePosixPath


MAX_XLSX_FILE_BYTES = 5 * 1024 * 1024
MAX_XLSX_ARCHIVE_MEMBERS = 128
MAX_XLSX_MEMBER_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
MAX_XLSX_TOTAL_UNCOMPRESSED_BYTES = 32 * 1024 * 1024
MAX_XLSX_COMPRESSION_RATIO = 100
SUPPORTED_XLSX_COMPRESSION_METHODS = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})
ZIP_END_OF_CENTRAL_DIRECTORY = b"PK\x05\x06"


class XlsxSecurityError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def validate_xlsx_file(file_bytes: bytes) -> None:
    if len(file_bytes) > MAX_XLSX_FILE_BYTES:
        raise XlsxSecurityError(
            "Modelo XLSX muito grande. Envie um arquivo de ate 5 MB.",
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        )
    validate_xlsx_entry_count(file_bytes)


def validate_xlsx_archive(archive: zipfile.ZipFile) -> None:
    members = archive.infolist()
    if len(members) > MAX_XLSX_ARCHIVE_MEMBERS:
        raise xlsx_complexity_error()
    total_uncompressed = 0
    member_names = set()
    for member in members:
        validate_xlsx_member_name(member.filename)
        if member.filename in member_names:
            raise XlsxSecurityError("Modelo XLSX invalido: membro duplicado.")
        member_names.add(member.filename)
        if member.flag_bits & 0x1:
            raise XlsxSecurityError("Modelo XLSX invalido: membros criptografados nao sao aceitos.")
        if member.compress_type not in SUPPORTED_XLSX_COMPRESSION_METHODS:
            raise XlsxSecurityError("Modelo XLSX invalido: metodo de compressao nao suportado.")
        if member.file_size < 0 or member.compress_size < 0:
            raise XlsxSecurityError("Modelo XLSX invalido.")
        if member.file_size > MAX_XLSX_MEMBER_UNCOMPRESSED_BYTES:
            raise xlsx_complexity_error()
        total_uncompressed += member.file_size
        if total_uncompressed > MAX_XLSX_TOTAL_UNCOMPRESSED_BYTES:
            raise xlsx_complexity_error()
        if member.file_size > 1024:
            if member.compress_size == 0 or member.file_size / member.compress_size > MAX_XLSX_COMPRESSION_RATIO:
                raise xlsx_complexity_error()


def validate_xlsx_entry_count(file_bytes: bytes) -> None:
    # Validar o EOCD antes de ZipFile evita materializar milhares de ZipInfo
    # controlados pelo upload apenas para descobrir o excesso depois.
    search_start = max(0, len(file_bytes) - 65_557)
    cursor = len(file_bytes)
    while cursor > search_start:
        offset = file_bytes.rfind(ZIP_END_OF_CENTRAL_DIRECTORY, search_start, cursor)
        if offset < 0:
            return
        if offset + 22 <= len(file_bytes):
            disk_number, directory_disk, entries_on_disk, entries_total = struct.unpack_from("<4H", file_bytes, offset + 4)
            comment_length = struct.unpack_from("<H", file_bytes, offset + 20)[0]
            if offset + 22 + comment_length == len(file_bytes):
                if disk_number != 0 or directory_disk != 0 or entries_on_disk != entries_total:
                    raise XlsxSecurityError("Modelo XLSX invalido: pacotes multidisco nao sao aceitos.")
                if entries_total == 0xFFFF or entries_total > MAX_XLSX_ARCHIVE_MEMBERS:
                    raise xlsx_complexity_error()
                return
        cursor = offset


def validate_xlsx_member_name(name: str) -> None:
    if not name or "\x00" in name or "\\" in name:
        raise XlsxSecurityError("Modelo XLSX invalido: caminho interno inseguro.")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise XlsxSecurityError("Modelo XLSX invalido: caminho interno inseguro.")


def read_xlsx_member(archive: zipfile.ZipFile, name: str) -> bytes:
    info = archive.getinfo(name)
    if info.file_size > MAX_XLSX_MEMBER_UNCOMPRESSED_BYTES:
        raise xlsx_complexity_error()
    with archive.open(info, "r") as source:
        content = source.read(MAX_XLSX_MEMBER_UNCOMPRESSED_BYTES + 1)
    if len(content) > MAX_XLSX_MEMBER_UNCOMPRESSED_BYTES or len(content) != info.file_size:
        raise xlsx_complexity_error()
    return content


def normalize_xlsx_worksheet_target(target: str) -> str:
    if not target or "\x00" in target or "\\" in target:
        raise XlsxSecurityError("Modelo XLSX invalido: caminho interno inseguro.")
    normalized = target.lstrip("/")
    if not normalized.startswith("xl/"):
        normalized = f"xl/{normalized}"
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise XlsxSecurityError("Modelo XLSX invalido: caminho interno inseguro.")
    if len(path.parts) < 3 or path.parts[:2] != ("xl", "worksheets") or path.suffix.lower() != ".xml":
        raise XlsxSecurityError("Modelo XLSX invalido: aba fora do pacote esperado.")
    return path.as_posix()


def xlsx_complexity_error() -> XlsxSecurityError:
    return XlsxSecurityError(
        "Modelo XLSX excede os limites seguros de importacao.",
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    )
