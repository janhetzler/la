"""
inspect_phoenix.py — Laborversuch: Stack + 1 Request + Phoenix Trace Auswertung

Local Agent (LA) — Sandbox Edition

Ablauf:
  1. llama-server starten
  2. Phoenix starten
  3. LiteLLM starten
  4. Agent Server starten
  5. Einen einzelnen Request an Comms Agent
  6. Phoenix Traces via arize-phoenix-client auslesen

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/inspect_phoenix.py

Voraussetzung:
  - pip install arize-phoenix-client
  - Modelle unter /tmp/granite-350m-Q4_K_M.gguf
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

def wait_for(url, label, retries=40, headers=None):
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            if headers:
                for k, v in headers.items(): req.add_header(k, v)
            urllib.request.urlopen(req, timeout=2)
            print(f'{label} OK', flush=True); return True
        except: time.sleep(1); print(f'{i+1}...', end=' ', flush=True)
    print(f'{label} TIMEOUT', flush=True); return False

# 1. llama-server (Binary mit --jinja fuer natives Tool-Calling)
LLAMA_BIN = '/tmp/llama-b9895/llama-server'
LLAMA_LOG = os.path.join(LOG_DIR, 'llama-server.log')

llama_proc = subprocess.Popen(
    [LLAMA_BIN, '-m', MODEL_PATH,
     '--host', '127.0.0.1', '--port', '8080',
     '--jinja', '--ctx-size', '32768',
     '--parallel', '1', '--log-disable'],
    stdout=open(LLAMA_LOG, 'w'), stderr=subprocess.STDOUT
)
wait_for('http://127.0.0.1:8080/v1/models', 'llama-server')

# 2. Phoenix
os.environ['PHOENIX_COLLECTOR_ENDPOINT'] = f'{PHOENIX_URL}/v1/traces'
os.environ['PHOENIX_CLIENT_HEADERS']     = 'api_key=not-needed'
phoenix_proc = subprocess.Popen(
    ['python3', '-m', 'phoenix.server.main', 'serve',
     '--host', '127.0.0.1', '--port', '6006'],
    stdout=open(os.path.join(LOG_DIR, 'phoenix.log'), 'w'),
    stderr=subprocess.STDOUT)
# /v1/projects statt /healthz — zuverlaessigerer Readiness-Endpoint
wait_for(f'{PHOENIX_URL}/v1/projects', 'Phoenix')

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
import uvicorn
import server as agent_server

def run_agent():
    uvicorn.Server(uvicorn.Config(
        agent_server.app, host='127.0.0.1', port=8002,
        log_level='error')).run()

threading.Thread(target=run_agent, daemon=True).start()
wait_for('http://127.0.0.1:8002/health', 'Agent Server')

# 6. Einzelner Request
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
    print(f'Antwort ({time.time()-t0:.1f}s):\n{text}', flush=True)
except Exception as e:
    print(f'Fehler: {e}', flush=True)

# Warten auf Trace-Delivery
print('\nWarte 5s auf Trace-Delivery...', flush=True)
time.sleep(5)

# 7. Phoenix Traces via arize-phoenix-client
# Verifizierte API: https://arize.com/docs/phoenix/sdk-api-reference/python/arize-phoenix-client
# from phoenix.client import Client
# client = Client(base_url=PHOENIX_URL)
# spans_df = client.spans.get_spans_dataframe(project_identifier="local-agent", limit=100)
print('\n=== PHOENIX TRACES ===', flush=True)
try:
    from phoenix.client import Client
    from datetime import datetime, timedelta

    client = Client(base_url=PHOENIX_URL)

    # Spans der letzten 30 Minuten
    spans_df = client.spans.get_spans_dataframe(
        project_identifier="local-agent",
        limit=50,
        root_spans_only=True,
        start_time=datetime.now() - timedelta(minutes=5)
    )

    span_output = ""
    if spans_df is not None and not spans_df.empty:
        print(f'\n{len(spans_df)} Spans gefunden:\n', flush=True)

        # Relevante Spalten anzeigen
        cols = [c for c in [
            'name', 'span_kind',
            'attributes.input.value',
            'attributes.output.value',
            'attributes.llm.model_name',
            'attributes.llm.token_count.prompt',
            'attributes.llm.token_count.completion',
            'attributes.llm.prompts',
            'status_code', 'latency_ms'
        ] if c in spans_df.columns]

        for _, row in spans_df[cols].iterrows():
            span_header = f'\n--- {row.get("name", "?")} [{row.get("span_kind", "?")}] ---'
            print(span_header, flush=True)
            span_output += span_header + "\n"
            for col in cols:
                if col in ['name', 'span_kind']: continue
                val = row.get(col)
                if val and str(val) != 'nan':
                    label = col.replace('attributes.', '').replace('llm.', '')
                    line = f'  {label}: {str(val)[:2000]}'
                    print(line[:300], flush=True)
                    span_output += line + "\n"
    else:
        print('Keine Spans gefunden.', flush=True)
        span_output = "Keine Spans gefunden."

except ImportError as e:
    print(f'arize-phoenix-client Import Fehler: {e}', flush=True)
    print('pip install --break-system-packages arize-phoenix-client', flush=True)
except Exception as e:
    print(f'Phoenix Client Fehler: {e}', flush=True)
    import traceback
    traceback.print_exc()

# 8. Trace-Datei erzeugen
from pathlib import Path

slug = PROMPT[:40].lower()
slug = ''.join(c if c.isalnum() else '-' for c in slug).strip('-')
slug = '-'.join(filter(None, slug.split('-')))[:40]
date_str = datetime.now().strftime('%Y-%m-%d')
trace_dir = Path('/home/claude/la/docs/traces/sandbox')
trace_dir.mkdir(parents=True, exist_ok=True)
trace_path = trace_dir / f"{date_str}_{slug}.md"

# Prompt-Versionen auslesen
router_md = Path('/home/claude/la/prompts/agents/router.md')
router_version = router_md.read_text() if router_md.exists() else "nicht gefunden"

# Logs auslesen
def tail_log(path, chars=1000):
    p = Path(path)
    if p.exists():
        txt = p.read_text()
        return txt[-chars:] if len(txt) > chars else txt
    return "kein Log"

antwort = text if 'text' in dir() else 'kein Ergebnis'
dauer = f"{time.time()-t0:.1f}s"

trace_content = f"""# Trace — {date_str}

**Prompt:** {PROMPT}
**Gesamtdauer:** {dauer}
**Stack:** llama-server b9895 + --jinja | LiteLLM 1.92.0 | Agent Server :8002

---

## 1. Finale Antwort

```
{antwort}
```

---

## 2. Vollstaendige Span-Kette (Phoenix)

{span_output if 'span_output' in dir() else 'keine Spans'}

---

## 3. Aktive Prompt-Version (router.md)

```
{router_version}
```

---

## 4. Infrastruktur-Logs (letzte 1000 Zeichen)

### LiteLLM
```
{tail_log('/tmp/logs/litellm.log')}
```

### llama-server
```
{tail_log('/tmp/logs/llama-server.log')}
```

"""

trace_path.write_text(trace_content, encoding='utf-8')
print(f'\nTrace gespeichert: {trace_path}', flush=True)
print(f'Trace Groesse: {len(trace_content)} Zeichen', flush=True)

# Cleanup
for proc in [litellm_proc, phoenix_proc]:
    if proc: proc.terminate()
print('\nStack gestoppt.', flush=True)
