---
type: Runbook
status: current
updated_at: 2026-07-30
stale_after: 2026-09-25
environment: sandbox
components: [llama-server, litellm, chromadb, phoenix, fastapi]
---
# SANDBOX.md — Local Agent, Claude Sandbox

**Zuletzt aktualisiert:** 2026-07-30
**Zweck:** Vollständige Anleitung um die Sandbox-Umgebung in einer neuen
Claude.ai Session von Grund auf neu aufzubauen.

Diese Datei beschreibt ausschließlich die **Sandbox-Umgebung**. Für die
anderen beiden Umgebungen siehe [HOST.md](HOST.md) und [DOCKER.md](DOCKER.md).

---

## Rollen im Projekt

| Rolle | Modell | Aufgabe |
|-------|--------|---------|
| **Mutterchat** | Sonnet | Architektur, Entscheidungen, GitHub-Operationen |
| **Develop-Chat** | Sonnet | Code entwickeln, Commits pushen |
| **Sandbox** | Haiku | Stack starten, testen, Ergebnisse melden — kein Code, keine Pushes |

Die Sandbox wird nur bei Bedarf aufgesetzt — nicht dauerhaft parallel betrieben.
Testergebnisse werden ausschließlich von der Sandbox gepusht, nie vom Mutterchat.

---

## Kontext-Prompt für neue Sandbox-Sessions

```
Baue die Sandbox-Umgebung für "Local Agent" (janhetzler/la) vollständig
neu auf — folge dabei strikt docs/SANDBOX.md aus dem Repository. Das ist
der aktuelle, gepflegte Aufbau-Guide; nutze keine anderen Quellen oder
Annahmen aus deinem Training.

## Kontext — wichtig zu wissen

Du bist eine neue Sandbox-Session für dieses Projekt. Vorherige Sandbox-
Sessions haben den Stack aufgebaut, getestet und alle Ergebnisse nach
GitHub gepusht — daraus ist docs/SANDBOX.md entstanden. Du fängst
komplett frisch an, rein auf Basis dessen was im Repository dokumentiert ist.

Falls du auf docs/SANDBOX_1.md oder docs/SANDBOX_1_TESTRESULTS.md stößt:
das sind historische Momentaufnahmen, keine aktuelle Anleitung — zur
Information, nicht zum Befolgen. Deine Referenz ist ausschließlich
docs/SANDBOX.md.

## Deine Rolle

Du bist die Sandbox — deine einzige Aufgabe ist:
1. Stack aufbauen (Schritte 1-6)
2. Tests ausführen
3. Ergebnis klar berichten

Du entwickelst keinen Code, pushst nichts zu GitHub (außer Testergebnisse
wenn explizit angewiesen), und triffst keine Architektur-Entscheidungen.
Diese Entscheidungen kommen vom Mutterchat.

## Vorgehen

Arbeite die Abschnitte 1-6 aus docs/SANDBOX.md der Reihe nach ab:
1. Disk-Platz prüfen
2. Repository klonen
3. Pakete installieren
4. Modelle herunterladen (Token wird benötigt — siehe Dokument)
5. Stack starten
6. Tests ausführen

Nutze außerdem die drei vorbereiteten Hilfsskripte unter scripts/sandbox/
(README.md dort erklärt wann welches sinnvoll ist):
- import_check.py — schneller Check ob alle Module fehlerfrei importieren
- start_quick.py — schlanker Start + 1-2 Requests, zeitsicher
- start_full.py — vollständiger Stack + kompletter Testlauf

## Wichtige Hintergründe, die du kennen solltest

- Diese Sandbox läuft mit sehr begrenztem Speicher/CPU (siehe Hardware-
  Tabelle in der README.md des Repos). Nutze das kleine Granite-350m-Modell,
  nicht das große Host-Modell.
- Ein einzelner bash_tool-Call ist die harte Grenze für alles was du
  startest — Hintergrundprozesse (Threads, Subprocesses) sterben vollständig
  sobald der Call endet. Deshalb müssen Stack-Start und Tests in einem
  einzigen zusammenhängenden Aufruf laufen.
- Nutze zuerst import_check.py (schnell, geringes Risiko) bevor du den
  vollen Stack startest.
- docs/BUGS.md enthält bekannte, noch offene Probleme. Lies diese Datei
  bevor du mit MCP-Tests beginnst.
- Es gibt KEINE handoff.md — falls du auf alte Erwähnungen davon stößt,
  ignoriere sie. docs/SANDBOX.md ist die einzige gültige Quelle.

## Was ich von dir am Ende brauche

Ein klarer Bericht:
- Ist jeder der 6 Schritte aus docs/SANDBOX.md ohne Anpassung so gelaufen
  wie dokumentiert, oder gab es Abweichungen? Wenn ja, welche genau?
- Funktioniert der Stack vollständig?
- Ist etwas in docs/SANDBOX.md ungenau, veraltet oder fehlend — aus der
  Perspektive von jemandem, der die Datei zum ersten Mal liest und
  ausschließlich ihr folgt?

Gehe Schritt für Schritt vor, nicht alles auf einmal. Committe/pushe
nichts, außer ich sage es dir ausdrücklich.
```

---

## 1. Disk-Platz prüfen (Minimum 2 GB frei)

```bash
df -h /
# System-Pakete die Platz fressen aber nicht von uns sind:
# nvidia 2.7GB, triton 641MB, opencv 200MB — NICHT anfassen
```

---

## 2. Repository

```bash
git clone https://github.com/janhetzler/la /home/claude/la
cd /home/claude/la
```

---

## 3. Pakete installieren

```bash
pip install --break-system-packages -r requirements.txt
```

> **Hinweis:** Die Datei heißt `requirements.txt` (nicht `requirements-host.txt`).

### 3b. llama-server Binary herunterladen

```bash
mkdir -p /tmp/llama-b9895
curl -L https://github.com/ggml-org/llama.cpp/releases/download/b9895/llama-b9895-bin-ubuntu-x64.tar.gz \
  -o /tmp/llama.tar.gz
tar -xzf /tmp/llama.tar.gz -C /tmp/llama-b9895 --strip-components=1
chmod +x /tmp/llama-b9895/llama-server

# Version und --jinja Flag prüfen
/tmp/llama-b9895/llama-server --version
/tmp/llama-b9895/llama-server --help | grep -i jinja
# Erwartet: --jinja erscheint in der Ausgabe
```

> **Hinweis:** Die Binary liegt dauerhaft unter `/tmp/llama-b9895/llama-server`.
> Sie wird von `start_full.py`, `start_quick.py`, `inspect_phoenix.py` und
> `test_mcp_toolcall.py` als Subprocess gestartet (nicht mehr als Python-Import).
> Details zum Swap: `docs/LLAMA.md`.

---

## 4. Modelle herunterladen

```bash
# Reasoning Modell (213 MB)
curl -L -o /tmp/granite-350m-Q4_K_M.gguf \
  -H "Authorization: Bearer GH_TOKEN" \
  "https://github.com/janhetzler/la/releases/download/granite-models/granite-4.0-h-350m-Q4_K_M.gguf"

# Embedding Modell (28 MB)
curl -L -o /tmp/granite-embedding-30m-Q4_0.gguf \
  -H "Authorization: Bearer GH_TOKEN" \
  "https://github.com/janhetzler/la/releases/download/granite-models/granite-embedding-30m-english-Q4_0.gguf"
```

`GH_TOKEN` = persönlicher GitHub-Token (wird separat mitgeteilt).

---

## 5. Stack starten (alles in einem Block)

**Wichtig:** Alle Hintergrundprozesse sterben wenn der bash-Aufruf endet.
Der komplette Stack muss deshalb in einem einzigen Python-Block gestartet werden.

Empfehlung: Starte zuerst den Import-Check, dann den Stack:

```bash
# Schritt 1: Import-Check (2 Sekunden, kein Risiko)
cd /home/claude/la && python3 scripts/sandbox/import_check.py

# Schritt 2a: Schlanker Stack (90s, sicher)
cd /home/claude/la && python3 scripts/sandbox/start_quick.py

# Schritt 2b: Vollständiger Stack + 6-Agenten-Test (~3 Min)
cd /home/claude/la && python3 scripts/sandbox/start_full.py
```

**llama-server Flags** (Pflicht — `--embeddings --pooling mean` für ChromaDB):

```bash
/tmp/llama-b9895/llama-server \
  -m /tmp/granite-350m-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 \
  --jinja --ctx-size 32768 \
  --parallel 1 --log-disable \
  --embeddings --pooling mean
```

> `--embeddings --pooling mean` ist Pflicht. Ohne diese Flags schlägt
> ChromaDB beim Schreiben fehl (kein `/v1/embeddings` Endpoint verfügbar).

**LiteLLM-Konfiguration** (wird von `start_full.py` dynamisch erzeugt,
Pfad `/tmp/litellm_sandbox.yaml`):

```yaml
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
  master_key: sk-cos-local-dev
litellm_settings:
  drop_params: true
  set_verbose: false
  success_callback: ["arize_phoenix"]
  failure_callback: ["arize_phoenix"]
```

> `granite-embed` zeigt auf Port 8081 — eigenstaendiger Embedding-Server
> mit `granite-embedding-30m-Q4_0.gguf`. Gestartet ohne `--jinja`.

**Start-Reihenfolge** (intern in `start_full.py`):
1. llama-server :8080 (`--jinja --embeddings --pooling mean`)
2. llama-server-embed :8081 (`--embeddings --pooling mean`, kein `--jinja`)
3. Phoenix :6006
4. LiteLLM :4000
5. LiteLLM → llama-server Readiness-Check (echter POST-Request, nicht nur Port-Ping)
6. LiteLLM → granite-embed Readiness-Check (echter Embeddings-Request)
7. Agent Config + Phoenix Tracing init
8. Agent Server :8002
9. ChromaDB `notes` Collection initialisieren (cosine)
10. Test Suite

---

## 6. Tests ausführen

```bash
cd /home/claude/la && python3 scripts/sandbox/start_full.py
```

Test-Ergebnisse werden auf der Konsole ausgegeben.
Logs liegen unter `/tmp/logs/`.

---

## 8. Terminal-Chat (Ersatz für VS Code Language Model API)

Die Sandbox hat keinen Web-Zugang für eine VS Code Verbindung. `scripts/chat.py`
ist der direkte Ersatz — ein Terminal-Client der gegen LiteLLM (Port 4000) spricht,
LiteLLM leitet zum Agent Server (Port 8002) weiter, der Supervisor routet zum
richtigen Spezialisten.

```bash
python3 scripts/chat.py
```

---

## A. Installierte Pakete (Stand 2026-07-20)

### Aktiv

| Paket | Version | Zweck |
|-------|---------|-------|
| langchain | 1.2.15 | Agent Framework |
| langchain-core | 1.3.2 | LangChain Kern |
| langchain-openai | 1.2.1 | LLM Client |
| langchain-mcp-adapters | 0.2.2 | MCP Integration |
| langgraph | 1.1.10 | Agent Orchestrierung |
| chromadb | 1.5.9 | Vektor Datenbank |
| litellm | 1.92.0 | API Gateway |
| arize-phoenix | 18.0.0 | Observability |
| openinference-instrumentation-langchain | 0.1.67 | Phoenix → LangChain |
| opentelemetry-sdk | 1.43.0 | Tracing |
| opentelemetry-exporter-otlp | 1.43.0 | Tracing Export |
| starlette-context | 0.5.1 | ASGI Middleware (uvicorn Abhängigkeit) |
| mcp-server-git | 2026.7.10 | Git MCP Tools |
| mcp-server-fetch | 2026.7.10 | Web Fetch MCP Tool |
| openai | >=2.26.0 (2.45.0 getestet) | API Client |
| fastapi | 0.139.0 | Agent Server |
| uvicorn | 0.51.0 | ASGI Server |
| httpx | 0.28.1 | HTTP Client |
| python-dotenv | 1.2.2 | Env-Variablen |
| llama-index-core | 0.14.23 | RAG / Embeddings |
| llama-index-embeddings-litellm | 0.5.0 | LiteLLM Embeddings |
| llama-index-instrumentation | 0.5.0 | LlamaIndex Tracing |
| llama-index-workflows | 2.22.2 | LlamaIndex Workflows |
| pydantic | 2.12.5 | Datenvalidierung |
| numpy | 2.4.4 | Numerik |
| tqdm | 4.67.3 | Fortschrittsbalken |

### Disabled (installiert, aber nicht aktiv)

| Paket | Grund |
|-------|-------|
| headroom-ai | DISABLED — benötigt headroom-ai[all] (~500MB + ONNX) |
| docling | DISABLED — zu groß, Import in ingest.py auskommentiert |

### Bewusst nicht installiert

| Paket | Grund |
|-------|-------|
| torch / transformers | Nicht benötigt, Embeddings via llama-server |
| qdrant-client | Ersetzt durch ChromaDB |
| langchain-ollama / ollama | Ersetzt durch llama-server |
| sounddevice / soundfile | Kein Audio in der Sandbox |

---

## B. Modelle

| Modell | Größe | Port | Zweck |
|--------|-------|------|-------|
| granite-4.0-h-350m-Q4_K_M.gguf | 213 MB | 8080 | Reasoning + Embeddings |
| granite-embedding-30m-english-Q4_0.gguf | 28 MB | 8081 | Spezialisiertes Embedding-Modell |

Beide als GitHub Release Assets unter dem Tag `granite-models`.

**Embedding-Strategie:** Das spezialisierte 30m Embedding-Modell laeuft als
eigenstaendiger llama-server auf Port 8081 (`--embeddings --pooling mean`,
kein `--jinja`). Das 350m Reasoning-Modell auf Port 8080 behaelt ebenfalls
`--embeddings --pooling mean` — LiteLLM routet `granite-embed` aber
ausschliesslich auf Port 8081.

---

## C. Ports

| Port | Dienst |
|------|--------|
| 8080 | llama-server Binary b9895 (`--jinja --embeddings --pooling mean`) |
| 8081 | llama-server-embed (granite-embedding-30m, `--embeddings --pooling mean`) |
| 8787 | Headroom Proxy — DISABLED |
| 6006 | Phoenix |
| 4000 | LiteLLM |
| 8002 | Agent Server |

---

## D. Datenstrukturen

### ChromaDB Collections (`/tmp/chroma_la/`)

| Collection | Inhalt | Wer schreibt |
|------------|--------|--------------|
| `notes` | Persönliche Notizen (Notes Agent) | `agents/server/notes.py` |
| `documents` | Ingested Dokumente (RAG) | `agents/ingestion/ingest.py` |

ChromaDB läuft als `PersistentClient` mit cosine-Distanz:

```python
client.get_or_create_collection(
    name='notes',
    metadata={"hnsw:space": "cosine"}
)
```

Daten bleiben in der Sandbox-Session erhalten, aber **nicht** zwischen
Sessions (tmpfs).

### Agent Registry (`agents/server/server.py`)

```python
AGENTS = {
    "agent-researcher": invoke_researcher_v2,
    "agent-comms":      invoke_comms,
    "agent-notes":      invoke_notes,
    "agent-code":       invoke_code,
    "agent-handoff":    invoke_handoff,
    "agent-local":      invoke_supervisor,   # ← Haupt-Endpoint
}
```

### Supervisor Routing (`agents/server/supervisor.py`)

Zweistufiges Routing:
1. **Heuristik** (`router_heuristic.py`) — Emoji + Keywords, 0ms, 8/8 OK
2. **LLM-Fallback** — nur wenn Heuristik kein Ergebnis liefert

```python
VALID_AGENTS = {"meta", "researcher", "comms", "notes", "code", "handoff"}
```

### Tool-Calling Format (Granite)

`tool_formatter.py` übersetzt OpenAI Tool-Definitionen ins native Granite XML-Format:

```xml
<tool_call>
{"name": "save_note", "arguments": {"text": "Meine Notiz", "title": "Titel"}}
</tool_call>
```

### MCP-Server (`mcp/sandbox/mcp.json`)

```json
{
  "mcpServers": {
    "git":   { "command": "python3", "args": ["-m", "mcp_server_git", "--repository", "/home/claude/la"] },
    "fetch": { "command": "python3", "args": ["-m", "mcp_server_fetch"] }
  }
}
```

---

## E. Bekannte Fixes

**Fix 1 — Phoenix skip_dep_check**
```python
# In telemetry.py — bereits eingebaut:
LangChainInstrumentor().instrument(
    tracer_provider=tracer_provider,
    skip_dep_check=True  # pydantic Metadaten-Konflikt
)
```

**Fix 2 — LiteLLM Readiness Check**
```python
# Nach LiteLLM Start — echter Request statt nur Port-Check:
req = urllib.request.Request(
    'http://127.0.0.1:4000/v1/chat/completions',
    data=json.dumps({'model':'granite-tiny',
        'messages':[{'role':'user','content':'hi'}],
        'max_tokens':3}).encode(), ...)
urllib.request.urlopen(req, timeout=30)
```

**Fix 3 — args_schema für MCP Tools**
```python
schema = dict(tool.args_schema)  # statt tool.args_schema.schema()
```

---

## F. Logging

Alle Logs liegen einheitlich unter `/tmp/logs/`:

| Datei | Komponente | Status |
|---|---|---|
| `/tmp/logs/litellm.log` | LiteLLM | ✓ funktioniert |
| `/tmp/logs/phoenix.log` | Phoenix | ✓ funktioniert |
| `/tmp/logs/llama-server.log` | Reasoning Server | ✓ via subprocess.Popen |
| `/tmp/logs/agent-server.log` | Agent Server | ⚠️ bleibt leer (uvicorn Thread-Logging) |

`start_full.py` prüft nach jedem Service-Start die Log-Datei auf
`ERROR:`, `Exception:`, `Traceback`, `CRITICAL`.

---

## G. Testergebnisse (Stand 2026-07-31, aktualisiert 2026-07-31)

| Test | Ergebnis |
|------|----------|
| llama-server :8080 (Binary b9895, --jinja) | ✓ ~27 t/s, Startup ~2s |
| llama-server Embeddings (--embeddings --pooling mean) | ✓ 768-dim |
| LiteLLM | ✓ |
| Phoenix Traces | ✓ |
| Agent Server | ✓ 6/6 Agenten registriert |
| ChromaDB cosine Collection | ✓ |
| Heuristik-Routing | ✓ 8/8 Test-Cases |
| tool_formatter.py | ✓ 18/18 Tests |
| Comms Agent | ✓ |
| Code Agent | ✓ |
| Researcher Agent | ✓ |
| Handoff Agent | ✓ |
| Notes Agent | ✓ save_note schreibt in ChromaDB notes Collection (BUG-019 behoben) |
| Supervisor Routing | ✓ Meta-Antwort korrekt (74 Zeichen) — BUG-024 geschlossen |

**Routing-Hinweis:** Heuristik löst 80% der Fälle ohne LLM-Call.
LLM-Router (Grammar Constraint) funktioniert korrekt fuer den Rest.
Auf dem Host mit Granite-Tiny (4B) entfaellt die Heuristik-Abhängigkeit.

---

## H. Bekannte offene Punkte

- **BUG-024 — GESCHLOSSEN (2026-07-31):** Ursache war `max_tokens` im
  Supervisor-Routing-Test von `start_full.py` — das 350m-Modell liefert
  Minimalantworten wenn `max_tokens` explizit gesetzt wird. Fix: Meta-Test
  ohne `max_tokens`. Verifiziert: 6/6 Agenten OK (Commit e0221a69).

- **BUG-020 — Researcher EISDIR:** `read_text_file` wird auf ein Verzeichnis
  aufgerufen. Workaround in researcher_v2.py vorhanden. (Geschlossen — Workaround aktiv)

- **BUG-025 — Hardcoded Collection-Name in notes.py:** `save_note` und
  `search_meetings` verwenden hardcoded String `"notes"` statt einer Config-Variable.
  Fix: `CHROMA_NOTES_COLLECTION` in `config.py` einführen, `notes.py` anpassen.

- **Embedding-Server (Port 8081)** laeuft als eigenstaendiger llama-server
  mit `granite-embedding-30m-Q4_0.gguf`. LiteLLM `granite-embed` zeigt auf :8081.

- **Agent Server Logs** bleiben leer — uvicorn Thread-Logging funktioniert
  in der Sandbox nicht. Kein funktionaler Fehler.

---

- Repository: https://github.com/janhetzler/la
- Original-Projekt: https://github.com/xaviervasques/chief-of-staff
- Architektur-Entscheidungen: [ROADMAP.md](ROADMAP.md)
