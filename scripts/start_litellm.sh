#!/bin/bash
# start_litellm.sh — LiteLLM Proxy starten (Host)
# Konfiguration via config/host/litellm.env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Umgebungsvariablen laden
set -a
source "$PROJECT_ROOT/config/host/common.env"
source "$PROJECT_ROOT/config/host/litellm.env"
set +a

LOG="${LITELLM_LOG:-/tmp/logs/litellm.log}"
mkdir -p "$(dirname "$LOG")"

echo "Starte LiteLLM auf Port ${LITELLM_PORT:-4000}..."
litellm \
  --config "$PROJECT_ROOT/$LITELLM_CONFIG_PATH" \
  --host 127.0.0.1 \
  --port "${LITELLM_PORT:-4000}" \
  > "$LOG" 2>&1 &

sleep 3
if curl -s "http://127.0.0.1:${LITELLM_PORT:-4000}/health" \
  -H "Authorization: Bearer $LITELLM_KEY" > /dev/null 2>&1; then
  echo "LiteLLM OK"
else
  echo "LiteLLM Fehler — Log: $LOG"
fi
