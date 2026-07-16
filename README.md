# Local Agent (la)

> Ein vollständig lokaler, quelloffener Multi-Agenten-Assistent —
> läuft auf eigener Infrastruktur mit IBM Granite Modellen,
> orchestriert mit LangGraph. Keine bezahlten APIs, keine Daten
> verlassen die eigene Maschine.

Fork von [xaviervasques/chief-of-staff](https://github.com/xaviervasques/chief-of-staff),
MIT-lizenziert, seitdem grundlegend umgebaut.

---

## Drei Umgebungen

Dieses Projekt existiert in drei parallelen Umgebungen — jede mit eigener
Dokumentation, eigenen Requirements und eigenen Start-Skripten:

| Umgebung | Zweck | Dokumentation |
|---|---|---|
| 🧪 **Sandbox** | Claude.ai Entwicklungsumgebung, kurzlebig | [docs/SANDBOX.md](docs/SANDBOX.md) |
| 🖥️ **Host** | Produktivbetrieb auf eigenem Server (systemd) | [docs/HOST.md](docs/HOST.md) |
| 🐳 **Docker** | Portable Version der Sandbox, für jeden x86_64 Server | [docs/DOCKER.md](docs/DOCKER.md) |

### Hardware im Vergleich

| | Sandbox | Host (Empfehlung) | Docker |
|---|---|---|---|
| CPU | Intel Xeon, 1 Core | x86_64, 4 Cores (AMD EPYC) | x86_64, 1 Core (wie Sandbox) |
| RAM | 4 GB | 10 GB | 4 GB (wie Sandbox) |
| Inferenz | llama-cpp-python (Python) | llama-server (Binary) | llama-cpp-python (Python) |
| Reasoning-Modell | Granite-4.0-H-350m (213 MB) | Granite-4.0-H-Tiny (4.2 GB) | Granite-4.0-H-350m (213 MB) |
| Embedding-Modell | Granite-Embedding-30m (28 MB) | Granite-Embedding-30m (28 MB) | Granite-Embedding-30m (28 MB) |
| Persistenz | Keine — stirbt nach Session | Dauerhaft (systemd) | Dauerhaft (Container) |

---

## Was es tut

Sechs Agenten hinter einer einzigen Chat-Oberfläche:

| Agent | Rolle |
|---|---|
| 🎯 Supervisor | Orchestriert, routet zu Spezialisten |
| 📚 Researcher | Durchsucht ChromaDB RAG + Web |
| 📝 Comms | E-Mails, Nachrichten, Kurzberichte |
| 🗒️ Notes | Wissensdatenbank |
| 💻 Code | Programmier-Fragen + GitHub Issues |
| 🔀 Handoff | Bereitet Prompts für Claude.ai/ChatGPT vor |

---

## Architektur

```
Interface — Terminal chat.py oder VS Code Language Model API
    │
LiteLLM Proxy (Port 4000) + Arize Phoenix Observability (Port 6006)
    │
FastAPI + LangGraph Agent-Server (Port 8002)
    │
llama-server Reasoning (Port 8080) + llama-server Embedding (Port 8081)
    │
ChromaDB (embedded) — Vektorspeicher für RAG
```

---

## Kernstück

`agents/` — der ursprüngliche Agent-Code aus dem Original-Projekt,
angepasst für lokalen Betrieb. Alles andere im Repo (Docker, Deploy-Skripte,
Dokumentation) ist im Rahmen dieses Forks entstanden.

**Wichtigste Änderungen gegenüber dem Original:**
- Ollama → llama-server (native Binary / llama-cpp-python)
- Qdrant → ChromaDB (embedded)
- torch/transformers entfernt — Embeddings via LiteLLM
- Open WebUI entfernt — VS Code Language Model API
- Audio/Meeting-Pipeline deaktiviert (Headless-Server)
- Arize Phoenix für Observability hinzugefügt
- MCP-Integration: mcp-server-git + mcp-server-fetch

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

| Modell | Größe | Rolle |
|---|---|---|
| Granite-4.0-H-Tiny (IQ4_XS) | 4.2 GB | Reasoning, alle Agenten (Host) |
| Granite-4.0-H-350m (Q4_K_M) | 213 MB | Reasoning (Sandbox/Docker) |
| Granite-Embedding-30m | 28-62 MB | RAG-Embeddings |

---

## Dokumentation

| Datei | Inhalt |
|---|---|
| [docs/SANDBOX.md](docs/SANDBOX.md) | Claude Sandbox aufbauen |
| [docs/HOST.md](docs/HOST.md) | Produktiv-Deployment |
| [docs/DOCKER.md](docs/DOCKER.md) | Docker Image bauen + nutzen |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Architektur-Entscheidungen, Phasen |
| [docs/MCP_SERVERS.md](docs/MCP_SERVERS.md) | MCP-Konfiguration |
| [docs/BUGS.md](docs/BUGS.md) | Bekannte Probleme |

---

## Credits

Aufgebaut mit: [Granite](https://www.ibm.com/granite) · [LangGraph](https://github.com/langchain-ai/langgraph) · [LiteLLM](https://github.com/BerriAI/litellm) · [ChromaDB](https://www.trychroma.com) · [Arize Phoenix](https://phoenix.arize.com) · [llama.cpp](https://github.com/ggml-org/llama.cpp)

Original-Projekt: [xaviervasques/chief-of-staff](https://github.com/xaviervasques/chief-of-staff) (MIT License)

## Lizenz

MIT
