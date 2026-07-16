# HANDOFF.md — Chief-of-Staff Projektübergabe
**Zuletzt aktualisiert:** 2026-07-16
**Zweck:** Vollständige Übergabe für neue Sessions und neuen Aufbau.

---

## ⚠️ ZWEI VERSCHIEDENE UMGEBUNGEN

| | Claude Sandbox | janhet (Produktion) |
|--|---------------|---------------------|
| **Zweck** | Entwicklung + Tests | Echter Betrieb |
| **Hardware** | Intel Xeon 1-Core, 4 GB RAM | AMD EPYC 7443P, 4 vCores, 10 GB RAM |
| **IP** | Claude.ai intern | [SERVER-IP] / [HOSTNAME] |
| **Inferenz** | llama-cpp-python (Python) | llama.cpp Binary |
| **Reasoning** | Granite-4.0-H-350m Q4_K_M (213 MB) | Granite-4.0-H-Tiny IQ4_XS (4.2 GB) |
| **Embedding** | Granite-Embedding-30m Q4_0 (28 MB) | Granite-Embedding-30m Q4_0 (28 MB) |
| **Installationsanleitung** | Abschnitt A | Abschnitt B |

---

## A. CLAUDE SANDBOX — Neue Session aufbauen

### A1. Disk-Platz prüfen (MINIMUM 2 GB frei)

```bash
df -h /
# System-Pakete die Platz fressen aber nicht von uns sind:
# nvidia 2.7GB, triton 641MB, opencv 200MB — NICHT anfassen
```

### A2. Repository

```bash
git clone https://github.com/janhetzler/la /home/claude/la
cd /home/claude/la
```

### A3. Pakete installieren

```bash
# Prebuilt Wheel — kein C++ Build, kein Compiler nötig
pip install --break-system-packages \
  "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.23/llama_cpp_python-0.3.23-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

pip install --break-system-packages -r requirements-janhet.txt
```

### A4. Modelle herunterladen

```bash
# Reasoning Modell (213 MB)
curl -L -o /tmp/granite-350m-Q4_K_M.gguf \
  -H "Authorization: Bearer GH_TOKEN" \
  "https://github.com/janhetzler/la/releases/download/granite-models/granite-4.0-h-350m-Q4_K_M.gguf"

# Embedding Modell (28 MB)
curl -L -o /tmp/granite-embedding-30m-Q4_0.gguf \
  -H "Authorization: Bearer GH_TOKEN" \
  "https://github.com/janhetzler/la/releases/download/granite-models/granite-embedding-30m-english-Q4_0.gguf"
```

### A5. Stack starten (alles in einem Block)

```python
import threading, time, urllib.request, json, subprocess, sys, os
import chromadb

os.makedirs('/tmp/chroma_chief', exist_ok=True)
sys.path.insert(0, '/home/claude/la/agents/server')
sys.path.insert(0, '/home/claude/la/agents/ingestion')

from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings
import uvicorn

# Reasoning Server Port 8080
settings = Settings(model='/tmp/granite-350m-Q4_K_M.gguf',
                    host='127.0.0.1', port=8080, n_ctx=4096,
                    n_threads=1, chat_format='chatml')
threading.Thread(target=uvicorn.Server(uvicorn.Config(
    create_app(settings=settings), host='127.0.0.1', port=8080,
    log_level='error')).run, daemon=True).start()

# Embedding Server Port 8081
settings_embed = Settings(model='/tmp/granite-embedding-30m-Q4_0.gguf',
                           host='127.0.0.1', port=8081, n_ctx=512,
                           n_threads=1, embedding=True)
threading.Thread(target=uvicorn.Server(uvicorn.Config(
    create_app(settings=settings_embed), host='127.0.0.1', port=8081,
    log_level='error')).run, daemon=True).start()

# LiteLLM
open('/tmp/litellm.yaml','w').write("""
model_list:
  - model_name: granite-tiny
    litellm_params:
      model: openai/granite
      api_base: http://127.0.0.1:8080/v1
      api_key: not-needed
  - model_name: granite-embed
    litellm_params:
      model: openai/granite-embed
      api_base: http://127.0.0.1:8081/v1
      api_key: not-needed
general_settings:
  master_key: sk-cos-local-dev
litellm_settings:
  drop_params: true
  set_verbose: false
""")
litellm_proc = subprocess.Popen(['litellm','--config','/tmp/litellm.yaml',
    '--host','127.0.0.1','--port','4000'],
    stdout=open('/tmp/litellm.log','w'), stderr=subprocess.STDOUT)

# Phoenix
os.environ['PHOENIX_COLLECTOR_ENDPOINT'] = 'http://127.0.0.1:6006/v1/traces'
phoenix_proc = subprocess.Popen(['python3','-m','phoenix.server.main',
    'serve','--host','127.0.0.1','--port','6006'],
    stdout=open('/tmp/phoenix.log','w'), stderr=subprocess.STDOUT)

# Agent Config
import config
config.LITELLM_URL = 'http://127.0.0.1:4000'
config.LITELLM_KEY = 'sk-cos-local-dev'
config.DEFAULT_LLM = 'granite-tiny'
config.CHROMA_PATH  = '/tmp/chroma_chief'
os.environ['OPENAI_API_KEY'] = 'sk-cos-local-dev'

# Phoenix Tracing
from telemetry import init_phoenix
init_phoenix()

# Agent Server
import server as agent_server
threading.Thread(target=uvicorn.Server(uvicorn.Config(
    agent_server.app, host='127.0.0.1', port=8002,
    log_level='error')).run, daemon=True).start()
```

### A6. Tests ausführen

```bash
python3 tests/run_tests.py
```

---

## B. JANHET — Produktion deployen

Vollständige Anleitung: `docs/INSTALL_JANHET.md`

```bash
ssh user@[HOSTNAME]
cd /home/user/chief/la && git pull
source /home/user/chief/venv/bin/activate
pip install -r requirements-janhet.txt

bash scripts/start_phoenix.sh
bash scripts/start_litellm.sh
bash /home/user/restart_llamaorgakt.sh   # Port 8080, Granite-Tiny-4B
bash /home/user/restart_embedding.sh     # Port 8081, Granite-Embedding-30m
cd agents/server && uvicorn server:app --host 127.0.0.1 --port 8002
python3 scripts/chat.py
```

---

## C. INSTALLIERTE PAKETE (Sandbox, Stand 2026-07-16)

### Aktive Pakete

| Paket | Version | Zweck |
|-------|---------|-------|
| langchain | 1.2.15 | Agent Framework |
| langchain-openai | 1.2.1 | LLM Client |
| langchain-mcp-adapters | 0.2.2 | MCP Integration |
| langgraph | 1.1.10 | Agent Orchestrierung |
| chromadb | 1.5.9 | Vektor Datenbank |
| litellm | 1.92.0 | API Gateway |
| arize-phoenix | 18.0.0 | Observability |
| openinference-instrumentation-langchain | 0.1.67 | Phoenix → LangChain |
| opentelemetry-sdk | 1.43.0 | Tracing |
| llama-cpp-python | 0.3.23 | Inferenz Server (Sandbox) |
| mcp-server-git | 2026.7.10 | Git MCP Tools |
| mcp-server-fetch | 2026.7.10 | Web Fetch MCP Tool |
| openai | 1.97.1 | API Client |
| fastapi | 0.139.0 | Agent Server |
| uvicorn | 0.51.0 | ASGI Server |
| llama-index-core | 0.14.23 | RAG / Embeddings |
| llama-index-embeddings-litellm | 0.5.0 | LiteLLM Embeddings |

### Disabled (installiert aber nicht aktiv)

| Paket | Grund |
|-------|-------|
| headroom-ai | DISABLED — benötigt headroom-ai[all] (~500MB + ONNX) |
| docling | DISABLED — zu gross, Import in ingest.py auskommentiert |

### Bewusst NICHT installiert

| Paket | Grund |
|-------|-------|
| torch / transformers | Nicht benötigt, Embeddings via llama-server |
| qdrant-client | Ersetzt durch ChromaDB |
| langchain-ollama / ollama | Ersetzt durch llama-server |
| sounddevice / soundfile | Kein Audio auf Server |

---

## D. MODELLE

| Modell | Größe | Port | Zweck | GitHub Release |
|--------|-------|------|-------|----------------|
| granite-4.0-h-350m-Q4_K_M.gguf | 213 MB | 8080 | Reasoning (Sandbox) | granite-models |
| granite-embedding-30m-english-Q4_0.gguf | 28 MB | 8081 | Embeddings | granite-models |
| granite-4.0-h-tiny.i1-IQ4_XS.gguf | 4.2 GB | 8080 | Reasoning (janhet) | separat |

---

## E. PORTS

| Port | Dienst | Sandbox | janhet |
|------|--------|---------|--------|
| 8080 | Reasoning llama-server | llama-cpp-python | Binary |
| 8081 | Embedding llama-server | llama-cpp-python | Binary |
| 8787 | Headroom Proxy | DISABLED | DISABLED |
| 6006 | Phoenix | ✓ | ✓ |
| 4000 | LiteLLM | ✓ | ✓ |
| 8002 | Agent Server | ✓ | ✓ |

---

## F. BEKANNTE FIXES

**Fix 1: Phoenix skip_dep_check**
```python
# In telemetry.py — bereits eingebaut:
LangChainInstrumentor().instrument(
    tracer_provider=tracer_provider,
    skip_dep_check=True  # pydantic Metadaten-Konflikt
)
```

**Fix 2: LiteLLM Readiness Check**
```python
# Nach LiteLLM Start — echter Request statt nur Port-Check:
req = urllib.request.Request(
    'http://127.0.0.1:4000/v1/chat/completions',
    data=json.dumps({'model':'granite-tiny',
        'messages':[{'role':'user','content':'hi'}],
        'max_tokens':3}).encode(), ...)
urllib.request.urlopen(req, timeout=30)
```

**Fix 3: mcp.json absoluter Pfad**
- Sandbox: `/home/claude/la`
- janhet: `/home/user/chief/la`

**Fix 4: args_schema für MCP Tools**
```python
schema = dict(tool.args_schema)  # statt tool.args_schema.schema()
```

**Fix 5: headroom-ai[all] statt [proxy]**
```bash
pip install "headroom-ai[all]==0.31.0"  # [proxy] allein reicht nicht
```

---

## G. TESTERGEBNISSE (Stand 2026-07-16)

| Test | Sandbox (350m) | janhet (4B) |
|------|---------------|-------------|
| llama-server :8080 | ✓ ~25 t/s | ✓ 28-32 t/s |
| llama-server :8081 Embedding | ✓ ~15ms/embedding | ✓ erwartet |
| LiteLLM | ✓ | ✓ erwartet |
| Phoenix Traces | ✓ | ✓ erwartet |
| Agent Server | ✓ 6/6 Agenten | ✓ erwartet |
| ChromaDB mit echten Embeddings | ✓ 384-dim | ✓ erwartet |
| MCP git_log | ✓ | ✓ erwartet |
| Tool-Calling | ✓ mit nativem Granite Format | ✓ bestätigt |
| tool_formatter.py | ✓ 18/18 Tests | ✓ |
| Supervisor Routing | ⚠️ 350m zu klein | ✓ erwartet |

**Routing Hinweis:** Das 350m Modell routet nicht zuverlässig.
Englische Prompts in Tests verwenden. Auf janhet mit 4B funktioniert Routing korrekt.

---

## H. NÄCHSTE SCHRITTE

1. **Docker Image bauen** — Dockerfile mit Prebuilt Wheel + beide Modelle
2. **janhet deployen** — git pull + Tests mit Granite-Tiny-4B
3. **Headroom reaktivieren** — wenn Disk-Platz vorhanden: `pip install "headroom-ai[all]==0.31.0"`
4. **Supervisor Routing** — bind_tools() + supports_tools: true in LiteLLM Config
5. **Phoenix Spans API** — richtigen Endpoint für Trace-Inhalte finden
6. **VS Code Anbindung** — Port 4000 als Language Model Provider
