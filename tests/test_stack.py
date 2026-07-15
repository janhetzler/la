"""
Chief-of-Staff janhet — Vollständige Test-Suite
Testet alle Agenten mit 4-Schritt Workflow, Phoenix Traces und Headroom Kompression.
"""
import json, time, urllib.request, sys
from datetime import datetime

AGENT_URL   = "http://127.0.0.1:8002/v1/chat/completions"
PHOENIX_URL = "http://127.0.0.1:6006"
HEADROOM_URL= "http://127.0.0.1:8787"
AUTH        = "Bearer sk-cos-local-dev"
results     = []

def api_call(url, data=None, method="GET", headers=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", AUTH)
    if data:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    if headers:
        for k,v in headers.items(): req.add_header(k,v)
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return json.loads(r.read()), r.status
    except Exception as e:
        return {"error": str(e)}, 0

def chat(frage, max_tokens=300):
    t0 = time.time()
    resp, status = api_call(AGENT_URL,
        data={"model":"agent-chief-of-staff",
              "messages":[{"role":"user","content":frage}],
              "max_tokens":max_tokens},
        method="POST")
    elapsed = time.time()-t0
    if "choices" in resp:
        return resp["choices"][0]["message"]["content"], resp.get("usage",{}).get("completion_tokens",0), elapsed, status
    return str(resp), 0, elapsed, 0

def test_agent(name, frage, beschreibung):
    print(f"\n{'='*55}", flush=True)
    print(f"TEST: {name}", flush=True)
    print(f"Info: {beschreibung}", flush=True)
    print(f"Frage: {frage[:80]}", flush=True)
    # Schritt 1+2: Call + Antwort
    text, tokens, elapsed, status = chat(frage)
    print(f"Antwort: {text[:200]}", flush=True)
    print(f"Tokens:{tokens} | Zeit:{elapsed:.1f}s", flush=True)
    # Schritt 3: Headroom Stats nach Call
    hs, _ = api_call(f"{HEADROOM_URL}/stats")
    hr = hs.get("requests",{}).get("total",0) if isinstance(hs,dict) else "?"
    print(f"Headroom Requests gesamt: {hr}", flush=True)
    # Schritt 4: Phoenix
    time.sleep(1)
    r = {"agent":name,"frage":frage[:60],"tokens":tokens,
         "zeit":round(elapsed,1),"status":"OK" if status==200 else "FAIL",
         "headroom_total":hr}
    results.append(r)
    return r

# ── STACK MUSS LAUFEN ────────────────────────────────────────────
print(f"\n=== CHIEF-OF-STAFF TEST SUITE ===", flush=True)
print(f"Start: {datetime.now().isoformat()}", flush=True)

# Agent Tests
test_agent("Supervisor Routing",
    "Kannst du mir kurz helfen?",
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
    "Save this note: janhet runs on AMD EPYC 7443P, 4 vCores, 10GB RAM, Granite-4.0-H-Tiny.",
    "Schritt 1-4: Supervisor→Notes→ChromaDB Schreiben→Bestätigung")

test_agent("Handoff Agent",
    "Prepare a prompt for Claude.ai: analyse local LLMs vs Cloud APIs.",
    "Schritt 1-4: Supervisor→Handoff→Prompt→Antwort")

# ── PHOENIX API ANALYSE ───────────────────────────────────────────
print(f"\n{'='*55}", flush=True)
print("PHOENIX TRACES ANALYSE", flush=True)
time.sleep(3)

for ep in ["/v1/projects", "/v1/spans?limit=20", "/v1/traces"]:
    data, st = api_call(f"{PHOENIX_URL}{ep}")
    if st == 200:
        print(f"\nEndpoint {ep}:", flush=True)
        if isinstance(data, dict):
            keys = list(data.keys())
            print(f"  Keys: {keys}", flush=True)
            if "data" in data:
                items = data["data"]
                print(f"  Einträge: {len(items)}", flush=True)
                for item in items[:3]:
                    name = item.get("name") or item.get("project_name") or str(item)[:80]
                    print(f"    - {name}", flush=True)
        else:
            print(f"  {str(data)[:200]}", flush=True)

# ── HEADROOM KOMPRESSION DETAIL ───────────────────────────────────
print(f"\n{'='*55}", flush=True)
print("HEADROOM KOMPRESSION DETAIL", flush=True)

for ep in ["/stats", "/stats-history", "/health", "/metrics"]:
    data, st = api_call(f"{HEADROOM_URL}{ep}")
    if st == 200 and isinstance(data, dict):
        print(f"\n{ep}:", flush=True)
        # Tokens gespart
        for key in ["tokens_saved","compression_ratio","requests","total_tokens_in","total_tokens_out"]:
            if key in data:
                print(f"  {key}: {data[key]}", flush=True)
        # Alles ausgeben wenn klein
        if len(str(data)) < 500:
            print(f"  Vollständig: {json.dumps(data, indent=2)}", flush=True)

# ── CHROMADB ──────────────────────────────────────────────────────
print(f"\n{'='*55}", flush=True)
print("CHROMADB STATUS", flush=True)
sys.path.insert(0,'/home/claude/la/agents/server')
sys.path.insert(0,'/home/claude/la/agents/ingestion')
import chromadb as cdb
client = cdb.PersistentClient(path='/tmp/chroma_chief')
for col in client.list_collections():
    c = client.get_collection(col.name)
    print(f"  Collection '{col.name}': {c.count()} Dokumente", flush=True)

# ── ZUSAMMENFASSUNG ───────────────────────────────────────────────
print(f"\n{'='*55}", flush=True)
print("ZUSAMMENFASSUNG", flush=True)
ok = sum(1 for r in results if r["status"]=="OK")
print(f"Tests: {ok}/{len(results)} OK", flush=True)
for r in results:
    icon = "✓" if r["status"]=="OK" else "✗"
    print(f"  {icon} {r['agent']}: {r['tokens']} tokens, {r['zeit']}s", flush=True)

report = {"timestamp":datetime.now().isoformat(),"results":results,"summary":{"total":len(results),"ok":ok}}
with open('/tmp/test_results.json','w') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f"\nReport gespeichert: /tmp/test_results.json", flush=True)
print(f"Ende: {datetime.now().isoformat()}", flush=True)
