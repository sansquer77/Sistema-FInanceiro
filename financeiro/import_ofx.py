"""Parser de arquivos OFX/QFX para importação."""
from __future__ import annotations

import re
from datetime import datetime
from xml.etree import ElementTree

from financeiro.import_utils import ImportError, normalize_amount


HEADER_FIELDS = {
    "OFXHEADER",
    "DATA",
    "VERSION",
    "SECURITY",
    "ENCODING",
    "CHARSET",
    "COMPRESSION",
    "OLDFILEUID",
    "NEWFILEUID",
    "RESTRICTED",
    "APPLICATION",
    "SUBJECT",
    "MSGSET",
}


def parse_ofx_rows(file_bytes: bytes) -> list[dict]:
    # spec: importacao/importacao-dados v1.16 — critério 4
    header = file_bytes[:2048].decode("ascii", errors="ignore")
    charset_match = re.search(r"(?im)^\s*CHARSET\s*:\s*([^\s]+)", header)
    declared_charset = charset_match.group(1).upper() if charset_match else ""
    charset_aliases = {
        "1252": "cp1252",
        "WINDOWS-1252": "cp1252",
        "8859-1": "latin-1",
        "ISO-8859-1": "latin-1",
        "UTF-8": "utf-8-sig",
        "65001": "utf-8-sig",
        "USASCII": "ascii",
    }
    encodings = [charset_aliases[declared_charset]] if declared_charset in charset_aliases else []
    encodings.extend(["utf-8-sig", "cp1252"])
    payload = None
    for encoding in encodings:
        try:
            payload = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if payload is None:
        payload = file_bytes.decode("utf-8", errors="replace")
    headerless = payload
    if payload.lstrip().upper().startswith("OFXHEADER:"):
        lines = []
        for line in payload.splitlines():
            match = re.match(r"^\s*([\w]+)\s*:", line)
            field = match.group(1).upper() if match else ""
            if field in HEADER_FIELDS:
                continue
            lines.append(line)
        headerless = "\n".join(lines)
    if not headerless.strip():
        raise ImportError("Arquivo OFX vazio.")
    xml_payload = re.sub(
        r"&(?!#\d+;|#x[0-9a-f]+;|(?:amp|lt|gt|quot|apos);)",
        "&amp;",
        headerless,
        flags=re.IGNORECASE,
    )
    leaf_tag = re.compile(r"<([A-Za-z][\w:.-]*)>([^<]*)(?=<)")

    def close_ofx_leaf(match: re.Match[str]) -> str:
        tag_name = match.group(1)
        value = match.group(2)
        next_tag = xml_payload[match.end():]
        if not value.strip() or re.match(rf"</{re.escape(tag_name)}\s*>", next_tag, re.IGNORECASE):
            return match.group(0)
        return f"<{tag_name}>{value}</{tag_name}>"

    xml_payload = leaf_tag.sub(close_ofx_leaf, xml_payload)
    try:
        root = ElementTree.fromstring(xml_payload)
    except ElementTree.ParseError as exc:
        raise ImportError("Arquivo OFX invalido.") from exc
    transactions = []
    statement_nodes = [
        node for node in root.iter()
        if node.tag.rsplit("}", 1)[-1].upper() == "STMTTRN"
    ]
    for index, node in enumerate(statement_nodes, start=1):
        date_raw = first_ofx_value(node, "DTPOSTED", "DTUSER", "DATE", "DTSTART")
        amount_raw = first_ofx_value(node, "TRNAMT")
        if not date_raw or amount_raw is None:
            continue
        description = first_ofx_value(node, "NAME", "MEMO", "DESCR") or "Movimento OFX"
        category = "Outras Receitas" if normalize_amount(amount_raw) > 0 else "Outras Despesas"
        transactions.append({
            "row": index,
            "date": format_ofx_date(date_raw),
            "description": " ".join(description.split()),
            "category": category,
            "subcategory": "",
            "amount": str(normalize_amount(amount_raw)),
            "status": "Pago",
            "tag": "",
            "notes": first_ofx_value(node, "MEMO") or "",
        })
    if not transactions:
        raise ImportError("Nenhuma transacao valida encontrada no arquivo OFX.")
    return transactions


def first_ofx_value(node: ElementTree.Element, *names: str) -> str:
    for name in names:
        for child in node.iter():
            if child.tag.rsplit("}", 1)[-1].upper() == name.upper():
                value = (child.text or "").strip()
                if value:
                    return value
    return ""


def format_ofx_date(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ImportError("Data invalida.")
    cleaned = raw.upper().replace("[", "").replace("]", "")
    match = re.search(r"(\d{8})", cleaned)
    if not match:
        raise ImportError("Data invalida.")
    date_text = match.group(1)
    try:
        return datetime.strptime(date_text, "%Y%m%d").date().isoformat()
    except ValueError as exc:
        raise ImportError("Data invalida.") from exc
