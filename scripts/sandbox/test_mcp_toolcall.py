"""
test_mcp_toolcall.py — MCP Tool-Call Test mit LangChain + Phoenix Tracing

Testet ob das 350m Modell selbst einen Tool-Call produziert.
Request laeuft durch LangChain damit Phoenix Spans erfasst werden.

Ablauf:
  1. llama-server starten
  2. Phoenix starten + LangChain Instrumentierung
  3. MCP Tools laden
  4. Tool-Definitionen via tool_formatter.py ins Granite XML-Format
  5. Request via LangChain ChatOpenAI — Phoenix erfasst Span
  6. Antwort parsen: <tool_call> gefunden?
  7. Falls ja: Tool aufrufen
  8. Phoenix Spans auslesen

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/test_mcp_toolcall.py
"""
import threading, time, urllib.request, json, subprocess, sys, os, asyncio
from datetime import datetime, timedelta

MODEL_PATH  = os.getenv("MODEL_PATH",  "/tmp/granite-350m-Q4_K_M.gguf")
LITELLM_KEY = os.getenv("LITELLM_KEY", "sk-cos-local-dev")
PHOENIX_URL = "http://127.0.0.1:6006"
LOG_DIR     = "/tmp/logs"

os.makedirs(LOG_DIR, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../agents/server"))

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
LLAMA_BIN = '/tmp/llama-b9895/llama-server'
llama_proc = subprocess.Popen(
    [LLAMA_BIN, '-m', MODEL_PATH,
     '--host', '127.0.0.1', '--port', '8080',
     '--jinja', '--ctx-size', '32768',
     '--parallel', '1', '--log-disable'],
    stdout=open('/tmp/logs/llama-server.log', 'w'), stderr=subprocess.STDOUT
)
threading.Thread(target=run_llama, daemon=True).start()
wait_for("http://127.0.0.1:8080/v1/models", "llama-server")

# 2. Phoenix + LangChain Instrumentierung
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = f"{PHOENIX_URL}/v1/traces"
os.environ["PHOENIX_CLIENT_HEADERS"]     = "api_key=not-needed"
phoenix_proc = subprocess.Popen(
    ["python3", "-m", "phoenix.server.main", "serve",
     "--host", "127.0.0.1", "--port", "6006"],
    stdout=open(os.path.join(LOG_DIR, "phoenix.log"), "w"),
    stderr=subprocess.STDOUT)
wait_for(f"{PHOENIX_URL}/v1/projects", "Phoenix")

# LangChain Instrumentierung initialisieren
try:
    from telemetry import init_phoenix
    init_phoenix()
    print("Phoenix Tracing OK", flush=True)
except Exception as e:
    print(f"Phoenix Tracing: {e}", flush=True)

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

TARGET_TOOLS = ["git_log", "git_status", "fetch"]
selected_tools = [t for t in tools if t.name in TARGET_TOOLS]
print(f"Gewaehlte Tools: {[t.name for t in selected_tools]}", flush=True)

# 4. Tool-Definitionen ins Granite XML-Format
from tool_formatter import format_tools_for_model, parse_tool_call_from_response

tool_defs = []
for t in selected_tools:
    schema = {}
    if hasattr(t, "args_schema") and t.args_schema:
        try:
            schema = t.args_schema.schema() if hasattr(t.args_schema, "schema") else dict(t.args_schema)
        except: pass
    tool_defs.append({
        "name": t.name,
        "description": t.description,
        "parameters": schema
    })

system_prompt = format_tools_for_model(tool_defs, model_name="granite-tiny")
print(f"\nSystem-Prompt ({len(system_prompt)} Zeichen):", flush=True)
print(system_prompt[:600], flush=True)

# 5. Request via LangChain ChatOpenAI
print("\n=== LANGCHAIN REQUEST ===", flush=True)
USER_PROMPT = "What are the last 3 commits in this repository?"
print(f"User: {USER_PROMPT}", flush=True)

import config
config.LITELLM_URL = "http://127.0.0.1:8080"
config.LITELLM_KEY = "not-needed"
os.environ["OPENAI_API_KEY"] = "not-needed"

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="not-needed",
    model="granite-tiny",
    temperature=0,
    max_tokens=300
)

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=USER_PROMPT)
]

t0 = time.time()
try:
    response = llm.invoke(messages)
    model_answer = response.content
    print(f"\nModell-Antwort ({time.time()-t0:.1f}s):", flush=True)
    print(model_answer, flush=True)
except Exception as e:
    print(f"Fehler: {e}", flush=True)
    model_answer = ""

# 6. Tool-Call parsen
print("\n=== TOOL-CALL ANALYSE ===", flush=True)
tool_call = parse_tool_call_from_response(model_answer, model_family="granite")

if tool_call:
    print(f"Tool-Call erkannt: {tool_call.get('name')}", flush=True)
    print(f"Arguments: {json.dumps(tool_call.get('arguments', {}), indent=2)}", flush=True)

    tool_name = tool_call.get("name")
    tool_args = tool_call.get("arguments", {})
    matched = next((t for t in selected_tools if t.name == tool_name), None)

    if matched:
        print(f"\nFuehre {tool_name} aus...", flush=True)
        try:
            result = asyncio.run(matched.ainvoke(tool_args))
            print(f"Ergebnis: {str(result)[:800]}", flush=True)
        except Exception as e:
            print(f"Tool-Fehler: {e}", flush=True)
    else:
        print(f"Tool {tool_name} nicht gefunden.", flush=True)
else:
    print("Kein <tool_call> in der Antwort.", flush=True)
    print("Modell hat Tool-Call nicht produziert.", flush=True)

# 7. Phoenix Spans
print("\nWarte 5s auf Trace-Delivery...", flush=True)
time.sleep(5)

print("\n=== PHOENIX SPANS ===", flush=True)
try:
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_URL)
    df = client.spans.get_spans_dataframe(
        project_identifier="local-agent",
        limit=20,
        root_spans_only=False,
        start_time=datetime.now() - timedelta(minutes=5)
    )
    if df is not None and not df.empty:
        print(f"{len(df)} Spans gefunden:", flush=True)
        cols = [c for c in [
            "name", "span_kind",
            "attributes.input.value",
            "attributes.output.value",
            "attributes.llm.token_count.prompt",
            "attributes.llm.token_count.completion",
        ] if c in df.columns]
        for _, row in df[cols].iterrows():
            print(f"\n--- {row.get('name','?')} [{row.get('span_kind','?')}] ---", flush=True)
            for col in cols:
                if col in ["name", "span_kind"]: continue
                val = row.get(col)
                if val and str(val) != "nan":
                    print(f"  {col.replace('attributes.','')}: {str(val)[:400]}", flush=True)
    else:
        print("0 Spans — kein LangChain Trace erfasst.", flush=True)
except Exception as e:
    print(f"Phoenix Client Fehler: {e}", flush=True)

phoenix_proc.terminate()
print("\nFertig.", flush=True)
