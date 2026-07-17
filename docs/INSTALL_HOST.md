# Installation Guide — Host

Schritt-für-Schritt Anleitung für die Installation von Local Agent (LA)
auf dem Host (AMD EPYC, 4 vCores, 10 GB RAM, Debian 12).
Funktioniert auf jedem ähnlichen Linux-Server ohne GPU.

---

## Voraussetzungen

| Komponente | Minimum | Empfohlen |
|-----------|---------|-----------| 
| RAM | 8 GB | 10 GB |
| CPU | 2 Kerne | 4 Kerne (AVX2) |
| Disk | 10 GB frei | 20 GB frei |
| OS | Debian 11 | Debian 12 |
| Python | 3.10 | 3.11–3.12 |

---

## Schritt 1 — llama-server installieren

llama-server ist die Inferenz-Engine. Wir nutzen das offizielle
vorgebaute Binary für Ubuntu/Debian x64.

```bash
# Verzeichnis anlegen
mkdir -p /home/user/llamaserver

# Aktuelles Release herunterladen (b9977 oder neuer)
cd /home/user/llamaserver
wget https://github.com/ggml-org/llama.cpp/releases/download/b9977/llama-b9977-bin-ubuntu-x64.zip
unzip llama-b9977-bin-ubuntu-x64.zip -d llama-b9977
chmod +x llama-b9977/llama-server

# Version prüfen
./llama-b9977/llama-server --version
```

---

## Schritt 2 — Modelle herunterladen

```bash
mkdir -p /home/user/models

# Hauptmodell: Granite 4.0-H-Tiny (Reasoning + Tool-Calling)
wget https://huggingface.co/ibm-granite/granite-4.0-h-tiny-GGUF/resolve/main/granite-4.0-h-tiny.i1-IQ4_XS.gguf \
  -O /home/user/models/granite-4.0-h-tiny.i1-IQ4_XS.gguf

# Embedding Modell: Granite Embedding 30m
wget https://huggingface.co/ibm-granite/granite-embedding-30m-english-GGUF/resolve/main/granite-embedding-30m-english-Q8_0.gguf \
  -O /home/user/models/granite-embedding-30m-Q8_0.gguf

# Größen prüfen
ls -lh /home/user/models/
```

---

## Schritt 3 — llama-server konfigurieren und starten

```bash
# Config für Reasoning-Modell (Port 8080)
cat << 'CFGEOF' > /home/user/models/config/granite-server-params.txt
-c 16384
-t 4
--threads-batch 4
--parallel 1
-ctk q4_0
-ctv q4_0
--no-mmap
--jinja
--repeat-penalty 1.15
--temp 0.1
--top-p 0.95
--top-k 20
-n 2048
--port 8080
CFGEOF

# Start-Script für Reasoning (Port 8080)
cat << 'SEOF' > /home/user/restart_llama.sh
#!/bin/bash
pkill -f "llama-server.*8080" || true
sleep 2
xargs -a /home/user/models/config/granite-server-params.txt \
  /home/user/llamaserver/llama-b9977/llama-server \
  -m /home/user/models/granite-4.0-h-tiny.i1-IQ4_XS.gguf \
  > /home/user/llama-granite.log 2>&1 &
sleep 5
tail -5 /home/user/llama-granite.log
SEOF
chmod +x /home/user/restart_llama.sh

# Start-Script für Embedding (Port 8081)
cat << 'EEOF' > /home/user/restart_embedding.sh
#!/bin/bash
pkill -f "llama-server.*8081" || true
sleep 2
/home/user/llamaserver/llama-b9977/llama-server \
  -m /home/user/models/granite-embedding-30m-Q8_0.gguf \
  --host 127.0.0.1 \
  --port 8081 \
  --embeddings \
  --no-mmap \
  > /home/user/llama-embedding.log 2>&1 &
sleep 3
tail -3 /home/user/llama-embedding.log
EEOF
chmod +x /home/user/restart_embedding.sh

# Beide starten
bash /home/user/restart_llama.sh
bash /home/user/restart_embedding.sh

# Testen
curl -s http://127.0.0.1:8080/health && echo "Reasoning OK"
curl -s http://127.0.0.1:8081/health && echo "Embedding OK"
```

---

## Schritt 4 — Python Umgebung

```bash
# Arbeitsverzeichnis
mkdir -p /home/user/la
cd /home/user/la

# Repository klonen
git clone https://github.com/janhetzler/la .

# Virtuelle Umgebung (ohne torch!)
python3 -m venv /home/user/venv
source /home/user/venv/bin/activate

# Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt

# Testen
python3 -c "import langchain, chromadb, litellm; print('OK')"
```

---

## Schritt 5 — Arize Phoenix

Phoenix sammelt Traces von allen Agent-Calls für Observability.

```bash
source /home/user/venv/bin/activate
bash /home/user/la/scripts/start_phoenix.sh

# Testen
curl -s http://127.0.0.1:6006/healthz
```

---

## Schritt 6 — LiteLLM Proxy

LiteLLM ist das zentrale API-Gateway. Routet direkt auf llama-server.

```bash
source /home/user/venv/bin/activate
bash /home/user/la/scripts/start_litellm.sh

# Testen
curl -s http://127.0.0.1:4000/health \
  -H "Authorization: Bearer sk-cos-local-dev"

# Modelle prüfen
curl -s http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer sk-cos-local-dev" | python3 -m json.tool
```

---

## Schritt 7 — Agent Server

```bash
source /home/user/venv/bin/activate
cd /home/user/la/agents/server

export LITELLM_URL=http://127.0.0.1:4000
export LITELLM_KEY=sk-cos-local-dev
export OPENAI_API_KEY=sk-cos-local-dev
export CHROMA_PATH=/home/user/chroma
export PHOENIX_HOST=http://127.0.0.1:6006

uvicorn server:app --host 127.0.0.1 --port 8002 &

# Testen
curl -s http://127.0.0.1:8002/health
curl -s http://127.0.0.1:8002/v1/models | python3 -m json.tool
```

---

## Schritt 8 — Terminal Chat testen

```bash
source /home/user/venv/bin/activate
python3 /home/user/la/scripts/chat.py
```

---

## Schritt 9 — Test Suite ausführen

```bash
source /home/user/venv/bin/activate
MODEL_PATH=/home/user/models/granite-4.0-h-tiny.i1-IQ4_XS.gguf \
CHROMA_PATH=/home/user/chroma \
python3 /home/user/la/tests/run_tests.py
```

---

## Schritt 10 — systemd Services (Dauerbetrieb)

```bash
# Templates aus deploy/systemd/ befüllen und installieren
# Siehe deploy/systemd/README.md für Platzhalter-Übersicht
sudo cp /home/user/la/deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Aktivieren und starten
sudo systemctl enable --now phoenix litellm agent

# Status prüfen
sudo systemctl status phoenix litellm agent
```

---

## Port-Übersicht

| Port | Dienst | Zweck |
|------|--------|-------|
| 8080 | llama-server | Granite Reasoning |
| 8081 | llama-server | Granite Embedding |
| 6006 | Phoenix | Observability |
| 4000 | LiteLLM | API-Gateway |
| 8002 | Agent Server | Local Agent |

Alle Ports sind nur auf `127.0.0.1` gebunden — kein externer Zugang.
Zugriff über Cloudflare Tunnel oder SSH-Tunnel.

---

## Datenfluss

```
Du (Terminal/VS Code)
    ↓ Port 4000
LiteLLM (API-Gateway)
    ↓ Port 8080
llama-server (Granite Reasoning)

Agent Server (Port 8002)
    ↓
ChromaDB (embedded, /home/user/chroma)
    ↓
llama-server (Port 8081, Embeddings)

Phoenix (Port 6006)
    ↑ alle LangChain Calls
```

---

## Troubleshooting

**llama-server startet nicht:**
```bash
tail -20 /home/user/llama-granite.log
# Häufig: --mlock schlägt fehl auf KVM → --no-mmap stattdessen
```

**LiteLLM antwortet nicht:**
```bash
tail -20 /tmp/litellm.log
# Häufig: Port 4000 bereits belegt
```

**Agent Server Fehler:**
```bash
journalctl -u agent -f
# Häufig: OPENAI_API_KEY nicht gesetzt
```

**Phoenix keine Traces:**
```bash
# PHOENIX_COLLECTOR_ENDPOINT muss gesetzt sein VOR dem Import
export PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6006/v1/traces
```

---

## Bekannte Probleme und Fixes

### Phoenix: LangChain Instrumentierung schlägt fehl

**Fehler:**
```
TypeError: 'NoneType' object is not iterable
```

**Fix:** Bereits in `telemetry.py` eingebaut:
```python
LangChainInstrumentor().instrument(
    tracer_provider=tracer_provider,
    skip_dep_check=True
)
```

Kein manueller Eingriff nötig — `git pull` und neu starten reicht.

---

## Tool-Calling: Modell-natives Format

LangChain `bind_tools()` sendet Tools im OpenAI-Format. Granite und andere
Modelle erwarten ihr eigenes Format. `tool_formatter.py` löst das generisch.

```python
from tool_formatter import format_tools_for_model

system = format_tools_for_model(tools, model_name="granite-tiny")
# → <tools>...</tools> XML für Granite
# → None für OpenAI-kompatible Modelle (pass-through)
```

| Familie | Erkennung | Format |
|---------|-----------|--------|
| granite | granite, ibm | `<tools>` XML + `<tool_call>` |
| qwen    | qwen | ChatML `<tools>` |
| llama   | llama, meta | JSON function |
| default | alles andere | OpenAI pass-through |
