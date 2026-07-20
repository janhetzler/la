# OPERATIONS_DOCKER.md — Betrieb & Logging (Docker)

**Umgebung:** Docker Container `ghcr.io/janhetzler/la:latest`
**Zuletzt aktualisiert:** 2026-07-20
**Verwandt:** OPERATIONS_SANDBOX.md, OPERATIONS_HOST.md

---

## Uebersicht: Alle Komponenten

| Komponente | Port (intern) | Port (extern) | Log-Datei | Status |
|------------|--------------|---------------|-----------|--------|
| llama-server (Reasoning) | 8080 | 18080 | `/var/log/llama-reasoning.log` | ✅ aktiv |
| llama-server (Embedding) | 8081 | 8081 | `/var/log/llama-embedding.log` | ✅ aktiv |
| Phoenix | 6006 | 6006 | `/var/log/phoenix.log` | ✅ aktiv |
| LiteLLM | 4000 | 4000 | `/var/log/litellm.log` | ✅ aktiv |
| Agent Server | 8002 | 8002 | `/var/log/agent-server.log` | ✅ aktiv |
| ChromaDB | — | — | kein separates Log | in-process |

**Log-Verzeichnis:** `/var/log/` (persistent innerhalb Container-Session)

> **Wichtig:** Port 8080 (Reasoning) ist extern auf 18080 gemappt um Konflikte
> mit dem Host zu vermeiden. Intern bleibt alles auf 8080.

---

## 1. llama-server Reasoning (Binary b9895)

**Start-Befehl (entrypoint.sh):**
```bash
/app/bin/llama-server \
    --model /app/models/granite-350m-Q4_K_M.gguf \
    --host 127.0.0.1 --port 8080 \
    --ctx-size 32768 --threads 4 --parallel 1 \
    --jinja --log-disable
```

**Log-Datei:** `/var/log/llama-reasoning.log`
**Log-Level:** `--log-disable` — Performance-Metriken trotzdem sichtbar

**Gemessene Performance (Docker, 2026-07-20):**
- Prompt eval: ~150 t/s
- Generation: ~7-70 t/s (je nach Antwortlaenge)
- Gesamtdauer pro Request: ~2.5-3.8s

**Debugging:**
```bash
docker exec -it local-agent cat /var/log/llama-reasoning.log | tail -20
curl -s http://localhost:18080/v1/models
```

---

## 2. llama-server Embedding (llama-cpp-python)

**Start-Befehl (entrypoint.sh):**
```bash
python3 -m llama_cpp.server \
    --model /app/models/granite-embedding-30m-Q4_0.gguf \
    --host 127.0.0.1 --port 8081 \
    --n_ctx 512 --n_threads 2 \
    --embedding True
```

**Log-Datei:** `/var/log/llama-embedding.log`

**Bekannte Probleme:**
- BUG-013: `--embedding` ohne `True` Argument → Server startet nicht (behoben in entrypoint.sh v2)

---

## 3. Phoenix (Arize Phoenix)

**Start-Befehl (entrypoint.sh):**
```bash
PHOENIX_HOST=0.0.0.0 PHOENIX_PORT=6006 \
python3 -m phoenix.server.main serve
```

**Log-Datei:** `/var/log/phoenix.log`
**Web-Interface:** `http://[HOST]:6006`

**Bekannte Probleme:**
- BUG-015: gRPC Port 4317 Konflikt beim Neustart — kill -9 [PID] noetig
- BUG-012: Aeltere Images starten Phoenix auf 127.0.0.1 (behoben in entrypoint.sh v2)

**Debugging:**
```bash
docker exec -it local-agent cat /var/log/phoenix.log | tail -20
curl -s http://localhost:6006/v1/projects
```

---

## 4. LiteLLM (1.92.0)

**Start-Befehl (entrypoint.sh):**
```bash
litellm --config /app/docker/litellm_config.yaml \
    --host 0.0.0.0 --port 4000
```

**Log-Datei:** `/var/log/litellm.log`

**Bekannte Warnungen (harmlos):**
- `register_model: model=openai/granite not in built-in cost map` — lokale Modelle
  sind nicht in LiteLLMs Cost-Map; Kosten werden als 0 gezaehlt

**Debugging:**
```bash
docker exec -it local-agent cat /var/log/litellm.log | tail -20
curl -s http://localhost:4000/health -H "Authorization: Bearer sk-cos-local-dev"
```

---

## 5. Agent Server (FastAPI)

**Start-Befehl (entrypoint.sh):**
```bash
uvicorn server:app --host 0.0.0.0 --port 8002
```

**Log-Datei:** `/var/log/agent-server.log`

**Debugging:**
```bash
docker exec -it local-agent cat /var/log/agent-server.log | tail -20
curl -s http://localhost:8002/health
```

---

## 6. ChromaDB

**Datenpfad:** `/app/data/chroma`
**Log:** kein separates Log — in-process

**Status pruefen:**
```bash
docker exec -it local-agent python3 -c "
import chromadb
client = chromadb.PersistentClient(path='/app/data/chroma')
for col in client.list_collections():
    print(f'{col.name}: {col.count()} Dokumente')
"
```

---

## 7. Container starten

```bash
docker run -d \
  --name local-agent \
  -p 18080:8080 \
  -p 8081:8081 \
  -p 4000:4000 \
  -p 6006:6006 \
  -p 8002:8002 \
  ghcr.io/janhetzler/la:latest
```

**Nach dem Start im Browser:**
- Phoenix: `http://localhost:6006`
- Agent Server Health: `http://localhost:8002/health`

---

## 8. Standard-Debugging-Workflow

```bash
# 1. In den Container einsteigen
docker exec -it local-agent /bin/bash

# 2. Alle Logs auf einmal
echo "=== REASONING ===" && tail -20 /var/log/llama-reasoning.log
echo "=== EMBEDDING ===" && tail -20 /var/log/llama-embedding.log
echo "=== PHOENIX ===" && tail -20 /var/log/phoenix.log
echo "=== LITELLM ===" && tail -20 /var/log/litellm.log
echo "=== AGENT SERVER ===" && tail -20 /var/log/agent-server.log

# 3. Echten Request schicken
curl -s -X POST http://127.0.0.1:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-cos-local-dev" \
  -d '{"model":"agent-local","messages":[{"role":"user","content":"Write a short email"}],"max_tokens":200}'

# 4. Trace in Phoenix anschauen
# Browser: http://localhost:6006 → Tracing → default
```

---

## Changelog

| Datum | Version | Aenderung |
|-------|---------|-----------|
| 2026-07-20 | v1 | Initial doc — erster Docker-Run, alle Komponenten dokumentiert |
