"""
test_mcp_toolcall.py — Gezielter MCP Tool-Call Test

Testet ob das 350m Modell selbst einen Tool-Call produziert
wenn es den nativen Granite XML-Format Prompt bekommt.

Ablauf:
  1. llama-server starten
  2. MCP Tools laden (git_log, git_status, fetch)
  3. Tool-Definitionen via tool_formatter.py ins Granite XML-Format
  4. Request ans Modell mit Tool-Prompt
  5. Antwort parsen — hat das Modell <tool_call> produziert?
  6. Falls ja: Tool aufrufen und Ergebnis zeigen
  7. Phoenix Trace auslesen

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/test_mcp_toolcall.py
"""
import threading, time, urllib.request, json, subprocess, sys, os, asyncio
from datetime import datetime, timedelta

MODEL_PATH = os.getenv("MODEL_PATH", "/tmp/granite-350m-Q4_K_M.gguf")
LITELLM_KEY = os.getenv("LITELLM_KEY", "sk-cos-local-dev")
PHOENIX_URL = "http://127.0.0.1:6006"
LOG_DIR = "/tmp/logs"

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

# 1. llama-server
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings
import uvicorn

settings = Settings(model=MODEL_PATH, host="127.0.0.1", port=8080,
                    n_ctx=2048, n_threads=1, chat_format="chatml")

def run_llama():
    uvicorn.Server(uvicorn.Config(
        create_app(settings=settings),
        host="127.0.0.1", port=8080, log_level="error")).run()

threading.Thread(target=run_llama, daemon=True).start()
wait_for("http://127.0.0.1:8080/v1/models", "llama-server")

# 2. Phoenix
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = f"{PHOENIX_URL}/v1/traces"
os.environ["PHOENIX_CLIENT_HEADERS"] = "api_key=not-needed"
phoenix_proc = subprocess.Popen(
    ["python3", "-m", "phoenix.server.main", "serve",
     "--host", "127.0.0.1", "--port", "6006"],
    stdout=open(os.path.join(LOG_DIR, "phoenix.log"), "w"),
    stderr=subprocess.STDOUT)
wait_for(f"{PHOENIX_URL}/v1/projects", "Phoenix")

# 3. MCP Tools laden
print("\n=== MCP TOOLS LADEN ===", flush=True)

async def load_tools():
    from langchain_mcp_adapters.client import MultiServerMCPClient
    client = MultiServerMCPClient({
        "git": {
            "command": "python3",
            "args": ["-m", "mcp_server_git", "--repository", "/home/claude/la"],
            "transport": "stdio",
        },
        "fetch": {
            "command": "python3",
            "args": ["-m", "mcp_server_fetch"],
            "transport": "stdio",
        }
    })
    tools = await client.get_tools()
    print(f"{len(tools)} Tools geladen:", flush=True)
    for t in tools:
        print(f"  - {t.name}", flush=True)
    return tools, client

tools, mcp_client = asyncio.run(load_tools())

# Nur relevante Tools fuer den Test
TARGET_TOOLS = ["git_log", "git_status", "fetch"]
selected_tools = [t for t in tools if t.name in TARGET_TOOLS]
print(f"\nGewaehlte Tools fuer Test: {[t.name for t in selected_tools]}", flush=True)

# 4. Tool-Definitionen ins Granite XML-Format
from tool_formatter import format_tools_for_model, parse_tool_call_from_response

# Tools als OpenAI-Format Dicts
tool_defs = []
for t in selected_tools:
    tool_defs.append({
        "name": t.name,
        "description": t.description,
        "parameters": dict(t.args_schema) if hasattr(t, "args_schema") else {}
    })

system_prompt = format_tools_for_model(tool_defs, model_name="granite-tiny")
print(f"\nSystem-Prompt ({len(system_prompt)} Zeichen):", flush=True)
print(system_prompt[:500], flush=True)

# 5. Request ans Modell
print("\n=== MODELL REQUEST ===", flush=True)
USER_PROMPT = "What are the last 3 commits in this repository?"
print(f"User: {USER_PROMPT}", flush=True)

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": USER_PROMPT}
]

t0 = time.time()
req = urllib.request.Request(
    "http://127.0.0.1:8080/v1/chat/completions",
    data=json.dumps({
        "messages": messages,
        "max_tokens": 300,
        "temperature": 0
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    r = urllib.request.urlopen(req, timeout=120)
    resp = json.loads(r.read())
    model_answer = resp["choices"][0]["message"]["content"]
    print(f"\nModell-Antwort ({time.time()-t0:.1f}s):", flush=True)
    print(model_answer, flush=True)
except Exception as e:
    print(f"Fehler: {e}", flush=True)
    model_answer = ""

# 6. Tool-Call parsen
print("\n=== TOOL-CALL ANALYSE ===", flush=True)
tool_call = parse_tool_call_from_response(model_answer, model_family="granite")

if tool_call:
    print(f"Tool-Call erkannt:", flush=True)
    print(f"  Name: {tool_call.get('name')}", flush=True)
    print(f"  Arguments: {json.dumps(tool_call.get('arguments', {}), indent=2)}", flush=True)

    # Tool aufrufen
    tool_name = tool_call.get("name")
    tool_args = tool_call.get("arguments", {})
    matched_tool = next((t for t in selected_tools if t.name == tool_name), None)

    if matched_tool:
        print(f"\nFuehre {tool_name} aus...", flush=True)
        try:
            result = asyncio.run(matched_tool.ainvoke(tool_args))
            print(f"Tool-Ergebnis:", flush=True)
            print(str(result)[:800], flush=True)
        except Exception as e:
            print(f"Tool-Ausfuehrung Fehler: {e}", flush=True)
    else:
        print(f"Tool {tool_name} nicht gefunden.", flush=True)
else:
    print("Kein <tool_call> in der Antwort gefunden.", flush=True)
    print("Das Modell hat den Tool-Call nicht produziert.", flush=True)

# 7. Phoenix Trace
print("\nWarte 3s auf Trace-Delivery...", flush=True)
time.sleep(3)

print("\n=== PHOENIX TRACE ===", flush=True)
try:
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_URL)
    spans_df = client.spans.get_spans_dataframe(
        project_identifier="local-agent",
        limit=10,
        root_spans_only=False,
        start_time=datetime.now() - timedelta(minutes=5)
    )
    if spans_df is not None and not spans_df.empty:
        print(f"{len(spans_df)} Spans:", flush=True)
        cols = [c for c in [
            "name", "span_kind",
            "attributes.input.value",
            "attributes.output.value",
            "attributes.llm.token_count.prompt",
            "attributes.llm.token_count.completion",
        ] if c in spans_df.columns]
        for _, row in spans_df[cols].iterrows():
            print(f"\n--- {row.get('name','?')} ---", flush=True)
            for col in cols:
                if col in ["name", "span_kind"]: continue
                val = row.get(col)
                if val and str(val) != "nan":
                    print(f"  {col.replace('attributes.','')}: {str(val)[:200]}", flush=True)
    else:
        print("Keine Spans.", flush=True)
except Exception as e:
    print(f"Phoenix Fehler: {e}", flush=True)

phoenix_proc.terminate()
print("\nFertig.", flush=True)
