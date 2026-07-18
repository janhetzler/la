"""
start_claude.py — Stack mit Claude API statt llama-server

Local Agent (LA) — Sandbox Edition

Startet: Phoenix, LiteLLM (-> Claude API), Agent Server
Fuehrt aus: vollstaendige 6-Agenten-Test-Suite

Kein llama-server noetig — LiteLLM routet direkt auf Anthropic API.
Die Sandbox hat impliziten Zugang zur Anthropic API ohne API Key.

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/start_claude.py

Logs: /tmp/logs/
"""
import threading, time, urllib.request, json, subprocess, sys, os
from datetime import datetime

CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma_la")
LITELLM_KEY = os.getenv("LITELLM_KEY", "sk-cos-local-dev")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
AGENT_URL    = "http://127.0.0.1:8002/v1/chat/completions"
PHOENIX_URL  = "http://127.0.0.1:6006"
LOG_DIR      = "/tmp/logs"
AUTH         = f"Bearer {LITELLM_KEY}"

os.makedirs(CHROMA_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../agents/server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../agents/ingestion"))

def wait_for(url, label, retries=40, headers=None):
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            if headers:
                for k, v in headers.items(): req.add_header(k, v)
            urllib.request.urlopen(req, timeout=2)
            print(f"{label} OK", flush=True); return True
        except: time.sleep(1); print(f"{i+1}...", end=" ", flush=True)
    print(f"{label} TIMEOUT", flush=True); return False

ERROR_PATTERNS = ["ERROR:", "Exception:", "Traceback", "CRITICAL"]

def check_log(log_file, label):
    if not os.path.exists(log_file):
        print(f"  [{label}] Log nicht gefunden", flush=True); return True
    with open(log_file) as f:
        lines = f.readlines()
    found = [l.strip()[:120] for l in lines if any(p in l for p in ERROR_PATTERNS)]
    if found:
        print(f"  [{label}] Fehler:", flush=True)
        for line in found[:3]: print(f"    {line}", flush=True)
        return False
    print(f"  [{label}] Log sauber ({len(lines)} Zeilen)", flush=True)
    return True

# 1. Phoenix
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = f"{PHOENIX_URL}/v1/traces"
os.environ["PHOENIX_CLIENT_HEADERS"]     = "api_key=not-needed"
phoenix_proc = subprocess.Popen(
    ["python3", "-m", "phoenix.server.main", "serve",
     "--host", "127.0.0.1", "--port", "6006"],
    stdout=open(os.path.join(LOG_DIR, "phoenix.log"), "w"),
    stderr=subprocess.STDOUT)
wait_for(f"{PHOENIX_URL}/v1/projects", "Phoenix")

# 2. LiteLLM mit Claude API
litellm_cfg = f"""
model_list:
  - model_name: claude-agent
    litellm_params:
      model: anthropic/{CLAUDE_MODEL}
      api_key: os.environ/ANTHROPIC_API_KEY
  - model_name: agent-local
    litellm_params:
      model: openai/agent-local
      api_base: http://127.0.0.1:8002/v1
      api_key: not-needed
general_settings:
  master_key: {LITELLM_KEY}
litellm_settings:
  drop_params: true
  set_verbose: false
  success_callback: ["arize_phoenix"]
  failure_callback: ["arize_phoenix"]
"""
with open("/tmp/litellm_claude.yaml", "w") as f: f.write(litellm_cfg)
litellm_proc = subprocess.Popen(
    ["litellm", "--config", "/tmp/litellm_claude.yaml",
     "--host", "127.0.0.1", "--port", "4000"],
    env=os.environ.copy(),
    stdout=open(os.path.join(LOG_DIR, "litellm.log"), "w"),
    stderr=subprocess.STDOUT)
wait_for("http://127.0.0.1:4000/health", "LiteLLM",
         headers={"Authorization": f"Bearer {LITELLM_KEY}"})

# Readiness-Check
print("Warte auf LiteLLM -> Claude API...", flush=True)
for i in range(20):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:4000/v1/chat/completions",
            data=json.dumps({
                "model": "claude-agent",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 5
            }).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {LITELLM_KEY}"},
            method="POST"
        )
        r = urllib.request.urlopen(req, timeout=30)
        resp = json.loads(r.read())
        print(f"LiteLLM -> Claude OK: {resp['choices'][0]['message']['content']}", flush=True)
        break
    except Exception as e:
        time.sleep(2); print(f"{i+1}({str(e)[:40]})...", end=" ", flush=True)

# 3. Agent Config + Phoenix Init
import config
config.LITELLM_URL = "http://127.0.0.1:4000"
config.LITELLM_KEY = LITELLM_KEY
config.DEFAULT_LLM = "claude-agent"
config.CHROMA_PATH = CHROMA_PATH
os.environ["OPENAI_API_KEY"] = LITELLM_KEY

try:
    from telemetry import init_phoenix
    init_phoenix()
    print("Phoenix Tracing OK", flush=True)
except Exception as e:
    print(f"Phoenix Tracing: {e}", flush=True)

# 4. Agent Server
import uvicorn
import server as agent_server

def run_agent():
    uvicorn.Server(uvicorn.Config(
        agent_server.app, host="127.0.0.1", port=8002,
        log_level="error")).run()

threading.Thread(target=run_agent, daemon=True).start()
wait_for("http://127.0.0.1:8002/health", "Agent Server")

# 5. Test Suite
print("\n=== STACK BEREIT - STARTE TEST SUITE (Claude API) ===\n", flush=True)
print(f"Modell: {CLAUDE_MODEL}", flush=True)
print(f"Start: {datetime.now().isoformat()}", flush=True)

results = []

def chat(frage, max_tokens=500):
    t0 = time.time()
    req = urllib.request.Request(
        AGENT_URL,
        data=json.dumps({
            "model": "agent-local",
            "messages": [{"role": "user", "content": frage}],
            "max_tokens": max_tokens
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": AUTH},
        method="POST"
    )
    try:
        r = urllib.request.urlopen(req, timeout=120)
        resp = json.loads(r.read())
        return resp["choices"][0]["message"]["content"], time.time()-t0, 200
    except Exception as e:
        return str(e), time.time()-t0, 0

def test_agent(name, frage, notes_check=False):
    print(f"\n{'='*55}", flush=True)
    print(f"TEST: {name}", flush=True)
    print(f"Frage: {frage[:70]}", flush=True)
    text, elapsed, status = chat(frage)
    print(f"Antwort ({elapsed:.1f}s): {text[:300]}", flush=True)
    ok = status == 200 and len(text.strip()) >= 10
    notes_ok = True
    if notes_check and ok:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            col = client.get_or_create_collection("notes")
            count = col.count()
            notes_ok = count > 0
            print(f"ChromaDB notes: {count} Dokumente", flush=True)
        except Exception as e:
            notes_ok = False
            print(f"ChromaDB Fehler: {e}", flush=True)
    overall = "OK" if (ok and notes_ok) else "FAIL"
    print(f"Ergebnis: {overall}", flush=True)
    results.append({"agent": name, "status": overall, "zeit": round(elapsed, 1)})

# Log-Check
print("\n=== LOG-CHECK ===", flush=True)
check_log(os.path.join(LOG_DIR, "litellm.log"), "LiteLLM")
check_log(os.path.join(LOG_DIR, "phoenix.log"), "Phoenix")

# Tests
test_agent("Supervisor Routing", "Can you help me?")
test_agent("Comms Agent", "Write a short professional email to the team about the project status.")
test_agent("Code Agent", "Write a Python function with type hints and docstring that sorts a list.")
test_agent("Researcher Agent", "What is LangGraph and how do multi-agent systems work with it?")
test_agent("Notes Agent", "Save this note: Local Agent runs on AMD EPYC, 4 vCores, 10GB RAM.", notes_check=True)
test_agent("Handoff Agent", "Prepare a prompt for Claude.ai: analyse local LLMs vs Cloud APIs.")

# Zusammenfassung
print(f"\n{'='*55}", flush=True)
print("ZUSAMMENFASSUNG", flush=True)
print(f"Ende: {datetime.now().isoformat()}", flush=True)
ok_count = sum(1 for r in results if r["status"] == "OK")
print(f"Tests: {ok_count}/{len(results)} OK", flush=True)
for r in results:
    icon = "OK" if r["status"] == "OK" else "FAIL"
    print(f"  {icon} {r['agent']} ({r['zeit']}s)", flush=True)

report = {"timestamp": datetime.now().isoformat(), "model": CLAUDE_MODEL,
          "results": results, "summary": {"total": len(results), "ok": ok_count}}
with open("/tmp/test_results_claude.json", "w") as f:
    json.dump(report, f, indent=2)
print("\nReport: /tmp/test_results_claude.json", flush=True)

for proc in [litellm_proc, phoenix_proc]:
    if proc: proc.terminate()
print("\nStack gestoppt.", flush=True)

# ------------------------------------------------------------
# NACH DEM TESTLAUF:
# docs/SANDBOX_2_TESTRESULTS.md aktualisieren mit Claude-Ergebnissen.
# Push via Python urllib + base64. Auf Go warten.
# ------------------------------------------------------------
