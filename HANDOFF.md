# HANDOFF.md — Chief-of-Staff janhet Edition
**Erstellt:** 2026-07-15  
**Zweck:** Neuen Container sofort wieder aufbauen — exakter Stand dieser Session.

---

## 1. Repository

```bash
git clone https://github.com/janhetzler/la /home/claude/la
cd /home/claude/la
# Token falls nötig:
# GH_TOKEN_HIER_EINSETZEN
```

**Letzter Commit:** `f37975c` — docs: Tool-Calling Dokumentation  
**Branch:** main  

---

## 2. Python Pakete installieren

```bash
# Originale requirements (mit torch — für Vollständigkeit)
pip install --break-system-packages -r requirements.txt

# Dann fehlende Pakete:
pip install --break-system-packages \
  "headroom-ai[proxy]" \
  "litellm[proxy]" \
  arize-phoenix \
  openinference-instrumentation-langchain \
  opentelemetry-sdk \
  opentelemetry-exporter-otlp \
  mcp-server-git \
  mcp-server-fetch \
  "llama-cpp-python==0.3.23" \
  starlette-context \
  chromadb \
  langchain-mcp-adapters
```

**Exakte Versionen (wichtig):**

| Paket | Version |
|-------|---------|
| langchain | 1.2.15 |
| langchain-openai | 1.2.1 |
| langgraph | 1.1.10 |
| langchain-mcp-adapters | 0.2.2 |
| chromadb | 1.5.9 |
| litellm | 1.92.0 |
| arize-phoenix | 18.0.0 |
| openinference-instrumentation-langchain | 0.1.67 |
| opentelemetry-sdk | 1.43.0 |
| llama-cpp-python | 0.3.23 |
| mcp-server-git | 2026.7.10 |
| mcp-server-fetch | 2026.7.10 |
| headroom-ai | 0.31.0 |
| torch | 2.11.0 |
| pydantic | 2.12.5 |
| fastapi | 0.139.0 |
| uvicorn | 0.51.0 |

---

## 3. Modell herunterladen

```bash
# Von GitHub Release (bereits hochgeladen):
python3 -c "
import urllib.request, time
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

---

## 4. Stack starten (für Tests)

```python
# Alles in einem Block — Hintergrundprozesse sterben zwischen Tool-Calls
import threading, time, urllib.request, json, subprocess, sys, os

os.makedirs('/tmp/chroma_chief', exist_ok=True)
sys.path.insert(0, '/home/claude/la/agents/server')
sys.path.insert(0, '/home/claude/la/agents/ingestion')

# llama-server
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings
import uvicorn

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

# Config
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

---

## 5. Offener Test — Tool-Calling mit nativem Granite Format

**Was getestet werden muss:**

Das 350m Modell hat ein vollständiges Chat-Template im GGUF (kv 44) das `<tool_call>` 
Tags nativ unterstützt. Bisher scheiterte Tool-Calling weil:
1. `bind_tools()` das falsche Format schickt (OpenAI statt Granite XML)
2. `tool.args_schema.schema()` wirft `AttributeError: 'dict' object has no attribute 'schema'`

**Fix für args_schema Fehler:**
```python
# Statt: one_tool.args_schema.schema()
# So:
schema = one_tool.args_schema.model_json_schema() if hasattr(one_tool.args_schema, 'model_json_schema') else dict(one_tool.args_schema)
```

**Nächster Test:**
```python
import asyncio, sys
sys.path.insert(0, '/home/claude/la/agents/server')
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from tool_formatter import format_tools_for_model, parse_tool_call_from_response

async def test():
    client = MultiServerMCPClient({
        "git": {"command": "python3",
                "args": ["-m", "mcp_server_git", "--repository", "/home/claude/la"],
                "transport": "stdio"}
    })
    all_tools = await client.get_tools()
    one_tool = next(t for t in all_tools if t.name == "git_log")
    
    # args_schema Fix
    try:
        schema = one_tool.args_schema.model_json_schema()
    except:
        schema = {"type": "object", "properties": {
            "repo_path": {"type": "string"},
            "max_count": {"type": "integer", "default": 5}
        }, "required": ["repo_path"]}
    
    tool_def = {"type": "function", "function": {
        "name": one_tool.name,
        "description": one_tool.description,
        "parameters": schema
    }}
    
    # Granite natives Format statt bind_tools()
    system_prompt = format_tools_for_model([tool_def], model_name="granite-tiny")
    
    llm = ChatOpenAI(base_url="http://127.0.0.1:8080/v1", api_key="not-needed",
                     model="granite", temperature=0, max_tokens=200)
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Show the last 3 git commits.")
    ])
    print(f"Antwort: {response.content}")
    
    parsed = parse_tool_call_from_response(response.content, model_family="granite")
    if parsed:
        print(f"✓ Tool-Call: {parsed}")
        result = await one_tool.ainvoke(parsed.get("arguments", {}))
        print(f"Ergebnis: {str(result)[:300]}")
    else:
        print("✗ Kein Tool-Call")

asyncio.run(test())
```

---

## 6. Geänderte Dateien (vs. Original Fork)

| Datei | Änderung |
|-------|---------|
| `agents/server/supervisor.py` | ChatOllama→ChatOpenAI, meeting disabled, Mac→janhet |
| `agents/server/code.py` | ChatOllama→ChatOpenAI auf Port 4000 |
| `agents/server/comms.py` | ChatOllama→ChatOpenAI auf Port 4000 |
| `agents/server/handoff.py` | ChatOllama→ChatOpenAI, Qdrant→chromadb |
| `agents/server/notes.py` | ChromaDB collection.query() statt Qdrant |
| `agents/server/researcher_v2.py` | metadata key fix (source, category) |
| `agents/server/server.py` | Phoenix init_phoenix() beim Start |
| `agents/server/config.py` | CHROMA_PATH statt Qdrant URL |
| `agents/server/telemetry.py` | **NEU** — Phoenix + LangChain (skip_dep_check=True!) |
| `agents/server/tool_formatter.py` | **NEU** — Generischer Tool Formatter (18/18 Tests) |
| `agents/server/tools.py` | get_tools_system_prompt() hinzugefügt |
| `agents/ingestion/ingest.py` | Qdrant→ChromaDB |
| `agents/ingestion/search.py` | ChromaDB, Filter-Fix |
| `agents/notes/recorder.py` | Disabled (kein Audio auf Server) |

---

## 7. Bekannte Fixes — NICHT VERGESSEN

**Fix 1: Phoenix skip_dep_check**
```python
# In telemetry.py — bereits eingebaut:
LangChainInstrumentor().instrument(tracer_provider=tracer_provider, skip_dep_check=True)
```

**Fix 2: headroom-ai statt headroom**
```bash
pip install "headroom-ai[proxy]"  # NICHT: pip install headroom
```

**Fix 3: mcp.json absoluter Pfad**
```json
{"mcpServers": {"git": {"args": ["-m", "mcp_server_git", "--repository", "/home/claude/la"]}}}
```

**Fix 4: args_schema AttributeError**
```python
# Statt: tool.args_schema.schema()
# So:    tool.args_schema.model_json_schema()
```

**Fix 5: llama-cpp-python Server Settings**
```python
# Kein ModelSettings — alles in Settings():
settings = Settings(model='...', host='127.0.0.1', port=8080, n_ctx=2048, ...)
```

---

## 8. Test-Ergebnisse Stand heute

| Test | Status |
|------|--------|
| llama-server (Granite 350m) | ✓ ~25 t/s |
| LiteLLM Proxy | ✓ |
| Phoenix Traces | ✓ skip_dep_check Fix |
| Agent Server | ✓ 6/6 Agenten |
| ChromaDB | ✓ |
| Headroom | ✓ installiert, 24 Requests |
| MCP git_log direkt | ✓ |
| MCP durch Agent | ✓ Tools laden |
| Tool-Calling 350m | ✓ Tool-Call generiert! args_schema via dict() Fix |
| Tool-Calling 4B (janhet) | ✓ bereits bestätigt |
| tool_formatter.py | ✓ 18/18 Tests |

---

## 9. Ports Übersicht

| Port | Dienst |
|------|--------|
| 8080 | llama-server (Reasoning) |
| 8081 | llama-server (Embedding, auf janhet) |
| 8787 | Headroom Proxy |
| 6006 | Arize Phoenix |
| 4000 | LiteLLM Gateway |
| 8002 | Agent Server (Chief-of-Staff) |

---

## 10. Nächste Schritte

1. ✓ ERLEDIGT: Tool-Calling 350m funktioniert mit nativem Granite Format
2. **Pfad-Fix**: Modell nutzt "." statt absolutem Pfad — System-Prompt anpassen
2. **Phoenix Spans** — richtigen API Endpoint finden für Trace-Inhalte
3. **Auf janhet deployen** — `git pull` + `pip install -r requirements-janhet.txt`
4. **Echte MCP Tests auf janhet** mit Granite-Tiny-4B
