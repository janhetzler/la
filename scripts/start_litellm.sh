#!/bin/bash
# LiteLLM API-Gateway
# Routet auf Headroom :8787 → llama-server :8080
# Phoenix Callbacks für Observability aktiv

CONFIG="/home/user/chief/la/docker/litellm_config_janhet.yaml"
LOG="/tmp/litellm.log"

if pgrep -f "litellm" > /dev/null 2>&1; then
    echo "LiteLLM läuft bereits auf Port 4000"
    exit 0
fi

# Config-Pfad anpassen falls abweichend
if [ ! -f "$CONFIG" ]; then
    CONFIG="$(dirname "$0")/../docker/litellm_config_janhet.yaml"
fi

echo "Starte LiteLLM auf Port 4000..."

litellm \
  --config "$CONFIG" \
  --host 127.0.0.1 \
  --port 4000 \
  >> "$LOG" 2>&1 &

echo "LiteLLM PID: $!"
sleep 8

if curl -s http://127.0.0.1:4000/health \
    -H "Authorization: Bearer sk-cos-local-dev" > /dev/null 2>&1; then
    echo "LiteLLM OK → http://127.0.0.1:4000"
    echo "Modelle: curl http://127.0.0.1:4000/v1/models -H 'Authorization: Bearer sk-cos-local-dev'"
else
    echo "LiteLLM noch nicht bereit — Log:"
    tail -10 "$LOG"
fi
