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
zusammengebaut. Ein neuer Agent = eine neue Konfigurationsdatei, kein
Python anfassen.

### Neue Struktur



### Was sich aendert

**Raus aus dem Code:**
-  und  werden zu  Dateien
- System-Prompts als hardkodierte Strings — alle raus in 
-  Dictionary in  — wird dynamisch aus Verzeichnis geladen

**Bleibt in Python (wegen echter Logik):**
-  — custom  + ChromaDB Embedding
-  — custom  + RAG-Suche
-  — RAG-Logik + mehrsprachige Templates
- , , ,  — Infrastruktur

**Neu:**
-  — liest Prompt aus  Datei, baut Agent zusammen
-  liest  statt hardkodierten String

### Modell-spezifische Prompts

Prompts sind umgebungsunabhaengig aber modellspezifisch.
Steuerung ueber Umgebungsvariable :



Separate Unterordner wenn Modell-Varianten benoetigt werden.

### Reihenfolge

1. Router-Prompt verbessern + mit Phoenix verifizieren (Baseline zuerst)
2.  Struktur anlegen, Prompts extrahieren
3. Code liest Prompts aus Dateien
4.  bauen
5.  laedt Agenten dynamisch

---

## Geplant: Prompt-Management und generischer Agent-Loader

**Stand:** 2026-07-17
**Voraussetzung:** Stack laeuft stabil, Baseline-Tests abgeschlossen

### Ziel

Agenten werden nicht mehr in Python hartkodiert sondern aus Konfiguration
zusammengebaut. Ein neuer Agent = eine neue Konfigurationsdatei,
kein Python anfassen.

### Neue Struktur

    prompts/
    - shared/
      - user_profile.md        (aus user_profile.py)
      - project_context.md     (aus project_context.py)
    - agents/
      - router.md
      - comms.md
      - code.md
      - notes.md
      - researcher.md
      - handoff.md

### Was sich aendert

**Raus aus dem Code:**
- user_profile.py und project_context.py werden zu .md Dateien
- System-Prompts als hardkodierte Strings — raus in prompts/agents/
- AGENTS Dictionary in server.py — wird dynamisch aus Verzeichnis geladen

**Bleibt in Python (wegen echter Logik):**
- notes.py — custom Tool-Decorator + ChromaDB Embedding
- researcher_v2.py — custom Tool-Decorator + RAG-Suche
- handoff.py — RAG-Logik + mehrsprachige Templates
- tool_formatter.py, tools.py, telemetry.py, config.py — Infrastruktur

**Neu:**
- agent_loader.py — liest Prompt aus .md Datei, baut Agent zusammen
- supervisor.py liest router.md statt hardkodierten String

### Modell-spezifische Prompts

Prompts sind umgebungsunabhaengig aber modellspezifisch.
Steuerung ueber Umgebungsvariable PROMPT_MODEL.
Separate Unterordner wenn Modell-Varianten benoetigt werden.

### Reihenfolge

1. Router-Prompt verbessern + mit Phoenix verifizieren (Baseline zuerst)
2. prompts/ Struktur anlegen, Prompts extrahieren
3. Code liest Prompts aus Dateien statt hardkodierten Strings
4. agent_loader.py bauen
5. server.py laedt Agenten dynamisch


---

## Offene Aufgabe: Tool-Calling auf dem Host aktivieren

**Stand:** 2026-07-17
**Voraussetzung:** Host-Deployment abgeschlossen

Die vollstaendige Tool-Calling-Kette muss auf dem Host implementiert werden:

1. `supports_tools: true` in `docker/litellm_config.yaml` ergaenzen:
   Damit LiteLLM eingehende tools-Arrays nicht verwirft sondern durchreicht.

2. `bind_tools()` in LangChain nutzen (researcher_v2.py, code.py):
   Ersetzt manuelles XML-Prompt-Engineering durch strukturierte API-Aufrufe.

3. llama-server mit `--jinja` starten (bereits in restart_llama.sh vorgesehen):
   Aktiviert natives Granite Chat-Template fuer Tool-Calling.
   Granite ist nativ in der llama.cpp Jinja-Template-Liste enthalten.

Hinweis: `tool_formatter.py` kann nach erfolgreichem Test entfernt werden.
In der Sandbox nicht testbar — llama-cpp-python Python-Wrapper unterstuetzt --jinja nicht.

## Referenzen

- Fork: https://github.com/janhetzler/la
- Original: https://github.com/xaviervasques/chief-of-staff
- llmtrim: https://github.com/fkiene/llmtrim
- ik_llama.cpp: https://github.com/ikawrakow/ik_llama.cpp (Spiegel: Codeberg ikawrakow/illama)
- Arize Phoenix: https://github.com/Arize-ai/phoenix
- VS Code 1.127 Release Notes: https://code.visualstudio.com/updates/v1_127
