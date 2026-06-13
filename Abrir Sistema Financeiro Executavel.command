#!/bin/sh

PROJECT_DIR="/Users/sansquer/Documents/Sistema Financeiro"
URL="http://localhost:8000"
LOG_FILE="$PROJECT_DIR/data/server.log"

mkdir -p "$PROJECT_DIR/data"

is_available() {
  /usr/bin/curl -fsS --max-time 1 "$URL" >/dev/null 2>&1
}

if ! is_available; then
  cd "$PROJECT_DIR" || exit 1
  /usr/bin/python3 "$PROJECT_DIR/app.py" >> "$LOG_FILE" 2>&1 </dev/null &

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
