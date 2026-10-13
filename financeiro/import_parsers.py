"""Parsers de formatos tabulares (XLS legado, XLSX e CSV) para importação."""
from __future__ import annotations

import csv
import re
import struct
import zipfile
from io import BytesIO, StringIO
from xml.etree import ElementTree

from financeiro.import_utils import (
    ImportError,
    excel_serial_to_date,
    get_cell,
    normalize_header,
    normalize_import_date,
    normalize_key,
    normalize_template_header,
)
from financeiro.xlsx_security import (
    XlsxSecurityError,
    normalize_xlsx_worksheet_target,
    read_xlsx_member,
    validate_xlsx_archive,
    validate_xlsx_file,
)


OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
MAX_XLSX_ROWS = 20_000
MAX_XLSX_CELLS = 250_000
MAX_XLSX_COLUMNS = 256
MAX_XLSX_SHARED_STRINGS = 100_000
END_OF_CHAIN = 0xFFFFFFFE
FREE_SECTOR = 0xFFFFFFFF
HEADER_ALIASES = {
    "data": "date",
    "descrição": "description",
    "descricao": "description",
    "categoria": "category",
    "subcategoria": "subcategory",
    "sub-categoria": "subcategory",
    "valor": "amount",
    "situação": "status",
    "situacao": "status",
    "tags": "tag",
    "tag": "tag",
    "informações adicionais": "notes",
    "informacoes adicionais": "notes",
}


def parse_xlsx_rows(file_bytes: bytes, sheet_name: str) -> list[list[str]]:
    # spec: importacao/importacao-dados v1.16 — limites de segurança do contêiner e da worksheet
    try:
        validate_xlsx_file(file_bytes)
        with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
            validate_xlsx_archive(archive)
            shared_strings = xlsx_shared_strings(archive)
            date_style_indexes = xlsx_date_style_indexes(archive)
            from datetime import date
            date_base = date(1904, 1, 1) if xlsx_uses_1904_date_system(archive) else date(1899, 12, 30)
            sheet_path = xlsx_sheet_path(archive, sheet_name)
            root = ElementTree.fromstring(read_xlsx_member(archive, sheet_path))
    except ImportError:
        raise
    except XlsxSecurityError as exc:
        raise ImportError(exc.message, exc.status) from exc
    except (KeyError, zipfile.BadZipFile, zipfile.LargeZipFile, ElementTree.ParseError,
            RuntimeError, NotImplementedError, OverflowError, ValueError) as exc:
        raise ImportError("Modelo XLSX invalido.") from exc
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    parsed_rows = []
    cell_count = 0
    for row_node in root.iterfind(".//main:sheetData/main:row", ns):
        if len(parsed_rows) >= MAX_XLSX_ROWS:
            raise xlsx_complexity_error()
        row_values = []
        for cell_node in row_node.iterfind("main:c", ns):
            cell_count += 1
            if cell_count > MAX_XLSX_CELLS:
                raise xlsx_complexity_error()
            cell_ref = cell_node.attrib.get("r", "")
            column = xlsx_column_index(cell_ref)
            if column > MAX_XLSX_COLUMNS:
                raise xlsx_complexity_error()
            while len(row_values) < column - 1:
                row_values.append("")
            row_values.append(xlsx_cell_text(cell_node, shared_strings, ns, date_style_indexes, date_base))
        parsed_rows.append(row_values)
    return parsed_rows


def xlsx_complexity_error() -> ImportError:
    from http import HTTPStatus
    return ImportError(
        "Modelo XLSX excede os limites seguros de importacao.",
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    )


def xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(read_xlsx_member(archive, "xl/sharedStrings.xml"))
    except KeyError:
        return []
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    strings = []
    for item in root.findall("main:si", ns):
        if len(strings) >= MAX_XLSX_SHARED_STRINGS:
            raise xlsx_complexity_error()
        text_parts = [node.text or "" for node in item.findall(".//main:t", ns)]
        strings.append("".join(text_parts))
    return strings


def xlsx_sheet_path(archive: zipfile.ZipFile, desired_name: str) -> str:
    workbook_root = ElementTree.fromstring(read_xlsx_member(archive, "xl/workbook.xml"))
    rels_root = ElementTree.fromstring(read_xlsx_member(archive, "xl/_rels/workbook.xml.rels"))
    main_ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
    relation_targets = {}
    for rel in rels_root.findall("rel:Relationship", rel_ns):
        if rel.attrib.get("TargetMode", "Internal") != "Internal":
            continue
        if not rel.attrib.get("Type", "").endswith("/worksheet"):
            continue
        relation_targets[rel.attrib["Id"]] = rel.attrib["Target"]
    desired_key = normalize_key(desired_name)
    first_relation_id = None
    for sheet in workbook_root.findall("main:sheets/main:sheet", main_ns):
        relation_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        first_relation_id = first_relation_id or relation_id
        if normalize_key(sheet.attrib.get("name")) == desired_key:
            return normalize_xlsx_worksheet_target(relation_targets[relation_id])
    if first_relation_id:
        return normalize_xlsx_worksheet_target(relation_targets[first_relation_id])
    raise ImportError("Aba de lancamentos nao encontrada no modelo.")


def xlsx_date_style_indexes(archive: zipfile.ZipFile) -> set[int]:
    try:
        root = ElementTree.fromstring(read_xlsx_member(archive, "xl/styles.xml"))
    except (KeyError, ElementTree.ParseError):
        return set()
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    date_num_fmt_ids = {
        14, 15, 16, 17, 22, 27, 30, 36, 45, 46, 47, 50, 57,
        165,
    }
    for num_fmt in root.findall("main:numFmts/main:numFmt", ns):
        try:
            num_fmt_id = int(num_fmt.attrib.get("numFmtId", "0"))
        except ValueError:
            continue
        format_code = normalize_key(num_fmt.attrib.get("formatCode", ""))
        if any(token in format_code for token in ("yyyy", "yy", "dd")) and "mm" in format_code:
            date_num_fmt_ids.add(num_fmt_id)
    date_style_indexes = set()
    for index, xf in enumerate(root.findall("main:cellXfs/main:xf", ns)):
        try:
            num_fmt_id = int(xf.attrib.get("numFmtId", "0"))
        except ValueError:
            continue
        if num_fmt_id in date_num_fmt_ids:
            date_style_indexes.add(index)
    return date_style_indexes


def xlsx_uses_1904_date_system(archive: zipfile.ZipFile) -> bool:
    try:
        root = ElementTree.fromstring(read_xlsx_member(archive, "xl/workbook.xml"))
    except (KeyError, ElementTree.ParseError):
        return False
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    workbook_pr = root.find("main:workbookPr", ns)
    return workbook_pr is not None and workbook_pr.attrib.get("date1904") in {"1", "true", "True"}


def xlsx_cell_text(cell_node, shared_strings: list[str], ns: dict[str, str], date_style_indexes: set[int], date_base) -> str:
    cell_type = cell_node.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell_node.findall(".//main:t", ns))
    value = cell_node.find("main:v", ns)
    if value is None or value.text is None:
        return ""
    if cell_type == "d":
        return normalize_import_date(value.text)
    if cell_type == "s":
        try:
            return shared_strings[int(value.text)]
        except (ValueError, IndexError):
            return ""
    if xlsx_cell_is_date(cell_node, date_style_indexes):
        parsed_date = excel_serial_to_date(value.text, date_base)
        if parsed_date:
            return parsed_date.isoformat()
    return value.text


def xlsx_cell_is_date(cell_node, date_style_indexes: set[int]) -> bool:
    try:
        style_index = int(cell_node.attrib.get("s", "-1"))
    except ValueError:
        return False
    return style_index in date_style_indexes


def xlsx_column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha()).upper()
    if not letters:
        return 1
    if len(letters) > 3:
        raise xlsx_complexity_error()
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return index


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


def decode_rk(raw: int) -> "Decimal":
    from decimal import Decimal
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


def rows_to_transactions(rows: list[list[object]]) -> list[dict]:
    if not rows:
        raise ImportError("Arquivo sem dados para importar.")
    header_index = find_header_index(rows)
    headers = [normalize_header(value) for value in rows[header_index]]
    positions = {HEADER_ALIASES[header]: index for index, header in enumerate(headers) if header in HEADER_ALIASES}
    required = {"date", "description", "category", "amount", "tag"}
    missing = sorted(required - positions.keys())
    if missing:
        raise ImportError("Arquivo fora do modelo esperado. Colunas obrigatorias ausentes: " + ", ".join(missing))
    transactions = []
    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(str(value or "").strip() for value in row):
            continue
        transactions.append({
            "row": row_number,
            "date": get_cell(row, positions["date"]),
            "description": get_cell(row, positions["description"]),
            "category": get_cell(row, positions["category"]),
            "subcategory": get_cell(row, positions.get("subcategory")),
            "amount": get_cell(row, positions["amount"]),
            "status": get_cell(row, positions.get("status")),
            "tag": get_cell(row, positions["tag"]),
            "notes": get_cell(row, positions.get("notes")),
        })
    return transactions


def find_header_index(rows: list[list[object]]) -> int:
    for index, row in enumerate(rows[:20]):
        normalized = {normalize_header(value) for value in row}
        if {"data", "valor"}.issubset(normalized) and ("descrição" in normalized or "descricao" in normalized):
            return index
    raise ImportError("Nao encontrei o cabecalho esperado no arquivo.")


def parse_system_template_file(file_bytes: bytes, filename: str) -> list[dict]:
    if not file_bytes:
        raise ImportError("Envie uma planilha modelo preenchida.")
    lower_filename = filename.lower()
    if lower_filename.endswith(".xlsx"):
        rows = parse_xlsx_rows(file_bytes, "Lançamentos")
    elif lower_filename.endswith(".csv"):
        rows = parse_csv_rows(file_bytes)
    else:
        raise ImportError("Envie o modelo em XLSX ou CSV UTF-8 separado por ponto e virgula.")
    if not rows:
        raise ImportError("Arquivo sem dados para importar.")
    headers = [normalize_template_header(value) for value in rows[0]]
    mapped_rows = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not any(str(value or "").strip() for value in row):
            continue
        if is_template_reference_section(row):
            break
        mapped_rows.append({
            "row": row_number,
            **{header: get_cell(row, index) for index, header in enumerate(headers) if header},
        })
    if not mapped_rows:
        raise ImportError("Nenhuma linha de lancamento encontrada no modelo.")
    return mapped_rows


def is_template_reference_section(row: list[object]) -> bool:
    first = normalize_key(get_cell(row, 0))
    return first in {"categorias_do_sistema", "tags_existentes"}
