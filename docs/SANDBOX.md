# SANDBOX.md — Local Agent, Claude Sandbox

**Zuletzt aktualisiert:** 2026-07-16
**Zweck:** Vollständige Anleitung um die Sandbox-Umgebung in einer neuen
Claude.ai Session von Grund auf neu aufzubauen.

Diese Datei beschreibt ausschließlich die **Sandbox-Umgebung**. Für die
anderen beiden Umgebungen siehe [HOST.md](HOST.md) und [DOCKER.md](DOCKER.md).

---

## 1. Disk-Platz prüfen (Minimum 2 GB frei)

```bash
df -h /
# System-Pakete die Platz fressen aber nicht von uns sind:
# nvidia 2.7GB, triton 641MB, opencv 200MB — NICHT anfassen
```

---

## 2. Repository

```bash
git clone https://github.com/janhetzler/la /home/claude/la
cd /home/claude/la
```

---

## 3. Pakete installieren

```bash
# Prebuilt Wheel — kein C++ Build, kein Compiler nötig
pip install --break-system-packages \
  "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.23/llama_cpp_python-0.3.23-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

pip install --break-system-packages -r requirements-janhet.txt
```

---

## 4. Modelle herunterladen

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

---

## 5. Stack starten (alles in einem Block)

**Wichtig:** Alle Hintergrundprozesse sterben wenn der bash-Aufruf endet.
Der komplette Stack muss deshalb in einem einzigen Python-Block gestartet werden.

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

---

## 6. Tests ausführen

```bash
python3 tests/run_tests.py
```

---

## 7. Terminal-Chat (Ersatz für VS Code Language Model API)

Die Sandbox hat keinen Web-Zugang für eine VS Code Verbindung. `scripts/chat.py`
ist der direkte Ersatz — ein Terminal-Client der gegen LiteLLM (Port 4000) spricht,
LiteLLM leitet zum Agent Server (Port 8002) weiter, der Supervisor routet zum
richtigen Spezialisten. Das entspricht dem Original-Konzept aus
`docker/litellm_config.yaml` (dort: `agent-chief-of-staff` → Port 8002).

```bash
python3 scripts/chat.py
```

`model="agent-local"` — funktioniert, seit `litellm_config_janhet.yaml` um den
`agent-local` Endpoint ergänzt wurde (Port 8002). Bestätigt getestet 2026-07-16:
Supervisor antwortet korrekt über diesen Pfad.

⚠️ **Bekannte Kleinigkeit:** `chat.py` Z.10 zeigt noch den alten Begrüßungstext
`"=== Chief-of-Staff Terminal Chat ==="` — kosmetisch, keine Funktionsauswirkung,
noch nicht nachgezogen bei der Umbenennung.

⚠️ **Timing beim Start:** `litellm.log` zeigt beim Hochfahren kurzzeitig
`ConnectionRefusedError` auf Port 8002, weil LiteLLM einen Readiness-Check
ausführt bevor der Agent Server bereit ist. Der eigentliche Request danach
funktioniert. Kein funktionaler Fehler, aber beim Log-Lesen nicht verwirren lassen.

---

## A. Installierte Pakete (Stand 2026-07-16)

### Aktiv

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
| llama-cpp-python | 0.3.23 | Inferenz Server |
| mcp-server-git | 2026.7.10 | Git MCP Tools |
| mcp-server-fetch | 2026.7.10 | Web Fetch MCP Tool |
| openai | 1.97.1 | API Client |
| fastapi | 0.139.0 | Agent Server |
| uvicorn | 0.51.0 | ASGI Server |
| llama-index-core | 0.14.23 | RAG / Embeddings |
| llama-index-embeddings-litellm | 0.5.0 | LiteLLM Embeddings |

### Disabled (installiert, aber nicht aktiv)

| Paket | Grund |
|-------|-------|
| headroom-ai | DISABLED — benötigt headroom-ai[all] (~500MB + ONNX) |
| docling | DISABLED — zu groß, Import in ingest.py auskommentiert |

### Bewusst nicht installiert

| Paket | Grund |
|-------|-------|
| torch / transformers | Nicht benötigt, Embeddings via llama-server |
| qdrant-client | Ersetzt durch ChromaDB |
| langchain-ollama / ollama | Ersetzt durch llama-server |
| sounddevice / soundfile | Kein Audio in der Sandbox |

---

## B. Modelle

| Modell | Größe | Port | Zweck |
|--------|-------|------|-------|
| granite-4.0-h-350m-Q4_K_M.gguf | 213 MB | 8080 | Reasoning |
| granite-embedding-30m-english-Q4_0.gguf | 28 MB | 8081 | Embeddings |

Beide als GitHub Release Assets unter dem Tag `granite-models`.

---

## C. Ports

| Port | Dienst |
|------|--------|
| 8080 | Reasoning llama-server (llama-cpp-python) |
| 8081 | Embedding llama-server (llama-cpp-python) |
| 8787 | Headroom Proxy — DISABLED |
| 6006 | Phoenix |
| 4000 | LiteLLM |
| 8002 | Agent Server |

---

## D. Bekannte Fixes

**Fix 1 — Phoenix skip_dep_check**
```python
# In telemetry.py — bereits eingebaut:
LangChainInstrumentor().instrument(
    tracer_provider=tracer_provider,
    skip_dep_check=True  # pydantic Metadaten-Konflikt
)
```

**Fix 2 — LiteLLM Readiness Check**
```python
# Nach LiteLLM Start — echter Request statt nur Port-Check:
req = urllib.request.Request(
    'http://127.0.0.1:4000/v1/chat/completions',
    data=json.dumps({'model':'granite-tiny',
        'messages':[{'role':'user','content':'hi'}],
        'max_tokens':3}).encode(), ...)
urllib.request.urlopen(req, timeout=30)
```

**Fix 3 — mcp.json Pfad**
In der Sandbox: `/home/claude/la`. Dieser Pfad ist Sandbox-spezifisch und
muss in anderen Umgebungen angepasst werden.

**Fix 4 — args_schema für MCP Tools**
```python
schema = dict(tool.args_schema)  # statt tool.args_schema.schema()
```

**Fix 5 — headroom-ai[all] statt [proxy]**
```bash
pip install "headroom-ai[all]==0.31.0"  # [proxy] allein reicht nicht
```
Aktuell nicht relevant — Headroom ist deaktiviert, siehe ROADMAP.md.

---

## E. Testergebnisse (Stand 2026-07-16)

| Test | Ergebnis |
|------|----------|
| llama-server :8080 | ✓ ~25 t/s |
| llama-server :8081 Embedding | ✓ ~15ms/embedding |
| LiteLLM | ✓ |
| Phoenix Traces | ✓ |
| Agent Server | ✓ 6/6 Agenten |
| ChromaDB mit echten Embeddings | ✓ 384-dim |
| MCP git_log | ✓ |
| Tool-Calling | ✓ mit nativem Granite Format |
| tool_formatter.py | ✓ 18/18 Tests |
| Supervisor Routing | ⚠️ 350m-Modell zu klein für zuverlässiges Routing |

**Routing-Hinweis:** Das 350m-Modell routet nicht zuverlässig — englische
Prompts in Tests verwenden. Das ist eine Modellgrößen-Limitation, kein Bug.

---

## F. Logging (Stand 2026-07-16, nachgerüstet)

Alle Logs liegen einheitlich unter `/tmp/logs/`:

| Datei | Komponente | Status |
|---|---|---|
| `/tmp/logs/litellm.log` | LiteLLM | ✓ funktioniert |
| `/tmp/logs/phoenix.log` | Phoenix | ✓ funktioniert |
| `/tmp/logs/llama-server.log` | Reasoning Server | ⚠️ bleibt leer — uvicorn-Thread-Logging greift nicht |
| `/tmp/logs/agent-server.log` | Agent Server | ⚠️ bleibt leer — gleicher Grund |

`tests/test_stack.py` prüft nach jedem Service-Start die jeweilige Log-Datei
auf `ERROR`, `Exception`, `Traceback`, `CRITICAL` — nicht erst am Ende des
gesamten Testlaufs.

**Antwort-Validierung:** Tests bewerten nicht mehr nur `status==200`, sondern
prüfen zusätzlich Mindestlänge der Antwort. Beim Notes-Agent wird gezielt in
ChromaDB nachgeschaut ob die neue Notiz tatsächlich gespeichert wurde.

---

## G. Bekannte offene Punkte (Stand 2026-07-16)

- **Headroom-Guardrails-Block** in `docker/litellm_config_janhet.yaml` ist
  noch vorhanden, obwohl Headroom deinstalliert ist (siehe ROADMAP.md —
  Headroom wurde zugunsten von llmtrim verworfen). Erzeugt vermutlich
  Warnungen beim LiteLLM-Start. Noch nicht bereinigt.
- **Embedding-Server (Port 8081)** wird in `run_tests.py` nicht gestartet —
  nur der Reasoning-Server läuft. Ob ChromaDB mit echten Embeddings über
  diesen Pfad aktuell funktioniert, ist ungeklärt.
- **Notes/Handoff-Agent Routing** bleibt unzuverlässig — bekanntes
  Kapazitätslimit des 350m-Modells beim Supervisor-Routing (nicht beim
  MCP-Tool-Calling, das funktioniert). Auf einem größeren Modell (Host)
  sollte dies nicht auftreten.
- **`chat.py` Begrüßungstext** noch nicht auf "Local Agent" umbenannt (kosmetisch).

- Repository: https://github.com/janhetzler/la
- Original-Projekt: https://github.com/xaviervasques/chief-of-staff
- Architektur-Entscheidungen: [ROADMAP.md](ROADMAP.md)
