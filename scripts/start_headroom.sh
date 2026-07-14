#!/bin/bash
# Headroom Proxy als Kompressionsschicht vor llama-server
HEADROOM_TELEMETRY=off \
OPENAI_TARGET_API_URL=http://127.0.0.1:8080/v1 \
headroom proxy \
  --host 127.0.0.1 \
  --port 8787 \
  --no-telemetry \
  >> /tmp/headroom.log 2>&1 &
echo "Headroom PID: $!"
