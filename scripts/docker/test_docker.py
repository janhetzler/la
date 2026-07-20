#!/usr/bin/env python3
"""
test_docker.py -- Agenten-Tester fuer Docker-Umgebung

Setzt voraus dass der Stack bereits laeuft (entrypoint.sh).
Kein Stack-Start -- direkt Tests gegen Port 8002.
"""

import json, time, urllib.request, os
from datetime import datetime

AGENT_URL  = "http://127.0.0.1:8002/v1/chat/completions"
AUTH       = f"Bearer {os.getenv('LITELLM_KEY', 'sk-cos-local-dev')}"
CHROMA_PATH = os.getenv("CHROMA_PATH", "/app/data/chroma")
LOG_DIR    = "/var/log"

results = []

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
    resp, status = api_call(AGENT_URL,
        data={"model": "agent-local",
              "messages": [{"role": "user", "content": frage}],
              "max_tokens": max_tokens}, method="POST")
    elapsed = time.time() - t0
    if "choices" in resp:
        return resp["choices"][0]["message"]["content"], elapsed, status
    return str(resp), elapsed, status

def validate_response(text, min_length=10):
    if not text or text.strip() == "": return False, "Antwort leer"
    if len(text.strip()) < min_length: return False, f"Zu kurz ({len(text.strip())} Zeichen)"
    if text.strip().startswith("{") and "error" in text.lower(): return False, "Fehler-JSON"
    return True, f"OK ({len(text.strip())} Zeichen)"

def check_log(path, label):
    try:
        with open(path) as f:
            content = f.read()
        errors = [l for l in content.splitlines()
                  if "ERROR:" in l and "CREATE TABLE" not in l]
        if errors:
            print(f"  WARNUNG {label}: {errors[-1][:100]}", flush=True)
    except:
        pass

def test_agent(name, frage, notes_check=False):
    print("\n" + "="*55, flush=True)
    print(f"TEST: {name}", flush=True)
    print(f"Frage: {frage[:70]}", flush=True)
    text, elapsed, status = chat(frage)
    print(f"Antwort: {text[:200]}", flush=True)
    print(f"Zeit: {elapsed:.1f}s | HTTP: {status}", flush=True)
    content_ok, content_reason = validate_response(text)
    notes_ok, notes_reason = True, "nicht geprueft"
    if notes_check and content_ok:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            col = client.get_or_create_collection("notes")
            count = col.count()
            notes_ok = count > 0
            notes_reason = f"ChromaDB notes: {count} Dokumente"
        except Exception as e:
            notes_ok = False
            notes_reason = f"ChromaDB Fehler: {e}"
        print(f"ChromaDB: {notes_reason}", flush=True)
    overall_ok = (status == 200) and content_ok and (notes_ok if notes_check else True)
    status_str = "OK" if overall_ok else "FAIL"
    reasons = [content_reason]
    if notes_check: reasons.append(notes_reason)
    print(f"Ergebnis: {status_str} - {' | '.join(reasons)}", flush=True)
    results.append({"agent": name, "frage": frage[:60], "zeit": round(elapsed, 1),
                    "status": status_str, "http": status, "reason": " | ".join(reasons)})

# Health-Check
print("=== DOCKER TEST SUITE ===", flush=True)
print(f"Start: {datetime.now().isoformat()}", flush=True)
resp, status = api_call("http://127.0.0.1:8002/health")
print(f"Agent Server Health: {status} — {resp}", flush=True)

# Agenten-Tests
test_agent("Supervisor Routing",
    "Can you help me?")
test_agent("Comms Agent",
    "Write a short professional email to the team about the project status.")
test_agent("Code Agent",
    "Write a Python function with type hints and docstring that sorts a list.")
test_agent("Researcher Agent",
    "What is LangGraph and how do multi-agent systems work with it?")
test_agent("Notes Agent",
    "Save this note: Local Agent Docker Test erfolgreich.",
    notes_check=True)
test_agent("Handoff Agent",
    "Prepare a prompt for Claude.ai: analyse local LLMs vs Cloud APIs.")

# ChromaDB Status
print("\n" + "="*55, flush=True)
print("CHROMADB STATUS", flush=True)
try:
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    cols = client.list_collections()
    if cols:
        for col in cols:
            c = client.get_collection(col.name)
            print(f"  Collection '{col.name}': {c.count()} Dokumente", flush=True)
    else:
        print("  Keine Collections vorhanden", flush=True)
except Exception as e:
    print(f"  ChromaDB Fehler: {e}", flush=True)

# Log-Check
print("\n" + "="*55, flush=True)
print("LOG-CHECK", flush=True)
for label, fname in [
    ("llama-server", "llama-reasoning.log"),
    ("LiteLLM",      "litellm.log"),
    ("Phoenix",      "phoenix.log"),
    ("Agent Server", "agent-server.log")
]:
    check_log(os.path.join(LOG_DIR, fname), label)

# Zusammenfassung
print("\n" + "="*55, flush=True)
print("ZUSAMMENFASSUNG", flush=True)
print(f"Ende: {datetime.now().isoformat()}", flush=True)
ok = sum(1 for r in results if r["status"] == "OK")
print(f"Tests: {ok}/{len(results)} OK", flush=True)
for r in results:
    icon = "✓" if r["status"] == "OK" else "✗"
    print(f"  {icon} {r['agent']}: {r['reason']}", flush=True)

report = {"timestamp": datetime.now().isoformat(), "results": results,
          "summary": {"total": len(results), "ok": ok},
          "environment": "docker"}
with open("/tmp/test_results.json", "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print("\nReport: /tmp/test_results.json", flush=True)
