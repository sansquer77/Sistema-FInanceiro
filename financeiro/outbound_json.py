from __future__ import annotations

import json
from http.client import HTTPException
from typing import Any

KIB = 1024
MIB = 1024 * KIB

MAX_VERSION_JSON_BYTES = 256 * KIB
MAX_AI_JSON_BYTES = 1 * MIB
MAX_EXCHANGE_RATE_JSON_BYTES = 1 * MIB
MAX_QUOTE_JSON_BYTES = 4 * MIB


class OutboundJsonError(ValueError):
    """Resposta JSON externa invalida ou maior que o limite permitido."""


def read_limited_json(response: Any, *, max_bytes: int) -> Any:
    """Le JSON externo sem permitir que metadados remotos removam o limite."""
    if max_bytes <= 0:
        raise ValueError("max_bytes deve ser positivo")

    # spec: seguranca-transporte-externo v1.0 — critérios 2, 3, 4, 5 e 6
    declared_length = _content_length(response)
    if declared_length is not None and declared_length > max_bytes:
        raise OutboundJsonError("Resposta JSON externa excede o limite permitido.")

    try:
        body = response.read(max_bytes + 1)
    except (HTTPException, OSError, TypeError, ValueError) as exc:
        raise OutboundJsonError("Nao foi possivel ler a resposta JSON externa.") from exc
    if not isinstance(body, (bytes, bytearray)):
        raise OutboundJsonError("Resposta JSON externa deve ser binaria.")
    if len(body) > max_bytes:
        raise OutboundJsonError("Resposta JSON externa excede o limite permitido.")
    try:
        return json.loads(bytes(body).decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise OutboundJsonError("Resposta JSON externa invalida.") from exc


def _content_length(response: Any) -> int | None:
    headers = getattr(response, "headers", None)
    if headers is None or not hasattr(headers, "get"):
        return None
    raw = headers.get("Content-Length")
    if not isinstance(raw, (str, bytes, int)):
        return None
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None
