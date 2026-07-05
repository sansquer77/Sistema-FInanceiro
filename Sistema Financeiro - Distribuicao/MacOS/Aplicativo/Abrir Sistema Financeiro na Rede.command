#!/bin/zsh
set -e

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$APP_DIR"
APP_BIN="$PROJECT_DIR/SistemaFinanceiro/SistemaFinanceiro"
APP_PORT="${APP_PORT:-8010}"
DATA_DIR="$PROJECT_DIR/data"

detect_ip() {
  /usr/sbin/ipconfig getifaddr en0 2>/dev/null && return 0
  /usr/sbin/ipconfig getifaddr en1 2>/dev/null && return 0
  /sbin/ifconfig 2>/dev/null | /usr/bin/awk '/inet / && $2 !~ /^127\\./ && $2 !~ /^169\\.254\\./ { print $2; exit }'
}

LOCAL_IP="$(detect_ip)"
if [ -z "$LOCAL_IP" ]; then
  echo "Nao foi possivel detectar o IP da rede local."
  echo "Conecte o Mac a uma rede e tente novamente."
  read "unused?Pressione Enter para finalizar."
  exit 1
fi

APP_HOST="0.0.0.0"
APP_URL="http://$LOCAL_IP:$APP_PORT"
APP_ALLOWED_HOSTS="$LOCAL_IP,$LOCAL_IP:$APP_PORT"
APP_ALLOWED_ORIGINS="$APP_URL"

mkdir -p "$DATA_DIR"

is_available() {
  /usr/bin/curl -fsS --max-time 1 "$APP_URL" >/dev/null 2>&1
}

if ! is_available; then
  cd "$PROJECT_DIR"
  APP_HOST="$APP_HOST" \
  APP_PORT="$APP_PORT" \
  APP_URL="$APP_URL" \
  APP_ALLOWED_HOSTS="$APP_ALLOWED_HOSTS" \
  APP_ALLOWED_ORIGINS="$APP_ALLOWED_ORIGINS" \
  SISTEMA_FINANCEIRO_DATA_DIR="$DATA_DIR" \
  /usr/bin/nohup "$APP_BIN" >> "$DATA_DIR/server.log" 2>&1 </dev/null &

  i=0
  while [ "$i" -lt 40 ]; do
    if is_available; then
      break
    fi
    sleep 0.25
    i=$((i + 1))
  done
fi

echo "Sistema Financeiro disponivel na rede local:"
echo "$APP_URL"
/usr/bin/open "$APP_URL" >/dev/null 2>&1 &
read "unused?Pressione Enter para finalizar."
