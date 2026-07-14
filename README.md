# Chief of Staff — janhet Edition

> A 100% local, open-source, multi-agent personal AI assistant — powered by Granite open-weight models, orchestrated with LangGraph, running on a Hetzner KVM vServer (AMD EPYC 7443P, 4 vCores, 10 GB RAM). No paid APIs, no data leaving your machine.

---

## What it does

A single chat interface — the **Chief of Staff** — that understands what you ask and delegates to the right specialist. Six agents work behind the scenes:

| Agent | Role |
|---|---|
| 🎯 **Chief of Staff** | Orchestrator, routes to specialists |
| 📚 **Researcher** | Searches your indexed library (ChromaDB RAG) + web |
| 📝 **Comms** | Drafts emails, messages, short reports |
| 🗒️ **Notes** | Explores your knowledge base |
| 💻 **Code** | Programming Q&A + GitHub issues |
| 🔀 **Handoff** | Prepares prompts for Claude.ai / ChatGPT |

---

## Architecture (janhet)

```
┌─────────────────────────────────────────────────────────┐
│ Interface — Terminal chat.py or VS Code 1.127 LM API    │
├─────────────────────────────────────────────────────────┤
│ LiteLLM proxy (OpenAI-compatible, port 4000)            │
│ + Arize Phoenix Observability (port 6006)               │
├─────────────────────────────────────────────────────────┤
│ FastAPI + LangGraph (agents, port 8002)                 │
│ 1 supervisor + 5 active specialists                     │
├─────────────────────────────────────────────────────────┤
│ llama-server (port 8080) — Granite 4.0-H-Tiny IQ4_XS   │
│ llama-server (port 8081) — granite-embedding-30m        │
├─────────────────────────────────────────────────────────┤
│ ChromaDB (embedded) — vector store for RAG              │
└─────────────────────────────────────────────────────────┘
```

**Key differences from the original Mac/Docker version:**
- No Docker, no Ollama, no Open WebUI
- No torch/transformers — embeddings via LiteLLM → llama-server
- Qdrant → ChromaDB (embedded, no separate service)
- Audio/Meeting pipeline disabled (headless server)
- Arize Phoenix for observability/tracing

---

## Models

| Model | Size | Role |
|---|---|---|
| `granite-4.0-h-tiny.i1-IQ4_XS.gguf` | 4.2 GB | All agents — reasoning, tool-calling |
| `granite-embedding-30m` | 62 MB | RAG embeddings (384-dim) |

---

## Quick start (janhet)

```bash
# 1. Clone
git clone https://github.com/janhetzler/la /home/user/chief/la
cd /home/user/chief/la

# 2. Python venv ohne torch
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-janhet.txt

# 3. LiteLLM starten
bash scripts/start_litellm.sh

# 4. Phoenix starten (optional)
bash scripts/start_phoenix.sh

# 5. Agent Server starten
cd agents/server
uvicorn server:app --host 127.0.0.1 --port 8002

# 6. Terminal Chat
python3 scripts/chat.py
```

---

## Test results (Claude container — Granite 4.0-H 350m)

Validated end-to-end on a 1-core Intel Xeon @ 2.1 GHz, 4 GB RAM:

| Component | Status |
|-----------|--------|
| llama-server | ✓ |
| LiteLLM routing | ✓ |
| Phoenix observability | ✓ |
| FastAPI Agent Server | ✓ |
| Supervisor routing | ✓ |
| Comms Agent | ✓ |
| Researcher Agent | ✓ |
| Code Agent | ✓ |
| ChromaDB write/read | ✓ |
| LiteLLM request logging | ✓ (5 POST requests logged) |

Routing correctly identifies language and delegates:
- German input → `researcher`
- English/code input → appropriate agent

Response time: 20–30s per call on 1-core Xeon. Expected 5–10s on janhet EPYC with 4 cores.

---

## Project structure

```
chief-of-staff/
├── requirements-janhet.txt          # Dependencies ohne torch/qdrant/ollama
├── deploy-janhet.sh                 # Deployment script für janhet
│
├── scripts/
│   ├── chat.py                      # Terminal Chat Client
│   ├── start_litellm.sh             # LiteLLM Proxy starten
│   └── start_phoenix.sh             # Arize Phoenix starten
│
├── docker/
│   ├── litellm_config_janhet.yaml   # LiteLLM Config für janhet
│   └── litellm_config.yaml          # Original Mac/Docker Config
│
├── agents/
│   ├── server/                      # 6 LangGraph agents + supervisor
│   │   ├── telemetry.py             # NEU: Phoenix + LiteLLM Client
│   │   └── config.py                # ChromaDB statt Qdrant
│   ├── notes/                       # recorder.py disabled auf Server
│   └── ingestion/                   # ChromaDB statt Qdrant
│
├── mcp/mcp.json                     # MCP Server Config (leer = kein MCP)
└── JANHET_SETUP.md                  # Detaillierte Setup-Dokumentation
```

---

## Disabled on janhet

- `agents/notes/recorder.py` — Audio capture (no hardware)
- `agents/server/meeting.py` — Meeting pipeline
- Docker/Ollama/Open WebUI — replaced by native llama-server

---

## Credits

Built on: [Granite](https://www.ibm.com/granite) · [LangGraph](https://github.com/langchain-ai/langgraph) · [LiteLLM](https://github.com/BerriAI/litellm) · [ChromaDB](https://www.trychroma.com) · [Arize Phoenix](https://phoenix.arize.com) · [llama.cpp](https://github.com/ggml-org/llama.cpp) · [Docling](https://github.com/DS4SD/docling)

Original project: [xaviervasques/chief-of-staff](https://github.com/xaviervasques/chief-of-staff)

## License

MIT
