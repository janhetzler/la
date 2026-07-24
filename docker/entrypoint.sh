#!/bin/bash
set -e

echo "=== Local Agent Starting ==="

# 1. llama-server Binary b9895 -- Reasoning + Embeddings auf Port 8080
# Identisch mit Sandbox-Konfiguration (start_full.py)
echo "Starting llama-server :8080..."
/app/bin/llama-server \
    --model /app/models/granite-350m-Q4_K_M.gguf \
    --host 127.0.0.1 --port 8080 \
    --ctx-size 32768 --threads 4 --parallel 1 \
    --jinja --embeddings --pooling mean --log-disable \
    > /var/log/llama-reasoning.log 2>&1 &

# 2. Warten bis llama-server bereit
echo "Waiting for llama-server..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8080/v1/models > /dev/null 2>&1; then
        echo "llama-server :8080 ready"
        break
    fi
    sleep 2
done

# 3. Phoenix (Port 6006) -- auf 0.0.0.0 fuer externe Erreichbarkeit
echo "Starting Phoenix :6006..."
PHOENIX_HOST=0.0.0.0 PHOENIX_PORT=6006 \
python3 -m phoenix.server.main serve \
    > /var/log/phoenix.log 2>&1 &
sleep 8

# 4. LiteLLM (Port 4000) -- auf 0.0.0.0 fuer externe Erreichbarkeit
echo "Starting LiteLLM :4000..."
litellm --config /app/docker/litellm_config.yaml \
    --host 0.0.0.0 --port 4000 \
    > /var/log/litellm.log 2>&1 &

# Warten bis LiteLLM bereit (echter Request)
for i in $(seq 1 20); do
    if curl -s -X POST http://127.0.0.1:4000/v1/chat/completions \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer sk-cos-local-dev" \
        -d '{"model":"granite-tiny","messages":[{"role":"user","content":"hi"}],"max_tokens":3}' \
        > /dev/null 2>&1; then
        echo "LiteLLM :4000 ready"
        break
    fi
    sleep 2
done

# Embedding Readiness Check
for i in $(seq 1 10); do
    if curl -s -X POST http://127.0.0.1:4000/v1/embeddings \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer sk-cos-local-dev" \
        -d '{"model":"granite-embed","input":"ready"}' \
        > /dev/null 2>&1; then
        echo "LiteLLM -> granite-embed ready"
        break
    fi
    sleep 2
done

# 5. ChromaDB notes-Collection initialisieren (cosine, einmalig)
python3 -c "
import chromadb
client = chromadb.PersistentClient(path='/app/data/chroma')
client.get_or_create_collection('notes', metadata={'hnsw:space': 'cosine'})
print('ChromaDB notes-Collection initialisiert (cosine)')
"

# 6. Agent Server (Port 8002)
echo "Starting Agent Server :8002..."
cd /app/agents/server
uvicorn server:app --host 0.0.0.0 --port 8002 \
    > /var/log/agent-server.log 2>&1 &
sleep 3

# 7. Smoke Test
echo "=== SMOKE TEST ==="
curl -sf http://127.0.0.1:8080/v1/models > /dev/null && echo "✅ llama-server OK" || echo "❌ llama-server FAIL"
curl -sf http://127.0.0.1:4000/health -H "Authorization: Bearer sk-cos-local-dev" > /dev/null && echo "✅ LiteLLM OK" || echo "❌ LiteLLM FAIL"
curl -sf http://127.0.0.1:8002/health > /dev/null && echo "✅ Agent Server OK" || echo "❌ Agent Server FAIL"
echo "=== SMOKE TEST DONE ==="

echo "=== Local Agent Ready ==="
echo "Agent Server: http://localhost:8002"
echo "LiteLLM:      http://localhost:4000"
echo "Phoenix:      http://localhost:6006"

# Logs im Vordergrund halten
tail -f /var/log/agent-server.log
