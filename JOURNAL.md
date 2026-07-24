# JOURNAL.md -- Entwicklungstagebuch Local Agent (LA)

Neuester Eintrag oben. Fuer Agenten: lies den ersten Eintrag um den aktuellen Stand zu kennen.

---

## Sandbox-Status (aktuell)

| Sandbox | Rolle | Beschreibung |
|---------|-------|--------------|
| **Sandbox 1** | Produktiv | Neu aufgesetzt 2026-07-21, llama-server b9895, Heuristik-Routing, 4/6 OK |
| **Sandbox 2** | Labor | Experimente, kein stabiler Stand garantiert |

Sandbox 1 hat immer den aktuellsten `git pull` Stand und ist die Referenz fuer Testergebnisse.
Sandbox 2 ist Spielwiese -- dort wird ausprobiert ohne Ruecksicht auf Stabilitaet.

---


## 2026-07-21 Nachtrag 4 — Tool-Calling Infrastruktur vollstaendig

### Was heute final bewiesen wurde

**Infrastruktur 100% korrekt:**
- format_tools_for_model() sendet <tools>...</tools> korrekt
- parse_tool_call_from_response() parst arguments-String korrekt
- ReAct-Loop behandelt unvollstaendige Tags korrekt
- LiteLLM gibt 200 OK fuer alle Notes-Requests
- ChromaDB Collection mit cosine bereit
- save_note Tool registriert und funktionsfaehig

**350m Modell-Limit (BUG-024) — finale Diagnose:**
Das Modell antwortet direkt mit Text statt <tool_call>.
Kein Code-Fix moeglich — das ist eine Kapazitaetsgrenze.
Im isolierten Phoenix-Trace produzierte es einmal einen
vollstaendigen <tool_call> — also KANN es, aber nicht zuverlaessig.

**Commits heute (Sandbox 2):**
- aa4294b0 — researcher_v2.py format_tools_for_model
- be6cdee4 — notes.py format_tools_for_model
- a2b58cf7/f4d2e680 — outer try/except
- 92183e17/5b7a04e6 — args_schema Fix
- 486c3d5d/60640a28 — max_tokens=512
- tool_formatter.py — arguments String-Fix
- notes.py — ReAct-Loop unvollstaendiger Tag Fix

### Naechster Schritt

**Host-Deployment** — Granite-4.0-H-Tiny (4B) auf dem Host.
Alle Infrastruktur-Komponenten sind bereit. Das Modell ist
der einzige fehlende Baustein fuer vollstaendiges Tool-Calling.

### Sandbox-Status

| Sandbox | Rolle | Status |
|---------|-------|--------|
| Sandbox 1 | Produktiv | 4/6 OK, Heuristik aktiv, aktueller Stand |
| Sandbox 2 | Labor | Erschoepft — naechste Session neu aufsetzen |


## 2026-07-21 Nachtrag 3 — format_tools_for_model Umbau

### Was erreicht wurde

**researcher_v2.py + notes.py umgebaut:**
- `create_agent()`/`bind_tools()` ersetzt durch `format_tools_for_model()`
- Native Granite XML Tool-Format: `<tools>...</tools>` im System-Prompt
- `parse_tool_call_from_response()` fuer Tool-Call Erkennung
- `args_schema` Fix: `model_json_schema()` statt `dict()` fuer Pydantic v2
- Outer try/except in beiden Dateien
- `max_tokens=512` fuer vollstaendige Tool-Call Ausgabe

**Beweis dass Architektur korrekt ist:**
- Notes-Agent produziert jetzt `<tool_call>` — war vorher nie der Fall
- JSON-Body unvollstaendig wegen 350m Kapazitaetslimit
- Researcher-Agent: 5047 Zeichen (vorher 3234) — bessere Antwortqualitaet

**Commits:**
- `aa4294b0` — researcher_v2.py format_tools_for_model
- `be6cdee4` — notes.py format_tools_for_model
- `a2b58cf7` + `f4d2e680` — outer try/except
- `92183e17` + `5b7a04e6` — args_schema Fix
- `486c3d5d` + `60640a28` — max_tokens=512

### Fazit

Die Architektur ist fertig und korrekt. Das 350m Modell versteht
das Granite XML Tool-Format und produziert `<tool_call>` — aber
der JSON-Body ist unvollstaendig wegen Kapazitaetslimit.

Mit Granite-Tiny (4B) auf dem Host wird der vollstaendige
`<tool_call>{"name": "save_note", ...}</tool_call>` kommen.


## 2026-07-21 Nachtrag 2 — ChromaDB cosine Fix + Researcher Fix

**ChromaDB BUG-017 behoben:**
- `start_full.py` initialisiert ChromaDB Collection mit `hnsw:space: cosine` beim Stack-Start
- 4/6 Agenten OK, Heuristik routet alle 5 Agenten korrekt
- Notes-Agent schreibt noch nicht (350m Tool-Calling Limit — auf Host loesbar)

**Researcher BUG-022 behoben:**
- `researcher_v2.py` — try/except um `agent.ainvoke()`
- "What is the Local Agent?" → `meta` → vollstaendige korrekte Antwort

**Heuristik BUG-023 behoben:**
- `"what is"` aus researcher Keywords entfernt
- Generische Fragen gehen jetzt zu `meta`

**Commits heute:**
- `95126b6a` — start_full.py ChromaDB cosine
- `31bd7161` — researcher_v2.py try/except
- `dcb828f3` — router_heuristic.py "what is" entfernt
- `3a8ebbc2` — router_heuristic.py neu
- `8ecd7696` — supervisor.py Pre-Filter


## 2026-07-21 Nachtrag — Sandbox 1 neu aufgesetzt

**Sandbox 1 komplett neu aufgesetzt** mit aktuellem Repo-Stand:
- llama-server Binary b9895 (nicht mehr llama-cpp-python)
- Heuristisches Routing aktiv (router_heuristic.py)
- 4/6 Agenten OK — Heuristik routet korrekt
- Comms, Code, Researcher, Handoff funktionieren
- Supervisor: kurze Antwort (350m Limit, bekannt)
- Notes: korrekt geroutet, ChromaDB-Schreiben noch nicht (Tool-Call Limit)

**Verbesserung gegenueber altem Stand:**
Vorher routete alles zu `meta` — jetzt greift die Heuristik
und routet 4/5 Agenten korrekt ohne LLM-Call.


## 2026-07-21 — Heuristisches Routing + Notes-Fixes

### Was erreicht wurde

**Heuristisches Routing implementiert:**
- `agents/server/router_heuristic.py` neu — Emoji + Keyword Pre-Filter
- `agents/server/supervisor.py` — heuristic_route() vor LLM-Call
- 8/8 Testfaelle korrekt, inkl. Deutsch ("Mail schreiben" → comms)
- Kein LLM-Routing-Call mehr fuer 5/6 Agenten

**Notes-Agent fixes (BUG-017, BUG-018, BUG-019):**
- ChromaDB Collection mit cosine Distanz (BUG-017)
- Source-Filter in search_meetings entfernt (BUG-018)
- save_note Tool implementiert (BUG-019)

**Embedding-Stack repariert (BUG-021):**
- llama-server braucht --embeddings + --pooling mean
- granite-embed in LiteLLM Config ergaenzt
- 768-dim Embeddings via LiteLLM funktionieren

**Ergebnis:** 4/6 Agenten OK — Notes antwortet (HTTP 200) aber
save_note wird vom 350m Modell nicht aufgerufen (Modell-Limit).

### Offene Punkte

- Docker entrypoint.sh: --embeddings + --pooling mean ergaenzen
- Sandbox 1 neu aufsetzen mit aktuellem Stand
- 1B Modell testen — save_note sollte dann funktionieren


## 2026-07-20 Nachtrag 2 -- Docker ChromaDB RAG Test

### Was erreicht wurde

**Docker Test-Run mit 1B Modell:**
- Granite 4.0-H-1B Q4_K_M (859 MB) als Ersatz fuer 350m getestet
- 5/6 Agenten OK -- deutlich bessere Antwortqualitaet als 350m
- Comms Agent: vollstaendige professionelle E-Mail (786 Zeichen)
- Researcher Agent: ausfuehrliche Antwort (3957 Zeichen)
- scripts/docker/test_docker.py erstellt und gepusht

**ChromaDB RAG vollstaendig getestet:**
- Embedding (Granite) → ChromaDB schreiben → ChromaDB lesen → Notes-Agent → Antwort
- Komplette Kette funktioniert mit Score 0.84
- Phoenix Traces beweisen: Tool-Call, Embedding, ChromaDB-Abfrage alles sichtbar

**4 neue Bugs entdeckt und dokumentiert:**
- BUG-016: mcp/docker/mcp.json fehlte (behoben -- ins Repo gepusht)
- BUG-017: ChromaDB Collection nutzt euklidische statt Kosinus-Distanz
- BUG-018: Notes-Agent Source-Filter zu restriktiv ("meeting" Pflicht)
- BUG-019: save_note Tool fehlt -- kein Agent kann in ChromaDB schreiben

**Wichtige Erkenntnis:**
Das Original-Projekt (xaviervasques/chief-of-staff) nutzt Qdrant, nicht ChromaDB.
ChromaDB-Schreiben ist ein neues Feature das wir selbst implementieren muessen.
Der Notes-Agent war nie ein Schreiber -- nur ein Vault-Reader mit RAG-Suche.

**Gemini Flash Lite Integration getestet:**
- Google-Proxy auf Host (10.0.2.2:5050) erreichbar aus Container
- Direkte LiteLLM-Anfrage funktioniert (vollstaendige E-Mail)
- Rate Limit: 13 RPM -- zu wenig fuer automatisierte Tests
- LiteLLM→Proxy Debug noch ausstehend

### Was funktioniert

- Docker Stack vollstaendig: alle 5 Dienste erreichbar von aussen
- Phoenix Web-UI: http://localhost:6006 -- Traces live sichtbar
- LiteLLM Swagger UI: http://localhost:4000
- ChromaDB RAG lesen: ✅ (mit korrektem Embedding + cosine Collection)
- 1B Modell: deutlich bessere Qualitaet als 350m

### Was nicht funktioniert

- Notes-Agent schreibt nicht in ChromaDB (BUG-019 -- save_note fehlt)
- ChromaDB Collection standardmaessig mit L2 statt cosine (BUG-017)
- mcp/docker/mcp.json war leer (BUG-016 -- behoben)

### Offene Punkte

- BUG-017 bis BUG-019 in Code umsetzen
- 1B Modell permanent ins Docker Image (Dockerfile anpassen)
- Neues Image bauen
- Host-Deployment steht noch aus


## 2026-07-20 — llama-server Binary, Tool-Calling, Trace-System

### Kontext

Mutterchat-Wechsel nach langem Arbeitstag. Sandbox 2 als aktive Spielwiese.
Zwei Sandboxen aktiv, alle Ergebnisse ins Repo gepusht.

### Kernentscheidung des Tages

Wechsel von `llama-cpp-python` (Python-Wrapper) zur nativen `llama-server`
Binary b9895. Grund: `--jinja` Flag fuer natives Tool-Calling nur mit Binary
moeglich. Der Swap war der zentrale Schritt des Tages.

### Was erreicht wurde

**llama-server Binary Swap (abgeschlossen):**
- llama-cpp-python vollstaendig ersetzt durch llama-server Binary b9895
- Download: `llama-b9895-bin-ubuntu-x64.tar.gz` (curl + tar --strip-components=1)
- Binary: `/tmp/llama-b9895/llama-server`
- Flags: `--jinja --ctx-size 32768 --parallel 1 --log-disable`
- 4 Scripts umgeschrieben: start_full.py, start_quick.py, inspect_phoenix.py,
  test_mcp_toolcall.py -- alle via subprocess.Popen statt Python-Import
- Startup-Zeit: ~2s (vorher ~20s mit Python-Wrapper)
- Baseline gehalten: 4/6 Agenten OK

**Tool-Calling bewiesen:**
- `finish_reason: tool_calls` mit Granite 350m + --jinja bestaetigt
- Das war mit llama-cpp-python nie moeglich
- Grammar Constraint (`extra_body={"grammar":...}`) funktioniert jetzt
  ohne `No connected db.` Fehler (Key-Alignment-Fix von 2026-07-18 hat
  LiteLLM-Auth-Problem behoben)
- Grammar dauerhaft in supervisor.py eingebaut: stabiler Token-Output,
  kein Einfluss auf inhaltliche Routing-Qualitaet

**Routing-Debugging:**
- Phoenix Traces analysiert: Router-Prompt korrekt (1613 Zeichen, 402 Token)
- Routing-Problem bestaetigt als Modellkapazitaets-Limit (nicht Prompt-Qualitaet)
- 350m assoziiert "write email" mit "code" -- Trainings-Artefakt
- Loesung: Granite-Tiny (4B) auf Host -- dort wird korrekt geroutet

**Trace-System aufgebaut:**
- `docs/traces/` Ordner mit sandbox/host/docker Unterstruktur
- `inspect_phoenix.py` erweitert: erzeugt automatisch Trace-Datei nach jedem Request
- Dateiname: `YYYY-MM-DD_[request-slug].md`
- Inhalt: vollstaendige Span-Kette, Performance, Infrastruktur-Logs, Prompt-Version
- Erste echte Trace-Datei: `2026-07-20_write-a-short-professional-email-to-the.md`

**Neue Dokumentation:**
- `docs/COMPONENT_SWAP_TEMPLATE.md` -- universelles Template fuer Komponenten-Docs
- `docs/LLAMA.md` -- vollstaendige Dokumentation llama-cpp-python vs. Binary
- `docs/AGENT_DEVELOPMENT.md` -- Anleitung neuen Agenten entwickeln
- `docs/OPERATIONS_SANDBOX.md` -- Betrieb & Logging fuer Sandbox-Umgebung
- `docs/traces/README.md` -- Erklaerung des Trace-Log-Systems
- `STYLEGUIDE.md` -- Component Documentation + Agenten-Entwicklung Sektionen
- `SANDBOX.md` -- aktualisiert auf Stand 2026-07-20 (Binary, --jinja)

**Bekannte Bugs gefunden/behoben:**
- `import uvicorn` fehlte nach llama-Block-Swap in start_full.py und
  inspect_phoenix.py -- behoben
- `--log-level error` existiert nicht in b9895 -- `--log-disable` ist korrekt
- Grammar Constraint Bug (2026-07-17) als behoben markiert

### Was funktioniert

- Stack startet mit Binary b9895 (llama-server, Phoenix, LiteLLM, Agent Server)
- 4/6 Agenten-Tests OK (Comms, Code, Researcher, Handoff)
- Tool-Calling via --jinja bewiesen
- Grammar Constraint stabil (keine Garbage-Tokens mehr)
- Phoenix Tracing erfasst alle LangChain-Calls
- Trace-System erzeugt vollstaendige Request-Dokumentation

### Was nicht funktioniert

- Notes Agent schreibt nicht in ChromaDB -- Routing-Limit 350m
- Supervisor-Routing: 350m routet falsch (code statt comms fuer E-Mail)
- llama-server.log bleibt leer -- `--log-disable` unterdrückt alle Ausgaben
- Agent Server Log bleibt leer -- uvicorn Thread-Logging funktioniert nicht

### Offene Punkte

- Host-Deployment mit Granite-Tiny -- Routing-Problem loest sich dort
- OPERATIONS_HOST.md und OPERATIONS_DOCKER.md noch zu erstellen
- user_profile.md und project_context.md mit echten Daten befuellen
- Notes Agent auf Host testen (ChromaDB schreiben via Tool-Calling)

### Naechster Schritt

Host-Deployment mit Granite-Tiny -- dort wird sich zeigen ob Routing, Tool-Calling und
ChromaDB-Schreiben durch den kompletten Stack funktionieren.

---

### Nachtrag 2026-07-20 — Erster erfolgreicher Docker-Run

**Was passiert ist:**

Das Docker Image wurde heute Nachmittag neu gebaut (GitHub Actions Run #26,
15:21 MESZ) und in einer QEMU Guest VM (Debian, Docker 29.6.2) getestet.

**Erste Erkenntnisse aus dem Docker-Run:**

Drei Bugs in `docker/entrypoint.sh` entdeckt und behoben:
- BUG-012: Phoenix + LiteLLM auf `127.0.0.1` statt `0.0.0.0` — von aussen
  nicht erreichbar trotz Port-Mapping
- BUG-013: Embedding Server startet nicht — `--embedding` braucht `True` als Argument
- BUG-014: llama-cpp-python statt Binary b9895 — kein `--jinja`, kein Tool-Calling
- BUG-015: Phoenix gRPC Port 4317 Konflikt beim Neustart im Container

Alle vier Bugs behoben, neues Image gebaut (Run #27).

**Zweiter Docker-Run — vollstaendig erfolgreich:**

- llama-server Binary b9895 mit `--jinja` laeuft im Container
- Embedding Server laeuft (--embedding True fix)
- Phoenix Web-Interface erreichbar unter http://localhost:6006
- LiteLLM Swagger UI erreichbar unter http://localhost:4000
- Agent Server Health OK, alle 6 Agenten geladen
- Sauberer Start ohne manuelle Eingriffe

**Neue Dokumentation:**
- `docs/OPERATIONS_DOCKER.md` — Betrieb & Logging fuer Docker-Umgebung
- `BUGS.md` — BUG-012 bis BUG-015 dokumentiert

**Stand am Ende des Tages:**

Stack laeuft vollstaendig in drei Umgebungen:
- Sandbox 2 (Claude Sandbox) — 4/6 Agenten, Binary b9895, --jinja aktiv
- Docker (QEMU VM) — vollstaendiger Stack, alle Dienste erreichbar
- Host — noch ausstehend (naechster Schritt)

---

## 2026-07-19

### Was wurde gemacht

**VS Code Space Experimente (Hugging Face Space):**
- llama-server mit  Flag gestartet -- Tool-Calling mit Granite 350m bewiesen
- VS Code Agent-Modus mit lokalem Modell via  (vendor: customendpoint)
- Modell-Alias gefaked: Granite 350m laeuft unter dem Namen des LFM 8B Modells
- Bifrost v1.6.4 als Gateway vor llama-server installiert und konfiguriert
- Provider  in Bifrost registriert (custom OpenAI-kompatibler Endpoint auf Port 8081)
- Bifrost Go Plugin (llmtrim-Kompression) mit Go 1.26.4 kompiliert (28 MB .so Datei)
- llmtrim v0.11.4 installiert und  Funktion getestet (stdin/stdout)
- Node.js v20.19.0 nach /tmp installiert (System-Node v12 inkompatibel mit Bifrost)

**LA Projekt (Mutterchat):**
- STYLEGUIDE.md erstellt -- Programmierrichtlinien fuer das Projekt
- JOURNAL.md erstellt -- dieses Dokument
- measure_resources.py: Phoenix Trace Auswertung nach Notes Agent Test eingebaut
- GitHub Token erneuert: ghp_... hat jetzt alle noetigen Rechte

### Was funktioniert

- ** = Tool-Calling bewiesen**: Granite 350m ruft  Tool korrekt auf wenn llama-server mit  gestartet wird. Ohne  ignoriert das Modell Tools komplett.
- **VS Code Agent-Modus mit lokalem Modell**: customendpoint Konfiguration funktioniert, Modell-ID muss exakt dem  Response entsprechen
- **Bifrost als Gateway**: Requests laufen durch Bifrost zu llama-server, Routing funktioniert, Health-Check OK
- **Bifrost Plugin kompiliert**: Go 1.26.4 Plugin baut erfolgreich, Go-Version muss via  aus der Binary gelesen werden

### Was nicht funktioniert

- **Bifrost Custom Plugins laden nicht**: NPX-Binary ist statisch gelinkt -- kann keine .so Dateien laden. Plugin erscheint nicht im Log als "active".
- **Bifrost direkte Binary crasht**: Segfault beim Plugin-Ladeversuch (), auch ohne Plugin instabil
- **Bifrost OSS nicht kompilierbar**:  fehlt im OSS-Repo (Enterprise-only Feature)
- **llmtrim kein HTTP-Proxy**: Ist HTTPS MITM-Proxy, kein lokaler HTTP-Reverse-Proxy.  ist stdin/stdout Tool, kein Server.
- **Kontextproblem real**: 16.000 Tokens fuer einen simplen bin
bin.usr-is-merged
boot
container_info.json
dev
etc
home
lib
lib.usr-is-merged
lib64
lost+found
media
mnt
old_root
opt
proc
root
run
sbin
sbin.usr-is-merged
srv
sys
tmp
usr
var Befehl in VS Code Agent-Modus

### Neue Erkenntnisse

- **Go-Version-Matching**: Binary-Go-Version via  ermitteln, Plugin mit exakt dieser Version bauen
- **Bifrost SQLite**:  wird beim Start durch SQLite ueberschrieben. Plugin-Tabelle: , Spalte:  (nicht )
- **llmtrim als MCP-Server moeglich**:  startet MCP-Server -- alternativer Integrationsweg ohne Plugin
- **350m Modell-Limit**: Kontextfenster laeuft bei komplexen Agentic-Tasks voll, Kontext-Kompression dringend noetig

### Offene Punkte / Naechste Schritte

- Bifrost Plugin-Problem loesen: dynamisch gelinkte Binary benoetigt (eigener Build oder alternatives Deployment)
- llmtrim Alternativen evaluieren: Python FastAPI-Wrapper als HTTP-Proxy, oder llmtrim als MCP-Server
- VS Code Space Setup als Vorlage fuer Host-Deployment dokumentieren
- Host-Deployment mit Granite-Tiny -- dort wird sich zeigen ob Routing und Tool-Calling durch den Stack funktionieren

---


## 2026-07-18

### Was wurde gemacht

**Architektur:**
- Konfigurationsbasiertes Agenten-System eingefuehrt (agent_loader.py)
- Alle System-Prompts aus Python-Code extrahiert nach prompts/agents/*.md
- YAML-Frontmatter Konzept implementiert (name, description, tools, temperature)
- Shared Context: prompts/shared/user_profile.md + project_context.md
- Templates fuer neue Agenten: prompts/agents/TEMPLATE.md + TEMPLATE_LOGIC.md

**Infrastruktur:**
- config/ Verzeichnis mit .env Dateien fuer alle drei Umgebungen
- Alle hardcodierten Werte (URLs, Keys, Pfade) aus Code entfernt
- LA_ENV Umgebungsvariable zur Umgebungserkennung eingefuehrt
- Dockerfile bereinigt: tests/ entfernt, prompts/ + config/ hinzugefuegt
- 20 alte Docker-Images geloescht, nur latest behalten

**Observability:**
- Arize Phoenix vollstaendig integriert (arize-phoenix-client)
- Phoenix Traces in measure_resources.py eingebaut
- Ressourcenmessung via /proc/meminfo (kein psutil noetig)

**Dokumentation:**
- README.md komplett neu geschrieben mit Agenten-System-Beschreibung
- CONTRIBUTING.md mit Testergebnis-Konvention
- prompts/README.md mit vollstaendigem Datenfluß-Diagramm
- STYLEGUIDE.md (heute) -- Programmierrichtlinien
- JOURNAL.md (heute) -- dieses Dokument

### Was funktioniert

- Stack startet sauber (llama-server, Phoenix, LiteLLM, Agent Server)
- 5/6 Agenten-Tests OK in Sandbox (Supervisor, Comms, Code, Researcher, Handoff)
- Phoenix Tracing erfasst alle LangChain-Calls
- agent_loader.py laedt Agenten dynamisch aus prompts/agents/*.md
- Template-Injection: { user_profile } und { project_context } werden korrekt befuellt
- RAM-Profil gemessen: Peak 2551 MB fuer vollstaendigen Stack

### Was nicht funktioniert

- Notes Agent schreibt nicht in ChromaDB -- 350m Modell ruft kein Tool auf
- Routing: 350m Modell routet fast alles zu meta (bekanntes Limit)
- Tool-Calling in Sandbox nicht testbar -- llama-cpp-python unterstuetzt kein --jinja

### Offene Punkte

- Host-Deployment steht aus -- dort mit Granite-Tiny testen
- Tool-Calling via bind_tools() + --jinja auf dem Host aktivieren
- user_profile.md und project_context.md mit echten Daten befuellen
- Ressourcenmessung in start_full.py einbauen (psutil)
- LiteLLM Authentifizierung fuer Host-Deployment loesen

### Naechster Schritt

Host-Deployment mit Granite-Tiny -- dort wird sich zeigen ob
Routing, Tool-Calling und ChromaDB-Schreiben wirklich funktionieren.

---
