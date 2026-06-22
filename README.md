# Chief of Staff

> A 100% local, open-source, multi-agent personal AI assistant — powered by Granite open-weight models, orchestrated with LangGraph, running on your laptop. No paid APIs, no data leaving your machine.

---

## What it does

A single chat interface — the **Chief of Staff** — that understands what you ask and delegates to the right specialist. Six agents work behind the scenes:

| Agent | Role | Tools |
|---|---|---|
| 🎯 **Chief of Staff** | Orchestrator, routes to specialists | (none — pure routing) |
| 📚 **Researcher** | Searches your indexed library + web | Qdrant RAG, Tavily, filesystem |
| 📝 **Comms** | Drafts emails, messages, short reports | (none — pure synthesis) |
| 🗒️ **Notes** | Explores your Obsidian vault | search_meetings, filesystem |
| 💻 **Code** | Programming Q&A + GitHub issues | GitHub MCP |
| 🔀 **Handoff** | Prepares prompts for Claude.ai / ChatGPT | Qdrant RAG for context |
| 🎙️ **Meeting** | Records meetings and produces structured notes | start/stop/status |

Plus:
- **Meeting capture pipeline** — audio capture (BlackHole) → transcription (whisper.cpp) → structured summary (Granite) → indexed in Qdrant
- **Categorized document ingestion** — drop a PDF into `data/library/<category>/` and it gets auto-indexed for RAG
- **Multilingual** — French, English, Spanish, Portuguese, German, Italian, and more
- **Honest handoff** — when local 7B isn't enough, prepares a prompt for your existing Claude.ai or ChatGPT subscription

---

## Quick start

### Requirements
- macOS 13+ (Apple Silicon recommended), Linux, or Windows 10+ (WSL2)
- 16 GB RAM (12 GB minimum)
- 25 GB free disk space
- Python 3.10+
- A container runtime: Docker Desktop, OrbStack, Colima, or Docker Engine

### Install (one time)

```bash
git clone https://github.com/<your-username>/chief-of-staff.git
cd chief-of-staff

# macOS / Linux
./install.sh

# Windows
install.bat
```

The installer is interactive and runs **8 verification + setup steps**:

1. **Prerequisites** — checks RAM, disk, Python, OS
2. **System tools** — verifies Docker and Ollama
3. **AI models** — pulls Granite 4 tiny-h, micro-h, and embedding (~7 GB)
4. **whisper.cpp** — clones, compiles, and downloads the Medium model (~1.5 GB)
5. **Python venv** — creates `.venv/` and installs `requirements.txt`
6. **Secrets** — interactively prompts for GitHub and Tavily keys, writes `.env`
7. **Docker stack** — starts Qdrant, Postgres, LiteLLM, Open WebUI
8. **End-to-end validation** — smoke test that everything works

Total time: 30 to 45 minutes depending on internet speed.

### Daily use

```bash
./start.sh             # bring everything up (~30 sec)
open http://localhost:3000     # macOS — or xdg-open / start
./stop.sh              # stop everything
```

In Open WebUI, select **agent-chief-of-staff** in the model picker and start chatting.

---

## Architecture

Six layers, all running locally:

```
┌─────────────────────────────────────────────────────────┐
│ Layer 6 — Open WebUI (chat interface, port 3000)        │
├─────────────────────────────────────────────────────────┤
│ Layer 5 — LiteLLM proxy (OpenAI-compatible, port 4000)  │
├─────────────────────────────────────────────────────────┤
│ Layer 4 — FastAPI + LangGraph (agents, port 8002)       │
│           1 supervisor + 6 specialists                  │
├─────────────────────────────────────────────────────────┤
│ Layer 3 — Specialists API (port 8001)                   │
│           whisper.cpp wrapper, embeddings, safety       │
├─────────────────────────────────────────────────────────┤
│ Layer 2 — Ollama (port 11434) + MCP servers (stdio)     │
│           Granite models + filesystem/GitHub/Tavily     │
├─────────────────────────────────────────────────────────┤
│ Layer 1 — Data                                          │
│           Qdrant (6333) + Postgres (5432) + Obsidian    │
└─────────────────────────────────────────────────────────┘
```

The OpenAI Chat Completions API is the lingua franca between layers — any component can be swapped as long as it speaks the API.

---

## Models

Primary models (used by the agents):

| Model | Size | Role |
|---|---|---|
| `ibm/granite4:tiny-h` | 4.2 GB | All agents — reasoning, tool-calling |
| `ibm/granite4:micro-h` | 1.9 GB | Fast classification, short outputs |
| `granite-embedding:30m` | 62 MB | RAG embeddings (384-dim, multilingual) |
| `whisper.cpp ggml-medium.bin` | 1.5 GB | Meeting transcription |

Optional models (available in the Open WebUI picker for experimentation, not used by agents):

| Model | Notes |
|---|---|
| `mistral` (7B) | Strong multilingual baseline |
| `gemma3:4b` | Small and fast alternative |
| `ibm/granite3.2-guardian:3b` | Safety classifier |

Pull them with `ollama pull <model>` if you want to chat with them directly.

---

## Project structure

```
chief-of-staff/
├── install.sh / install.bat / install.py    # cross-OS guided installer
├── start.sh / stop.sh                       # daily lifecycle scripts
├── requirements.txt                         # Python dependencies (pinned)
│
├── docker/
│   ├── docker-compose.yml                   # Qdrant, Postgres, LiteLLM, Open WebUI
│   └── litellm_config.yaml                  # routes agents + models
│
├── agents/
│   ├── server/                              # 6 LangGraph agents + supervisor (port 8002)
│   ├── notes/                               # meeting recorder + post-processor
│   └── ingestion/                           # document watcher + ingest pipeline
│
├── specialists/main.py                      # whisper.cpp + embeddings wrapper (port 8001)
│
├── installer/
│   ├── checks.py, colors.py
│   ├── steps/                               # 8 install steps
│   └── data/demo-attention-is-all-you-need.pdf   # demo paper for first-time RAG test
│
├── mcp/mcp.json.template                    # MCP servers config (filesystem/github/tavily)
│
├── data/library/                            # drop documents here for RAG ingestion
│   ├── idn/   research/   personal/   admin/   inbox/
│
├── vault/                                   # Obsidian-compatible markdown notes (gitignored)
├── docs/                                    # detailed install + troubleshooting
└── BUGS.md                                  # known issues
```

---

## Customization

Three things to personalize the system:

- **`agents/server/user_profile.py`** — your identity, style, tone preferences, expertise areas. Ships as a template; fill in the placeholders.
- **`agents/server/project_context.py`** — what the system can do, so agents reference local capabilities instead of generic suggestions.
- **`data/library/<category>/`** — library category folders. The default set (`idn`, `research`, `personal`, `admin`, `inbox`) is illustrative; rename or add categories to match how you organize your documents. If you change them, also update `VALID_CATEGORIES` in `agents/ingestion/{search,ingest}.py` and `CATEGORY_FOLDERS` in `agents/ingestion/watcher.py`.

Edit them freely. The more precise they are, the more the system feels personalized.

---

## Adding a new agent

Pattern in 5 steps (~15 min):

1. Create `agents/server/<name>.py` modeled on `comms.py` (simple) or `researcher_v2.py` (with tools)
2. Import + register in `AGENTS` dict in `agents/server/server.py`
3. Add to router in `agents/server/supervisor.py` (`ROUTER_PROMPT`, `VALID_AGENTS`, `invoke_supervisor`)
4. Declare in `docker/litellm_config.yaml`
5. `docker compose restart litellm`

---

## Known limitations

- **Latency**: ~10-30 sec per response on a 16 GB M3 (first call slower while the model warms up)
- **Pipeline réunion**: macOS-only out of the box (BlackHole 2ch). Linux/Windows works but needs manual audio loopback setup (PulseAudio loopback / VB-Cable)
- **No streaming**: responses arrive in one chunk
- **Hallucinations on bulky tool outputs**: that's why the Handoff agent exists
- **Single-user**: no multi-tenancy, no auth — don't expose port 3000 to your network

See [BUGS.md](./BUGS.md) for current open issues and good first-contribution opportunities.

---

## Documentation

- **Installation guide**: [docs/INSTALL.md](./docs/INSTALL.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)
- **Architecture deep dive**: see the Medium article (link below)

---

## Article

A complete engineering deep dive on this project — the why, the how, and the lessons learned — is published on Medium:

📖 **[I Built a 100% Local AI Chief of Staff on My Laptop. Here's the Full Blueprint.](https://medium.com/@xaviervasques)**

---

## Credits

Built on these open-source projects:

- [Granite](https://www.ibm.com/granite) — open-weight foundation models (Apache 2.0)
- [Ollama](https://ollama.com) — local LLM runtime
- [LangChain / LangGraph](https://github.com/langchain-ai/langgraph) — agent orchestration
- [LiteLLM](https://github.com/BerriAI/litellm) — unified proxy
- [Open WebUI](https://github.com/open-webui/open-webui) — chat interface
- [Qdrant](https://qdrant.tech) — vector store
- [Model Context Protocol](https://modelcontextprotocol.io) — universal tool protocol
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) — fast local transcription
- [Docling](https://github.com/DS4SD/docling) — open-source document parser
- [Tavily](https://tavily.com) — web search API
- Vaswani et al. 2017 — "Attention Is All You Need" (the demo PDF that's indexed during install)

---

## License

MIT — see [LICENSE](./LICENSE).

Contributions welcome. Open an issue, fork, send a PR. If you build something interesting on top of this, I'd love to hear about it.
