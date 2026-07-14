# Installation Guide — janhet Edition

Schritt-für-Schritt Anleitung für die Installation des Chief-of-Staff
auf einem Hetzner KVM Server (AMD EPYC, 4 vCores, 10 GB RAM, Debian 12).
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
mkdir -p /home/user/llamaorgakt

# Aktuelles Release herunterladen (b9977 oder neuer)
cd /home/user/llamaorgakt
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
--tools read_file,grep_search,file_glob_search,get_datetime
--repeat-penalty 1.15
--temp 0.1
--top-p 0.95
--top-k 20
-n 2048
--port 8080
CFGEOF

# Start-Script für Reasoning (Port 8080)
cat << 'SEOF' > /home/user/restart_llamaorgakt.sh
#!/bin/bash
pkill -f "llama-server.*8080" || true
sleep 2
xargs -a /home/user/models/config/granite-server-params.txt \
  /home/user/llamaorgakt/llama-b9977/llama-server \
  -m /home/user/models/granite-4.0-h-tiny.i1-IQ4_XS.gguf \
  > /home/user/llama-granite.log 2>&1 &
sleep 5
tail -5 /home/user/llama-granite.log
SEOF
chmod +x /home/user/restart_llamaorgakt.sh

# Start-Script für Embedding (Port 8081)
cat << 'EEOF' > /home/user/restart_embedding.sh
#!/bin/bash
pkill -f "llama-server.*8081" || true
sleep 2
/home/user/llamaorgakt/llama-b9977/llama-server \
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
bash /home/user/restart_llamaorgakt.sh
bash /home/user/restart_embedding.sh

# Testen
curl -s http://127.0.0.1:8080/health && echo "Reasoning OK"
curl -s http://127.0.0.1:8081/health && echo "Embedding OK"
```

---

## Schritt 4 — Python Umgebung

```bash
# Arbeitsverzeichnis
mkdir -p /home/user/chief
cd /home/user/chief

# Repository klonen
git clone https://github.com/janhetzler/la la
cd la

# Virtuelle Umgebung (ohne torch!)
python3 -m venv /home/user/chief/venv
source /home/user/chief/venv/bin/activate

# Dependencies installieren
pip install --upgrade pip
pip install -r requirements-janhet.txt
pip install "headroom-ai[proxy]"

# Testen
python3 -c "import langchain, chromadb, litellm; print('OK')"
```

---

## Schritt 5 — Headroom Proxy

Headroom komprimiert Kontexte bevor sie den llama-server erreichen.
Sitzt zwischen LiteLLM (Port 4000) und llama-server (Port 8080).

```bash
# Starten
source /home/user/chief/venv/bin/activate
bash /home/user/chief/la/scripts/start_headroom.sh

# Testen
curl -s http://127.0.0.1:8787/health | python3 -m json.tool
```

---

## Schritt 6 — Arize Phoenix

Phoenix sammelt Traces von allen Agent-Calls für Observability.

```bash
source /home/user/chief/venv/bin/activate
bash /home/user/chief/la/scripts/start_phoenix.sh

# Testen
curl -s http://127.0.0.1:6006/healthz
```

---

## Schritt 7 — LiteLLM Proxy

LiteLLM ist das zentrale API-Gateway. Routet auf Headroom → llama-server.

```bash
source /home/user/chief/venv/bin/activate
bash /home/user/chief/la/scripts/start_litellm.sh

# Testen
curl -s http://127.0.0.1:4000/health \
  -H "Authorization: Bearer sk-cos-local-dev"

# Modelle prüfen
curl -s http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer sk-cos-local-dev" | python3 -m json.tool
```

---

## Schritt 8 — Agent Server

```bash
source /home/user/chief/venv/bin/activate
cd /home/user/chief/la/agents/server

export LITELLM_URL=http://127.0.0.1:4000
export LITELLM_KEY=sk-cos-local-dev
export OPENAI_API_KEY=sk-cos-local-dev
export CHROMA_PATH=/home/user/chief/chroma_db
export PHOENIX_HOST=http://127.0.0.1:6006

uvicorn server:app --host 127.0.0.1 --port 8002 &

# Testen
curl -s http://127.0.0.1:8002/health
curl -s http://127.0.0.1:8002/v1/models | python3 -m json.tool
```

---

## Schritt 9 — Terminal Chat testen

```bash
source /home/user/chief/venv/bin/activate
python3 /home/user/chief/la/scripts/chat.py
```

---

## Schritt 10 — Test Suite ausführen

```bash
source /home/user/chief/venv/bin/activate
MODEL_PATH=/home/user/models/granite-4.0-h-tiny.i1-IQ4_XS.gguf \
CHROMA_PATH=/home/user/chief/chroma_db \
python3 /home/user/chief/la/tests/run_tests.py
```

---

## Schritt 11 — systemd Services (Dauerbetrieb)

```bash
# Alle 4 Services installieren
sudo cp /home/user/chief/la/deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Aktivieren und starten
sudo systemctl enable --now headroom phoenix litellm chief-agent

# Status prüfen
sudo systemctl status headroom phoenix litellm chief-agent
```

---

## Port-Übersicht

| Port | Dienst | Zweck |
|------|--------|-------|
| 8080 | llama-server | Granite Reasoning |
| 8081 | llama-server | Granite Embedding |
| 8787 | Headroom | Kontext-Kompression |
| 6006 | Phoenix | Observability |
| 4000 | LiteLLM | API-Gateway |
| 8002 | Agent Server | Chief-of-Staff |

Alle Ports sind nur auf `127.0.0.1` gebunden — kein externer Zugang.
Zugriff über Cloudflare Tunnel oder SSH-Tunnel.

---

## Datenfluss

```
Du (Terminal/VS Code)
    ↓ Port 4000
LiteLLM (API-Gateway)
    ↓ Port 8787
Headroom (Kompression)
    ↓ Port 8080
llama-server (Granite Reasoning)

Agent Server (Port 8002)
    ↓
ChromaDB (embedded, /home/user/chief/chroma_db)
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
journalctl -u chief-agent -f
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

**Ursache:** Pakete mit ungültigen Metadaten (z.B. pydantic) verursachen einen Fehler
in `get_dependency_conflicts()` von opentelemetry-instrumentation.

**Fix:** Bereits in `telemetry.py` eingebaut:
```python
LangChainInstrumentor().instrument(
    tracer_provider=tracer_provider,
    skip_dep_check=True  # ← dieser Parameter löst das Problem
)
```

Kein manueller Eingriff nötig — `git pull` und neu starten reicht.

### Headroom: Falsches Paket

`pip install headroom` installiert ein falsches Terminal-Tool.
Das richtige Paket heißt:
```bash
pip install "headroom-ai[proxy]"
```

---

## Tool-Calling: Modell-natives Format

LangChain `bind_tools()` sendet Tools im OpenAI-Format. Granite, Qwen
und andere Modelle erwarten ihr eigenes Format. Der `tool_formatter.py`
löst das generisch.

**Wie es funktioniert:**

```python
from tool_formatter import format_tools_for_model

# Gibt nativen System-Prompt zurück statt bind_tools()
system = format_tools_for_model(tools, model_name="granite-tiny")
# → <tools>...</tools> XML für Granite
# → <tools>...</tools> ChatML für Qwen  
# → None für OpenAI-kompatible Modelle (pass-through)
```

**Unterstützte Modell-Familien:**

| Familie | Erkennung | Format |
|---------|-----------|--------|
| granite | granite, ibm | `<tools>` XML + `<tool_call>` |
| qwen    | qwen | ChatML `<tools>` |
| llama   | llama, meta | JSON function |
| default | alles andere | OpenAI pass-through |

**Neues Modell hinzufügen:** `MODEL_FAMILIES` und `FORMATTERS`
in `tool_formatter.py` erweitern — kein anderer Code ändern nötig.
