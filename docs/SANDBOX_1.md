# Status-Bericht — Local Agent Sandbox
**Erstellt:** 2026-07-16  
**Basis:** Direkter Code-Check, keine Vermutungen

---

## 1. Alte Namen — wo noch verwendet

### "host"
Vorkommt legitim in Dokumentation und Kommentaren — das ist korrekt und beabsichtigt:
- `deploy-host.sh` Z.2-3: Deploy-Script Header
- `agents/server/telemetry.py` Z.2: Modul-Docstring
- `agents/server/tool_formatter.py` Z.2: Modul-Docstring
- `agents/server/supervisor.py` Z.82: SYSTEM_FACTS Prompt ("running on host")
- `agents/server/supervisor.py` Z.299: Kommentar
- `agents/notes/recorder.py` Z.2,7: Disabled-Kommentar
- `agents/ingestion/search.py` Z.2: Modul-Header
- `agents/ingestion/ingest.py` Z.2: Modul-Header
- `requirements-host.txt` Z.1,4,43: Datei-Header
- `README.md` Z.1,22,59,69,107,115,116,124,140: Dokumentation
- `HANDOFF.md` Z.9,13,45,153,156,216,222,257,273,287: Dokumentation
- `tests/test_stack.py` Z.2,71,83: Test-Header und Prompts
- `tests/run_tests.py` Z.2: Modul-Header
- `docker/entrypoint.sh` Z.43: Config-Pfad
- `docker/litellm_config_host.yaml` Z.1: Header
- `scripts/start_headroom.sh` Z.5,9: Kommentare
- `scripts/start_litellm.sh` Z.6,16: Config-Pfad
- `docs/INSTALL_JANHET.md`: Gesamte Datei

**Bewertung:** Alle Vorkommen sind korrekt — "host" ist der Name des Produktions-Servers.

### "local-agent" / "Local Agent"
- `agents/server/server.py` Z.54: `"agent-local": invoke_supervisor` — **aktiver Code**
- `agents/server/server.py` Z.69: `"owned_by": "local-agent"` — **aktiver Code**
- `agents/server/server.py` Z.25: FastAPI title
- `agents/server/telemetry.py` Z.22: Phoenix `project_name="local-agent"` — **aktiver Code**
- `agents/server/supervisor.py` Z.82: SYSTEM_FACTS Prompt
- `agents/server/user_profile.py` Z.40: Beschreibung
- `agents/server/project_context.py` Z.4: Beschreibung
- `docker/litellm_config.yaml` Z.1,66,68,72,136: **ORIGINAL-Datei** (nicht aktiv)
- `scripts/chat.py` Z.26: `model="agent-local"` — **aktiver Code, aber Diskrepanz!**
- `tests/test_stack.py` Z.31: `model="agent-local"` — **aktiver Code**

### IP-Adressen und Hostnamen
- `HANDOFF.md` Z.13: `185.129.86.169 / host` — nur Dokumentation, korrekt

### Modellnamen — Diskrepanz
**Aktuelle LiteLLM Config** (`litellm_config_host.yaml`) kennt:
- `granite-tiny` (Port 8080)
- `granite-embed` (Port 8081)

**Noch alte Modellnamen in:**
- `scripts/chat.py` Z.26: nutzt `model="agent-local"` → **nicht in LiteLLM Config**
- `tests/test_stack.py` Z.31: nutzt `model="agent-local"` → **geht an Port 8002 (Agent Server), nicht LiteLLM — korrekt**
- `docker/litellm_config.yaml` (Original): enthält `agent-local`, `agent-researcher` etc. → **nicht aktiv**

**Wichtig:** `chat.py` schickt `agent-local` an Port 4000 (LiteLLM) — dieser Modellname existiert nicht in `litellm_config_host.yaml`. Das ist ein **echter Bug** in `chat.py`.  
`test_stack.py` schickt `agent-local` an Port 8002 (Agent Server) — dort ist der Name in `server.py` Z.54 registriert — **korrekt**.

---

## 2. Neue Namen — aktueller Stand

### litellm_config_host.yaml — vollständiger Inhalt
```yaml
model_list:
  - model_name: granite-tiny        # Port 8080, Reasoning
  - model_name: granite-embed       # Port 8081, Embedding

guardrails:
  - guardrail_name: headroom-compression   # DISABLED — headroom-ai nicht installiert
    litellm_params:
      mode: pre_call
      api_base: http://127.0.0.1:8787

general_settings:
  master_key: sk-cos-local-dev

litellm_settings:
  drop_params: true
  success_callback: ["arize_phoenix"]
  failure_callback: ["arize_phoenix"]
```

**Diskrepanz:** Guardrails-Block referenziert Headroom auf Port 8787 — headroom-ai ist deinstalliert. Dieser Block wird beim Start Fehler/Warnungen erzeugen.

### chat.py Bug
`chat.py` Z.26: `model="agent-local"` → LiteLLM kennt diesen Namen nicht.  
Fix nötig: entweder `model="granite-tiny"` (direkt LLM) oder Port auf 8002 ändern (Agent Server).

---

## 3. Was wurde gemacht — Chronologie

### Architektur-Entscheidungen umgesetzt
| Entscheidung | Status |
|-------------|--------|
| Ollama → llama-server (llama-cpp-python) | ✓ |
| Qdrant → ChromaDB (embedded) | ✓ |
| langchain-ollama → langchain-openai | ✓ |
| torch/transformers entfernt | ✓ |
| Open WebUI entfernt | ✓ (nie installiert) |
| Docker-Stack entfernt | ✓ |
| Audio/Meeting Pipeline disabled | ✓ |
| Docling disabled | ✓ |
| Headroom disabled | ✓ (headroom-ai deinstalliert) |
| LiteLLM als zentrales Gateway | ✓ |
| Arize Phoenix für Observability | ✓ |
| MCP git + fetch Server | ✓ |
| Granite Embedding 30m | ✓ |
| Docker Image via GitHub Actions | ✓ |

### Neu erstellte Dateien (nicht im Original)
- `agents/server/telemetry.py` — Phoenix + LangChain Instrumentierung
- `agents/server/tool_formatter.py` — Generischer Tool Formatter (18/18 Tests)
- `agents/server/tools.py` — get_tools_system_prompt()
- `docker/litellm_config_host.yaml` — LiteLLM Config
- `docker/entrypoint.sh` — Docker Start-Script
- `Dockerfile` — Docker Image Definition
- `.github/workflows/docker.yml` — GitHub Actions
- `.dockerignore`
- `requirements-host.txt` — ohne torch/qdrant/ollama
- `deploy-host.sh` — Deploy Script
- `deploy/systemd/*.service` — 4 systemd Units
- `scripts/chat.py` — Terminal Chat Client
- `scripts/start_litellm.sh`, `start_phoenix.sh`, `start_headroom.sh`
- `mcp/mcp.json` — MCP Server Config
- `HANDOFF.md`, `JANHET_SETUP.md`, `STATUS_REPORT.md`
- `docs/INSTALL_JANHET.md`, `docs/MCP_SERVERS.md`
- `tests/test_stack.py`, `tests/run_tests.py`, `tests/TEST_RESULTS.md`
- `tests/test_tool_formatter.py`

### Veränderte Original-Dateien
| Datei | Änderung |
|-------|---------|
| `agents/server/code.py` | ChatOllama→ChatOpenAI, Port 4000 |
| `agents/server/comms.py` | ChatOllama→ChatOpenAI, Port 4000 |
| `agents/server/handoff.py` | ChatOllama→ChatOpenAI, Qdrant→ChromaDB |
| `agents/server/notes.py` | ChromaDB statt Qdrant |
| `agents/server/researcher_v2.py` | metadata key fix, Port 4000 |
| `agents/server/supervisor.py` | Ollama→OpenAI, meeting disabled, ROUTING_TOOLS hinzugefügt |
| `agents/server/config.py` | CHROMA_PATH statt Qdrant URL |
| `agents/server/server.py` | Phoenix init_phoenix() beim Start |
| `agents/ingestion/ingest.py` | Qdrant→ChromaDB, Docling disabled |
| `agents/ingestion/search.py` | ChromaDB, Filter-Fix |
| `agents/notes/recorder.py` | Disabled (print + exit) |
| `agents/server/meeting.py` | Disabled |
| `README.md` | Komplett neu für host |
| `requirements.txt` | Fork-Header hinzugefügt |

### Entfernte Original-Dateien
- `CoS.workflow/` — macOS Automator
- `installer/` — Original Installer
- `specialists/` — whisper.cpp Wrapper
- `install.sh`, `install.bat`, `install.py`
- `start.sh`, `stop.sh`
- `docker/docker-compose.yml`
- `docs/INSTALL.md`, `docs/TROUBLESHOOTING.md`
- `logs/`, `data/` (Verzeichnisse)

---

## 4. Was wurde getestet

### Existierende Test-Dateien
- `tests/test_stack.py` — 6-Agenten Test Suite
- `tests/run_tests.py` — Stack starten + Tests ausführen
- `tests/test_tool_formatter.py` — tool_formatter Unit Tests

### Letzter Testlauf Ergebnisse

| Komponente | Status | Detail |
|-----------|--------|--------|
| llama-server :8080 | ✓ | Granite 350m, ~25 t/s |
| llama-server :8081 | ✓ | Embedding 30m, 384-dim, ~15ms |
| LiteLLM :4000 | ✓ | Routet korrekt |
| Phoenix :6006 | ✓ | Traces empfangen |
| Agent Server :8002 | ✓ | 7 Modelle registriert |
| ChromaDB | ✓ | Echte Embeddings (384-dim) |
| Comms Agent | ✓ | E-Mail generiert |
| Code Agent | ✓ | Python Funktion |
| Researcher Agent | ✓ | Antwortet |
| Notes Agent | ⚠️ | Antwortet, Routing unzuverlässig |
| Handoff Agent | ⚠️ | Antwortet, Routing unzuverlässig |
| MCP git_log direkt | ✓ | Commit History gelesen |
| MCP durch Agent | ⚠️ | Tools laden, aber 350m ruft nicht auf |
| Tool-Calling | ✓ | <tool_call> generiert mit nativem Format |
| tool_formatter.py | ✓ | 18/18 Tests |
| Supervisor Routing | ⚠️ | 350m zu klein, englische Prompts nötig |

### Bekannte Probleme
1. **Routing 350m** — nutzt `first_token` Parsing, 350m antwortet mit Sätzen statt Agent-Namen. Auf host mit 4B korrekt.
2. **chat.py Bug** — `model="agent-local"` an Port 4000 — Modellname nicht in LiteLLM Config.
3. **Headroom Guardrail in Config** — Config referenziert Port 8787 obwohl headroom-ai deinstalliert.
4. **run_tests.py** — hat Readiness-Check Änderung die noch nicht vollständig getestet wurde.

---

## 5. Konfiguration

### mcp/mcp.json
```json
{
  "mcpServers": {
    "git": {
      "command": "python3",
      "args": ["-m", "mcp_server_git", "--repository", "/home/claude/la"],
      "transport": "stdio"
    },
    "fetch": {
      "command": "python3", 
      "args": ["-m", "mcp_server_fetch"],
      "transport": "stdio"
    }
  }
}
```
**Problem:** Pfad `/home/claude/la` ist Sandbox-spezifisch. Auf host muss es `/home/user/la` sein.

### deploy/systemd/ — Status

| Service | Gedacht für | Disabled? |
|---------|------------|---------|
| `litellm.service` | host | Nein — aktiv |
| `phoenix.service` | host | Nein — aktiv |
| `local-agent.service` | host | Nein — aktiv |
| `headroom.service` | host | **Ja — headroom-ai deinstalliert** |

### requirements-host.txt vs requirements.txt
| | requirements.txt | requirements-host.txt |
|--|-----------------|------------------------|
| **Zweck** | Original Mac/Docker | host/Sandbox |
| **Maßgeblich** | Nein | **Ja** |
| **torch** | Ja | Nein |
| **qdrant** | Ja | Nein |
| **docling** | Ja | Nein (disabled) |
| **headroom-ai** | Nein | Nein (disabled) |
| **llama-cpp-python** | Nein | Kommentiert (via Wheel im Dockerfile) |
| **chromadb** | Nein | Ja |
| **litellm** | Ja | Ja |
| **arize-phoenix** | Nein | Ja |

---

## 6. Docker-Build Status

### Letzter Build
- **Run ID:** 29481428131
- **Status:** ✓ **SUCCESS**
- **Gestartet:** 2026-07-16T07:52:40Z
- **Image:** `ghcr.io/janhetzler/la:latest`

### Image-Inhalt
- Base: `python:3.12-slim-bookworm`
- llama-cpp-python 0.3.23 (Prebuilt Wheel, kein C++ Build)
- Granite 350m Q4_K_M (213 MB) — direkt im Image
- Granite Embedding 30m Q4_0 (28 MB) — direkt im Image
- Alle Pakete aus requirements-host.txt
- Rust + build-essential (für chromadb Kompilierung)

### Bekannte Probleme im Dockerfile
1. **Rust bleibt im Image** — wird nur für chromadb gebraucht, macht Image ~500 MB größer als nötig. Fix: Multi-Stage Build
2. **Headroom Guardrail in litellm_config_host.yaml** — wird beim Start Warnungen erzeugen
3. **chat.py Bug** — `model="agent-local"` funktioniert nicht direkt gegen LiteLLM
4. **mcp.json Pfad** — `/home/claude/la` ist falsch im Container, sollte `/app` sein
