"""
inspect_phoenix.py — Laborversuch: Stack + 1 Request + Phoenix Trace Auswertung

Local Agent (LA) — Sandbox Edition

Ablauf:
  1. llama-server starten
  2. Phoenix starten
  3. LiteLLM starten
  4. Agent Server starten
  5. Einen einzelnen Request an Comms Agent
  6. Phoenix CLI (px) aufrufen und Trace ausgeben
  7. Fallback: Phoenix REST API wenn px nicht verfuegbar

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/inspect_phoenix.py

Voraussetzung:
  - Node.js verfuegbar fuer Phoenix CLI (optional)
  - Stack-Modelle unter /tmp/granite-350m-Q4_K_M.gguf
"""
import threading, time, urllib.request, json, subprocess, sys, os
from datetime import datetime

# Konfiguration
MODEL_PATH  = os.getenv("MODEL_PATH",  "/tmp/granite-350m-Q4_K_M.gguf")
CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma_la")
LITELLM_KEY = os.getenv("LITELLM_KEY", "sk-cos-local-dev")
LOG_DIR     = "/tmp/logs"
PHOENIX_URL = "http://127.0.0.1:6006"

os.makedirs(CHROMA_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../agents/server'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../agents/ingestion'))

def wait_for(url, label, retries=25, headers=None):
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            if headers:
                for k, v in headers.items(): req.add_header(k, v)
            urllib.request.urlopen(req, timeout=2)
            print(f'{label} OK', flush=True); return True
        except: time.sleep(1); print(f'{i+1}...', end=' ', flush=True)
    print(f'{label} TIMEOUT', flush=True); return False

# 1. llama-server
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings
import uvicorn

settings = Settings(model=MODEL_PATH, host='127.0.0.1', port=8080,
                    n_ctx=2048, n_threads=1, chat_format='chatml')

def run_llama():
    uvicorn.Server(uvicorn.Config(
        create_app(settings=settings),
        host='127.0.0.1', port=8080, log_level='error')).run()

threading.Thread(target=run_llama, daemon=True).start()
wait_for('http://127.0.0.1:8080/v1/models', 'llama-server')

# 2. Phoenix
os.environ['PHOENIX_COLLECTOR_ENDPOINT'] = f'{PHOENIX_URL}/v1/traces'
os.environ['PHOENIX_CLIENT_HEADERS']     = 'api_key=not-needed'
phoenix_proc = subprocess.Popen(
    ['python3', '-m', 'phoenix.server.main', 'serve',
     '--host', '127.0.0.1', '--port', '6006'],
    stdout=open(os.path.join(LOG_DIR, 'phoenix.log'), 'w'),
    stderr=subprocess.STDOUT)
wait_for(f'{PHOENIX_URL}/healthz', 'Phoenix')

# 3. LiteLLM
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
litellm_settings:
  drop_params: true
  set_verbose: false
  success_callback: ["arize_phoenix"]
  failure_callback: ["arize_phoenix"]
"""
with open('/tmp/litellm_phoenix.yaml', 'w') as f: f.write(litellm_cfg)
litellm_proc = subprocess.Popen(
    ['litellm', '--config', '/tmp/litellm_phoenix.yaml',
     '--host', '127.0.0.1', '--port', '4000'],
    env=os.environ.copy(),
    stdout=open(os.path.join(LOG_DIR, 'litellm.log'), 'w'),
    stderr=subprocess.STDOUT)
wait_for('http://127.0.0.1:4000/health', 'LiteLLM',
         headers={'Authorization': f'Bearer {LITELLM_KEY}'})

# Readiness-Check
for i in range(20):
    try:
        req = urllib.request.Request('http://127.0.0.1:4000/v1/chat/completions',
            data=json.dumps({'model':'granite-tiny',
                'messages':[{'role':'user','content':'hi'}],'max_tokens':3}).encode(),
            headers={'Content-Type':'application/json',
                     'Authorization':f'Bearer {LITELLM_KEY}'}, method='POST')
        urllib.request.urlopen(req, timeout=30)
        print('LiteLLM -> llama-server OK', flush=True); break
    except: time.sleep(2); print(f'{i+1}...', end=' ', flush=True)

# 4. Agent Config + Phoenix Init
import config
config.LITELLM_URL = 'http://127.0.0.1:4000'
config.LITELLM_KEY = LITELLM_KEY
config.DEFAULT_LLM = 'granite-tiny'
config.CHROMA_PATH = CHROMA_PATH
os.environ['OPENAI_API_KEY'] = LITELLM_KEY

try:
    from telemetry import init_phoenix
    init_phoenix()
    print('Phoenix Tracing OK', flush=True)
except Exception as e:
    print(f'Phoenix Tracing: {e}', flush=True)

# 5. Agent Server
import server as agent_server

def run_agent():
    uvicorn.Server(uvicorn.Config(
        agent_server.app, host='127.0.0.1', port=8002,
        log_level='error')).run()

threading.Thread(target=run_agent, daemon=True).start()
wait_for('http://127.0.0.1:8002/health', 'Agent Server')

# 6. Einzelner Request — Comms Agent
print('\n=== REQUEST ===', flush=True)
PROMPT = "Write a short professional email to the team about the project status."
print(f'Prompt: {PROMPT}', flush=True)

t0 = time.time()
req = urllib.request.Request('http://127.0.0.1:8002/v1/chat/completions',
    data=json.dumps({'model':'agent-local',
        'messages':[{'role':'user','content':PROMPT}],
        'max_tokens':300}).encode(),
    headers={'Content-Type':'application/json',
             'Authorization':f'Bearer {LITELLM_KEY}'}, method='POST')
try:
    r = urllib.request.urlopen(req, timeout=120)
    resp = json.loads(r.read())
    text = resp['choices'][0]['message']['content']
    print(f'Antwort ({time.time()-t0:.1f}s): {text[:300]}', flush=True)
except Exception as e:
    print(f'Fehler: {e}', flush=True)

# Kurz warten damit Traces bei Phoenix ankommen
print('\nWarte 3s auf Trace-Delivery...', flush=True)
time.sleep(3)

# 7. Phoenix Traces auslesen
print('\n=== PHOENIX TRACES ===', flush=True)

# Versuch 1: Phoenix CLI (px)
px_available = False
try:
    result = subprocess.run(['which', 'px'], capture_output=True, text=True)
    px_available = result.returncode == 0
except: pass

if px_available:
    print('Phoenix CLI verfuegbar — px trace list:', flush=True)
    os.environ['PHOENIX_HOST'] = PHOENIX_URL
    os.environ['PHOENIX_PROJECT'] = 'local-agent'
    result = subprocess.run(
        ['px', 'trace', 'list', '--limit', '5', '--format', 'raw'],
        capture_output=True, text=True, env=os.environ.copy()
    )
    print(result.stdout[:3000], flush=True)
    if result.stderr:
        print('STDERR:', result.stderr[:500], flush=True)
else:
    print('Phoenix CLI nicht verfuegbar — nutze REST API', flush=True)

    # Versuch 2: REST API
    try:
        # Projekte auflisten
        req = urllib.request.Request(f'{PHOENIX_URL}/v1/projects')
        r = urllib.request.urlopen(req, timeout=10)
        projects = json.loads(r.read())
        print(f'Projekte: {json.dumps(projects, indent=2)[:500]}', flush=True)

        # Spans des ersten Projekts
        if projects.get('data'):
            project_id = projects['data'][0]['id']
            req = urllib.request.Request(
                f'{PHOENIX_URL}/v1/projects/{project_id}/spans?limit=10'
            )
            r = urllib.request.urlopen(req, timeout=10)
            spans = json.loads(r.read())
            print(f'\nSpans ({len(spans.get("data",[]))} gefunden):', flush=True)
            for span in spans.get('data', [])[:5]:
                print(f'\n--- Span: {span.get("name")} ---', flush=True)
                attrs = span.get('attributes', {})
                # Die wichtigen Felder
                for key in ['input.value', 'output.value', 'llm.model_name',
                            'llm.token_count.prompt', 'llm.token_count.completion',
                            'tool.name', 'llm.prompts']:
                    if key in attrs:
                        val = str(attrs[key])[:200]
                        print(f'  {key}: {val}', flush=True)
    except Exception as e:
        print(f'REST API Fehler: {e}', flush=True)

# Cleanup
for proc in [litellm_proc, phoenix_proc]:
    if proc: proc.terminate()
print('\nStack gestoppt.', flush=True)
