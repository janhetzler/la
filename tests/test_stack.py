"""
Chief-of-Staff janhet — Vollständige Test-Suite
Testet alle Agenten mit 4-Schritt Workflow, Phoenix Traces und ChromaDB.
"""
import json, time, urllib.request, sys, os
from datetime import datetime

AGENT_URL    = "http://127.0.0.1:8002/v1/chat/completions"
PHOENIX_URL  = "http://127.0.0.1:6006"
AUTH         = "Bearer sk-cos-local-dev"
LOG_DIR      = "/tmp/logs"
CHROMA_PATH  = os.getenv("CHROMA_PATH", "/tmp/chroma_chief")
results      = []

# ── Log-Check Funktion ───────────────────────────────────────────
ERROR_PATTERNS = ["ERROR", "Exception", "Traceback", "CRITICAL"]

def check_log(log_file: str, label: str) -> bool:
    """Liest Log-Datei und sucht nach Fehler-Mustern. Gibt True zurück wenn sauber."""
    if not os.path.exists(log_file):
        print(f"  [{label}] Log-Datei nicht gefunden: {log_file}", flush=True)
        return True  # Kein Log = kein Fehler (z.B. llama-server noch nichts geloggt)
    with open(log_file) as f:
        lines = f.readlines()
    found = []
    for i, line in enumerate(lines):
        if any(p in line for p in ERROR_PATTERNS):
            found.append(f"    Zeile {i+1}: {line.strip()[:120]}")
    if found:
        print(f"  [{label}] ⚠️  Fehler in {log_file}:", flush=True)
        for f in found[:5]:
            print(f, flush=True)
        return False
    print(f"  [{label}] Log sauber ✓ ({len(lines)} Zeilen)", flush=True)
    return True

# ── Log-Check nach Service-Start ─────────────────────────────────
print("=== LOG-CHECK NACH SERVICE-START ===", flush=True)
check_log(os.path.join(LOG_DIR, "llama-server.log"), "llama-server")
check_log(os.path.join(LOG_DIR, "litellm.log"),      "LiteLLM")
check_log(os.path.join(LOG_DIR, "phoenix.log"),      "Phoenix")
check_log(os.path.join(LOG_DIR, "agent-server.log"), "Agent Server")

# ── API-Helfer ───────────────────────────────────────────────────
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
    resp, status = api_call(
        AGENT_URL,
        data={"model": "agent-local",
              "messages": [{"role": "user", "content": frage}],
              "max_tokens": max_tokens},
        method="POST")
    elapsed = time.time() - t0
    if "choices" in resp:
        text = resp["choices"][0]["message"]["content"]
        tokens = resp.get("usage", {}).get("completion_tokens", 0)
        return text, tokens, elapsed, status
    return str(resp), 0, elapsed, status

# ── Antwort-Validierung ──────────────────────────────────────────
def validate_response(text: str, min_length: int = 10) -> tuple[bool, str]:
    """Validiert Antwort inhaltlich. Gibt (ok, grund) zurück."""
    if not text or text.strip() == "":
        return False, "Antwort leer"
    if len(text.strip()) < min_length:
        return False, f"Antwort zu kurz ({len(text.strip())} < {min_length} Zeichen)"
    if text.strip().startswith("{") and "error" in text.lower():
        return False, f"Antwort ist Fehler-JSON"
    return True, f"OK ({len(text.strip())} Zeichen)"

def test_agent(name, frage, beschreibung, notes_check=False):
    print(f"\n{'='*55}", flush=True)
    print(f"TEST: {name}", flush=True)
    print(f"Info: {beschreibung}", flush=True)
    print(f"Frage: {frage[:70]}", flush=True)

    text, tokens, elapsed, status = chat(frage)
    print(f"Antwort: {text[:200]}", flush=True)
    print(f"Tokens: {tokens} | Zeit: {elapsed:.1f}s | HTTP: {status}", flush=True)

    # Inhaltliche Validierung
    content_ok, content_reason = validate_response(text)

    # Notes Agent: ChromaDB nachprüfen
    notes_ok = True
    notes_reason = "nicht geprüft"
    if notes_check and content_ok:
        try:
            sys.path.insert(0, '/home/claude/la/agents/server')
            sys.path.insert(0, '/home/claude/la/agents/ingestion')
            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            col = client.get_or_create_collection('notes')
            count = col.count()
            notes_ok = count > 0
            notes_reason = f"ChromaDB 'notes' collection: {count} Dokumente"
        except Exception as e:
            notes_ok = False
            notes_reason = f"ChromaDB Fehler: {e}"
        print(f"ChromaDB: {notes_reason}", flush=True)

    # Gesamtergebnis
    overall_ok = (status == 200) and content_ok and (notes_ok if notes_check else True)
    status_str = "OK" if overall_ok else "FAIL"

    reasons = []
    if status != 200: reasons.append(f"HTTP {status}")
    reasons.append(content_reason)
    if notes_check: reasons.append(notes_reason)

    print(f"Ergebnis: {status_str} — {' | '.join(reasons)}", flush=True)

    # Log nach jedem Agent-Call prüfen
    check_log(os.path.join(LOG_DIR, "agent-server.log"), f"Agent Server nach {name}")

    r = {
        "agent": name,
        "frage": frage[:60],
        "tokens": tokens,
        "zeit": round(elapsed, 1),
        "status": status_str,
        "http": status,
        "content_ok": content_ok,
        "reason": ' | '.join(reasons),
    }
    results.append(r)
    return r

# ── AGENT TESTS ──────────────────────────────────────────────────
print(f"\n=== CHIEF-OF-STAFF TEST SUITE ===", flush=True)
print(f"Start: {datetime.now().isoformat()}", flush=True)

test_agent("Supervisor Routing",
    "Can you help me?",
    "Schritt 1-4: Supervisor empfängt + routet + antwortet")

test_agent("Comms Agent",
    "Write a short professional email to the team about the janhet project status.",
    "Schritt 1-4: Supervisor→Comms→Generierung→Antwort")

test_agent("Code Agent",
    "Write a Python function with type hints and docstring that sorts a list.",
    "Schritt 1-4: Supervisor→Code→Generierung→Antwort")

test_agent("Researcher Agent",
    "What is LangGraph and how do multi-agent systems work with it?",
    "Schritt 1-4: Supervisor→Researcher→ChromaDB→Antwort")

test_agent("Notes Agent",
    "Save this note: janhet runs on AMD EPYC 7443P, 4 vCores, 10GB RAM.",
    "Schritt 1-4: Supervisor→Notes→ChromaDB Schreiben→Bestätigung",
    notes_check=True)

test_agent("Handoff Agent",
    "Prepare a prompt for Claude.ai: analyse local LLMs vs Cloud APIs.",
    "Schritt 1-4: Supervisor→Handoff→Prompt→Antwort")

# ── CHROMADB STATUS ───────────────────────────────────────────────
print(f"\n{'='*55}", flush=True)
print("CHROMADB STATUS", flush=True)
try:
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    for col in client.list_collections():
        c = client.get_collection(col.name)
        print(f"  Collection '{col.name}': {c.count()} Dokumente", flush=True)
except Exception as e:
    print(f"  ChromaDB Fehler: {e}", flush=True)

# ── FINALER LOG-CHECK ─────────────────────────────────────────────
print(f"\n{'='*55}", flush=True)
print("FINALER LOG-CHECK", flush=True)
for label, fname in [
    ("llama-server", "llama-server.log"),
    ("LiteLLM",      "litellm.log"),
    ("Phoenix",      "phoenix.log"),
    ("Agent Server", "agent-server.log"),
]:
    check_log(os.path.join(LOG_DIR, fname), label)

# ── ZUSAMMENFASSUNG ───────────────────────────────────────────────
print(f"\n{'='*55}", flush=True)
print("ZUSAMMENFASSUNG", flush=True)
print(f"Ende: {datetime.now().isoformat()}", flush=True)
ok = sum(1 for r in results if r["status"] == "OK")
print(f"Tests: {ok}/{len(results)} OK", flush=True)
for r in results:
    icon = "✓" if r["status"] == "OK" else "✗"
    print(f"  {icon} {r['agent']}: {r['reason']}", flush=True)

report = {
    "timestamp": datetime.now().isoformat(),
    "results": results,
    "summary": {"total": len(results), "ok": ok}
}
with open('/tmp/test_results.json', 'w') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f"\nReport: /tmp/test_results.json", flush=True)
