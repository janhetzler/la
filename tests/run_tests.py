"""
Chief-of-Staff janhet — Stack starten und Test Suite ausführen.
Startet llama-server, Headroom, Phoenix, LiteLLM und Agent Server,
dann führt test_stack.py aus.

Verwendung:
  python3 tests/run_tests.py

Voraussetzungen:
  - Granite GGUF Modell unter MODEL_PATH
  - pip install "headroom-ai[proxy]" arize-phoenix litellm
"""
import threading, time, urllib.request, json, subprocess, sys, os

# ── Konfiguration ────────────────────────────────────────────────
MODEL_PATH   = os.getenv("MODEL_PATH", "/tmp/granite-350m-Q4_K_M.gguf")
CHROMA_PATH  = os.getenv("CHROMA_PATH", "/tmp/chroma_chief")
LITELLM_KEY  = os.getenv("LITELLM_KEY", "sk-cos-local-dev")

os.makedirs(CHROMA_PATH, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../agents/server'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../agents/ingestion'))

def wait_for(url, label, retries=25, headers=None):
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            if headers:
                for k,v in headers.items(): req.add_header(k,v)
            urllib.request.urlopen(req, timeout=2)
            print(f'{label} ✓', flush=True); return True
        except: time.sleep(1); print(f'{i+1}...', end=' ', flush=True)
    print(f'{label} TIMEOUT', flush=True); return False

# ── 1. llama-server ──────────────────────────────────────────────
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings
import uvicorn

settings = Settings(model=MODEL_PATH, host='127.0.0.1', port=8080,
                    n_ctx=2048, n_threads=1, chat_format='chatml')
threading.Thread(target=uvicorn.Server(
    uvicorn.Config(create_app(settings=settings),
    host='127.0.0.1', port=8080, log_level='error')).run,
    daemon=True).start()
wait_for('http://127.0.0.1:8080/v1/models', 'llama-server')

# ── 2. Headroom Proxy ────────────────────────────────────────────
headroom_env = os.environ.copy()
headroom_env.update({'HEADROOM_TELEMETRY':'off',
                     'OPENAI_TARGET_API_URL':'http://127.0.0.1:8080/v1'})
headroom_proc = subprocess.Popen(
    ['headroom', 'proxy', '--host', '127.0.0.1', '--port', '8787', '--no-telemetry'],
    env=headroom_env,
    stdout=open('/tmp/headroom.log','w'), stderr=subprocess.STDOUT)
wait_for('http://127.0.0.1:8787/health', 'Headroom')

# ── 3. Phoenix ───────────────────────────────────────────────────
os.environ['PHOENIX_COLLECTOR_ENDPOINT'] = 'http://127.0.0.1:6006/v1/traces'
os.environ['PHOENIX_CLIENT_HEADERS']     = 'api_key=not-needed'
phoenix_proc = subprocess.Popen(
    ['python3', '-m', 'phoenix.server.main', 'serve',
     '--host', '127.0.0.1', '--port', '6006'],
    stdout=open('/tmp/phoenix.log','w'), stderr=subprocess.STDOUT)
wait_for('http://127.0.0.1:6006/healthz', 'Phoenix')

# ── 4. LiteLLM ───────────────────────────────────────────────────
litellm_cfg = """
model_list:
  - model_name: granite-tiny
    litellm_params:
      model: openai/granite
      api_base: http://127.0.0.1:8787/v1
      api_key: not-needed
general_settings:
  master_key: sk-cos-local-dev
litellm_settings:
  drop_params: true
  set_verbose: false
  success_callback: ["arize_phoenix"]
  failure_callback: ["arize_phoenix"]
"""
with open('/tmp/litellm_test.yaml','w') as f: f.write(litellm_cfg)
litellm_env = os.environ.copy()
litellm_proc = subprocess.Popen(
    ['litellm', '--config', '/tmp/litellm_test.yaml',
     '--host', '127.0.0.1', '--port', '4000'],
    env=litellm_env,
    stdout=open('/tmp/litellm.log','w'), stderr=subprocess.STDOUT)
wait_for('http://127.0.0.1:4000/health', 'LiteLLM',
         headers={'Authorization': f'Bearer {LITELLM_KEY}'})

# ── 5. Agent Config + Phoenix Init ───────────────────────────────
import config
config.LITELLM_URL  = 'http://127.0.0.1:4000'
config.LITELLM_KEY  = LITELLM_KEY
config.DEFAULT_LLM  = 'granite-tiny'
config.CHROMA_PATH  = CHROMA_PATH
os.environ['OPENAI_API_KEY'] = LITELLM_KEY

try:
    from telemetry import init_phoenix
    init_phoenix()
    print('Phoenix Tracing ✓', flush=True)
except Exception as e:
    print(f'Phoenix Tracing: {e}', flush=True)

# ── 6. Agent Server ──────────────────────────────────────────────
import server as agent_server
threading.Thread(target=uvicorn.Server(
    uvicorn.Config(agent_server.app, host='127.0.0.1',
    port=8002, log_level='error')).run,
    daemon=True).start()
wait_for('http://127.0.0.1:8002/health', 'Agent Server')

# ── 7. Test Suite ────────────────────────────────────────────────
print('\n=== STACK BEREIT — STARTE TEST SUITE ===\n', flush=True)
test_path = os.path.join(os.path.dirname(__file__), 'test_stack.py')
exec(open(test_path).read())

# ── 8. Cleanup ───────────────────────────────────────────────────
for proc in [litellm_proc, phoenix_proc, headroom_proc]:
    proc.terminate()
print('\nStack gestoppt.', flush=True)
