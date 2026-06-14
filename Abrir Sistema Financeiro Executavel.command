#!/bin/sh

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_HOST="127.0.0.1"
APP_PORT="8010"
URL="http://sistema-financeiro.localhost:$APP_PORT"
LOG_FILE="$PROJECT_DIR/data/server.log"

mkdir -p "$PROJECT_DIR/data"

is_available() {
  /usr/bin/curl -fsS --max-time 1 "$URL" >/dev/null 2>&1
}

if ! is_available; then
  cd "$PROJECT_DIR" || exit 1
  APP_HOST="$APP_HOST" APP_PORT="$APP_PORT" APP_URL="$URL" /usr/bin/nohup /usr/bin/python3 "$PROJECT_DIR/app.py" >> "$LOG_FILE" 2>&1 </dev/null &

  i=0
  while [ "$i" -lt 40 ]; do
    if is_available; then
      break
    fi
    sleep 0.25
    i=$((i + 1))
  done
fi

/usr/bin/open "$URL" >/dev/null 2>&1 &
exit 0
