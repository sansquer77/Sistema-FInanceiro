#!/bin/sh

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_HOST="127.0.0.1"
APP_PORT="8010"
URL="http://sistema-financeiro.localhost:$APP_PORT"
APP_ALLOWED_HOSTS=""
APP_ALLOWED_ORIGINS=""
EXPOSE_LAN="${EXPOSE_LAN:-0}"

# If EXPOSE_LAN is set to 1, try to detect local IP and expose on LAN
if [ "$EXPOSE_LAN" = "1" ] || [ "$EXPOSE_LAN" = "true" ]; then
  # try common interfaces
  LOCAL_IP=""
  for IF in en0 en1 en2 bridge0 awdl0; do
    if command -v ipconfig >/dev/null 2>&1; then
      IP=$(ipconfig getifaddr $IF 2>/dev/null || true)
    else
      IP=""
    fi
    if [ -n "$IP" ]; then
      LOCAL_IP="$IP"
      break
    fi
  done
  # fallback to python socket trick
  if [ -z "$LOCAL_IP" ] && command -v python3 >/dev/null 2>&1; then
    LOCAL_IP=$(python3 -c "import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
try:
    s.connect(('8.8.8.8',80)); print(s.getsockname()[0])
except:
    pass
s.close()" 2>/dev/null || true)
  fi
  if [ -n "$LOCAL_IP" ]; then
    APP_HOST="0.0.0.0"
    URL="http://$LOCAL_IP:$APP_PORT"
    # prefill allowed hosts/origins for backend
    APP_ALLOWED_HOSTS="$LOCAL_IP"
    APP_ALLOWED_ORIGINS="http://$LOCAL_IP:$APP_PORT"
  fi
fi
LOG_FILE="$PROJECT_DIR/data/server.log"

mkdir -p "$PROJECT_DIR/data"

is_available() {
  /usr/bin/curl -fsS --max-time 1 "$URL" >/dev/null 2>&1
}

kill_existing_server() {
  PIDS=$(/usr/sbin/lsof -ti :"$APP_PORT" 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "$PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    PIDS=$(/usr/sbin/lsof -ti :"$APP_PORT" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
      echo "$PIDS" | xargs kill -KILL 2>/dev/null || true
      sleep 0.5
    fi
  fi
}

kill_existing_server

if ! is_available; then
  cd "$PROJECT_DIR" || exit 1
  APP_HOST="$APP_HOST" APP_PORT="$APP_PORT" APP_URL="$URL" \
    APP_ALLOWED_HOSTS="$APP_ALLOWED_HOSTS" APP_ALLOWED_ORIGINS="$APP_ALLOWED_ORIGINS" \
    /usr/bin/nohup /usr/bin/python3 "$PROJECT_DIR/app.py" >> "$LOG_FILE" 2>&1 </dev/null &

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
