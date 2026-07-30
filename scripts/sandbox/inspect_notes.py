"""
inspect_notes.py -- Diagnose-Skript fuer den Notes-Agent (save_note-Pfad)

Local Agent (LA) -- Sandbox Edition

Ablauf:
  1. llama-server :8080 starten (Reasoning, --jinja)
  2. llama-server :8081 starten (Embedding, kein --jinja)
  3. Phoenix starten
  4. LiteLLM starten
  5. Agent Server starten
  6. ChromaDB-Count vor dem Request
  7. Request: "Save this note: test direct call"
  8. ChromaDB-Count nach dem Request
  9. Phoenix Spans auslesen
 10. Output nach /tmp/inspect_notes_output.txt schreiben
 11. Datei via GitHub API nach docs/traces/sandbox/ pushen

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/inspect_notes.py

Umgebungsvariablen:
  MODEL_PATH       (default: /tmp/granite-350m-Q4_K_M.gguf)
  EMBED_MODEL_PATH (default: /tmp/granite-embedding-30m-Q4_0.gguf)
  CHROMA_PATH      (default: /tmp/chroma_la)
  LITELLM_KEY      (default: sk-cos-local-dev)
  GH_TOKEN         (Push nach docs/traces/sandbox/ -- optional)
"""
import threading, time, urllib.request, json, subprocess, sys, os, base64
import httpx
from datetime import datetime
from pathlib import Path

# Konfiguration
MODEL_PATH       = os.getenv("MODEL_PATH",       "/tmp/granite-350m-Q4_K_M.gguf")
EMBED_MODEL_PATH = os.getenv("EMBED_MODEL_PATH", "/tmp/granite-embedding-30m-Q4_0.gguf")
CHROMA_PATH      = os.getenv("CHROMA_PATH",      "/tmp/chroma_la")
LITELLM_KEY      = os.getenv("LITELLM_KEY",      "sk-cos-local-dev")
GH_TOKEN         = os.getenv("GH_TOKEN",         "")
LOG_DIR          = "/tmp/logs"
PHOENIX_URL      = "http://127.0.0.1:6006"
PROMPT           = "Save this note: test direct call"

os.makedirs(CHROMA_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../agents/server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../agents/ingestion"))

# Ausgabe-Puffer -- alles landet in output_lines und spaeter in der Datei
output_lines = []

def log(msg: str) -> None:
    """Gibt Nachricht auf Konsole aus und puffert sie fuer die Ausgabedatei."""
    print(msg, flush=True)
    output_lines.append(msg)


# Hilfsfunktionen
def wait_for(url: str, label: str, retries: int = 40, headers: dict = None) -> bool:
    """Wartet bis ein HTTP-Endpunkt antwortet."""
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            urllib.request.urlopen(req, timeout=2)
            log(f"{label} OK")
            return True
        except Exception:
            time.sleep(1)
            print(f"{i+1}...", end=" ", flush=True)
    log(f"{label} TIMEOUT")
    return False


def chroma_count() -> int:
    """Gibt Anzahl Dokumente in der notes-Collection zurueck."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        col = client.get_or_create_collection(
            name="notes",
            metadata={"hnsw:space": "cosine"}
        )
        return col.count()
    except Exception as e:
        log(f"[ChromaDB] Fehler bei Count: {e}")
        return -1


# 1. llama-server :8080 (Reasoning, --jinja)
LLAMA_BIN = "/tmp/llama-b9895/llama-server"
LLAMA_LOG = os.path.join(LOG_DIR, "llama-server.log")

llama_proc = subprocess.Popen(
    [LLAMA_BIN, "-m", MODEL_PATH,
     "--host", "127.0.0.1", "--port", "8080",
     "--jinja", "--ctx-size", "32768",
     "--parallel", "1", "--log-disable",
     "--embeddings", "--pooling", "mean"],
    stdout=open(LLAMA_LOG, "w"), stderr=subprocess.STDOUT
)
wait_for("http://127.0.0.1:8080/v1/models", "llama-server", retries=40)

# Inference-Readiness-Check :8080 -- sicherstellen dass Modell vollstaendig geladen ist
log("Warte auf llama-server :8080 Inference-Bereitschaft...")
for _i in range(20):
    try:
        _req = urllib.request.Request(
            "http://127.0.0.1:8080/v1/chat/completions",
            data=json.dumps({
                "model": "granite",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(_req, timeout=15)
        log("llama-server :8080 Inference OK")
        break
    except Exception:
        time.sleep(2)
        print(f"{_i+1}...", end=" ", flush=True)
else:
    log("llama-server :8080 Inference TIMEOUT -- Stack moeglicherweise instabil")

# 2. llama-server :8081 (Embedding, kein --jinja)
LLAMA_EMBED_LOG = os.path.join(LOG_DIR, "llama-server-embed.log")

llama_embed_proc = subprocess.Popen(
    [LLAMA_BIN, "-m", EMBED_MODEL_PATH,
     "--host", "127.0.0.1", "--port", "8081",
     "--embeddings", "--pooling", "mean",
     "--parallel", "1", "--log-disable"],
    stdout=open(LLAMA_EMBED_LOG, "w"), stderr=subprocess.STDOUT
)
wait_for("http://127.0.0.1:8081/v1/models", "llama-server-embed")

# 3. Phoenix
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = f"{PHOENIX_URL}/v1/traces"
os.environ["PHOENIX_CLIENT_HEADERS"]     = "api_key=not-needed"
phoenix_proc = subprocess.Popen(
    ["python3", "-m", "phoenix.server.main", "serve",
     "--host", "127.0.0.1", "--port", "6006"],
    stdout=open(os.path.join(LOG_DIR, "phoenix.log"), "w"),
    stderr=subprocess.STDOUT
)
wait_for(f"{PHOENIX_URL}/v1/projects", "Phoenix")

# 4. LiteLLM
litellm_cfg = f"""
model_list:
  - model_name: granite-tiny
    litellm_params:
      model: openai/granite
      api_base: http://127.0.0.1:8080/v1
      api_key: not-needed
  - model_name: granite-embed
    litellm_params:
      model: openai/granite-embed
      api_base: http://127.0.0.1:8081/v1
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
with open("/tmp/litellm_notes.yaml", "w") as f:
    f.write(litellm_cfg)

litellm_proc = subprocess.Popen(
    ["litellm", "--config", "/tmp/litellm_notes.yaml",
     "--host", "127.0.0.1", "--port", "4000"],
    env=os.environ.copy(),
    stdout=open(os.path.join(LOG_DIR, "litellm.log"), "w"),
    stderr=subprocess.STDOUT
)
wait_for("http://127.0.0.1:4000/health", "LiteLLM",
         headers={"Authorization": f"Bearer {LITELLM_KEY}"})

# LiteLLM -> llama-server Readiness-Check
log("Warte auf LiteLLM -> llama-server...")
for i in range(20):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:4000/v1/chat/completions",
            data=json.dumps({
                "model": "granite-tiny",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 3
            }).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {LITELLM_KEY}"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=30)
        log("LiteLLM -> llama-server OK")
        break
    except Exception:
        time.sleep(2)
        print(f"{i+1}...", end=" ", flush=True)

# LiteLLM -> granite-embed Readiness-Check
log("Warte auf LiteLLM -> granite-embed...")
for i in range(15):
    try:
        with httpx.Client(timeout=10) as c:
            r = c.post(
                "http://127.0.0.1:4000/v1/embeddings",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
                json={"model": "granite-embed", "input": "ready"}
            )
            r.raise_for_status()
        log("LiteLLM -> granite-embed OK")
        break
    except Exception:
        time.sleep(2)
        print(f"{i+1}...", end=" ", flush=True)

# 5. Agent Config + Phoenix Init
import config
config.LITELLM_URL  = "http://127.0.0.1:4000"
config.LITELLM_KEY  = LITELLM_KEY
config.DEFAULT_LLM  = "granite-tiny"
config.CHROMA_PATH  = CHROMA_PATH
config.EMBED_MODEL  = "granite-embed"
os.environ["OPENAI_API_KEY"] = LITELLM_KEY

try:
    from telemetry import init_phoenix
    init_phoenix()
    log("Phoenix Tracing OK")
except Exception as e:
    log(f"Phoenix Tracing: {e}")

# Agent Server
import uvicorn
import server as agent_server

def run_agent():
    """Agent Server als Daemon-Thread."""
    uvicorn.Server(uvicorn.Config(
        agent_server.app, host="127.0.0.1", port=8002,
        log_level="error"
    )).run()

threading.Thread(target=run_agent, daemon=True).start()
wait_for("http://127.0.0.1:8002/health", "Agent Server")

# ChromaDB -- notes-Collection initialisieren (cosine)
import chromadb as _chromadb
_chroma_client = _chromadb.PersistentClient(path=CHROMA_PATH)
_chroma_client.get_or_create_collection(
    name="notes",
    metadata={"hnsw:space": "cosine"}
)

# 6. ChromaDB-Count VOR dem Request
count_before = chroma_count()
log(f"\nChromaDB notes vor Request: {count_before} Dokumente")

# 7. Request
log(f"\n=== REQUEST ===")
log(f"Prompt: {PROMPT}")

t0 = time.time()
req = urllib.request.Request(
    "http://127.0.0.1:8002/v1/chat/completions",
    data=json.dumps({
        "model": "agent-local",
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 300
    }).encode(),
    headers={"Content-Type": "application/json",
             "Authorization": f"Bearer {LITELLM_KEY}"},
    method="POST"
)
antwort = ""
try:
    r = urllib.request.urlopen(req, timeout=120)
    resp = json.loads(r.read())
    antwort = resp["choices"][0]["message"]["content"]
    log(f"Antwort ({time.time()-t0:.1f}s):\n{antwort}")
except Exception as e:
    antwort = f"Fehler: {e}"
    log(antwort)

# 8. ChromaDB-Count NACH dem Request
count_after = chroma_count()
log(f"\nChromaDB notes nach Request: {count_after} Dokumente")
if count_after > count_before:
    log(f"✓ save_note ausgefuehrt — {count_after - count_before} neue Dokumente")
else:
    log("✗ save_note NICHT ausgefuehrt — ChromaDB unveraendert")

# Warten auf Trace-Delivery
log("\nWarte 5s auf Trace-Delivery...")
time.sleep(5)

# 9. Phoenix Spans
log("\n=== PHOENIX SPANS ===")
span_output = ""
try:
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_URL)
    spans_df = client.spans.get_spans_dataframe(
        project_identifier="local-agent",
        limit=50,
        root_spans_only=False,
        start_time=datetime.now().__class__.now() - __import__("datetime").timedelta(minutes=10)
    )
    if spans_df is not None and not spans_df.empty:
        log(f"{len(spans_df)} Spans gefunden:")
        cols = [c for c in [
            "name", "span_kind",
            "attributes.input.value",
            "attributes.output.value",
            "attributes.llm.model_name",
            "attributes.llm.token_count.prompt",
            "attributes.llm.token_count.completion",
            "status_code", "latency_ms"
        ] if c in spans_df.columns]
        for _, row in spans_df[cols].iterrows():
            header = f"\n--- {row.get('name', '?')} [{row.get('span_kind', '?')}] ---"
            log(header)
            span_output += header + "\n"
            for col in cols:
                if col in ["name", "span_kind"]:
                    continue
                val = row.get(col)
                if val and str(val) != "nan":
                    label = col.replace("attributes.", "").replace("llm.", "")
                    line = f"  {label}: {str(val)[:500]}"
                    log(line)
                    span_output += line + "\n"
    else:
        log("Keine Spans gefunden.")
        span_output = "Keine Spans gefunden."
except Exception as e:
    log(f"Phoenix Client Fehler: {e}")
    import traceback
    span_output = traceback.format_exc()
    log(span_output)

# 10. Output-Datei schreiben
output_path = Path("/tmp/inspect_notes_output.txt")
full_output = "\n".join(output_lines)
output_path.write_text(full_output, encoding="utf-8")
log(f"\nOutput gespeichert: {output_path} ({len(full_output)} Zeichen)")

# Trace-MD aufbauen
date_str = datetime.now().strftime("%Y-%m-%d")
trace_content = f"""# Notes-Agent Trace — {date_str}

**Prompt:** {PROMPT}
**Gesamtdauer:** {time.time()-t0:.1f}s
**Stack:** llama-server b9895 + --jinja | LiteLLM | Agent Server :8002 | Embedding :8081

---

## 1. Ergebnis

**ChromaDB vor Request:** {count_before} Dokumente
**ChromaDB nach Request:** {count_after} Dokumente
**save_note ausgefuehrt:** {"JA" if count_after > count_before else "NEIN"}

**Antwort des Agents:**
```
{antwort}
```

---

## 2. Phoenix Spans

{span_output}

---

## 3. Konsolen-Output (komplett)

```
{full_output}
```
"""

# 11. Push nach docs/traces/sandbox/
trace_filename = f"{date_str}_inspect-notes.md"
trace_repo_path = f"docs/traces/sandbox/{trace_filename}"

if GH_TOKEN:
    log(f"\nPushe {trace_repo_path} nach GitHub...")
    try:
        # Pruefen ob Datei bereits existiert (SHA noetig fuer Update)
        check_req = urllib.request.Request(
            f"https://api.github.com/repos/janhetzler/la/contents/{trace_repo_path}",
            headers={"Authorization": f"Bearer {GH_TOKEN}",
                     "Accept": "application/vnd.github+json"}
        )
        existing_sha = None
        try:
            existing_data = json.loads(urllib.request.urlopen(check_req).read())
            existing_sha = existing_data.get("sha")
        except Exception:
            pass  # Datei existiert noch nicht -- kein SHA noetig

        push_payload = {
            "message": f"trace: Notes-Agent inspect run {date_str}",
            "content": base64.b64encode(trace_content.encode("utf-8")).decode("ascii"),
        }
        if existing_sha:
            push_payload["sha"] = existing_sha

        push_req = urllib.request.Request(
            f"https://api.github.com/repos/janhetzler/la/contents/{trace_repo_path}",
            data=json.dumps(push_payload).encode("utf-8"),
            method="PUT",
            headers={"Authorization": f"Bearer {GH_TOKEN}",
                     "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json"}
        )
        push_result = json.loads(urllib.request.urlopen(push_req).read())
        log(f"Push OK: {push_result['commit']['sha'][:8]} -> {trace_repo_path}")
    except Exception as e:
        log(f"Push FAIL: {e}")
else:
    log("\nGH_TOKEN nicht gesetzt -- kein Push. Trace liegt lokal unter:")
    log(f"  /tmp/inspect_notes_output.txt")

# Cleanup
for proc in [litellm_proc, phoenix_proc, llama_embed_proc]:
    if proc:
        proc.terminate()
log("\nStack gestoppt.")
