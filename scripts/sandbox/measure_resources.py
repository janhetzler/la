"""
measure_resources.py -- Ressourcenmessung + ChromaDB Schreib-/Lesetest

Startet alle Infrastrukturdienste und misst RAM/CPU nach jedem Service-Start.
Testet dann direkt den Notes-Agenten (Schreiben + Lesen) ohne Routing.

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/measure_resources.py

Logs: /tmp/logs/
"""
import threading, time, subprocess, sys, os, urllib.request, json
from datetime import datetime
from pathlib import Path

MODEL_PATH      = os.getenv("MODEL_PATH",      "/tmp/granite-350m-Q4_K_M.gguf")
EMBED_PATH      = os.getenv("EMBED_PATH",      "/tmp/granite-embedding-30m-Q4_0.gguf")
CHROMA_PATH     = os.getenv("CHROMA_PATH",     "/tmp/chroma_la")
LITELLM_KEY     = os.getenv("LITELLM_KEY",     "sk-cos-local-dev")
PHOENIX_URL     = "http://127.0.0.1:6006"
LOG_DIR         = "/tmp/logs"

os.makedirs(CHROMA_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../agents/server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../agents/ingestion"))

# ── Ressourcenmessung via /proc (kein psutil noetig) ─────────────────────────

def ram_used_mb() -> int:
    """Genutzter RAM in MB via /proc/meminfo."""
    with open("/proc/meminfo") as f:
        lines = {l.split(":")[0]: int(l.split()[1]) for l in f if ":" in l}
    total = lines.get("MemTotal", 0)
    avail = lines.get("MemAvailable", 0)
    return (total - avail) // 1024

def cpu_percent() -> float:
    """CPU-Auslastung in % via /proc/stat (1s Messung)."""
    def read_stat():
        with open("/proc/stat") as f:
            line = f.readline()
        vals = list(map(int, line.split()[1:]))
        idle = vals[3]
        total = sum(vals)
        return idle, total

    idle1, total1 = read_stat()
    time.sleep(1)
    idle2, total2 = read_stat()
    if total2 == total1:
        return 0.0
    return round(100.0 * (1 - (idle2 - idle1) / (total2 - total1)), 1)

def snapshot(label: str, measurements: list):
    ram = ram_used_mb()
    cpu = cpu_percent()
    measurements.append({"label": label, "ram_mb": ram, "cpu_pct": cpu})
    print(f"  [{label}] RAM: {ram} MB | CPU: {cpu}%", flush=True)
    return ram, cpu

# ── Warten auf Service ────────────────────────────────────────────────────────

def wait_for(url, label, retries=40, headers=None):
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            if headers:
                for k, v in headers.items(): req.add_header(k, v)
            urllib.request.urlopen(req, timeout=2)
            print(f"  {label} bereit", flush=True); return True
        except: time.sleep(1); print(f"  {i+1}...", end=" ", flush=True)
    print(f"  {label} TIMEOUT", flush=True); return False

# ── Messungen sammeln ─────────────────────────────────────────────────────────

measurements = []

print("=" * 60, flush=True)
print("RESSOURCENMESSUNG -- Local Agent Stack", flush=True)
print(f"Start: {datetime.now().isoformat()}", flush=True)
print("=" * 60, flush=True)

# Baseline
print("\n[0] Baseline (vor Stack-Start):", flush=True)
snapshot("Baseline", measurements)

# ── 1. llama-server (Reasoning) ───────────────────────────────────────────────
print("\n[1] llama-server Reasoning (Port 8080):", flush=True)

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
wait_for("http://127.0.0.1:8080/v1/models", "llama-server Reasoning")
snapshot("Nach llama-server Reasoning", measurements)

# ── 2. llama-server (Embedding) ───────────────────────────────────────────────
print("\n[2] llama-server Embedding (Port 8081):", flush=True)

embed_proc = None
if Path(EMBED_PATH).exists():
    embed_proc = subprocess.Popen(
        ["python3", "-m", "llama_cpp.server",
         "--model", EMBED_PATH,
         "--host", "127.0.0.1",
         "--port", "8081",
         "--embedding", "true",
         "--n_ctx", "512"],
        stdout=open(os.path.join(LOG_DIR, "embedding.log"), "w"),
        stderr=subprocess.STDOUT
    )
    wait_for("http://127.0.0.1:8081/v1/models", "llama-server Embedding")
    snapshot("Nach llama-server Embedding", measurements)
else:
    print(f"  Embedding-Modell nicht gefunden: {EMBED_PATH}", flush=True)
    print("  Embedding-Server wird uebersprungen.", flush=True)

# ── 3. Phoenix ────────────────────────────────────────────────────────────────
print("\n[3] Arize Phoenix (Port 6006):", flush=True)

os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = f"{PHOENIX_URL}/v1/traces"
os.environ["PHOENIX_CLIENT_HEADERS"]     = "api_key=not-needed"
phoenix_proc = subprocess.Popen(
    ["python3", "-m", "phoenix.server.main", "serve",
     "--host", "127.0.0.1", "--port", "6006"],
    stdout=open(os.path.join(LOG_DIR, "phoenix.log"), "w"),
    stderr=subprocess.STDOUT)
wait_for(f"{PHOENIX_URL}/v1/projects", "Phoenix")
snapshot("Nach Phoenix", measurements)

# ── 4. LiteLLM ───────────────────────────────────────────────────────────────
print("\n[4] LiteLLM Proxy (Port 4000):", flush=True)

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
  - model_name: granite-embed
    litellm_params:
      model: openai/granite-embed
      api_base: http://127.0.0.1:8081/v1
      api_key: not-needed
general_settings:
  master_key: {LITELLM_KEY}
litellm_settings:
  drop_params: true
  set_verbose: false
  success_callback: ["arize_phoenix"]
  failure_callback: ["arize_phoenix"]
"""
with open("/tmp/litellm_measure.yaml", "w") as f:
    f.write(litellm_cfg)

litellm_proc = subprocess.Popen(
    ["litellm", "--config", "/tmp/litellm_measure.yaml",
     "--host", "127.0.0.1", "--port", "4000"],
    env=os.environ.copy(),
    stdout=open(os.path.join(LOG_DIR, "litellm.log"), "w"),
    stderr=subprocess.STDOUT)
wait_for("http://127.0.0.1:4000/health", "LiteLLM",
         headers={"Authorization": f"Bearer {LITELLM_KEY}"})
snapshot("Nach LiteLLM", measurements)

# ── 5. Agent Config + Phoenix Init ────────────────────────────────────────────
import config
config.LITELLM_URL = "http://127.0.0.1:4000"
config.LITELLM_KEY = LITELLM_KEY
config.DEFAULT_LLM = "granite-tiny"
config.CHROMA_PATH = CHROMA_PATH
os.environ["OPENAI_API_KEY"] = LITELLM_KEY

try:
    from telemetry import init_phoenix
    init_phoenix()
    print("  Phoenix Tracing OK", flush=True)
except Exception as e:
    print(f"  Phoenix Tracing: {e}", flush=True)

# ── 6. Agent Server ───────────────────────────────────────────────────────────
print("\n[5] Agent Server (Port 8002):", flush=True)

import server as agent_server

def run_agent():
    uvicorn.Server(uvicorn.Config(
        agent_server.app, host="127.0.0.1", port=8002,
        log_level="error")).run()

threading.Thread(target=run_agent, daemon=True).start()
wait_for("http://127.0.0.1:8002/health", "Agent Server")
snapshot("Nach Agent Server", measurements)

# ── 7. ChromaDB direkt initialisieren ─────────────────────────────────────────
print("\n[6] ChromaDB (embedded):", flush=True)
import chromadb
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
col = chroma_client.get_or_create_collection("notes")
print(f"  Collection 'notes': {col.count()} Dokumente", flush=True)
snapshot("Nach ChromaDB Init", measurements)

# ── 8. Notes Agent -- Schreiben ───────────────────────────────────────────────
print("\n" + "=" * 60, flush=True)
print("NOTES AGENT TEST -- Schreiben", flush=True)
print("=" * 60, flush=True)

from notes import invoke_notes_sync

test_note = "Local Agent laeuft auf AMD EPYC, 4 vCores, 10 GB RAM. Sandbox-Test erfolgreich."
print(f"Schreibe: '{test_note}'", flush=True)

t0 = time.time()
write_result = invoke_notes_sync(test_note, "English")
write_time = time.time() - t0
print(f"Antwort ({write_time:.1f}s): {write_result[:200]}", flush=True)
snapshot("Nach Notes Schreiben", measurements)

# ChromaDB pruefen
col = chroma_client.get_or_create_collection("notes")
after_write = col.count()
print(f"\nChromaDB 'notes' nach Schreiben: {after_write} Dokumente", flush=True)

# ── 9. Notes Agent -- Lesen ───────────────────────────────────────────────────
print("\n" + "=" * 60, flush=True)
print("NOTES AGENT TEST -- Lesen", flush=True)
print("=" * 60, flush=True)

search_query = "Was weisst du ueber den AMD EPYC Server?"
print(f"Suche: '{search_query}'", flush=True)

t0 = time.time()
read_result = invoke_notes_sync(search_query, "English")
read_time = time.time() - t0
print(f"Antwort ({read_time:.1f}s): {read_result[:400]}", flush=True)
snapshot("Nach Notes Lesen", measurements)

# ── 10. Zusammenfassung ───────────────────────────────────────────────────────
print("\n" + "=" * 60, flush=True)
print("RESSOURCEN-ZUSAMMENFASSUNG", flush=True)
print("=" * 60, flush=True)
print(f"{'Service':<35} {'RAM (MB)':>10} {'CPU %':>8}", flush=True)
print("-" * 55, flush=True)
for m in measurements:
    print(f"{m['label']:<35} {m['ram_mb']:>10} {m['cpu_pct']:>7}%", flush=True)

baseline = measurements[0]["ram_mb"]
peak = max(m["ram_mb"] for m in measurements)
print(f"\nBaseline RAM:  {baseline} MB", flush=True)
print(f"Peak RAM:      {peak} MB", flush=True)
print(f"Stack-Overhead: {peak - baseline} MB", flush=True)

print("\nChromaDB Ergebnis:", flush=True)
print(f"  Dokumente nach Schreiben: {after_write}", flush=True)
print(f"  Schreib-Test: {'OK' if after_write > 0 else 'FAIL'}", flush=True)
print(f"  Lese-Antwort: {'OK' if len(read_result) > 20 else 'FAIL'}", flush=True)

# Report speichern
report = {
    "timestamp": datetime.now().isoformat(),
    "measurements": measurements,
    "summary": {
        "baseline_ram_mb": baseline,
        "peak_ram_mb": peak,
        "overhead_mb": peak - baseline,
        "chromadb_docs_after_write": after_write,
        "write_ok": after_write > 0,
        "read_ok": len(read_result) > 20
    }
}
with open("/tmp/resource_report.json", "w") as f:
    json.dump(report, f, indent=2)
print("\nReport: /tmp/resource_report.json", flush=True)


# ── Phoenix Traces auswerten ─────────────────────────────────────────────────
print("\n" + "=" * 60, flush=True)
print("PHOENIX TRACES -- Notes Agent Requests", flush=True)
print("=" * 60, flush=True)

time.sleep(3)  # Trace-Delivery abwarten

try:
    from phoenix.client import Client
    from datetime import timedelta

    px_client = Client(base_url=PHOENIX_URL)
    df = px_client.spans.get_spans_dataframe(
        project_identifier="local-agent",
        limit=20,
        root_spans_only=False,
        start_time=datetime.now() - timedelta(minutes=10)
    )

    if df is not None and not df.empty:
        print(f"\n{len(df)} Spans erfasst:\n", flush=True)
        cols = [c for c in [
            "name", "span_kind",
            "attributes.input.value",
            "attributes.output.value",
            "attributes.llm.token_count.prompt",
            "attributes.llm.token_count.completion",
            "attributes.tool.name",
        ] if c in df.columns]

        for _, row in df[cols].iterrows():
            print(f"\n--- {row.get('name','?')} [{row.get('span_kind','?')}] ---", flush=True)
            for col in cols:
                if col in ["name", "span_kind"]: continue
                val = row.get(col)
                if val and str(val) != "nan":
                    label = col.replace("attributes.", "")
                    print(f"  {label}: {str(val)[:400]}", flush=True)
    else:
        print("Keine Spans gefunden.", flush=True)

except Exception as e:
    print(f"Phoenix Client Fehler: {e}", flush=True)

# Cleanup
for proc in [litellm_proc, phoenix_proc]:
    if proc: proc.terminate()
if embed_proc:
    embed_proc.terminate()
print("\nStack gestoppt.", flush=True)
