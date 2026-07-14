#!/bin/bash
# LiteLLM Proxy starten auf janhet
# Port 4000 — nur localhost

set -e

CONFIG="/home/user/chief/la/docker/litellm_config_janhet.yaml"
LOG="/home/user/chief/litellm.log"

# Prüfen ob bereits läuft
if pgrep -f "litellm" > /dev/null; then
    echo "LiteLLM läuft bereits"
    exit 0
fi

echo "Starte LiteLLM auf Port 4000..."

nohup python3 -m litellm \
    --config "$CONFIG" \
    --host 127.0.0.1 \
    --port 4000 \
    > "$LOG" 2>&1 &

echo "LiteLLM PID: $!"
sleep 5
curl -s http://127.0.0.1:4000/health && echo "LiteLLM OK" || echo "LiteLLM noch nicht bereit"
