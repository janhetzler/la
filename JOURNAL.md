# JOURNAL.md -- Entwicklungstagebuch Local Agent (LA)

Neuester Eintrag oben. Fuer Agenten: lies den ersten Eintrag um den aktuellen Stand zu kennen.

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
