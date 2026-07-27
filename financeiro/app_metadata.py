from __future__ import annotations

APP_NAME = "Sistema Financeiro"
APP_VERSION = "1.0.50"


def app_info() -> dict[str, str]:
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
    }
