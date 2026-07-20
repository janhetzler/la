# JOURNAL.md -- Entwicklungstagebuch Local Agent (LA)

Neuester Eintrag oben. Fuer Agenten: lies den ersten Eintrag um den aktuellen Stand zu kennen.

---

## Sandbox-Status (aktuell)

| Sandbox | Rolle | Beschreibung |
|---------|-------|--------------|
| **Sandbox 1** | Produktiv | Aktueller Repo-Stand, getesteter Stack, 5/6 Agenten OK |
| **Sandbox 2** | Labor | Experimente, kein stabiler Stand garantiert |

Sandbox 1 hat immer den aktuellsten `git pull` Stand und ist die Referenz fuer Testergebnisse.
Sandbox 2 ist Spielwiese -- dort wird ausprobiert ohne Ruecksicht auf Stabilitaet.

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

- Host-Deployment auf janhet mit Granite-Tiny -- Routing-Problem loest sich dort
- OPERATIONS_HOST.md und OPERATIONS_DOCKER.md noch zu erstellen
- user_profile.md und project_context.md mit echten Daten befuellen
- Notes Agent auf Host testen (ChromaDB schreiben via Tool-Calling)

### Naechster Schritt

Host-Deployment auf janhet (AMD EPYC 7443P, 4 vCores, 10 GB RAM) mit
Granite-Tiny -- dort wird sich zeigen ob Routing, Tool-Calling und
ChromaDB-Schreiben durch den kompletten Stack funktionieren.

---
