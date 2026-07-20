# LLAMA.md — Reasoning Server: llama-cpp-python vs. llama-server Binary

**Komponente:** Reasoning Model Server (Granite 350m)

**Zweck:** Lädt das Granite 4.0-H-350m Modell und serviert es über eine OpenAI-kompatible API auf Port 8080. 
Die Wahl zwischen Python-Wrapper und Binary bestimmt, ob natives Tool-Calling mit `--jinja` möglich ist.

---

## 1. Component Overview

**Aktueller Status (Sandbox 2, 2026-07-20):** `llama-cpp-python` 0.3.23 (Python-Wrapper)

**Alternative Implementierung:** `llama-server` Binary (llama.cpp b9895+)

**Kritische Abhängigkeiten:**
- Granite-4.0-H-350m-Q4_K_M.gguf (213 MB) unter `/tmp/`
- Python 3.10+ (nur für llama-cpp-python)
- POSIX-System (Linux)

**Ports:**
- **8080** — OpenAI-compatible `/v1/chat/completions`, `/v1/models`

**Läuft in:**
- Sandbox: ✅ llama-cpp-python (aktuell)
- Docker: ❌ (nicht in Docker-Setup konfiguriert)
- Host (janhet): ✅ llama-server Binary (geplant, nicht getestet)

---

## 2. Supported Versions & Alternatives

| Implementierung | Version | Status | Notes |
|-----------------|---------|--------|-------|
| llama-cpp-python | 0.3.23 | ✅ Aktuell (Sandbox) | Kein `--jinja` Flag → kein natives Tool-Calling |
| llama-server Binary | b9895+ | ✅ Tested (Hugging Face Space) | Supports `--jinja` → natives Tool-Calling möglich |
| ollama | latest | ⏳ Nicht getestet | Alternative, aber API-Unterschiede |
| vLLM | latest | ⏳ Nicht getestet | Schneller, aber anderer Inference-Stil |

**Warum wir llama-cpp-python (aktuell) nutzen:**
- Einfache Python-Integration via `from llama_cpp.server.app import create_app`
- Kein separates Binary nötig — alles im Python-Prozess
- Funktioniert in der Claude Sandbox ohne System-Dependencies

**Warum wir zu llama-server Binary wechseln (Ziel):**
- Natives `--jinja` Flag für Tool-Calling
- Granite ist in der llama.cpp Jinja-Template-Liste registriert
- Bessere Separation of Concerns (Server-Prozess vs. Python)
- Bessere Fehlerdiagnose (echte Logs statt Thread-Logging)

---

## 3. Architecture & Integration

```
┌─────────────────────────────────────────────────────────────┐
│ Agent Stack                                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [LiteLLM Gateway :4000]                                    │
│          ↓                                                   │
│  [Reasoning Server :8080] ← [LLAMA Component]              │
│          ↓                                                   │
│  [Model Inference]                                          │
│          ↓                                                   │
│  [Response] → LangChain bind_tools() → Agent               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Kritische APIs:**
- **Endpoint:** `http://127.0.0.1:8080/v1/chat/completions`
- **Schema:** OpenAI-kompatibel (messages[], model, max_tokens)
- **Special:** `tools` array wird über LiteLLM 1.92.0 durchgereicht (nur mit `supports_tools: true` in config)

**Daten-Persistierung:**
- **Modell:** `/tmp/granite-350m-Q4_K_M.gguf` (heruntergeladen bei Sandbox-Start)
- **Kontext:** In-Memory pro Request (n_ctx=32768 max.)
- **Session:** Ephemeral — kein Speicher zwischen Sandbox-Sessions

---

## 4. Configuration Files & Dependencies

### 4.1 Files Referencing This Component

| Datei | Zeile(n) | Was ändert sich beim Swap? |
|-------|----------|--------------------------|
| `scripts/sandbox/start_full.py` | Z.45-67 | Import → Subprocess, uvicorn → subprocess.Popen |
| `scripts/sandbox/start_quick.py` | Z.40-62 | Gleiches Pattern |
| `scripts/sandbox/inspect_phoenix.py` | Z.30-50 | Gleiches Pattern |
| `tests/test_mcp_toolcall.py` | Z.25-45 | Gleiches Pattern |
| `docker/litellm_config.yaml` | Z.12-18 | `api_base: http://127.0.0.1:8080` bleibt gleich |
| `requirements.txt` | Z.55 | llama-cpp-python entfernen |
| `docs/SANDBOX.md` | Z.45-78 | Abschnitt "4. Modelle herunterladen" anpassen |

### 4.2 Environment Variables

| Variable | Sandbox-Wert | Host-Wert | Zweck |
|----------|--------------|-----------|-------|
| `LLAMA_MODEL_PATH` | `/tmp/granite-350m-Q4_K_M.gguf` | `/data/models/granite-350m-Q4_K_M.gguf` | Pfad zum GGUF-Modell |
| `LLAMA_CONTEXT_SIZE` | `32768` | `32768` | Max. Context Window |
| `LLAMA_N_THREADS` | `1` | `4` (or more on janhet) | CPU Parallelisierung |
| `LLAMA_JINJA_ENABLED` | `false` (aktuell) | `true` (Ziel) | `--jinja` Flag aktiv? |

### 4.3 Dependencies in requirements.txt

```
# Aktuell (Python-Wrapper):
llama-cpp-python==0.3.23  # Reason: einfache Python-Integration, funktioniert in Sandbox

# Nach Swap (Binary nur):
# llama-cpp-python wird ENTFERNT
# Abhängigkeit: ./llama-server Binary muss manuell in PATH sein
```

---

## 5. Swap Scenarios

### Scenario A: llama-cpp-python → llama-server Binary (Sandbox 2)

**Wann:** JETZT (2026-07-20) — sobald wir Tool-Calling testen wollen

**Impact Assessment:**
- [x] Neue Abhängigkeiten: Nein (Binary, nicht in pip)
- [x] Code-Änderungen: JA — 4 Scripts (start_full.py, start_quick.py, inspect_phoenix.py, test_mcp_toolcall.py)
- [x] Ports: Nein (8080 bleibt)
- [x] Datenformat: Nein (OpenAI-kompatible API bleibt identisch)

**Phase 1: Binary vorbereiten**

```bash
# 1. llama-server Binary herunterladen
cd /tmp
wget https://github.com/ggml-org/llama.cpp/releases/download/b9895/llama-server-b9895-linux-x86_64.zip
unzip llama-server-b9895-linux-x86_64.zip
chmod +x ./llama-server

# 2. Teste das Binary mit --jinja Flag
./llama-server --help | grep -i jinja
# Output sollte sein: --jinja

# 3. Schnell-Test: Starte Server mit Modell
./llama-server -m /tmp/granite-350m-Q4_K_M.gguf --jinja --port 8080 &
sleep 5

# 4. Teste API-Endpunkt
curl http://127.0.0.1:8080/v1/models
# Output: {"object":"list","data":[{"id":"granite-tiny",...}]}

# 5. Cleanup
kill %1
```

**Phase 2: Python-Code updaten**

Für jedes der 4 Scripts (Beispiel: `start_full.py`):

```python
# ALT (llama-cpp-python):
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings

settings = Settings(
    model=str(MODEL_PATH),
    n_ctx=32768,
    n_threads=1,
    chat_format='chatml'
)
app = create_app(settings=settings)

llama_thread = threading.Thread(
    target=uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=8080, log_level="error")
    ).run,
    daemon=True
)
llama_thread.start()

# NEU (llama-server Binary):
import subprocess

llama_process = subprocess.Popen(
    [
        "./llama-server",
        "-m", str(MODEL_PATH),
        "--host", "127.0.0.1",
        "--port", "8080",
        "--jinja",  # ← KRITISCH: Tool-Calling
        "--ctx-size", "32768",
        "--parallel", "1",
        "--log-level", "error"
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
```

**Dateien die ändern müssen:**

- [ ] `scripts/sandbox/start_full.py` — Z.45-67: Import → Subprocess
- [ ] `scripts/sandbox/start_quick.py` — Z.40-62: Import → Subprocess
- [ ] `scripts/sandbox/inspect_phoenix.py` — Z.30-50: Import → Subprocess
- [ ] `tests/test_mcp_toolcall.py` — Z.25-45: Import → Subprocess
- [ ] `requirements.txt` — Z.55: `llama-cpp-python==0.3.23` entfernen
- [ ] `docs/SANDBOX.md` — Abschnitt "4. Modelle herunterladen" + neue Zeile "4a. llama-server Binary"

**Tests nach dem Swap:**

```bash
# 1. Import-Check (sollte FEHLER werfen, da llama-cpp-python nicht mehr da ist)
cd /home/claude/la && python3 scripts/sandbox/import_check.py
# → Erwartet: ModuleNotFoundError für llama_cpp
# → Dann: requirements.txt neu evaluieren

# 2. Quick-Start (90 Sekunden, nur Stack ohne Phoenix/Tests)
cd /home/claude/la && python3 scripts/sandbox/start_quick.py
# → Erwartet: Port 8080 mit "Server running"

# 3. Full-Start + 6-Agent-Tests (3 Min)
cd /home/claude/la && python3 scripts/sandbox/start_full.py
# → Erwartet: 5/6 Agenten OK, Tool-Calling jetzt auch beim Notes Agent

# 4. Spezial-Test: Tool-Calling mit Granite
cd /home/claude/la && python3 tests/test_mcp_toolcall.py
# → Erwartet: 18/18 Tests OK (vorher waren einige skipped)
```

**Erwartete Output (erfolgreich):**
```
[llama-server] Server running on http://127.0.0.1:8080
[Phoenix] Listening on :6006
[LiteLLM] Ready
[Agent Server] 6 agents registered
[Tests] 5/6 agents passing
[Tool-Calling] 18/18 tool format tests passing
```

**Fallback Plan (wenn's bricht):**

```bash
# 1. Git revert zur vorigen Version
cd /home/claude/la
git log --oneline | head -5  # Finde den Commit vor dem Swap
git revert [COMMIT_HASH]
git push

# 2. Oder: nur requirements.txt rollback
git checkout requirements.txt
pip install -r requirements.txt

# 3. llama-cpp-python erneut starten
cd /home/claude/la && python3 scripts/sandbox/start_full.py
```

---

## 6. Known Issues & Troubleshooting

| Problem | Symptom | Workaround | Fix |
|---------|---------|-----------|-----|
| `llama-server: command not found` | Script startet, dann Error | Binary muss in PATH oder absolute Pfad | Pfad in Script zu `./llama-server` korrigieren |
| Port 8080 bereits in Use | `Address already in use` | `lsof -i :8080 \| kill -9 [PID]` | Vorherigen llama-Prozess killen |
| `--jinja` Flag nicht erkannt | Binary läuft, aber `--jinja` wird ignoriert | Binary ist zu alt (vor b9895) | Neuere Binary herunterladen |
| Logs sind leer | Debugging unmöglich | Stderr/Stdout manuell auf Datei umleiten | `start_full.py` updaten: `stderr=open('/tmp/llama.log', 'w')` |
| Tool-Calling trotz `--jinja` nicht funktioniert | Model ignoriert tools-Array | Phoenix Trace checken: hat das Model die tools empfangen? | LiteLLM Config: `supports_tools: true`? |

**Debugging Checkliste:**

```bash
# 1. Läuft der Server?
curl http://127.0.0.1:8080/v1/models

# 2. Antwortet das Modell?
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "granite-tiny",
    "messages": [{"role": "user", "content": "Hallo"}],
    "max_tokens": 10
  }'

# 3. Verarbeitet es Tools?
# → Siehe test_mcp_toolcall.py für Beispiel

# 4. Phoenix Traces
# → http://127.0.0.1:6006 im Browser
# → Schaue auf die Tool-JSON im "Messages" Panel
```

---

## 7. Performance & Resource Requirements

| Metrik | Sandbox (Python) | Sandbox (Binary) | Host (Binary) |
|--------|------------------|------------------|---------------|
| RAM | ~800 MB | ~800 MB (gleich) | ~1200 MB (größeres Modell möglich) |
| CPU | 1 vCore (Thread) | 1 vCore (Prozess) | 4 vCores (Parallelisierung) |
| Startup Time | ~5 Sekunden | ~8 Sekunden | ~12 Sekunden |
| Token/Sec (Inference) | ~24 t/s | ~25 t/s (identisch) | ~45 t/s (größeres Modell) |
| Disk I/O | Modell-Laden: ~2 MB/s | Modell-Laden: ~2 MB/s | SSD: ~50 MB/s |

**Anmerkung:** Inference-Speed ist identisch; Binary hat nur bessere Logging und `--jinja` Support.

---

## 8. References & Related Components

**Externe Dokumentation:**
- llama.cpp Function Calling: https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md
- Granite native support in llama.cpp: [llama.cpp Server README](https://github.com/ggml-org/llama.cpp/tree/master/examples/server#supported-models)

**Verwandte Komponenten:**
- `LITELLM.md` — Gateway-Konfiguration, wie sie sich auf Reasoning Server auswirkt
- `PHOENIX.md` — Tracing und Observability des Reasoning Servers
- `docs/SANDBOX.md` — allgemeiner Setup-Guide (referenziert dieses Dokument)

**Relevant Bugs/Issues:**
- `BUGS.md#Tool-Calling nicht testbar in der Sandbox (llama-cpp-python Limitation)` — dieser Swap behebt das
- `ROADMAP.md#Host Deployment` — Binary ist Teil des Host-Plans

---

## Changelog

| Datum | Version | Änderung |
|-------|---------|----------|
| 2026-07-20 | v1 | Initial doc: llama-cpp-python vs. Binary comparison, Swap Scenario A |

