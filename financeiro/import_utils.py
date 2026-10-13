"""Utilitários compartilhados entre parsers e orquestração de importação."""
from __future__ import annotations

import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus

from financeiro.identifiers import positive_int_id
from financeiro.money import decimal_to_cents


class ImportError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def normalize_key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join("".join(char if char.isalnum() else " " for char in text).split())


def normalize_header(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def normalize_template_header(value: object) -> str:
    return normalize_key(value).replace(" ", "_").replace("-", "_")


def get_cell(row: list[object], index: int | None) -> object:
    if index is None or index >= len(row):
        return ""
    return row[index]


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
    return decimal_to_cents(value)


def normalize_import_date(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value or "").strip()
    serial_date = excel_serial_to_date(raw)
    if serial_date and 2000 <= serial_date.year <= 2100:
        return serial_date.isoformat()
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    raise ImportError("Data invalida.")


def excel_serial_to_date(value: object, date_base: date = date(1899, 12, 30)) -> date | None:
    try:
        serial = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    if serial < 1:
        return None
    return date_base + timedelta(days=int(serial))


def normalize_import_money_for_form(value: object) -> str:
    return f"{normalize_amount(value):.2f}".replace(".", ",")


def normalize_optional_import_money_for_form(value: object) -> str:
    if str(value or "").strip() == "":
        return ""
    return normalize_import_money_for_form(value)


def normalize_import_flag(value: object) -> bool:
    raw = str(value or "").strip().lower()
    return raw in {"1", "true", "yes", "sim", "s", "on", "verdadeiro"}


def normalize_import_target(value: object) -> str:
    target = normalize_key(value)
    if target in {"card", "cartao", "cartoes", "credit_card"}:
        return "card"
    return "account"


def normalize_import_month(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return raw
    if len(raw) == 7 and raw[4] == "-":
        return raw
    normalized_date = normalize_import_date(raw)
    if len(normalized_date) >= 7 and normalized_date[4] == "-":
        return normalized_date[:7]
    return raw


def normalize_account_id(value: object) -> int:
    try:
        return positive_int_id(value)
    except ValueError as exc:
        raise ImportError("Informe a conta que recebera a importacao.") from exc
