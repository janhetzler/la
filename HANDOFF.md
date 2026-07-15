# HANDOFF.md — Chief-of-Staff Projektübergabe
**Erstellt:** 2026-07-15  
**Zweck:** Vollständige Übergabe für neue Sessions und neuen Aufbau.

---

## ⚠️ ZWEI VERSCHIEDENE UMGEBUNGEN

| | Claude Sandbox | janhet (Produktion) |
|--|---------------|---------------------|
| **Zweck** | Entwicklung + Tests | Echter Betrieb |
| **Hardware** | Intel Xeon 1-Core, 4 GB RAM | AMD EPYC 7443P, 4 vCores, 10 GB RAM |
| **IP** | Claude.ai intern | 185.129.86.169 / janhet.de |
| **llama-server** | llama-cpp-python (Python) | llama.cpp Binary |
| **Modell** | Granite-350m Q4_K_M (212 MB) | Granite-4.0-H-Tiny IQ4_XS (4.2 GB) |
| **Anleitung** | Abschnitt A (unten) | Abschnitt B (unten) |

---

## A. CLAUDE SANDBOX — Neue Session aufbauen

Für Tests und Entwicklung in der Claude.ai Umgebung.

### A1. Disk-Platz sicherstellen (KRITISCH)

```bash
df -h /          # Minimum 3 GB frei nötig
pip cache purge  # Falls zu voll
apt clean
# torch NICHT installieren — nicht nötig und frisst 1.2 GB
```

### A2. Repository

```bash
git clone https://github.com/janhetzler/la /home/claude/la
cd /home/claude/la
```

### A3. Pakete installieren

```bash
pip install --break-system-packages -r requirements-janhet.txt
# llama-cpp-python braucht ~500 MB Disk + 5 Min C++ Build
```

### A4. Modell herunterladen (212 MB)

```bash
python3 -c "
import urllib.request
URL = 'https://github.com/janhetzler/la/releases/download/granite-models/granite-4.0-h-350m-Q4_K_M.gguf'
req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as r, open('/tmp/granite-350m-Q4_K_M.gguf','wb') as f:
    while chunk := r.read(1024*1024): f.write(chunk)
print('Fertig: /tmp/granite-350m-Q4_K_M.gguf')
"
```

### A5. Stack starten (alles in einem Block)

```python
import threading, time, urllib.request, json, subprocess, sys, os

os.makedirs('/tmp/chroma_chief', exist_ok=True)
sys.path.insert(0, '/home/claude/la/agents/server')
sys.path.insert(0, '/home/claude/la/agents/ingestion')

from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings
import uvicorn

# llama-server mit Granite-350m
settings = Settings(model='/tmp/granite-350m-Q4_K_M.gguf', host='127.0.0.1', port=8080,
                    n_ctx=4096, n_threads=1, chat_format='chatml')
threading.Thread(target=uvicorn.Server(uvicorn.Config(
    create_app(settings=settings), host='127.0.0.1', port=8080, log_level='error')).run,
    daemon=True).start()

# LiteLLM
with open('/tmp/litellm_test.yaml','w') as f:
    f.write("model_list:\n  - model_name: granite-tiny\n    litellm_params:\n      model: openai/granite\n      api_base: http://127.0.0.1:8080/v1\n      api_key: not-needed\ngeneral_settings:\n  master_key: sk-cos-local-dev\nlitellm_settings:\n  drop_params: true\n  set_verbose: false\n")
litellm_proc = subprocess.Popen(['litellm', '--config', '/tmp/litellm_test.yaml',
    '--host', '127.0.0.1', '--port', '4000'],
    stdout=open('/tmp/litellm.log','w'), stderr=subprocess.STDOUT)

# Phoenix
os.environ['PHOENIX_COLLECTOR_ENDPOINT'] = 'http://127.0.0.1:6006/v1/traces'
phoenix_proc = subprocess.Popen(['python3', '-m', 'phoenix.server.main', 'serve',
    '--host', '127.0.0.1', '--port', '6006'],
    stdout=open('/tmp/phoenix.log','w'), stderr=subprocess.STDOUT)

# Agent Config
import config
config.LITELLM_URL = 'http://127.0.0.1:4000'
config.LITELLM_KEY = 'sk-cos-local-dev'
config.DEFAULT_LLM = 'granite-tiny'
config.CHROMA_PATH = '/tmp/chroma_chief'
os.environ['OPENAI_API_KEY'] = 'sk-cos-local-dev'

# Agent Server
import server as agent_server
threading.Thread(target=uvicorn.Server(uvicorn.Config(
    agent_server.app, host='127.0.0.1', port=8002, log_level='error')).run,
    daemon=True).start()
```

### A6. Tests ausführen

```bash
MODEL_PATH=/tmp/granite-350m-Q4_K_M.gguf python3 tests/run_tests.py
```

---

## B. JANHET — Produktion deployen

Für den echten Betrieb auf janhet (185.129.86.169).  
Vollständige Anleitung: `docs/INSTALL_JANHET.md`

### B1. Repository

```bash
ssh janhetzler@ssh.janhet.de
cd /home/user/chief/la && git pull
```

### B2. Python Umgebung

```bash
source /home/user/chief/venv/bin/activate
pip install -r requirements-janhet.txt
# kein llama-cpp-python nötig — janhet nutzt llama-server Binary
```

### B3. Services starten

```bash
bash scripts/start_phoenix.sh
bash scripts/start_headroom.sh
bash scripts/start_litellm.sh
cd agents/server && uvicorn server:app --host 127.0.0.1 --port 8002
```

### B4. llama-server (bereits auf janhet)

```bash
bash /home/user/restart_llamaorgakt.sh   # Port 8080, Granite-Tiny-4B
bash /home/user/restart_embedding.sh     # Port 8081, Granite-Embedding-30m
```

### B5. Test

```bash
python3 scripts/chat.py
# oder:
MODEL_PATH=/home/user/models/granite-4.0-h-tiny.i1-IQ4_XS.gguf \
python3 tests/run_tests.py
```

---

## C. BEKANNTE FIXES

**Fix 1: Phoenix skip_dep_check**
```python
LangChainInstrumentor().instrument(tracer_provider=tracer_provider, skip_dep_check=True)
# bereits in telemetry.py eingebaut
```

**Fix 2: headroom-ai statt headroom**
```bash
pip install "headroom-ai[proxy]"  # NICHT: pip install headroom
# bereits in requirements-janhet.txt
```

**Fix 3: mcp.json absoluter Pfad**
- Sandbox: `/home/claude/la`
- janhet: `/home/user/chief/la`

**Fix 4: args_schema für MCP Tools**
```python
schema = dict(tool.args_schema)  # statt tool.args_schema.schema()
```

**Fix 5: llama-cpp-python Settings**
```python
settings = Settings(model='...', host='127.0.0.1', port=8080, ...)
# KEIN separates ModelSettings Objekt
```

---

## D. TESTERGEBNISSE (Claude Sandbox, Granite-350m)

| Test | Sandbox | janhet |
|------|---------|--------|
| llama-server | ✓ 25 t/s | ✓ 28-32 t/s |
| LiteLLM | ✓ | ✓ (erwartet) |
| Phoenix Traces | ✓ | ✓ (erwartet) |
| Headroom | ✓ 24 Requests | ✓ (erwartet) |
| Agent Server | ✓ 6/6 | ✓ (erwartet) |
| ChromaDB | ✓ | ✓ (erwartet) |
| MCP git_log | ✓ | ✓ (erwartet) |
| Tool-Calling | ✓ 350m mit nativem Format | ✓ 4B bestätigt |
| tool_formatter.py | ✓ 18/18 Tests | ✓ (erwartet) |

---

## E. PORTS

| Port | Dienst | Sandbox | janhet |
|------|--------|---------|--------|
| 8080 | llama-server Reasoning | llama-cpp-python | llama-server Binary |
| 8081 | llama-server Embedding | — | llama-server Binary |
| 8787 | Headroom | ✓ | ✓ |
| 6006 | Phoenix | ✓ | ✓ |
| 4000 | LiteLLM | ✓ | ✓ |
| 8002 | Agent Server | ✓ | ✓ |

---

## F. NÄCHSTE SCHRITTE

1. **janhet deployen** — `git pull` auf janhet, Tests mit Granite-Tiny-4B
2. **Phoenix Spans API** — richtigen Endpoint für Trace-Inhalte finden
3. **MCP Pfad-Fix** — System-Prompt soll absoluten Pfad vorgeben
4. **VS Code Anbindung** — Port 4000 als Language Model Provider eintragen
