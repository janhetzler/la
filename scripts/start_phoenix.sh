#!/bin/bash
# Arize Phoenix Observability
# Empfängt LangChain Traces von allen Agent-Calls
# UI: http://127.0.0.1:6006 (nur via SSH-Tunnel erreichbar)

PHOENIX_DIR="/home/user/chief/phoenix_data"
LOG="/tmp/phoenix.log"

if pgrep -f "phoenix.server.main" > /dev/null 2>&1; then
    echo "Phoenix läuft bereits auf Port 6006"
    exit 0
fi

mkdir -p "$PHOENIX_DIR"
echo "Starte Arize Phoenix auf Port 6006..."

python3 -m phoenix.server.main serve \
  --host 127.0.0.1 \
  --port 6006 \
  >> "$LOG" 2>&1 &

echo "Phoenix PID: $!"
sleep 5

if curl -s http://127.0.0.1:6006/healthz > /dev/null 2>&1; then
    echo "Phoenix OK → http://127.0.0.1:6006"
    echo "Traces API: curl http://127.0.0.1:6006/v1/projects"
else
    echo "Phoenix noch nicht bereit — Log:"
    tail -5 "$LOG"
fi
