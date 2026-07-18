# Local Agent (la)

> Ein vollstaendig lokaler, quelloffener Multi-Agenten-Assistent --
> laeuft auf eigener Infrastruktur mit IBM Granite Modellen,
> orchestriert mit LangGraph. Keine bezahlten APIs, keine Daten
> verlassen die eigene Maschine.

Fork von [xaviervasques/chief-of-staff](https://github.com/xaviervasques/chief-of-staff),
MIT-lizenziert, seitdem grundlegend umgebaut.

---

## Drei Umgebungen

Dieses Projekt existiert in drei parallelen Umgebungen -- jede mit eigener
Dokumentation, eigenen Requirements und eigenen Start-Skripten:

| Umgebung | Zweck | Dokumentation |
|---|---|---|
| Sandbox | Claude.ai Entwicklungsumgebung, kurzlebig | [docs/SANDBOX.md](docs/SANDBOX.md) |
| Host | Produktivbetrieb auf eigenem Server (systemd) | [docs/INSTALL_HOST.md](docs/INSTALL_HOST.md) |
| Docker | Portable Version, fuer jeden x86_64 Server | [docs/DOCKER.md](docs/DOCKER.md) |

### Hardware im Vergleich

| | Sandbox | Host (Empfehlung) | Docker |
|---|---|---|---|
| CPU | Intel Xeon, 1 Core | x86_64, 4 Cores (AMD EPYC) | x86_64, 1 Core |
| RAM | 4 GB | 10 GB | 4 GB |
| Inferenz | llama-cpp-python (Python) | llama-server (Binary) | llama-cpp-python (Python) |
| Reasoning-Modell | Granite-4.0-H-350m (213 MB) | Granite-4.0-H-Tiny (4.2 GB) | Granite-4.0-H-350m (213 MB) |
| Persistenz | Keine -- stirbt nach Session | Dauerhaft (systemd) | Dauerhaft (Container) |

---

## Was es tut

Sechs Agenten hinter einer einzigen Chat-Oberflaeche:

| Agent | Rolle |
|---|---|
| Supervisor | Orchestriert, routet zu Spezialisten |
| Researcher | Durchsucht ChromaDB RAG + Web |
| Comms | E-Mails, Nachrichten, Kurzberichte |
| Notes | Wissensdatenbank in ChromaDB |
| Code | Programmier-Fragen + GitHub Issues |
| Handoff | Bereitet Prompts fuer Claude.ai/ChatGPT vor |

---

## Architektur

```
Interface -- Terminal chat.py oder VS Code Language Model API
    |
LiteLLM Proxy (Port 4000) + Arize Phoenix Observability (Port 6006)
    |
FastAPI + LangGraph Agent-Server (Port 8002)
    |
llama-server Reasoning (Port 8080) + llama-server Embedding (Port 8081)
    |
ChromaDB (embedded) -- Vektorspeicher fuer RAG
```

---

## Agenten-System

### Konfigurationsbasierte Architektur

Agenten werden nicht in Python hartkodiert -- sie werden aus Konfigurationsdateien
geladen. Ein neuer Agent = eine neue `.md` Datei, kein Python anfassen.

```
prompts/
├── shared/
│   ├── user_profile.md       <- Wer bist du? Deine Praeferenzen.
│   └── project_context.md    <- Welche Projekte, welcher Stack?
└── agents/
    ├── router.md             <- Router-System-Prompt
    ├── comms.md              <- Comms Agent Prompt + Metadaten
    ├── code.md               <- Code Agent Prompt + Metadaten
    ├── notes.md              <- Notes Agent Prompt + Metadaten
    ├── researcher.md         <- Researcher Agent Prompt + Metadaten
    └── handoff.md            <- Handoff Agent Prompt + Metadaten
```

### Aufbau einer Agent-.md Datei (YAML-Frontmatter)

```markdown
---
name: comms
description: "E-Mails, Nachrichten, Kurzberichte. Kein RAG, keine Suche."
tools: []
temperature: 0.3
model: null
---
Du bist der Kommunikations-Spezialist.

{{ project_context }}

{{ user_profile }}

Deine Aufgabe: ...
```

Der YAML-Header enthaelt die Metadaten. Der Text darunter ist der System-Prompt.
`{{ user_profile }}` und `{{ project_context }}` werden automatisch
aus `prompts/shared/` injiziert.

### Was wo geaendert werden muss

| Ich moechte... | Datei aendern |
|---|---|
| System-Prompt eines Agenten aendern | `prompts/agents/<agent>.md` |
| Temperatur oder Modell eines Agenten aendern | `prompts/agents/<agent>.md` (Frontmatter) |
| Tools eines Agenten aendern | `prompts/agents/<agent>.md` (Frontmatter: `tools:`) |
| Meinen persoenlichen Kontext aktualisieren | `prompts/shared/user_profile.md` |
| Projektkontext aktualisieren | `prompts/shared/project_context.md` |
| Router-Logik aendern | `prompts/agents/router.md` |
| Neuen Agenten hinzufuegen (rein textbasiert) | Neue `prompts/agents/<name>.md` anlegen |
| Neuen Agenten mit eigener Logik hinzufuegen | `prompts/agents/<name>.md` + `agents/server/<name>.py` |
| Agent-Lade-Logik aendern | `agents/server/agent_loader.py` |
| Routing-Logik (Python) aendern | `agents/server/supervisor.py` |
| Stack-Konfiguration (Ports, Keys) | `config/<umgebung>/*.env` |

### Hybrides Design

Reine Text-Agenten (comms, code) werden komplett aus `.md` geladen,
kein eigenes Python mehr.

Logik-Agenten (notes, researcher, handoff) behalten Python fuer
ChromaDB-Zugriff, RAG-Suche und Template-Logik. Laden aber ihren
System-Prompt aus `prompts/agents/*.md`.

### Shared Context

Beide Dateien werden beim Start in jeden Agenten injiziert:

**`prompts/shared/user_profile.md`** -- Wer bist du?
Dein Name, deine Rolle, deine Praeferenzen, deine Projekte.
Diese Datei muss von dir manuell befuellt werden.

**`prompts/shared/project_context.md`** -- Was laeuft gerade?
Aktueller Stack, aktive Aufgaben, Architektur-Entscheidungen.
Diese Datei muss von dir manuell befuellt werden.

---

## Umgebungskonfiguration

Alle Werte (URLs, Keys, Pfade) kommen aus `.env` Dateien:

```
config/
├── sandbox/
│   ├── common.env    <- LITELLM_URL, LITELLM_KEY, PHOENIX_HOST
│   ├── agent.env     <- CHROMA_PATH, MODEL_PATH, MCP_CONFIG_PATH
│   ├── litellm.env   <- LITELLM_PORT, LITELLM_CONFIG_PATH
│   └── phoenix.env   <- PHOENIX_PORT, PHOENIX_DATA_PATH
├── host/
│   └── ...           <- gleiche Struktur, andere Werte
└── docker/
    └── ...
```

Umgebung waehlen: `LA_ENV=sandbox` (default), `LA_ENV=host`, `LA_ENV=docker`

---

## MCP Server

Zwei MCP-Server sind konfiguriert und getestet:

| Server | Tools | Zweck |
|---|---|---|
| mcp-server-git | 12 Tools | Repository durchsuchen |
| mcp-server-fetch | 1 Tool | Web-Inhalte abrufen |

Details: [docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)

---

## Modelle

| Modell | Groesse | Rolle |
|---|---|---|
| Granite-4.0-H-Tiny (IQ4_XS) | 4.2 GB | Reasoning, alle Agenten (Host) |
| Granite-4.0-H-350m (Q4_K_M) | 213 MB | Reasoning (Sandbox/Docker) |
| Granite-Embedding-30m | 28-62 MB | RAG-Embeddings |

---

## Observability

Arize Phoenix laeuft auf Port 6006 und erfasst alle LangChain-Calls als Traces.

Nach jedem Testlauf Traces abrufen:

```python
from phoenix.client import Client
from datetime import datetime, timedelta

client = Client(base_url="http://127.0.0.1:6006")
df = client.spans.get_spans_dataframe(
    project_identifier="local-agent",
    limit=20,
    root_spans_only=False,
    start_time=datetime.now() - timedelta(minutes=5)
)
```

---

## Dokumentation

| Datei | Inhalt |
|---|---|
| [docs/SANDBOX.md](docs/SANDBOX.md) | Claude Sandbox aufbauen |
| [docs/INSTALL_HOST.md](docs/INSTALL_HOST.md) | Produktiv-Deployment |
| [docs/DOCKER.md](docs/DOCKER.md) | Docker Image bauen + nutzen |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Architektur-Entscheidungen, Phasen |
| [docs/MCP_SERVERS.md](docs/MCP_SERVERS.md) | MCP-Konfiguration |
| [BUGS.md](BUGS.md) | Bekannte Probleme und Erkenntnisse |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Repo-Struktur und Konventionen |

---

## Credits

Aufgebaut mit: [Granite](https://www.ibm.com/granite) · [LangGraph](https://github.com/langchain-ai/langgraph) · [LiteLLM](https://github.com/BerriAI/litellm) · [ChromaDB](https://www.trychroma.com) · [Arize Phoenix](https://phoenix.arize.com) · [llama.cpp](https://github.com/ggml-org/llama.cpp)

Original-Projekt: [xaviervasques/chief-of-staff](https://github.com/xaviervasques/chief-of-staff) (MIT License)

## Lizenz

MIT
