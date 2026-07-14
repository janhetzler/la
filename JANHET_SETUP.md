# Chief-of-Staff — janhet Deployment Status
## Stand: Juli 2026

---

## 1. Umgebung (Claude Container — Analyse & Test)

### Installation
```bash
git clone https://github.com/janhetzler/la
cd la
pip install -r requirements.txt  # original, mit torch
```

### Installierte Pakete (relevant)
| Paket | Version | Zweck |
|-------|---------|-------|
| torch | 2.11.0 | Embedding (wird auf janhet ersetzt) |
| langchain | 1.2.15 | Agent Framework |
| langchain-openai | 1.2.1 | LiteLLM Anbindung |
| langchain-ollama | 1.1.0 | Original Mac — auf janhet nicht genutzt |
| langgraph | 1.1.10 | Agent Orchestrierung |
| fastapi | 0.136.1 | API Server |
| uvicorn | 0.51.0 | ASGI Server |
| chromadb | 1.5.9 | Vektordatenbank (ersetzt Qdrant) |
| llama-index-embeddings-litellm | 0.5.0 | Embeddings via LiteLLM |
| langchain-mcp-adapters | 0.2.2 | MCP Tool Integration |

### Gemessene Performance
| Metrik | Wert | Ursache |
|--------|------|---------|
| Supervisor Import | **75–84 Sekunden** | torch |
| Server Import | 0,26 Sekunden | schnell |
| Disk (Dependencies) | ~11 GB | torch + transformers |
| RAM beim Import | ~800 MB | torch |

### Fazit torch auf janhet
- 75s Startzeit ist inakzeptabel für einen Dienst
- **Lösung:** `requirements-janhet.txt` ohne torch — Embeddings via LiteLLM

---

## 2. Code-Analyse

### Architektur
```
FastAPI :8002
  └── Supervisor (supervisor.py)
        ├── code      → Code-Debugging, Bash-Skripte
        ├── comms     → E-Mail, Slack
        ├── handoff   → Prompt für Claude.ai/ChatGPT aufbereiten
        ├── meeting   → DISABLED auf janhet (kein Audio)
        ├── notes     → Notizen in ChromaDB speichern
        ├── researcher → RAG-Suche in ChromaDB
        └── tools     → MCP Server Integration
```

### Routing-Logik
Supervisor bekommt User-Message → LLM entscheidet welcher Agent →
Agent macht seinen Job → Antwort zurück.
**Kontext pro Call: nur aktuelle Message + Agent-System-Prompt.**
Kein volles Konversations-History-Dumping → 8K reicht.

### API-Endpunkte
| Route | Funktion |
|-------|---------|
| GET /health | Status-Check |
| GET /v1/models | Modell-Liste (VS Code kompatibel) |
| POST /v1/chat/completions | Haupt-Endpunkt (OpenAI-kompatibel) |
| GET /docs | Swagger UI |

---

## 3. Durchgeführte Änderungen

### 3.1 supervisor.py
- `from langchain_ollama import ChatOllama` → `from langchain_openai import ChatOpenAI`
- `base_url="http://localhost:11434"` → `base_url="http://localhost:4000/v1"`
- Meeting Agent disabled (kein Audio auf Server)
- Mac-Referenzen → janhet

### 3.2 notes.py
- `client.query_points()` (Qdrant API) → `collection.query()` (ChromaDB API)
- `config.QDRANT_COLLECTION` → `config.CHROMA_COLLECTION`

### 3.3 researcher_v2.py
- Key-Mapping fix: `r['source']` → `r['metadata']['source']`
- Key-Mapping fix: `r['category']` → `r['metadata']['category']`

### 3.4 recorder.py (agents/notes/)
- Disabled mit Header-Kommentar
- Kein sounddevice/soundfile auf Server

### 3.5 handoff.py, comms.py, code.py
- `ChatOllama` → `ChatOpenAI` auf Port 4000
- `model="ibm/granite4:tiny-h"` → `model="granite-tiny"`

---

## 4. Was getestet wurde

| Test | Ergebnis |
|------|---------|
| `import supervisor` | ✓ OK (75s wegen torch) |
| `import server` | ✓ OK (0.26s) |
| FastAPI startet | ✓ OK, alle 7 Routes vorhanden |
| `/health` erreichbar | ✓ OK |
| `/v1/models` erreichbar | ✓ OK |
| Echter LLM-Call | ✗ Nicht getestet (kein LiteLLM/Granite hier) |
| ChromaDB Schreiben | ✗ Nicht getestet |
| ChromaDB Suche | ✗ Nicht getestet |
| MCP Tools | ✗ Nicht getestet |

---

## 5. Was auf janhet noch fehlt

### Zwingend für Start:
1. **LiteLLM** auf Port 4000 mit Granite-Tiny Config
2. **llama-server Embedding** auf Port 8081 mit granite-embedding-30m
3. **ChromaDB** Verzeichnis anlegen: `/app/workspace/chroma_db`
4. **.env** Datei mit:
   ```
   OPENAI_API_KEY=sk-cos-local-dev
   LITELLM_URL=http://localhost:4000
   CHROMA_PATH=/app/workspace/chroma_db
   ```

### Optional (später):
5. MCP Server für tools.py
6. Arize Phoenix auf Port 6006
7. Headroom Proxy auf Port 8787

---

## 6. Deployment auf janhet

```bash
# Repository holen
git clone https://github.com/janhetzler/la /home/user/chief/la
cd /home/user/chief/la

# Python-Umgebung OHNE torch
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-janhet.txt

# Starten
cd agents/server
uvicorn server:app --host 127.0.0.1 --port 8002
```

Erwartete Startzeit ohne torch: **< 5 Sekunden**
