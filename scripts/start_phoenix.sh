#!/bin/bash
# Arize Phoenix starten auf janhet
# Port 6006 — nur localhost, kein externer Zugang

set -e

PHOENIX_PORT=6006
PHOENIX_DIR="/home/user/chief/phoenix_data"
LOG="/home/user/chief/phoenix.log"

mkdir -p "$PHOENIX_DIR"

# Prüfen ob bereits läuft
if pgrep -f "phoenix serve" > /dev/null; then
    echo "Phoenix läuft bereits"
    exit 0
fi

echo "Starte Arize Phoenix auf Port $PHOENIX_PORT..."

nohup python3 -m phoenix.server.main serve \
    --host 127.0.0.1 \
    --port $PHOENIX_PORT \
    --storage-dir "$PHOENIX_DIR" \
    > "$LOG" 2>&1 &

echo "Phoenix PID: $!"
sleep 3
curl -s http://127.0.0.1:$PHOENIX_PORT/healthz && echo "Phoenix OK" || echo "Phoenix noch nicht bereit"
