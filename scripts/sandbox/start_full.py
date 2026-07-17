"""
start_full.py — Vollständiger Stack-Start + kompletter Agenten-Testlauf.

Local Agent (LA) — Sandbox Edition

Startet: llama-server, Phoenix, LiteLLM, Agent Server
Führt aus: vollständige 6-Agenten-Test-Suite + ChromaDB + Log-Checks

Zeitbudget: ~3 Minuten — knapp innerhalb des bash_tool-Limits.

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/start_full.py

Umgebungsvariablen:
  MODEL_PATH  (default: /tmp/granite-350m-Q4_K_M.gguf)
  CHROMA_PATH (default: /tmp/chroma_la)
  LITELLM_KEY (default: sk-local-dev)

Logs: /tmp/logs/
"""
import threading, time, urllib.request, json, subprocess, sys, os, logging
from datetime import datetime

# ── Konfiguration ────────────────────────────────────────────────
MODEL_PATH  = os.getenv("MODEL_PATH",  "/tmp/granite-350m-Q4_K_M.gguf")
CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma_la")
LITELLM_KEY = os.getenv("LITELLM_KEY", "sk-local-dev")
AGENT_URL   = "http://127.0.0.1:8002/v1/chat/completions"
PHOENIX_URL = "http://127.0.0.1:6006"
AUTH        = f"Bearer {LITELLM_KEY}"
LOG_DIR     = "/tmp/logs"

os.makedirs(CHROMA_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../agents/server'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../agents/ingestion'))

# ── Hilfsfunktionen ──────────────────────────────────────────────
def wait_for(url, label, retries=25, headers=None):
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            if headers:
                for k, v in headers.items(): req.add_header(k, v)
            urllib.request.urlopen(req, timeout=2)
            print(f'{label} ✓', flush=True); return True
        except: time.sleep(1); print(f'{i+1}...', end=' ', flush=True)
    print(f'{label} TIMEOUT', flush=True); return False

ERROR_PATTERNS = ["ERROR:", "Exception:", "Traceback", "CRITICAL"]

def check_log(log_file, label):
    if not os.path.exists(log_file):
        print(f'  [{label}] Log nicht gefunden', flush=True); return True
    with open(log_file) as f:
        lines = f.readlines()
    found = [l.strip()[:120] for l in lines if any(p in l for p in ERROR_PATTERNS)]
    if found:
        print(f'  [{label}] ⚠️  Fehler:', flush=True)
        for f in found[:5]: print(f'    {f}', flush=True)
        return False
    print(f'  [{label}] Log sauber ✓ ({len(lines)} Zeilen)', flush=True)
    return True

# ── 1. llama-server ──────────────────────────────────────────────
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings
import uvicorn

LLAMA_LOG = os.path.join(LOG_DIR, "llama-server.log")
settings = Settings(model=MODEL_PATH, host='127.0.0.1', port=8080,
                    n_ctx=2048, n_threads=1, chat_format='chatml')

def run_llama_server():
    log_config = uvicorn.config.LOGGING_CONFIG.copy()
    log_config["handlers"]["file"] = {"class": "logging.FileHandler",
        "filename": LLAMA_LOG, "formatter": "default"}
    log_config["loggers"]["uvicorn"]["handlers"] = ["file"]
    log_config["loggers"]["uvicorn.error"]["handlers"] = ["file"]
    uvicorn.Server(uvicorn.Config(create_app(settings=settings),
        host='127.0.0.1', port=8080, log_level='error',
        log_config=log_config)).run()

threading.Thread(target=run_llama_server, daemon=True).start()
wait_for('http://127.0.0.1:8080/v1/models', 'llama-server')

# ── 2. Phoenix ───────────────────────────────────────────────────
os.environ['PHOENIX_COLLECTOR_ENDPOINT'] = 'http://127.0.0.1:6006/v1/traces'
os.environ['PHOENIX_CLIENT_HEADERS']     = 'api_key=not-needed'
phoenix_proc = subprocess.Popen(
    ['python3', '-m', 'phoenix.server.main', 'serve', '--host', '127.0.0.1', '--port', '6006'],
    stdout=open(os.path.join(LOG_DIR, 'phoenix.log'), 'w'), stderr=subprocess.STDOUT)
wait_for('http://127.0.0.1:6006/healthz', 'Phoenix')

# ── 3. LiteLLM ───────────────────────────────────────────────────
litellm_cfg = f"""
model_list:
  - model_name: granite-tiny
    litellm_params:
      model: openai/granite
      api_base: http://127.0.0.1:8080/v1
      api_key: not-needed
  - model_name: agent-local
    litellm_params:
      model: openai/agent-local
      api_base: http://127.0.0.1:8002/v1
      api_key: not-needed
general_settings:
  master_key: {LITELLM_KEY}
  database_url: "sqlite:////tmp/litellm.db"
litellm_settings:
  drop_params: true
  set_verbose: false
  success_callback: ["arize_phoenix"]
  failure_callback: ["arize_phoenix"]
"""
with open('/tmp/litellm_sandbox.yaml', 'w') as f: f.write(litellm_cfg)
litellm_proc = subprocess.Popen(
    ['litellm', '--config', '/tmp/litellm_sandbox.yaml', '--host', '127.0.0.1', '--port', '4000'],
    env=os.environ.copy(),
    stdout=open(os.path.join(LOG_DIR, 'litellm.log'), 'w'), stderr=subprocess.STDOUT)
wait_for('http://127.0.0.1:4000/health', 'LiteLLM',
         headers={'Authorization': f'Bearer {LITELLM_KEY}'})

# Echter Readiness-Check
print('Warte auf LiteLLM → llama-server...', flush=True)
for i in range(30):
    try:
        req = urllib.request.Request('http://127.0.0.1:4000/v1/chat/completions',
            data=json.dumps({'model':'granite-tiny',
                'messages':[{'role':'user','content':'hi'}],'max_tokens':3}).encode(),
            headers={'Content-Type':'application/json','Authorization':f'Bearer {LITELLM_KEY}'},
            method='POST')
        urllib.request.urlopen(req, timeout=30)
        print('LiteLLM → llama-server ✓', flush=True); break
    except: time.sleep(2); print(f'{i+1}...', end=' ', flush=True)

# ── 4. Agent Config + Phoenix Init ───────────────────────────────
import config
config.LITELLM_URL = 'http://127.0.0.1:4000'
config.LITELLM_KEY = LITELLM_KEY
config.DEFAULT_LLM = 'granite-tiny'
config.CHROMA_PATH = CHROMA_PATH
os.environ['OPENAI_API_KEY'] = LITELLM_KEY

try:
    from telemetry import init_phoenix
    init_phoenix()
    print('Phoenix Tracing ✓', flush=True)
except Exception as e:
    print(f'Phoenix Tracing: {e}', flush=True)

# ── 5. Agent Server ───────────────────────────────────────────────
AGENT_LOG = os.path.join(LOG_DIR, "agent-server.log")
import server as agent_server

def run_agent_server():
    log_config = uvicorn.config.LOGGING_CONFIG.copy()
    log_config["handlers"]["file"] = {"class": "logging.FileHandler",
        "filename": AGENT_LOG, "formatter": "default"}
    log_config["loggers"]["uvicorn"]["handlers"] = ["file"]
    log_config["loggers"]["uvicorn.error"]["handlers"] = ["file"]
    uvicorn.Server(uvicorn.Config(agent_server.app,
        host='127.0.0.1', port=8002, log_level='error',
        log_config=log_config)).run()

threading.Thread(target=run_agent_server, daemon=True).start()
wait_for('http://127.0.0.1:8002/health', 'Agent Server')

# ── 6. Test Suite ────────────────────────────────────────────────
print(f'
=== STACK BEREIT — STARTE TEST SUITE ===
', flush=True)
print(f'Start: {datetime.now().isoformat()}', flush=True)

results = []

def api_call(url, data=None, method="GET"):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", AUTH)
    if data:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return json.loads(r.read()), r.status
    except Exception as e:
        return {"error": str(e)}, 0

def chat(frage, max_tokens=300):
    t0 = time.time()
    resp, status = api_call(AGENT_URL,
        data={"model": "agent-local",
              "messages": [{"role": "user", "content": frage}],
              "max_tokens": max_tokens}, method="POST")
    elapsed = time.time() - t0
    if "choices" in resp:
        text = resp["choices"][0]["message"]["content"]
        return text, elapsed, status
    return str(resp), elapsed, status

def validate_response(text, min_length=10):
    if not text or text.strip() == "": return False, "Antwort leer"
    if len(text.strip()) < min_length: return False, f"Zu kurz ({len(text.strip())} Zeichen)"
    if text.strip().startswith("{") and "error" in text.lower(): return False, "Fehler-JSON"
    return True, f"OK ({len(text.strip())} Zeichen)"

def test_agent(name, frage, beschreibung, notes_check=False):
    print(f'
{"="*55}', flush=True)
    print(f'TEST: {name}', flush=True)
    print(f'Frage: {frage[:70]}', flush=True)
    text, elapsed, status = chat(frage)
    print(f'Antwort: {text[:200]}', flush=True)
    print(f'Zeit: {elapsed:.1f}s | HTTP: {status}', flush=True)
    content_ok, content_reason = validate_response(text)
    notes_ok, notes_reason = True, "nicht geprüft"
    if notes_check and content_ok:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            col = client.get_or_create_collection('notes')
            count = col.count()
            notes_ok = count > 0
            notes_reason = f"ChromaDB 'notes': {count} Dokumente"
        except Exception as e:
            notes_ok = False
            notes_reason = f"ChromaDB Fehler: {e}"
        print(f'ChromaDB: {notes_reason}', flush=True)
    overall_ok = (status == 200) and content_ok and (notes_ok if notes_check else True)
    status_str = "OK" if overall_ok else "FAIL"
    reasons = [content_reason]
    if notes_check: reasons.append(notes_reason)
    print(f'Ergebnis: {status_str} — {" | ".join(reasons)}', flush=True)
    check_log(AGENT_LOG, f"Agent Server nach {name}")
    results.append({"agent": name, "frage": frage[:60], "zeit": round(elapsed, 1),
                    "status": status_str, "http": status, "reason": ' | '.join(reasons)})

# Log-Check nach Service-Start
print("=== LOG-CHECK NACH SERVICE-START ===", flush=True)
check_log(os.path.join(LOG_DIR, "llama-server.log"), "llama-server")
check_log(os.path.join(LOG_DIR, "litellm.log"),      "LiteLLM")
check_log(os.path.join(LOG_DIR, "phoenix.log"),      "Phoenix")
check_log(os.path.join(LOG_DIR, "agent-server.log"), "Agent Server")

# Agenten-Tests
test_agent("Supervisor Routing",
    "Can you help me?",
    "Supervisor empfängt + routet + antwortet")

test_agent("Comms Agent",
    "Write a short professional email to the team about the project status.",
    "Supervisor → Comms → Generierung → Antwort")

test_agent("Code Agent",
    "Write a Python function with type hints and docstring that sorts a list.",
    "Supervisor → Code → Generierung → Antwort")

test_agent("Researcher Agent",
    "What is LangGraph and how do multi-agent systems work with it?",
    "Supervisor → Researcher → ChromaDB → Antwort")

test_agent("Notes Agent",
    "Save this note: Local Agent runs on AMD EPYC, 4 vCores, 10GB RAM.",
    "Supervisor → Notes → ChromaDB Schreiben → Bestätigung",
    notes_check=True)

test_agent("Handoff Agent",
    "Prepare a prompt for Claude.ai: analyse local LLMs vs Cloud APIs.",
    "Supervisor → Handoff → Prompt → Antwort")

# ChromaDB Status
print(f'
{"="*55}', flush=True)
print("CHROMADB STATUS", flush=True)
try:
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    for col in client.list_collections():
        c = client.get_collection(col.name)
        print(f"  Collection '{col.name}': {c.count()} Dokumente", flush=True)
except Exception as e:
    print(f"  ChromaDB Fehler: {e}", flush=True)

# Finaler Log-Check
print(f'
{"="*55}', flush=True)
print("FINALER LOG-CHECK", flush=True)
for label, fname in [("llama-server","llama-server.log"),("LiteLLM","litellm.log"),
                     ("Phoenix","phoenix.log"),("Agent Server","agent-server.log")]:
    check_log(os.path.join(LOG_DIR, fname), label)

# Zusammenfassung
print(f'
{"="*55}', flush=True)
print("ZUSAMMENFASSUNG", flush=True)
print(f'Ende: {datetime.now().isoformat()}', flush=True)
ok = sum(1 for r in results if r["status"] == "OK")
print(f'Tests: {ok}/{len(results)} OK', flush=True)
for r in results:
    icon = "✓" if r["status"] == "OK" else "✗"
    print(f'  {icon} {r["agent"]}: {r["reason"]}', flush=True)

report = {"timestamp": datetime.now().isoformat(), "results": results,
          "summary": {"total": len(results), "ok": ok}}
with open('/tmp/test_results.json', 'w') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f'
Report: /tmp/test_results.json', flush=True)

# Cleanup
for proc in [litellm_proc, phoenix_proc]:
    if proc: proc.terminate()
print('
Stack gestoppt.', flush=True)
