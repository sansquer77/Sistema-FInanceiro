#!/bin/bash
set -Eeuo pipefail

SRC="/Users/sansquer/Documents/Sistema Financeiro"
DEST="/Volumes/Endor/Sistema Financeiro"
REMOTE="sansquer@192.168.1.212"
REMOTE_SCRIPT="/opt/scripts/atualiza-financeiro.sh"

echo "Verificando a homologação e o volume do servidor..."
test -f "$SRC/app.py"
test -d "$SRC/financeiro"
test -d "$SRC/web"
test -d "/Volumes/Endor"
mkdir -p "$DEST"

echo "Sincronizando a homologação validada com o staging Endor..."
rsync -avh --progress --delete \
  --exclude '.git/' \
  --exclude '.gitignore' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  --exclude '.pytest_cache/' \
  --exclude 'build/' \
  --exclude 'data/' \
  --exclude 'secure/' \
  --exclude 'Sistema Financeiro - Distribuicao/' \
  --exclude 'launcher.applescript' \
  --exclude 'server.log' \
  "$SRC/" "$DEST/"

echo "Atualizando a produção e validando o serviço..."
ssh "$REMOTE" \
  "sudo '$REMOTE_SCRIPT'"

echo "Deploy concluído com sucesso; serviço ativo."
