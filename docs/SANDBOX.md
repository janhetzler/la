# SANDBOX.md — Local Agent, Claude Sandbox

**Zuletzt aktualisiert:** 2026-07-20
**Zweck:** Vollständige Anleitung um die Sandbox-Umgebung in einer neuen
Claude.ai Session von Grund auf neu aufzubauen.

Diese Datei beschreibt ausschließlich die **Sandbox-Umgebung**. Für die
anderen beiden Umgebungen siehe [HOST.md](HOST.md) und [DOCKER.md](DOCKER.md).

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

## Vorgehen

Arbeite die Abschnitte 1-7 aus docs/SANDBOX.md der Reihe nach ab:
1. Disk-Platz prüfen
2. Repository klonen
3. Pakete installieren
4. Modelle herunterladen (Token wird benötigt — siehe Dokument)
5. Pre-Flight Fix (mcp.json Pfad — PFLICHT vor Stack-Start)
6. Stack starten
7. Tests ausführen

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
- Ist jeder der 7 Schritte aus docs/SANDBOX.md ohne Anpassung so gelaufen
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

> **Hinweis:** Die Datei heißt `requirements.txt` (nicht `requirements-janhet.txt`).

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

## 5. Pre-Flight Fix — mcp.json Pfad (PFLICHT vor Stack-Start)

> ⚠️ **Dieser Fix ist zwingend erforderlich für jede neue Sandbox-Session.**
> Ohne ihn schlägt der Agent Server beim Start mit `FileNotFoundError` fehl.
> Details: `BUGS.md` → Abschnitt "mcp.json Pfad nach Ordner-Umstrukturierung".

**Problem:** `agents/server/tools.py` Z.39 liest `PROJECT_ROOT / "mcp" / "mcp.json"`,
aber die Datei liegt nach der Ordner-Umstrukturierung unter `mcp/sandbox/mcp.json`.

**Fix:**

```bash
sed -i 's|PROJECT_ROOT / "mcp" / "mcp.json"|PROJECT_ROOT / "mcp" / "sandbox" / "mcp.json"|' \
  /home/claude/la/agents/server/tools.py

# Prüfen:
grep "config_path" /home/claude/la/agents/server/tools.py
# Soll zeigen: config_path = PROJECT_ROOT / "mcp" / "sandbox" / "mcp.json"
```

> **Offen:** Dieser Fix ist eine lokale Sandbox-Anpassung, kein Commit.
> Die eigentliche Lösung (Umgebungsvariable `LOCAL_AGENT_ENV`) ist noch nicht
> implementiert — siehe `BUGS.md`. Sobald sie fertig ist, entfällt dieser
> manuelle Schritt.

---

## 6. Stack starten (alles in einem Block)

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

Oder manuell (entspricht `tests/run_tests.py`):

```bash
cd /home/claude/la && python3 tests/run_tests.py
```

**LiteLLM-Konfiguration** (wird von `run_tests.py` / `start_full.py` dynamisch erzeugt,
Pfad `/tmp/litellm_test.yaml`):

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

**Start-Reihenfolge** (intern in `run_tests.py`):
1. llama-server :8080 (Reasoning)
2. Phoenix :6006
3. LiteLLM :4000
4. LiteLLM → llama-server Readiness-Check (echter POST-Request, nicht nur Port-Ping)
5. Agent Config + Phoenix Tracing init
6. Agent Server :8002
7. Test Suite (`tests/test_stack.py`)

**Embedding-Server (Port 8081)** wird von `run_tests.py` **nicht** gestartet.
ChromaDB nutzt in der Sandbox `LiteLLMEmbedding` via Port 8080 (nicht 8081).
Das Embedding-Modell unter `/tmp/granite-embedding-30m-Q4_0.gguf` ist für die
Sandbox-Tests aktuell nicht aktiv in Verwendung.

---

## 7. Tests ausführen

```bash
cd /home/claude/la && python3 tests/run_tests.py
```

Oder über den Wrapper:

```bash
cd /home/claude/la && python3 scripts/sandbox/start_full.py
```

`start_full.py` ist ein reiner Wrapper, der `tests/run_tests.py` aufruft.
`tests/run_tests.py` ist die kanonische Quelle — nicht duplizieren.

Test-Report landet in `/tmp/test_results.json`.

---

## 8. Terminal-Chat (Ersatz für VS Code Language Model API)

Die Sandbox hat keinen Web-Zugang für eine VS Code Verbindung. `scripts/chat.py`
ist der direkte Ersatz — ein Terminal-Client der gegen LiteLLM (Port 4000) spricht,
LiteLLM leitet zum Agent Server (Port 8002) weiter, der Supervisor routet zum
richtigen Spezialisten. Das entspricht dem Original-Konzept aus
`docker/litellm_config.yaml` (dort: `agent-chief-of-staff` → Port 8002).

```bash
python3 scripts/chat.py
```

`model="agent-local"` — funktioniert, seit `litellm_config.yaml` um den
`agent-local` Endpoint ergänzt wurde (Port 8002). Bestätigt getestet 2026-07-16:
Supervisor antwortet korrekt über diesen Pfad.

⚠️ **Bekannte Kleinigkeit:** `chat.py` Z.10 zeigt noch den alten Begrüßungstext
`"=== Chief-of-Staff Terminal Chat ==="` — kosmetisch, keine Funktionsauswirkung,
noch nicht nachgezogen bei der Umbenennung.

⚠️ **Timing beim Start:** `litellm.log` zeigt beim Hochfahren kurzzeitig
`ConnectionRefusedError` auf Port 8002, weil LiteLLM einen Readiness-Check
ausführt bevor der Agent Server bereit ist. Der eigentliche Request danach
funktioniert. Kein funktionaler Fehler, aber beim Log-Lesen nicht verwirren lassen.

---

## A. Installierte Pakete (Stand 2026-07-16)

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
| granite-4.0-h-350m-Q4_K_M.gguf | 213 MB | 8080 | Reasoning |
| granite-embedding-30m-english-Q4_0.gguf | 28 MB | (8081, derzeit ungenutzt) | Embeddings |

Beide als GitHub Release Assets unter dem Tag `granite-models`.

**Embedding-Server-Status:** Das Embedding-Modell wird heruntergeladen,
aber Port 8081 wird in der Sandbox nicht gestartet. ChromaDB nutzt
`LiteLLMEmbedding` über Port 8080 (Reasoning-Server).

---

## C. Ports

| Port | Dienst |
|------|--------|
| 8080 | Reasoning llama-server Binary b9895 (--jinja aktiv) |
| 8081 | Embedding llama-server — NICHT gestartet in Sandbox-Tests |
| 8787 | Headroom Proxy — DISABLED |
| 6006 | Phoenix |
| 4000 | LiteLLM |
| 8002 | Agent Server |

---

## D. Datenstrukturen

### ChromaDB Collections (`/tmp/chroma_chief/`)

| Collection | Inhalt | Wer schreibt |
|------------|--------|--------------|
| `notes` | Persönliche Notizen (Notes Agent) | `agents/server/notes.py` |
| `documents` | Ingested Dokumente (RAG) | `agents/ingestion/ingest.py` |

ChromaDB läuft als `PersistentClient` — Daten bleiben in der Sandbox-Session
erhalten, aber **nicht** zwischen Sessions (tmpfs).

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

```python
VALID_AGENTS = {"meta", "researcher", "comms", "notes", "code", "handoff"}
```

Der Supervisor erkennt Sprache, routet, dann delegiert an den entsprechenden
Spezialisten. `agent-local` → `invoke_supervisor` ist der einzige öffentliche
Endpoint; die einzelnen Agenten-Endpoints existieren, werden aber im normalen
Betrieb nicht direkt angesprochen.

### MCP-Server (`mcp/sandbox/mcp.json`)

```json
{
  "mcpServers": {
    "git":   { "command": "python3", "args": ["-m", "mcp_server_git", "--repository", "/home/claude/la"] },
    "fetch": { "command": "python3", "args": ["-m", "mcp_server_fetch"] }
  }
}
```

Pfad nach Pre-Flight Fix (Schritt 5): `PROJECT_ROOT / "mcp" / "sandbox" / "mcp.json"`.

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

**Fix 3 — mcp.json Pfad (Pre-Flight, Schritt 5)**
```bash
sed -i 's|PROJECT_ROOT / "mcp" / "mcp.json"|PROJECT_ROOT / "mcp" / "sandbox" / "mcp.json"|' \
  /home/claude/la/agents/server/tools.py
```
Sandbox-spezifisch, nicht committen. Langfristige Lösung via `LOCAL_AGENT_ENV`
noch offen — siehe `BUGS.md`.

**Fix 4 — args_schema für MCP Tools**
```python
schema = dict(tool.args_schema)  # statt tool.args_schema.schema()
```

**Fix 5 — headroom-ai[all] statt [proxy]**
```bash
pip install "headroom-ai[all]==0.31.0"  # [proxy] allein reicht nicht
```
Aktuell nicht relevant — Headroom ist deaktiviert, siehe ROADMAP.md.

---

## F. Logging (Stand 2026-07-16)

Alle Logs liegen einheitlich unter `/tmp/logs/`:

| Datei | Komponente | Status |
|---|---|---|
| `/tmp/logs/litellm.log` | LiteLLM | ✓ funktioniert |
| `/tmp/logs/phoenix.log` | Phoenix | ✓ funktioniert |
| `/tmp/llama-server-test.log` | Reasoning Server | ✓ stdout/stderr Redirect via subprocess.Popen |
| `/tmp/logs/agent-server.log` | Agent Server | ⚠️ bleibt leer — gleicher Grund |

`tests/test_stack.py` prüft nach jedem Service-Start die jeweilige Log-Datei
auf `ERROR`, `Exception`, `Traceback`, `CRITICAL` — nicht erst am Ende des
gesamten Testlaufs.

**Antwort-Validierung:** Tests bewerten nicht mehr nur `status==200`, sondern
prüfen zusätzlich Mindestlänge der Antwort. Beim Notes-Agent wird gezielt in
ChromaDB nachgeschaut ob die neue Notiz tatsächlich gespeichert wurde.

---

## G. Testergebnisse (Stand 2026-07-16)

| Test | Ergebnis |
|------|----------|
| llama-server :8080 (Binary b9895, --jinja) | ✓ ~27 t/s, Startup ~2s |
| llama-server :8081 Embedding | ✓ ~15ms/embedding (Modell vorhanden, Server nicht aktiv) |
| LiteLLM | ✓ |
| Phoenix Traces | ✓ |
| Agent Server | ✓ 6/6 Agenten registriert |
| ChromaDB mit echten Embeddings | ✓ 384-dim |
| MCP git_log | ✓ |
| Tool-Calling | ✓ finish_reason: tool_calls (bewiesen mit --jinja, 2026-07-20) |
| tool_formatter.py | ✓ 18/18 Tests |
| Supervisor Routing | ⚠️ 350m-Modell zu klein für zuverlässiges Routing |

**Routing-Hinweis:** Das 350m-Modell routet nicht zuverlässig — englische
Prompts in Tests verwenden. Das ist eine Modellgrößen-Limitation, kein Bug.

**Stand 2026-07-20:** Stack läuft mit llama-server Binary b9895 (nicht mehr
llama-cpp-python). Tool-Calling via `--jinja` bewiesen. Startup ~2s (vorher ~20s).

---

## H. Bekannte offene Punkte (Stand 2026-07-16)

- **mcp.json Pfad in tools.py** — muss per Pre-Flight Fix (Schritt 5) manuell
  korrigiert werden. Langfristige Lösung via `LOCAL_AGENT_ENV` Umgebungsvariable
  noch nicht implementiert. Muss im Code behoben sein bevor die nächste neue
  Session frisch klont — sonst wird Pre-Flight Fix dauerhaft nötig bleiben.

- **Embedding-Server (Port 8081)** wird in `run_tests.py` nicht gestartet —
  nur der Reasoning-Server läuft. Ob ChromaDB mit echten Embeddings über
  diesen Pfad aktuell funktioniert, ist ungeklärt.

- **Notes/Handoff-Agent Routing** bleibt unzuverlässig — bekanntes
  Kapazitätslimit des 350m-Modells beim Supervisor-Routing (nicht beim
  MCP-Tool-Calling, das funktioniert). Auf einem größeren Modell (Host)
  sollte dies nicht auftreten.

- **`chat.py` Begrüßungstext** noch nicht auf "Local Agent" umbenannt (kosmetisch).

- **llama-server Logs** funktionieren jetzt via `/tmp/llama-server-test.log`
  (subprocess.Popen Redirect). Agent Server Logs bleiben leer — uvicorn-Thread-
  Logging funktioniert weiterhin nicht.

- **Phoenix Log-Check False Positive** — `test_stack.py` sucht nach dem
  String `"ERROR"` in Logs. Phoenix schreibt beim Start SQL-`CREATE TABLE`-
  Statements mit Constraint-Namen wie `"ck_spans_\`valid_status\`"` die den
  String `"ERROR"` enthalten — kein echter Fehler. Details: `BUGS.md`.
  Fix: Log-Check auf Zeilenmuster `"ERROR:"` oder `"Exception:"` (mit Doppelpunkt)
  statt bloßem Vorkommen von `"ERROR"` einschränken.

---

- Repository: https://github.com/janhetzler/la
- Original-Projekt: https://github.com/xaviervasques/chief-of-staff
- Architektur-Entscheidungen: [ROADMAP.md](ROADMAP.md)
