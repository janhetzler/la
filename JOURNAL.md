# JOURNAL.md -- Entwicklungstagebuch Local Agent (LA)

Neuester Eintrag oben. Fuer Agenten: lies den ersten Eintrag um den aktuellen Stand zu kennen.

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
