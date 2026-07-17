#!/bin/bash
# start_phoenix.sh — Arize Phoenix starten (Host)
# Konfiguration via config/host/phoenix.env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Umgebungsvariablen laden
set -a
source "$PROJECT_ROOT/config/host/common.env"
source "$PROJECT_ROOT/config/host/phoenix.env"
set +a

LOG="${PHOENIX_LOG:-/tmp/logs/phoenix.log}"
mkdir -p "$(dirname "$LOG")"
mkdir -p "${PHOENIX_DATA_PATH:-/tmp/phoenix}"

echo "Starte Phoenix auf Port ${PHOENIX_PORT:-6006}..."
python3 -m phoenix.server.main serve \
  --host 127.0.0.1 \
  --port "${PHOENIX_PORT:-6006}" \
  > "$LOG" 2>&1 &

sleep 3
if curl -s "http://127.0.0.1:${PHOENIX_PORT:-6006}/healthz" > /dev/null 2>&1; then
  echo "Phoenix OK"
else
  echo "Phoenix Fehler — Log: $LOG"
fi
