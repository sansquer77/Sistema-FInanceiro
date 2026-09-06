#!/bin/bash
set -Eeuo pipefail

SOURCE="/mnt/endor/Sistema Financeiro"
TARGET="/opt/sistema-financeiro"
BACKUP="/mnt/endor/Sistema Financeiro_backup"
SERVICE="sistema-financeiro.service"
SERVICE_STOPPED=0

restart_on_error() {
  status=$?
  if [ "$status" -ne 0 ] && [ "$SERVICE_STOPPED" -eq 1 ]; then
    echo "A atualização falhou; tentando restabelecer o serviço." >&2
    systemctl start "$SERVICE" || true
  fi
  exit "$status"
}
trap restart_on_error EXIT

# Valida a origem, o destino e a ferramenta antes de interromper o serviço.
test -d "$TARGET"
test -d "$SOURCE"
test -f "$SOURCE/app.py"
test -d "$SOURCE/financeiro"
test -d "$SOURCE/web"
command -v rsync >/dev/null

systemctl status "$SERVICE" --no-pager || true
systemctl stop "$SERVICE"
SERVICE_STOPPED=1

# Mantém uma cópia operacional integral da versão anterior.
mkdir -p "$BACKUP"
rsync -a --delete "$TARGET/" "$BACKUP/"

test -d "$BACKUP"
test -f "$BACKUP/app.py"
test -d "$BACKUP/financeiro"
test -d "$BACKUP/web"

# spec: Update Server v1.3 — critério 4
# Atualiza apenas o código; dados, segredos e ambiente Python pertencem à instalação.
# Exclusões também ficam protegidas contra a remoção causada por --delete.
rsync -a --delete \
  --exclude 'data/' \
  --exclude 'secure/' \
  --exclude '.venv/' \
  --exclude '.git/' \
  --exclude '.gitignore' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'build/' \
  --exclude 'Sistema Financeiro - Distribuicao/' \
  --exclude 'launcher.applescript' \
  --exclude 'server.log' \
  "$SOURCE/" \
  "$TARGET/"

chown -R sistema:sistema "$TARGET"
systemctl start "$SERVICE"
systemctl is-active --quiet "$SERVICE"
SERVICE_STOPPED=0

trap - EXIT
echo "Atualização concluída; serviço ativo."
