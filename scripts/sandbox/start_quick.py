"""
start_quick.py — schlanker Stack-Start für schnelle Checks.

Startet: llama-server + LiteLLM + Agent Server
KEIN Phoenix (spart ~20s Startzeit)
KEIN vollständiger 6-Agenten-Test (zu zeitaufwändig)

Führt aus:
  1. Import-Check (wie import_check.py)
  2. Stack starten (~45s)
  3. Einen gezielten Request: meta-Frage über LiteLLM → Agent Server
  4. Log-Check auf Fehler

Zeitbudget: ~90s gesamt — sicher innerhalb des bash_tool-Limits.

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/start_quick.py

Umgebungsvariablen:
  MODEL_PATH  (default: /tmp/granite-350m-Q4_K_M.gguf)
  CHROMA_PATH (default: /tmp/chroma_chief)
  LITELLM_KEY (default: sk-cos-local-dev)
"""
import threading, time, urllib.request, json, subprocess, sys, os

# ── Konfiguration ─────────────────────────────────────────────────
MODEL_PATH  = os.getenv("MODEL_PATH",  "/tmp/granite-350m-Q4_K_M.gguf")
CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma_chief")
LITELLM_KEY = os.getenv("LITELLM_KEY", "sk-cos-local-dev")
LOG_DIR     = "/tmp/logs"
REPO_ROOT   = os.path.join(os.path.dirname(__file__), "../..")

os.makedirs(CHROMA_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
sys.path.insert(0, os.path.join(REPO_ROOT, "agents/server"))
sys.path.insert(0, os.path.join(REPO_ROOT, "agents/ingestion"))

def wait_for(url, label, retries=25, headers=None):
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            if headers:
                for k, v in headers.items(): req.add_header(k, v)
            urllib.request.urlopen(req, timeout=2)
            print(f"{label} ✓", flush=True); return True
        except: time.sleep(1); print(f"{i+1}...", end=" ", flush=True)
    print(f"{label} TIMEOUT", flush=True); return False

def check_log(path, label):
    if not os.path.exists(path): return
    with open(path) as f: lines = f.readlines()
    bad = [l.strip() for l in lines if any(p in l for p in ["ERROR","Exception","Traceback","CRITICAL"])]
    if bad:
        print(f"  [{label}] ⚠️  {len(bad)} Fehler-Zeilen:", flush=True)
        for b in bad[:3]: print(f"    {b[:100]}", flush=True)
    else:
        print(f"  [{label}] Log sauber ({len(lines)} Zeilen)", flush=True)

# ── 0. Import-Check ───────────────────────────────────────────────
print("=== SCHRITT 0: Import-Check ===", flush=True)
errors = []
for mod in ["config","supervisor","server","telemetry","tool_formatter","tools"]:
    try:
        __import__(mod)
        print(f"  ✓ {mod}", flush=True)
    except Exception as e:
        print(f"  ✗ {mod}: {e}", flush=True)
        errors.append(mod)
if errors:
    print(f"ABBRUCH: {len(errors)} Import-Fehler", flush=True)
    sys.exit(1)

# VALID_AGENTS vs server AGENTS Diskrepanz
from supervisor import VALID_AGENTS
from server import AGENTS
only_reg = set(k.replace("agent-","") for k in AGENTS if k != "agent-local") - VALID_AGENTS
if only_reg:
    print(f"  ⚠️  In server.py aber nicht in VALID_AGENTS: {only_reg}", flush=True)

# ── 1. llama-server ───────────────────────────────────────────────
print("
=== SCHRITT 1: llama-server ===", flush=True)
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings
import uvicorn

settings = Settings(model=MODEL_PATH, host="127.0.0.1", port=8080,
                    n_ctx=2048, n_threads=1, chat_format="chatml")
threading.Thread(target=uvicorn.Server(uvicorn.Config(
    create_app(settings=settings), host="127.0.0.1", port=8080, log_level="error")).run,
    daemon=True).start()
if not wait_for("http://127.0.0.1:8080/v1/models", "llama-server"):
    sys.exit(1)

# ── 2. LiteLLM (kein Phoenix) ─────────────────────────────────────
print("
=== SCHRITT 2: LiteLLM ===", flush=True)
open("/tmp/litellm_quick.yaml", "w").write(f"""
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
""")
lp = subprocess.Popen(["litellm","--config","/tmp/litellm_quick.yaml",
    "--host","127.0.0.1","--port","4000"],
    stdout=open(os.path.join(LOG_DIR,"litellm.log"),"w"), stderr=subprocess.STDOUT)
if not wait_for("http://127.0.0.1:4000/health", "LiteLLM",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"}):
    lp.terminate(); sys.exit(1)

# Readiness-Check
print("Warte auf LiteLLM → llama-server...", flush=True)
for i in range(20):
    try:
        req = urllib.request.Request("http://127.0.0.1:4000/v1/chat/completions",
            data=json.dumps({"model":"granite-tiny","messages":[{"role":"user","content":"hi"}],"max_tokens":3}).encode(),
            headers={"Content-Type":"application/json","Authorization":f"Bearer {LITELLM_KEY}"}, method="POST")
        urllib.request.urlopen(req, timeout=30)
        print("LiteLLM→llama-server ✓", flush=True); break
    except: time.sleep(2); print(f"{i+1}...", end=" ", flush=True)

# ── 3. Agent Server ───────────────────────────────────────────────
print("
=== SCHRITT 3: Agent Server ===", flush=True)
import config
config.LITELLM_URL = "http://127.0.0.1:4000"
config.LITELLM_KEY = LITELLM_KEY
config.DEFAULT_LLM = "granite-tiny"
config.CHROMA_PATH = CHROMA_PATH
os.environ["OPENAI_API_KEY"] = LITELLM_KEY

import server as agent_server
threading.Thread(target=uvicorn.Server(uvicorn.Config(
    agent_server.app, host="127.0.0.1", port=8002, log_level="error")).run,
    daemon=True).start()
if not wait_for("http://127.0.0.1:8002/health", "Agent Server"):
    lp.terminate(); sys.exit(1)

# ── 4. Gezielter Test ─────────────────────────────────────────────
print("
=== SCHRITT 4: Test ===", flush=True)
t0 = time.time()
req = urllib.request.Request("http://127.0.0.1:4000/v1/chat/completions",
    data=json.dumps({"model":"agent-local",
        "messages":[{"role":"user","content":"Hi, what can you do?"}],
        "max_tokens":150}).encode(),
    headers={"Content-Type":"application/json","Authorization":f"Bearer {LITELLM_KEY}"},
    method="POST")
try:
    r = urllib.request.urlopen(req, timeout=120)
    resp = json.loads(r.read())
    text = resp["choices"][0]["message"]["content"]
    print(f"Antwort: {text[:200]}", flush=True)
    print(f"Zeit: {time.time()-t0:.1f}s", flush=True)
    print("Test ✓", flush=True)
except Exception as e:
    print(f"Test FEHLER: {e}", flush=True)

# ── 5. Log-Check ──────────────────────────────────────────────────
print("
=== SCHRITT 5: Log-Check ===", flush=True)
check_log(os.path.join(LOG_DIR, "litellm.log"), "LiteLLM")

lp.terminate()
print("
Stack gestoppt.", flush=True)
