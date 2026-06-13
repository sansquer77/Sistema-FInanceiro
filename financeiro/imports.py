from __future__ import annotations

import csv
import struct
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus
from io import StringIO

from financeiro.categories import ClassificationError, get_or_create_category, get_or_create_tag, normalize_name
from financeiro.transactions import apply_balance_delta, balance_delta, get_active_account, normalize_tags, replace_transaction_tags
from financeiro.database import get_connection

OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
END_OF_CHAIN = 0xFFFFFFFE
FREE_SECTOR = 0xFFFFFFFF
HEADER_ALIASES = {
    "data": "date",
    "descrição": "description",
    "descricao": "description",
    "categoria": "category",
    "valor": "amount",
    "situação": "status",
    "situacao": "status",
    "tags": "tag",
    "tag": "tag",
    "informações adicionais": "notes",
    "informacoes adicionais": "notes",
}


class ImportError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def import_organizze_transactions(user_id: int, account_id: object, file_bytes: bytes, filename: str) -> dict:
    normalized_account_id = normalize_account_id(account_id)
    raw_rows = parse_organizze_file(file_bytes, filename)
    imported = []
    skipped = []
    with get_connection() as conn:
        get_active_account(conn, user_id, normalized_account_id)
        for raw in raw_rows:
            try:
                transaction = normalize_imported_transaction(raw)
            except ImportError as exc:
                skipped.append({"row": raw["row"], "description": raw.get("description", ""), "reason": exc.message})
                continue
            category_id = get_or_create_category(conn, user_id, transaction["category"])
            tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in transaction["tags"]]
            apply_balance_delta(
                conn,
                normalized_account_id,
                balance_delta(transaction["type"], transaction["amount_cents"], "source"),
            )
            cursor = conn.execute(
                """
                INSERT INTO transactions (
                    user_id, type, description, amount_cents, date, account_id,
                    category_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    transaction["type"],
                    transaction["description"],
                    transaction["amount_cents"],
                    transaction["date"],
                    normalized_account_id,
                    category_id,
                    transaction["notes"],
                ),
            )
            replace_transaction_tags(conn, cursor.lastrowid, tag_ids)
            imported.append({"row": raw["row"], "id": cursor.lastrowid, "description": transaction["description"]})
    return {
        "imported": len(imported),
        "skipped": len(skipped),
        "total_rows": len(raw_rows),
        "rows": imported,
        "errors": skipped[:50],
    }


def parse_organizze_file(file_bytes: bytes, filename: str) -> list[dict]:
    if not file_bytes:
        raise ImportError("Envie um arquivo para importar.")
    name = filename.lower()
    if name.endswith(".xls") or file_bytes.startswith(OLE_MAGIC):
        rows = parse_xls_rows(file_bytes)
    elif name.endswith(".csv"):
        rows = parse_csv_rows(file_bytes)
    else:
        raise ImportError("Formato nao suportado. Envie o arquivo .xls exportado pelo Organizze.")
    return rows_to_transactions(rows)


def rows_to_transactions(rows: list[list[object]]) -> list[dict]:
    if not rows:
        raise ImportError("Arquivo sem dados para importar.")
    header_index = find_header_index(rows)
    headers = [normalize_header(value) for value in rows[header_index]]
    positions = {HEADER_ALIASES[header]: index for index, header in enumerate(headers) if header in HEADER_ALIASES}
    required = {"date", "description", "category", "amount", "tag"}
    missing = sorted(required - positions.keys())
    if missing:
        raise ImportError("Arquivo fora do modelo Organizze. Colunas obrigatorias ausentes: " + ", ".join(missing))
    transactions = []
    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(str(value or "").strip() for value in row):
            continue
        transactions.append({
            "row": row_number,
            "date": get_cell(row, positions["date"]),
            "description": get_cell(row, positions["description"]),
            "category": get_cell(row, positions["category"]),
            "amount": get_cell(row, positions["amount"]),
            "status": get_cell(row, positions.get("status")),
            "tag": get_cell(row, positions["tag"]),
            "notes": get_cell(row, positions.get("notes")),
        })
    return transactions


def normalize_imported_transaction(row: dict) -> dict:
    status = str(row.get("status") or "").strip().lower()
    if status and status != "pago":
        raise ImportError("Lancamento ignorado porque a situacao nao esta como Pago.")
    amount = normalize_amount(row.get("amount"))
    if amount == 0:
        raise ImportError("Valor precisa ser diferente de zero.")
    description = " ".join(str(row.get("description") or "").strip().split())
    if not description:
        raise ImportError("Informe a descricao.")
    try:
        category = normalize_name(row.get("category"), "Informe a categoria.")
        tags = normalize_tags(row.get("tag"))
    except ClassificationError as exc:
        raise ImportError(exc.message) from exc
    except Exception as exc:
        message = getattr(exc, "message", "Informe ao menos uma tag.")
        raise ImportError(message) from exc
    notes = " ".join(str(row.get("notes") or "").strip().split()) or None
    return {
        "type": "income" if amount > 0 else "expense",
        "description": description,
        "amount_cents": money_decimal_to_cents(abs(amount)),
        "date": normalize_import_date(row.get("date")),
        "category": category,
        "tags": tags,
        "notes": notes,
    }


def normalize_account_id(value: object) -> int:
    try:
        account_id = int(str(value or "").strip())
    except ValueError as exc:
        raise ImportError("Informe a conta que recebera a importacao.") from exc
    if account_id <= 0:
        raise ImportError("Informe a conta que recebera a importacao.")
    return account_id


def normalize_import_date(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value or "").strip()
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    raise ImportError("Data invalida.")


def normalize_amount(value: object) -> Decimal:
    raw = str(value or "").strip()
    if isinstance(value, (int, float, Decimal)):
        raw = str(value)
    raw = raw.replace("R$", "").replace(" ", "")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ImportError("Valor invalido.") from exc


def money_decimal_to_cents(value: Decimal) -> int:
    return int((value * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def find_header_index(rows: list[list[object]]) -> int:
    for index, row in enumerate(rows[:20]):
        normalized = {normalize_header(value) for value in row}
        if {"data", "valor"}.issubset(normalized) and ("descrição" in normalized or "descricao" in normalized):
            return index
    raise ImportError("Nao encontrei o cabecalho do Organizze no arquivo.")


def normalize_header(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def get_cell(row: list[object], index: int | None) -> object:
    if index is None or index >= len(row):
        return ""
    return row[index]


def parse_csv_rows(file_bytes: bytes) -> list[list[object]]:
    text = file_bytes.decode("utf-8-sig")
    sample = text[:2048]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    return [row for row in csv.reader(StringIO(text), delimiter=delimiter)]


def parse_xls_rows(file_bytes: bytes) -> list[list[object]]:
    stream = read_ole_workbook_stream(file_bytes)
    shared_strings = []
    cells = {}
    in_sheet = False
    for record_type, payload in iter_biff_records(stream):
        if record_type == 0x0809 and len(payload) >= 4:
            in_sheet = struct.unpack_from("<H", payload, 2)[0] == 0x0010
        if record_type == 0x00FC:
            shared_strings = parse_shared_strings(payload)
        if not in_sheet:
            continue
        if record_type == 0x00FD:
            row, col, _, shared_index = struct.unpack_from("<HHHI", payload, 0)
            cells[(row, col)] = shared_strings[shared_index]
        elif record_type == 0x0204:
            row, col, _ = struct.unpack_from("<HHH", payload, 0)
            length = struct.unpack_from("<H", payload, 6)[0]
            cells[(row, col)] = payload[8 : 8 + length].decode("latin1", "replace")
        elif record_type == 0x0203:
            row, col, _ = struct.unpack_from("<HHH", payload, 0)
            cells[(row, col)] = struct.unpack_from("<d", payload, 6)[0]
        elif record_type == 0x027E:
            row, col, _, raw = struct.unpack_from("<HHHI", payload, 0)
            cells[(row, col)] = decode_rk(raw)
        elif record_type == 0x00BD:
            row, first_col, last_col = struct.unpack_from("<HHH", payload, 0)
            offset = 6
            for col in range(first_col, last_col + 1):
                _, raw = struct.unpack_from("<HI", payload, offset)
                cells[(row, col)] = decode_rk(raw)
                offset += 6
    if not cells:
        return []
    max_row = max(row for row, _ in cells)
    max_col = max(col for _, col in cells)
    return [[cells.get((row, col), "") for col in range(max_col + 1)] for row in range(max_row + 1)]


def read_ole_workbook_stream(file_bytes: bytes) -> bytes:
    if not file_bytes.startswith(OLE_MAGIC):
        raise ImportError("Arquivo .xls invalido.")
    sector_size = 1 << struct.unpack_from("<H", file_bytes, 30)[0]
    fat_sector_count = struct.unpack_from("<I", file_bytes, 44)[0]
    first_dir_sector = struct.unpack_from("<I", file_bytes, 48)[0]
    difat = [
        sector for sector in struct.unpack_from("<109I", file_bytes, 76)
        if sector not in (FREE_SECTOR, END_OF_CHAIN)
    ]
    fat = []
    for sector in difat[:fat_sector_count]:
        offset = sector_offset(sector, sector_size)
        fat.extend(struct.unpack_from(f"<{sector_size // 4}I", file_bytes, offset))
    directory = read_sector_chain(file_bytes, fat, first_dir_sector, sector_size)
    for offset in range(0, len(directory), 128):
        entry = directory[offset : offset + 128]
        if len(entry) < 128:
            continue
        name_length = struct.unpack_from("<H", entry, 64)[0]
        if name_length < 2:
            continue
        name = entry[: name_length - 2].decode("utf-16le", "ignore")
        if name in {"Workbook", "Book"}:
            start_sector = struct.unpack_from("<I", entry, 116)[0]
            size = struct.unpack_from("<Q", entry, 120)[0]
            return read_sector_chain(file_bytes, fat, start_sector, sector_size, size)
    raise ImportError("Nao encontrei a planilha principal dentro do arquivo .xls.")


def read_sector_chain(file_bytes: bytes, fat: list[int], start_sector: int, sector_size: int, size: int | None = None) -> bytes:
    chunks = []
    sector = start_sector
    seen = set()
    while sector not in (END_OF_CHAIN, FREE_SECTOR) and sector < len(fat) and sector not in seen:
        seen.add(sector)
        offset = sector_offset(sector, sector_size)
        chunks.append(file_bytes[offset : offset + sector_size])
        sector = fat[sector]
    data = b"".join(chunks)
    return data[:size] if size is not None else data


def sector_offset(sector: int, sector_size: int) -> int:
    return (sector + 1) * sector_size


def iter_biff_records(stream: bytes):
    position = 0
    while position + 4 <= len(stream):
        record_type, length = struct.unpack_from("<HH", stream, position)
        position += 4
        payload = stream[position : position + length]
        position += length
        yield record_type, payload


def parse_shared_strings(payload: bytes) -> list[str]:
    if len(payload) < 8:
        return []
    _, unique_count = struct.unpack_from("<II", payload, 0)
    position = 8
    values = []
    for _ in range(unique_count):
        value, position = parse_biff_string(payload, position)
        values.append(value)
    return values


def parse_biff_string(payload: bytes, position: int) -> tuple[str, int]:
    char_count = struct.unpack_from("<H", payload, position)[0]
    position += 2
    flags = payload[position]
    position += 1
    is_utf16 = bool(flags & 0x01)
    rich_runs = 0
    extension_size = 0
    if flags & 0x08:
        rich_runs = struct.unpack_from("<H", payload, position)[0]
        position += 2
    if flags & 0x04:
        extension_size = struct.unpack_from("<I", payload, position)[0]
        position += 4
    byte_count = char_count * (2 if is_utf16 else 1)
    raw = payload[position : position + byte_count]
    position += byte_count
    value = raw.decode("utf-16le" if is_utf16 else "latin1", "replace")
    position += rich_runs * 4 + extension_size
    return value, position


def decode_rk(raw: int) -> Decimal:
    divide_by_100 = bool(raw & 0x01)
    is_integer = bool(raw & 0x02)
    if is_integer:
        value = raw & 0xFFFFFFFC
        if value & 0x80000000:
            value -= 0x100000000
        decoded = Decimal(value >> 2)
    else:
        packed = struct.pack("<Q", (raw & 0xFFFFFFFC) << 32)
        decoded = Decimal(str(struct.unpack("<d", packed)[0]))
    return decoded / Decimal(100) if divide_by_100 else decoded
