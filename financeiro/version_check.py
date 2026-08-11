from __future__ import annotations

import json
import os
import re
import ssl
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from financeiro.app_metadata import APP_VERSION

# spec: alerta-nova-versao v1.2 — regras de cache, timeout e fallback TLS
_LANDING_LATEST_VERSION_URL = os.environ.get(
    "SISTEMA_FINANCEIRO_LANDING_URL",
    "https://sistemafinanceiropage.vercel.app/api/latest-version",
)
_CACHE_TTL_SECONDS = 3600
_REQUEST_TIMEOUT_SECONDS = 5

_lock = threading.Lock()
_cache: dict[str, Any] = {
    "fetched_at": None,
    "data": None,
}


def _parse_version(version: str | None) -> tuple[int, int, int] | None:
    if not version:
        return None
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(version))
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _version_greater(left: str | None, right: str | None) -> bool:
    left_parsed = _parse_version(left)
    right_parsed = _parse_version(right)
    if not left_parsed or not right_parsed:
        return False
    return left_parsed > right_parsed


def _create_ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _fetch_latest_release() -> dict[str, Any] | None:
    try:
        context = _create_ssl_context()
        with urllib.request.urlopen(
            urllib.request.Request(
                _LANDING_LATEST_VERSION_URL,
                headers={"Accept": "application/json"},
            ),
            timeout=_REQUEST_TIMEOUT_SECONDS,
            context=context,
        ) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def latest_version_info() -> dict[str, Any]:
    """Retorna informações de versão local vs. publicada, com cache de 1h."""
    global _cache

    with _lock:
        now = datetime.now(timezone.utc)
        cached_at = _cache.get("fetched_at")
        if cached_at and (now - cached_at).total_seconds() < _CACHE_TTL_SECONDS:
            release = _cache["data"]
        else:
            release = _fetch_latest_release()
            _cache = {"fetched_at": now, "data": release}

    latest_version = release.get("version") if release else None
    download_url = release.get("download_url") if release else None
    release_url = release.get("release_url") if release else None

    return {
        "current_version": APP_VERSION,
        "latest_version": latest_version,
        "update_available": _version_greater(latest_version, APP_VERSION),
        "download_url": download_url or "https://github.com/sansquer77/Sistema-FInanceiro/releases",
        "release_url": release_url or "https://github.com/sansquer77/Sistema-FInanceiro/releases",
        "landing_url": "https://sistemafinanceiropage.vercel.app/#downloads",
    }
