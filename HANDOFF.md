# HANDOFF.md — Chief-of-Staff janhet Edition
**Erstellt:** 2026-07-15 (Update)
**Zweck:** Neuen Container sofort wieder aufbauen — exakter Stand dieser Session.

---

## KRITISCH: Container-Disk-Problem

Der Claude.ai Sandbox-Container läuft mit **100% Disk-Auslastung** (~252 GB, 70 MB frei).
Folgende Schritte konnten deshalb **nicht ausgeführt** werden:
- `llama-cpp-python==0.3.23` — Wheel-Build schlägt fehl (braucht ~500 MB tmp)
- Modell-Download (`granite-4.0-h-350m-Q4_K_M.gguf`, 212 MB) — kein Platz in `/tmp`
- `tests/run_tests.py` — setzt `llama-cpp-python` + Modell voraus

**Alle anderen Pakete waren bereits installiert** (aus vorherigen Sessions).

---

## 1. Repository

```bash
git clone https://github.com/janhetzler/la /home/claude/la
cd /home/claude/la
```

**Aktueller Stand:**
| | |
|---|---|
| Letzter Commit | `ae471a6` — test: Tool-Calling 350m bestätigt ✓ |
| Branch | main |
| Commits diese Session | 3 (tool_formatter, docs, handoff) |

---

## 2. Python-Pakete installieren

### 2a. Base requirements (exakt pinned, kein torch):
```bash
pip install --break-system-packages -r requirements-janhet.txt
```

> **Hinweis `llama-cpp-python`:** Braucht ~500 MB Disk für den C++-Build.
> Wenn Disk voll → erst aufräumen: `pip cache purge && apt clean`
> Alles andere (mcp-server-git/fetch, headroom-ai, phoenix) ist in requirements-janhet.txt enthalten.

### 2c. Vollständige installierte Paket-Versionen (Stand dieser Session):

| Paket | Version |
|-------|---------|
| langchain | 1.2.15 |
| langchain-core | 1.3.2 |
| langchain-openai | 1.2.1 |
| langchain-mcp-adapters | 0.2.2 |
| langgraph | 1.1.10 |
| llama-index-core | 0.14.21 |
| llama-index-embeddings-litellm | 0.5.0 |
| llama-index-workflows | 2.20.0 |
| chromadb | 1.5.9 |
| litellm | 1.92.0 |
| litellm-enterprise | 0.1.47 |
| arize-phoenix | 17.7.0 |
| arize-phoenix-client | 2.13.0 |
| openinference-instrumentation-langchain | 0.1.67 |
| opentelemetry-sdk | 1.43.0 |
| opentelemetry-exporter-otlp | 1.43.0 |
| openai | 2.45.0 |
| headroom-ai | 0.31.0 |
| mcp | 1.28.1 |
| mcp-server-git | 2026.7.10 |
| mcp-server-fetch | 2026.7.10 |
| fastmcp-slim | 3.4.4 |
| starlette-context | 0.5.1 |
| pydantic | 2.12.5 |
| fastapi | 0.136.1 |
| uvicorn | 0.51.0 |
| torch | 2.13.0 |
| httpx | 0.28.1 |
| llama-cpp-python | **NICHT installiert** (Disk-Problem) |

---

## 3. Modell herunterladen

```bash
python3 -c "
import urllib.request
URL = 'https://github.com/janhetzler/la/releases/download/granite-models/granite-4.0-h-350m-Q4_K_M.gguf'
FILE = '/tmp/granite-350m-Q4_K_M.gguf'
req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as r, open(FILE, 'wb') as f:
    downloaded = 0
    while True:
        chunk = r.read(1024*1024)
        if not chunk: break
        f.write(chunk); downloaded += len(chunk)
        print(f'{downloaded//1024//1024} MB', end='\r')
print('Fertig:', FILE)
"
```

**Modell-Details:** `granite-4.0-h-350m-Q4_K_M.gguf`, ~212 MB
**Auf janhet:** `Granite-4.0-H-Tiny IQ4_XS` (4B, 28-32 t/s) — bevorzugtes Produktionsmodell

---

## 4. Verzeichnisstruktur

```
/home/claude/la/
├── agents/
│   ├── server/
│   │   ├── code.py           # Code-Agent (→ ChatOpenAI Port 4000)
│   │   ├── comms.py          # Comms-Agent (→ ChatOpenAI Port 4000)
│   │   ├── config.py         # Zentrales Config (CHROMA_PATH, LiteLLM URLs)
│   │   ├── handoff.py        # Handoff-Agent (→ ChatOpenAI, ChromaDB)
│   │   ├── meeting.py        # DISABLED auf Server
│   │   ├── notes.py          # Notes-Agent (ChromaDB statt Qdrant)
│   │   ├── project_context.py
│   │   ├── researcher_v2.py  # Researcher (metadata key fix: source,category)
│   │   ├── server.py         # FastAPI Agent-Server (Phoenix init beim Start)
│   │   ├── supervisor.py     # Supervisor (→ ChatOpenAI, meeting disabled)
│   │   ├── telemetry.py      # NEU: Phoenix + LangChain (skip_dep_check=True!)
│   │   ├── tool_formatter.py # NEU: Generischer Tool-Formatter (18/18 Tests ✓)
│   │   ├── tools.py          # get_tools_system_prompt() hinzugefügt
│   │   ├── user_profile.py
│   │   └── project_context.py
│   └── ingestion/
│       ├── ingest.py         # Qdrant→ChromaDB
│       └── search.py         # ChromaDB, Filter-Fix
├── tests/
│   ├── run_tests.py          # Stack starten + Tests (braucht MODEL_PATH)
│   └── test_stack.py         # Test-Suite (6 Agenten, Headroom, Phoenix)
├── requirements.txt          # Original (mit torch)
├── requirements-janhet.txt   # JANHET: ohne torch/qdrant/audio
├── HANDOFF.md                # Diese Datei
├── BUGS.md                   # Bekannte Probleme
└── JANHET_SETUP.md           # janhet Deployment-Anleitung
```

---

## 5. Wichtigste neue Datei: tool_formatter.py

**Pfad:** `agents/server/tool_formatter.py`

Übersetzt OpenAI tool-call Format in natives Chat-Template Format des Modells.
Status: **18/18 Tests bestanden ✓**

```python
from tool_formatter import format_tools_for_model, parse_tool_call_from_response

# Tool-Definition
tool_def = {"type": "function", "function": {
    "name": "git_log",
    "description": "Show git commit history",
    "parameters": {"type": "object",
                   "properties": {"max_count": {"type": "integer"}},
                   "required": []}
}}

# System-Prompt für Granite
system_prompt = format_tools_for_model([tool_def], model_name="granite-tiny")

# Nach LLM-Antwort: Tool-Call parsen
parsed = parse_tool_call_from_response(response.content, model_family="granite")
# → {"name": "git_log", "arguments": {"max_count": 5}}
```

**Unterstützte Modelle:** `granite`, `qwen`, `llama`, `mistral`, `default`

---

## 6. Stack starten (Tests)

```bash
# Alle Dienste + Tests in einem Block:
MODEL_PATH=/tmp/granite-350m-Q4_K_M.gguf \
python3 tests/run_tests.py
```

**Was run_tests.py startet:**
1. llama-server (Port 8080) — via llama_cpp.server
2. Headroom Proxy (Port 8787) — Kontext-Kompression
3. Arize Phoenix (Port 6006) — Observability
4. LiteLLM (Port 4000) — API Gateway
5. Agent Server (Port 8002) — Chief-of-Staff FastAPI

**Ports:**
| Port | Dienst |
|------|--------|
| 8080 | llama-server (Reasoning) |
| 8081 | llama-server (Embedding, auf janhet) |
| 8787 | Headroom Proxy |
| 6006 | Arize Phoenix UI |
| 4000 | LiteLLM Gateway |
| 8002 | Agent Server (Chief-of-Staff) |

---

## 7. Geänderte Dateien vs. Original Fork

| Datei | Änderung |
|-------|----------|
| `agents/server/supervisor.py` | ChatOllama→ChatOpenAI, meeting disabled |
| `agents/server/code.py` | ChatOllama→ChatOpenAI Port 4000 |
| `agents/server/comms.py` | ChatOllama→ChatOpenAI Port 4000 |
| `agents/server/handoff.py` | ChatOpenAI, Qdrant→ChromaDB |
| `agents/server/notes.py` | ChromaDB collection.query() statt Qdrant |
| `agents/server/researcher_v2.py` | metadata key fix (source, category) |
| `agents/server/server.py` | Phoenix init_phoenix() beim Start |
| `agents/server/config.py` | CHROMA_PATH statt Qdrant URL |
| `agents/server/telemetry.py` | **NEU** — Phoenix + LangChain Instrumentation |
| `agents/server/tool_formatter.py` | **NEU** — Generischer Tool Formatter |
| `agents/server/tools.py` | get_tools_system_prompt() |
| `agents/ingestion/ingest.py` | Qdrant→ChromaDB |
| `agents/ingestion/search.py` | ChromaDB, Filter-Fix |

---

## 8. Kritische Fixes — NICHT VERGESSEN

**Fix 1: Phoenix skip_dep_check**
```python
# In telemetry.py — bereits eingebaut:
LangChainInstrumentor().instrument(tracer_provider=tracer_provider, skip_dep_check=True)
```

**Fix 2: headroom-ai Paketname**
```bash
pip install "headroom-ai[proxy]"  # NICHT: pip install headroom
```

**Fix 3: args_schema AttributeError**
```python
# Statt: tool.args_schema.schema()
# So:
try:
    schema = tool.args_schema.model_json_schema()
except AttributeError:
    schema = dict(tool.args_schema)
```

**Fix 4: llama-cpp-python Server Settings**
```python
# Kein ModelSettings Objekt — alles in Settings():
from llama_cpp.server.settings import Settings
settings = Settings(model='/tmp/model.gguf', host='127.0.0.1', port=8080,
                    n_ctx=16384, n_threads=4, chat_format='chatml')
# Auf janhet: n_threads=4, --parallel 1 (kein --no-mmap, kein --mlock)
```

**Fix 5: mcp.json absoluter Pfad**
```json
{
  "mcpServers": {
    "git": {
      "command": "python3",
      "args": ["-m", "mcp_server_git", "--repository", "/home/claude/la"],
      "transport": "stdio"
    }
  }
}
```

---

## 9. Test-Ergebnisse (letzte erfolgreiche Session)

| Test | Status | Anmerkung |
|------|--------|-----------|
| llama-server (Granite 350m) | ✓ ~25 t/s | Port 8080 |
| LiteLLM Proxy | ✓ | Port 4000 |
| Phoenix Traces | ✓ | skip_dep_check Fix nötig |
| Agent Server | ✓ 6/6 Agenten | Port 8002 |
| ChromaDB | ✓ | /tmp/chroma_chief |
| Headroom Proxy | ✓ | 24 Requests komprimiert |
| MCP git_log direkt | ✓ | stdio transport |
| MCP durch Agent | ✓ | Tools laden erfolgreich |
| Tool-Calling 350m | ✓ | args_schema dict() Fix |
| Tool-Calling 4B (janhet) | ✓ | bestätigt |
| tool_formatter.py | ✓ 18/18 | alle Modell-Familien |

**In dieser Session nicht ausgeführt** (Disk voll):
- run_tests.py — braucht llama-cpp-python + 212 MB Modell

---

## 10. janhet Deployment

```bash
# Auf janhet (185.129.86.169):
cd /pfad/zu/chief
git pull

# Janhet-spezifische requirements (kein torch):
pip install --break-system-packages -r requirements-janhet.txt

# Modell liegt bereits auf janhet:
# Granite-4.0-H-Tiny IQ4_XS (4B, 28-32 t/s)
# llama-server mit --parallel 1, kein --no-mmap, kein --mlock

# Tests:
MODEL_PATH=/pfad/zu/granite-tiny.gguf python3 tests/run_tests.py
```

---

## 11. Nächste Schritte

1. ✓ ERLEDIGT: tool_formatter.py — 18/18 Tests
2. ✓ ERLEDIGT: Tool-Calling 350m funktioniert nativ
3. **Offen: Phoenix Spans** — API Endpoint für Trace-Inhalte finden
4. **Offen: System-Prompt Pfad-Fix** — Modell nutzt "." statt absolutem Pfad
5. **Offen: janhet Deployment** — `git pull` + Tests mit Granite-Tiny-4B
6. **Offen: run_tests.py im frischen Container** — braucht genug Disk für llama-cpp-python Build
