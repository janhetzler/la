# OPERATIONS_SANDBOX.md — Betrieb & Logging (Sandbox)

**Umgebung:** Claude Sandbox (bash_tool, Claude Container)
**Zuletzt aktualisiert:** 2026-07-20
**Verwandt:** OPERATIONS_HOST.md, OPERATIONS_DOCKER.md

---

## Uebersicht: Alle Komponenten

| Komponente | Port | Log-Datei | Log-Level | Status |
|------------|------|-----------|-----------|--------|
| llama-server | 8080 | `/tmp/logs/llama-server.log` | `--log-disable` | ⚠️ leer |
| Phoenix | 6006 | `/tmp/logs/phoenix.log` | default | ✅ aktiv |
| LiteLLM | 4000 | `/tmp/logs/litellm.log` | `set_verbose: false` | ✅ aktiv |
| Agent Server | 8002 | `/tmp/logs/agent-server.log` | `error` | ⚠️ leer |
| ChromaDB | — | kein separates Log | — | in-process |

**Log-Verzeichnis:** `/tmp/logs/` (wird bei jedem Stack-Start angelegt)

⚠️ **Wichtig:** `/tmp/` ist nicht persistent — Logs sterben mit der Sandbox-Session.

---

## 1. llama-server (Binary b9895)

**Zweck:** Reasoning Model Server — Granite 350m Q4_K_M

**Start-Befehl:**
```bash
/tmp/llama-b9895/llama-server \
  -m /tmp/granite-350m-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 \
  --ctx-size 32768 --parallel 1 \
  --jinja --log-disable
```

**Log-Datei:** `/tmp/logs/llama-server.log`

**Log-Level:** `--log-disable` — alle Logs deaktiviert

**Status:** ⚠️ Log bleibt leer — `--log-disable` unterdrückt jede Ausgabe.

**Debugging ohne Logs:**
```bash
# Health-Check
curl http://127.0.0.1:8080/v1/models

# Direkter Chat-Request
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"granite-tiny","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

**Beim Komponenten-Tausch prüfen:**
- Binary vorhanden? `ls -lh /tmp/llama-b9895/llama-server`
- `--jinja` Flag verfuegbar? `./llama-server --help | grep jinja`
- Port 8080 frei? `lsof -i :8080`
- Modell vorhanden? `ls -lh /tmp/granite-350m-Q4_K_M.gguf`

**Log-Level aendern (fuer Debugging):**
```bash
# Statt --log-disable: mit Logs starten
/tmp/llama-b9895/llama-server -m [MODEL] --port 8080 --jinja \
  > /tmp/llama-debug.log 2>&1 &
```

**Bekannte Probleme:**
- `--log-level error` existiert nicht in b9895 — nur `--log-disable`
- Log bleibt leer weil `--log-disable` alle Ausgaben unterdrückt

---

## 2. Phoenix (Arize Phoenix 18.0.0)

**Zweck:** Observability — LLM Traces, Spans, Token-Counts

**Start-Befehl:**
```bash
python3 -m phoenix.server.main serve --host 127.0.0.1 --port 6006
```

**Log-Datei:** `/tmp/logs/phoenix.log`

**Log-Level:** Standard (nicht konfiguriert)

**Status:** ✅ Log aktiv

**Web-Interface:** http://127.0.0.1:6006 (nicht erreichbar aus Sandbox-Browser)

**Readiness-Check:**
```bash
curl http://127.0.0.1:6006/v1/projects
# Erwartet: JSON mit Projekt-Liste
```

**Traces auslesen:**
```python
from phoenix.client import Client
from datetime import datetime, timedelta
client = Client(base_url="http://127.0.0.1:6006")
spans_df = client.spans.get_spans_dataframe(
    project_identifier="local-agent",
    limit=50,
    start_time=datetime.now() - timedelta(minutes=5)
)
```

**Bekannte Probleme:**
- False Positive: `CREATE TABLE` SQL-Statements enthalten String `"ERROR"` —
  kein echter Fehler (siehe BUGS.md)
- Traces nur verfuegbar solange Phoenix laeuft — nach Stack-Stop nicht mehr
  via Client abrufbar

**Beim Komponenten-Tausch prüfen:**
- Traces werden gesammelt? (LangChainInstrumentor aktiv?)
- `skip_dep_check=True` gesetzt? (pydantic Konflikt)
- Readiness via `/v1/projects` (nicht `/healthz`)

---

## 3. LiteLLM (1.92.0)

**Zweck:** API Gateway — unified OpenAI-compatible endpoint fuer alle Modelle

**Start-Befehl:**
```bash
litellm --config /tmp/litellm_phoenix.yaml --host 127.0.0.1 --port 4000
```

**Konfiguration (`/tmp/litellm_phoenix.yaml`):**
```yaml
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
  master_key: sk-cos-local-dev
litellm_settings:
  drop_params: true
  set_verbose: false
  success_callback: ["arize_phoenix"]
  failure_callback: ["arize_phoenix"]
```

**Log-Datei:** `/tmp/logs/litellm.log`

**Log-Level:** `set_verbose: false`

**Status:** ✅ Log aktiv

**Readiness-Check (echter Request — nicht nur Port-Ping):**
```bash
curl -X POST http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-cos-local-dev" \
  -H "Content-Type: application/json" \
  -d '{"model":"granite-tiny","messages":[{"role":"user","content":"hi"}],"max_tokens":3}'
```

**Bekannte Probleme:**
- Health-Endpoint `/health` gibt 200 bevor Modell-Verbindung steht —
  immer echten Request als Readiness-Check nutzen
- `extra_body={"grammar":...}` funktioniert jetzt ohne Fehler (behoben 2026-07-20)
- SQLite nicht unterstuetzt fuer master_key — PostgreSQL noetig fuer
  erweiterte Features (Grammar Constraints waren davon betroffen, jetzt OK)

**Beim Komponenten-Tausch prüfen:**
- `master_key` in Config identisch mit `LITELLM_KEY` im Stack?
- `drop_params: true` gesetzt? (verhindert unbekannte Parameter-Fehler)
- Phoenix Callbacks aktiv? (`success_callback: ["arize_phoenix"]`)

---

## 4. Agent Server (FastAPI + uvicorn)

**Zweck:** Agenten-Orchestrierung — Supervisor + 6 Spezialisten

**Start-Befehl (intern via uvicorn Thread):**
```python
uvicorn.Server(uvicorn.Config(
    app, host='127.0.0.1', port=8002,
    log_level='error', log_config=log_config
)).run()
```

**Log-Datei:** `/tmp/logs/agent-server.log`

**Log-Level:** `error`

**Status:** ⚠️ Log bleibt leer — uvicorn Thread-Logging funktioniert nicht
zuverlässig in dieser Konfiguration

**Readiness-Check:**
```bash
curl http://127.0.0.1:8002/health
```

**Agenten-Endpunkte:**
```bash
# Supervisor (Haupt-Endpoint)
curl -X POST http://127.0.0.1:8002/v1/chat/completions \
  -H "Authorization: Bearer sk-cos-local-dev" \
  -H "Content-Type: application/json" \
  -d '{"model":"agent-local","messages":[{"role":"user","content":"hi"}],"max_tokens":100}'
```

**Bekannte Probleme:**
- Log bleibt leer — uvicorn Thread gibt Logs nicht an FileHandler weiter
- Debugging nur via Phoenix Traces moeglich
- `import uvicorn` muss separat bleiben — nicht mit llama-Block entfernen

**Beim Komponenten-Tausch prüfen:**
- Alle 6 Agenten registriert? (`/health` zeigt Agent-Liste)
- `mcp.json` Pfad korrekt? (Pre-Flight Fix in tools.py — siehe SANDBOX.md Schritt 5)
- Phoenix Tracing aktiv? (`LangChainInstrumentor` in telemetry.py)

---

## 5. ChromaDB (1.5.9)

**Zweck:** Vektor-Datenbank fuer Notes-Agent und RAG

**Start:** In-process (kein separater Server)

**Datenpfad:** `/tmp/chroma_la/`

**Log:** Kein separates Log — Ausgaben gehen nach stdout/stderr des Agent Servers

**Collections:**

| Collection | Inhalt | Wer schreibt |
|------------|--------|-------------|
| `notes` | Persoenliche Notizen | `agents/server/notes.py` |
| `documents` | RAG-Dokumente | `agents/ingestion/ingest.py` |

**Status prüfen:**
```python
import chromadb
client = chromadb.PersistentClient(path="/tmp/chroma_la")
for col in client.list_collections():
    print(f"{col.name}: {col.count()} Dokumente")
```

**Bekannte Probleme:**
- Notes-Agent schreibt nicht — Routing-Limit 350m (kein ChromaDB-Bug)
- Daten nicht persistent zwischen Sessions (tmpfs)

**Beim Komponenten-Tausch prüfen:**
- Collection-Schema kompatibel mit neuer Version?
- `LiteLLMEmbedding` via Port 8080 erreichbar?

---

## 6. Log-Check Routine (in start_full.py)

Nach jedem Service-Start und nach jedem Test läuft automatisch:

```python
def check_log(log_file, label):
    # Prueft auf ERROR, Exception, Traceback, CRITICAL
    # Gibt Warnung aus wenn gefunden
```

**False Positive bekannt:** Phoenix `CREATE TABLE` SQL enthaelt `"ERROR"` —
kein echter Fehler. Fix: Log-Check auf `"ERROR:"` mit Doppelpunkt eingrenzen.

---

## 7. Trace-Logs (neu seit 2026-07-20)

**Zweck:** Vollstaendige Request-Kette dokumentieren

**Erzeugt von:** `scripts/sandbox/inspect_phoenix.py`

**Ablage:** `docs/traces/sandbox/YYYY-MM-DD_[slug].md`

**Inhalt jeder Trace-Datei:**
- Finaler Request + Antwort
- Alle Phoenix Spans (vollstaendiger Input/Output)
- Aktive Prompt-Version (router.md)
- LiteLLM + llama-server Logs zum Zeitpunkt des Requests

**Wann ausfuehren:**
- Nach jeder Prompt-Aenderung
- Nach jedem Komponenten-Tausch
- Als Baseline vor groesseren Aenderungen

---

## 8. Standard-Debugging-Workflow

```bash
# 1. Stack-Status prüfen
curl http://127.0.0.1:8080/v1/models   # llama-server
curl http://127.0.0.1:6006/v1/projects # Phoenix
curl http://127.0.0.1:4000/health      # LiteLLM
curl http://127.0.0.1:8002/health      # Agent Server

# 2. Logs lesen
tail -50 /tmp/logs/litellm.log
tail -50 /tmp/logs/phoenix.log
cat /tmp/logs/llama-server.log   # meist leer

# 3. Trace erzeugen
cd /home/claude/la && python3 scripts/sandbox/inspect_phoenix.py

# 4. Trace lesen
ls -lt docs/traces/sandbox/ | head -5
cat docs/traces/sandbox/[neueste-datei].md
```
