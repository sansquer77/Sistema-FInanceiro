#!/bin/bash
set -Eeuo pipefail

SRC="/Users/sansquer/Documents/Sistema Financeiro"
DEST="/Volumes/Endor/Sistema Financeiro"
REMOTE="sansquer@192.168.1.212"
REMOTE_SCRIPT="/opt/scripts/atualiza-financeiro.sh"
UNICODE_FILES=("docs/distribuição.md")

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
  --exclude 'docs/distribuição.md' \
  --exclude 'Sistema Financeiro - Distribuicao/' \
  --exclude 'launcher.applescript' \
  --exclude 'server.log' \
  "$SRC/" "$DEST/"

# O openrsync do macOS não oferece --iconv. O volume Endor apresenta nomes
# Unicode em NFD, enquanto a homologação usa NFC; copie estes poucos caminhos
# fora do rsync para evitar exclusão/reenvio a cada deploy. Não usar `cp -p`:
# o volume não aceita o `chflags` acionado pela preservação de flags do macOS.
for relative_path in "${UNICODE_FILES[@]}"; do
  source_path="$SRC/$relative_path"
  destination_path="$DEST/$relative_path"
  if [ -f "$source_path" ]; then
    mkdir -p "$(dirname "$destination_path")"
    cp -f "$source_path" "$destination_path"
  elif [ -e "$destination_path" ]; then
    rm -f "$destination_path"
  fi
done

echo "Atualizando a produção e validando o serviço..."
ssh "$REMOTE" \
  "sudo '$REMOTE_SCRIPT'"

echo "Deploy concluído com sucesso; serviço ativo."
