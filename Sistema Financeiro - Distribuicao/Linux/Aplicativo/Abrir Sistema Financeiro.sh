#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export APP_HOST="${APP_HOST:-127.0.0.1}"
export APP_PORT="${APP_PORT:-8010}"
export APP_URL="${APP_URL:-http://127.0.0.1:${APP_PORT}}"

echo "Sistema Financeiro rodando em ${APP_URL}"
exec "$SCRIPT_DIR/SistemaFinanceiro/SistemaFinanceiro"
