#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export APP_URL="${APP_URL:-https://sistema-financeiro.net:8030}"

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$APP_URL" >/dev/null 2>&1 &
fi

echo "Abrindo Sistema Financeiro em ${APP_URL}"
