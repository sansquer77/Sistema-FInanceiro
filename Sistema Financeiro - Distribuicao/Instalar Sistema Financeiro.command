#!/bin/zsh
set -e

PACKAGE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SOURCE_DIR="$PACKAGE_DIR/Aplicativo"
DEST_DIR="$HOME/Documents/Sistema Financeiro"
APP_SOURCE="$SOURCE_DIR/Sistema Financeiro.app"
APP_DEST="/Applications/Sistema Financeiro.app"

echo "Instalando Sistema Financeiro..."
echo ""

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Erro: pasta Aplicativo nao encontrada ao lado do instalador."
  exit 1
fi

mkdir -p "$DEST_DIR"

echo "Copiando arquivos do sistema para:"
echo "$DEST_DIR"

/usr/bin/rsync -a \
  --exclude 'data/' \
  --exclude '__pycache__/' \
  --exclude '.DS_Store' \
  --exclude 'launcher_distribuicao.c' \
  --exclude 'Sistema Financeiro.app/' \
  "$SOURCE_DIR/" "$DEST_DIR/"

echo ""
echo "Instalando icone em /Applications..."

copy_app() {
  if [ -d "$APP_DEST" ]; then
    rm -rf "$APP_DEST"
  fi
  cp -R "$APP_SOURCE" "$APP_DEST"
}

if ! copy_app 2>/tmp/sistema-financeiro-install-error.log; then
  echo "Permissao administrativa necessaria para instalar em /Applications."
  echo "O macOS pode solicitar a senha deste usuario."
  /usr/bin/osascript -e "do shell script \"rm -rf '/Applications/Sistema Financeiro.app' && cp -R '$APP_SOURCE' '/Applications/'\" with administrator privileges"
fi
xattr -dr com.apple.quarantine "$APP_DEST" 2>/dev/null || true

echo ""
echo "Instalacao concluida."
echo "Abra o app pela pasta Aplicativos: Sistema Financeiro."
echo ""
echo "O banco de dados sera criado vazio no primeiro uso em:"
echo "$DEST_DIR/data/finance.db"
echo ""
read "unused?Pressione Enter para finalizar."
