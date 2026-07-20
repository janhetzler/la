# ROADMAP — janhetzler/la (Chief of Staff)

**Letzte Aktualisierung:** 2026-07-16  
**Basis:** xaviervasques/chief-of-staff  
**Ziel:** Lokaler Multi-Agenten-Stack auf janhet (AMD EPYC, 10 GB RAM)

---

## Architektur-Entscheidungen (final)

| Komponente | Original | Ersatz | Grund |
|---|---|---|---|
| Vektordatenbank | Qdrant (Docker) | ChromaDB (embedded) | kein Container, weniger RAM |
| LLM-Backend | Ollama | llama-server (ik_llama.cpp) | bereits auf janhet, mehr Kontrolle |
| LLM-Client | langchain-ollama | langchain-openai | OpenAI-kompatibler Endpoint |
| Embeddings | torch + transformers | LiteLLM → llama-server :8081 | 3.2 GB Einsparung |
| Observability | — | Arize Phoenix | Tracing, RAG-Eval, CI-Tests |
| Frontend | Open WebUI | VS Code 1.127 (code-server) | Language Model API, Agent Customizations |
| Audio/Meeting | recorder.py, whisper.cpp | entfernt | kein Audio auf vServer |
| Token-Proxy | — | llmtrim (Phase 2+3) | Kontext-Kontrolle |

---

## Stack-Übersicht

```
code-server (VS Code 1.127)
    └── Language Model API → LiteLLM :4000
                                └── llama-server :8080 (Granite4-tiny-h)
                                └── llama-server :8081 (Granite-embedding-30m)
                                └── [Cloud-Escalation] Anthropic/OpenAI (via llmtrim)

FastAPI Agent-Server :8002 (LangGraph)
    ├── Supervisor
    ├── Researcher  → ChromaDB (embedded)
    ├── Comms
    ├── Code
    ├── Notes
    ├── Handoff
    └── Meta

Arize Phoenix :6006 (Observability)
```

---

## Port-Übersicht

| Port | Dienst |
|---|---|
| 8080 | llama-server (Granite4-tiny-h, Reasoning) |
| 8081 | llama-server (Granite-embedding-30m) |
| 4000 | LiteLLM (zentraler Proxy) |
| 8002 | FastAPI Agent-Server |
| 6006 | Arize Phoenix |
| 8443 | code-server (VS Code) |

---

## Modelle

| Modell | Zweck | Format | Erwartete t/s (janhet) |
|---|---|---|---|
| Granite4-tiny-h (7B MoE Hybrid) | Reasoning, alle Agenten | IQ4_XS | ~35-45 t/s |
| Granite4-micro-h (3B Hybrid) | Supervisor-Routing | Q4_K_M | ~60-80 t/s |
| Granite-embedding-30m | RAG-Embeddings | Q4 | sehr schnell |

---

## Phasen

### Phase 1 — Stack deployen (AKTUELL)
**Ziel:** Alles läuft auf janhet, Agenten antworten, Phoenix tracet

- [ ] `git pull` auf janhet
- [ ] Python venv + `requirements-janhet.txt` installieren
- [ ] llama-server mit Granite4-tiny-h starten
- [ ] llama-server mit Granite-embedding-30m starten (Port 8081)
- [ ] LiteLLM mit `litellm_config_janhet.yaml` starten
- [ ] Phoenix starten
- [ ] Agent-Server starten (Port 8002)
- [ ] Tests: `python3 tests/run_tests.py`
- [ ] VS Code 1.127: LiteLLM als Language Model Provider eintragen

**Erfolgskriterium:** Alle 6 Agenten antworten, Phoenix zeigt Traces

---

### Phase 2 — llmtrim für Cloud-Calls
**Ziel:** Cloud-Escalation via LiteLLM wird durch llmtrim komprimiert

**Voraussetzung:** Phase 1 vollständig abgeschlossen + Phoenix-Daten vorhanden

- [ ] llmtrim installieren (`npm install -g @llmtrim/cli && llmtrim setup`)
- [ ] systemd Service: llmtrim als Daemon
- [ ] LiteLLM systemd Service: `HTTPS_PROXY` + `NODE_EXTRA_CA_CERTS` setzen
- [ ] Cloud-Provider in `litellm_config_janhet.yaml` eintragen
- [ ] Complexity Router in LiteLLM konfigurieren (lokal vs. Cloud)
- [ ] Testen: Cloud-Call → Phoenix zeigt Trace → llmtrim status zeigt Ersparnis

**Erfolgskriterium:** Cloud-Calls gehen durch llmtrim, lokale Calls unverändert

---

### Phase 3 — Interne Kontext-Kompression
**Ziel:** Supervisor-Logik komprimiert Kontext vor lokalen LLM-Calls

**Voraussetzung:** Phase 2 abgeschlossen + Phoenix-Traces zeigen wo Bloat entsteht

- [ ] Phoenix-Analyse: welche Agenten produzieren längste Outputs?
- [ ] Conversation-History-Kompression im Supervisor
- [ ] RAG-Chunk-Optimierung basierend auf Phoenix-Retrieval-Daten
- [ ] Tool-Output-Kompression in LangGraph Tool-Nodes
- [ ] Erneute Phoenix-Messung: Vorher/Nachher-Vergleich

**Erfolgskriterium:** Messbare Reduktion der Token-Counts in Phoenix ohne Qualitätsverlust

---

## Was entfernt wurde

| Datei/Komponente | Grund |
|---|---|
| `agents/notes/recorder.py` | kein Audio auf vServer |
| `agents/notes/process.py` | kein whisper.cpp |
| `specialists/main.py` | whisper.cpp Wrapper |
| `models/whisper/` | kein Whisper |
| `CoS.workflow/` | macOS Automator |
| `install.bat` | Windows |
| `torch`, `transformers`, `sounddevice`, `soundfile` | nicht benötigt |
| `langchain-ollama`, `qdrant-client`, `llama-index-vector-stores-qdrant` | ersetzt |
| Open WebUI | ersetzt durch VS Code 1.127 |
| Postgres | nur für LiteLLM-Logging, nicht benötigt |

---

## Wichtige Hinweise für neue Sessions

1. **Zwei requirements-Dateien:**
   - `requirements.txt` — bereinigt, ohne Versionen für neue Pakete
   - `requirements-janhet.txt` — vollständig gepinnt, für janhet und Sandbox

2. **llmtrim ist KEIN Reverse-Proxy** — funktioniert als HTTPS MITM-Proxy
   via `HTTPS_PROXY` Umgebungsvariable. Nicht als URL in LiteLLM eintragen.

3. **ik_llama.cpp statt mainline** — für IQK-Quants und Mamba-Hybrid-Support.
   TheTom Fork für TurboQuant wenn Kontext > 15.000 Token.

4. **Phoenix skip_dep_check** — bereits in `agents/server/telemetry.py` eingebaut.

5. **ChromaDB Collections:**
   - `documents` — PDFs, DOCX
   - `research` — Web-Research-Ergebnisse
   - `personal` — private Notizen
   - `notes` — Meeting-Notizen (falls später relevant)

6. **VS Code Integration:**
   - LiteLLM :4000 als OpenAI-kompatibler Language Model Provider
   - Jeden Agenten als eigenes "Modell" eintragen
   - Später: Chat Participants via schlanke Extension

---

## Bekannte Lösung, noch nicht implementiert: MCP Tool-Calling für kleine Modelle

**Stand:** 2026-07-16. Betrifft: `agents/server/researcher_v2.py`

Das kleine Granite-350m-Modell (Sandbox) kann MCP-Tools (git_log, fetch etc.)
zuverlässig aufrufen — das wurde bereits erfolgreich isoliert getestet
(Commit `ae471a6`). Der Ansatz ist im Code vorhanden, aber **nicht in den
Produktivpfad des Researcher-Agenten eingebaut.** Deshalb schlägt MCP im
regulären Agenten-Betrieb mit dem 350m-Modell fehl, obwohl die Lösung
bereits existiert.

**Das Problem:** `researcher_v2.py` nutzt `create_agent()` aus LangGraph,
das intern `bind_tools()` verwendet — also das Standard-OpenAI-
Function-Calling-Format. Das 350m-Modell kann dieses Format nicht
zuverlässig bedienen.

**Die bereits erprobte Lösung:** Tools nicht über `bind_tools()` einbinden,
sondern über das **native Granite XML-Tool-Format**, erzeugt mit der bereits
vorhandenen Funktion `format_tools_for_model()` aus `tool_formatter.py`:

```python
system_prompt = format_tools_for_model([tool_def], model_name="granite-tiny")
llm.invoke([SystemMessage(content=system_prompt), HumanMessage(...)])
```

Der Prompt enthält dann `<tools>...</tools>`, und das Modell antwortet mit
`<tool_call>{"name": ..., "arguments": ...}</tool_call>` — zuverlässig
erkennbar per `parse_tool_call_from_response()`.

**Zusätzlich nötiger Fix:** Wenn Tools über `get_tools_by_names()` aus MCP
geladen werden, liefert `tool.args_schema` ein Dict statt eines Pydantic-
Objekts. Der Aufruf `.schema()` schlägt dann fehl — stattdessen
`dict(tool.args_schema)` verwenden.

**Was konkret zu tun ist, um das nachzuziehen:**
1. In `researcher_v2.py`: `create_agent()`/`bind_tools()` durch einen
   manuellen LangGraph-Agenten ersetzen, der `format_tools_for_model()`
   für den System-Prompt nutzt.
2. `args_schema`-Fix (`dict(...)` statt `.schema()`) beim MCP-Tool-Loading
   übernehmen.
3. Erneut mit `scripts/sandbox/start_full.py` oder gezielt gegen den
   Researcher-Agenten testen (git_log, fetch).

**Warum das wichtig ist:** Ohne diesen Umbau funktioniert MCP-Tool-Calling
nur in isolierten Tests, nicht im echten Agenten-Betrieb — auf dem Host mit
einem größeren Modell (Granite-4.0-H-Tiny) mag `bind_tools()` funktionieren,
aber für die Sandbox und kleinere Modelle ist dieser Umbau die Voraussetzung
für funktionierendes MCP.

---

---

## Offene Architektur-Aufgabe: Keine hardcodierten Pfade

**Stand:** 2026-07-17

Aktuell sind in mehreren Dateien Pfade hardcodiert — z.B. `/tmp/chroma_la`,
`mcp/sandbox/mcp.json`, `/tmp/litellm.db`. Das funktioniert solange wir nur
eine Umgebung haben, bricht aber sobald Dienste auf unterschiedlichen Hosts
oder in unterschiedlichen Containern laufen.

**Ziel:** Alle Pfade und umgebungsspezifische Werte werden ausschließlich
über Umgebungsvariablen gesetzt. Der Code selbst weiß nicht wo er läuft.

**Betrifft:**
- `agents/server/config.py` — zentrale Stelle, dort alle Pfade als `os.getenv()`
- `agents/server/tools.py` — `MCP_CONFIG_PATH` statt hardcodiertem Pfad
- `scripts/sandbox/start_full.py` — Env-Variablen explizit setzen
- `scripts/sandbox/start_quick.py` — Env-Variablen explizit setzen
- `deploy/systemd/litellm.service.template` — `DATABASE_URL` als Env-Variable
- `docker/entrypoint.sh` — Env-Variablen für Docker-Pfade

**Umgebungsvariablen (geplant):**

| Variable | Sandbox | Host | Docker |
|----------|---------|------|--------|
| `CHROMA_PATH` | `/tmp/chroma_la` | `/home/user/chroma` | `/app/data/chroma` |
| `LITELLM_DB_PATH` | `/tmp/litellm.db` | `/home/user/litellm.db` | `/app/data/litellm.db` |
| `MCP_CONFIG_PATH` | `mcp/sandbox/mcp.json` | `mcp/host/mcp.json` | `mcp/docker/mcp.json` |
| `LITELLM_KEY` | `sk-local-dev` | via Secret | via Secret |

**Voraussetzung:** Phase 1 (Stack läuft stabil auf Host) abgeschlossen.

---

## Offene Aufgabe: LiteLLM Authentifizierung

**Stand:** 2026-07-17

LiteLLM 1.92.0 unterstuetzt `master_key` nur mit PostgreSQL als Backend.
SQLite wird nicht unterstuetzt. Aktuell laeuft LiteLLM ohne `database_url` --
wenn Request-Key == master_key prueft LiteLLM keine DB (kein DB-Check noetig).

Das ist fuer die Sandbox akzeptabel (nur localhost), aber nicht fuer den Host.

**Optionen fuer den Host:**
1. LiteLLM auf eine aeltere Version downgraden die SQLite unterstuetzt
2. PostgreSQL als LiteLLM-Backend -- separater Dienst, hoehere Komplexitaet
3. Auth auf Netzwerk-Ebene loesen (Cloudflare Tunnel, nginx) statt in LiteLLM

**Voraussetzung:** Erst angehen wenn Stack stabil auf Host laeuft.

---

## Geplant: Prompt-Management und generischer Agent-Loader

**Stand:** 2026-07-17
**Voraussetzung:** Stack laeuft stabil, Baseline-Tests abgeschlossen

### Ziel

Agenten werden nicht mehr in Python hartkodiert sondern aus Konfiguration
zusammengebaut. Ein neuer Agent = eine neue .md Datei mit YAML-Frontmatter,
kein Python anfassen.

### Kernkonzept: YAML-Frontmatter in .md Dateien

Jede Agent-Datei kombiniert Metadaten (YAML) und System-Prompt (Markdown)
in einer einzigen Datei. Beispiel prompts/agents/comms.md:

    ---
    name: comms
    description: E-Mails, Nachrichten, Kurzberichte. Kein RAG, keine Suche.
    tools: []
    temperature: 0.3
    ---
    Du bist der Kommunikations-Spezialist.
    {{ project_context }}
    {{ user_profile }}

Vorteile:
- Konfiguration und Prompt in einer Datei
- supervisor.py liest description aus Frontmatter und baut Router-Prompt dynamisch
- agent_loader.py liest tools und bindet sie via bind_tools()
- Template-Injection: {{ project_context }} wird via String-Replace befuellt
- Neuer Agent: einfach neue .md Datei anlegen, Router weiss sofort davon

### Neue Struktur

    prompts/
    - shared/
      - user_profile.md
      - project_context.md
    - agents/
      - router.md
      - comms.md
      - code.md
      - notes.md
      - researcher.md
      - handoff.md

### Hybrides Design

Reine Text-Agenten (comms, code) werden zu reiner Konfiguration:
Python-Datei entfaellt, agent_loader.py baut Agent aus .md.

Logik-Agenten (notes, researcher, handoff) behalten Python:
Wegen custom Tools und RAG-Logik — lesen aber Prompt aus .md.

Infrastruktur bleibt unveraendert:
tool_formatter.py, tools.py, telemetry.py, config.py.

Neu: agent_loader.py (parst Frontmatter, baut Agent) und
supervisor.py liest alle agents/*.md dynamisch.

### Modell-spezifische Prompts

Steuerung ueber Umgebungsvariable PROMPT_MODEL.
Separate Unterordner fuer Modell-Varianten (z.B. granite-350m/).

### Reihenfolge (Strangler-Fig-Pattern)

1. prompts/ Struktur anlegen, Prompts aus Code extrahieren
2. Code liest Prompts aus .md Dateien (keine Funktionsaenderung)
3. agent_loader.py bauen
4. supervisor.py dynamisieren
5. server.py laedt Agenten dynamisch


---

## Offene Aufgabe: Ressourcenmessung in Testlaeufen

**Stand:** 2026-07-18

Aktuell messen unsere Testlaeufe nur ob Tests OK/FAIL sind und wie lange sie dauern.
RAM-Verbrauch und CPU-Last werden nicht erfasst.

**Ziel:** Jeder Testlauf dokumentiert automatisch:
- RAM vor Stack-Start
- RAM nach jedem Service-Start (llama-server, Embedding, Phoenix, LiteLLM, Agent Server)
- Peak-RAM waehrend der Tests
- CPU-Last waehrend der Tests
- Alles in den TESTRESULTS.md dokumentiert

**Implementierung:**
-  in  erganzen
- Ressourcenmessung in  und  einbauen
-  startet alle Dienste + Notes-Agent Test + Ressourcenmessung

**Voraussetzung:** Stack laeuft stabil.
## Referenzen

- Fork: https://github.com/janhetzler/la
- Original: https://github.com/xaviervasques/chief-of-staff
- llmtrim: https://github.com/fkiene/llmtrim
- ik_llama.cpp: https://github.com/ikawrakow/ik_llama.cpp (Spiegel: Codeberg ikawrakow/illama)
- Arize Phoenix: https://github.com/Arize-ai/phoenix
- VS Code 1.127 Release Notes: https://code.visualstudio.com/updates/v1_127


---

## Evaluierung: Bifrost als LiteLLM-Ersatz (2026-07-19)

**Status:** Teilweise evaluiert, Plugin-Problem offen

**Was funktioniert:**
- Bifrost v1.6.4 als Gateway vor llama-server
- Custom OpenAI-kompatibler Provider via API registrieren
- Routing zu lokalem llama-server

**Was nicht funktioniert:**
- Custom Go Plugins (statische NPX-Binary)
- Bifrost OSS kompilieren (fehlende Enterprise-Pakete)

**Alternativen fuer llmtrim-Integration:**
1. Python FastAPI-Wrapper: empfaengt Request, piped durch llmtrim compress, leitet weiter
2. llmtrim als MCP-Server:  -- Tools: llmtrim_compress, llmtrim_compress_text
3. llmtrim Upstream-Proxy: LLMTRIM_UPSTREAM_PROXY vor Bifrost schalten

**Naechste Schritte:**
- [ ] Python FastAPI-Wrapper als HTTP-Proxy implementieren (einfachste Loesung)
- [ ] llmtrim MCP-Server evaluieren
- [ ] Bifrost Enterprise kontaktieren wegen dynamischer Binary


---

## Heuristisches Routing (Idee aus 2026-07-20)

### Problem
Das 350m Modell routet unzuverlaessig — selbst mit Grammar Constraint
und Few-Shot-Beispielen landet "write an email" bei `code` statt `comms`.

### Loesung: Pre-Filter vor LLM-Call

**Stufe 1 — Emoji-Routing (0ms):**
```python
EMOJI_ROUTING = {
    "📧": "comms", "💻": "code",
    "🔍": "researcher", "📝": "notes", "🔄": "handoff"
}
```

**Stufe 2 — Keyword-Heuristik (0ms):**
```python
ROUTING_KEYWORDS = {
    "comms":      ["email", "mail", "write", "message", "draft", "letter"],
    "code":       ["python", "debug", "script", "function", "bug", "github"],
    "notes":      ["note", "save", "remember", "meeting", "vault"],
    "researcher": ["search", "find", "web", "news", "latest", "research"],
    "handoff":    ["claude", "chatgpt", "complex", "analyse", "deep"],
}
```

**Stufe 3 — LLM (nur bei kein Match):**
Nur wenn Stufe 1 und 2 keinen Match liefern → LLM-Call wie bisher.

### Testergebnis (2026-07-20, Docker Container)
```
comms        (keyword score 3) <- write an email to my boss       ✅
comms        (keyword score 1) <- ich möchte eine Mail schreiben  ✅
code         (keyword score 4) <- debug my python script          ✅
notes        (keyword score 2) <- save this note: Docker Test     ✅
researcher   (keyword score 3) <- search for latest AI news       ✅
comms        (emoji)           <- 📧 write to John                ✅
LLM          (kein Match)      <- Can you help me?                ✅
handoff      (keyword score 1) <- Prepare a prompt for Claude.ai  ✅
```

**8/8 korrekt** — loest 80% der Routing-Fehler ohne LLM-Call.

### Implementierung
- Neue Datei: `agents/server/router_heuristic.py`
- Aenderung: `agents/server/supervisor.py` — Pre-Filter vor `router_llm.ainvoke()`
- Kein neues Modell, kein neues Image noetig

### Status
Getestet im Docker Container (2026-07-20). Implementierung ausstehend.
