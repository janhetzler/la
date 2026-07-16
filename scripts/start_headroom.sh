#!/bin/bash
# DISABLED — Headroom Proxy
# 
# Headroom benötigt "headroom-ai[all]" (~500 MB + ONNX Runtime + HuggingFace Modell).
# Zu groß für die Sandbox und janhet Erstinstallation.
#
# Reaktivierung:
#   pip install "headroom-ai[all]==0.31.0"
#   Dann in litellm_config_janhet.yaml:
#     api_base: http://127.0.0.1:8787/v1  (statt 8080)
#   Dann:
#   HEADROOM_TELEMETRY=off \
#   OPENAI_TARGET_API_URL=http://127.0.0.1:8080/v1 \
#   headroom proxy --host 127.0.0.1 --port 8787 --no-telemetry
#
echo "Headroom ist disabled — siehe Kommentar in dieser Datei für Reaktivierung"
