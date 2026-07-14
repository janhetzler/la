#!/bin/bash
# Headroom Context Compression Proxy
# Sitzt zwischen LiteLLM (Port 4000) und llama-server (Port 8080)
# Komprimiert RAG-Outputs, Tool-Antworten und lange Kontexte

LOG="/tmp/headroom.log"

# Prüfen ob bereits läuft
if pgrep -f "headroom proxy" > /dev/null 2>&1; then
    echo "Headroom läuft bereits auf Port 8787"
    exit 0
fi

echo "Starte Headroom Proxy auf Port 8787..."

HEADROOM_TELEMETRY=off \
OPENAI_TARGET_API_URL=http://127.0.0.1:8080/v1 \
headroom proxy \
  --host 127.0.0.1 \
  --port 8787 \
  --no-telemetry \
  >> "$LOG" 2>&1 &

echo "Headroom PID: $!"
sleep 3

# Health Check
if curl -s http://127.0.0.1:8787/health > /dev/null 2>&1; then
    echo "Headroom OK → http://127.0.0.1:8787"
    echo "Stats: curl http://127.0.0.1:8787/stats"
else
    echo "Headroom noch nicht bereit — Log:"
    tail -5 "$LOG"
fi
