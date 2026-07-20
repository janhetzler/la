#!/bin/bash
set -e

echo "=== Local Agent Starting ==="

# 1. llama-server Reasoning (Port 8080) -- Binary b9895 mit --jinja
echo "Starting llama-server :8080..."
/app/bin/llama-server \
    --model /app/models/granite-350m-Q4_K_M.gguf \
    --host 127.0.0.1 --port 8080 \
    --ctx-size 32768 --threads 4 --parallel 1 \
    --jinja --log-disable \
    > /var/log/llama-reasoning.log 2>&1 &

# 2. llama-server Embedding (Port 8081) -- Python-Wrapper (Binary hat kein --embedding)
echo "Starting llama-server :8081 (embedding)..."
python3 -m llama_cpp.server \
    --model /app/models/granite-embedding-30m-Q4_0.gguf \
    --host 127.0.0.1 --port 8081 \
    --n_ctx 512 --n_threads 2 \
    --embedding True \
    > /var/log/llama-embedding.log 2>&1 &

# 3. Warten bis llama-server bereit
echo "Waiting for llama-server..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8080/v1/models > /dev/null 2>&1; then
        echo "llama-server :8080 ready"
        break
    fi
    sleep 2
done

# 4. Phoenix (Port 6006) -- auf 0.0.0.0 fuer externe Erreichbarkeit
echo "Starting Phoenix :6006..."
PHOENIX_HOST=0.0.0.0 PHOENIX_PORT=6006 \
python3 -m phoenix.server.main serve \
    > /var/log/phoenix.log 2>&1 &
sleep 8

# 5. LiteLLM (Port 4000) -- auf 0.0.0.0 fuer externe Erreichbarkeit
echo "Starting LiteLLM :4000..."
litellm --config /app/docker/litellm_config.yaml \
    --host 0.0.0.0 --port 4000 \
    > /var/log/litellm.log 2>&1 &

# Warten bis LiteLLM bereit
for i in $(seq 1 20); do
    if curl -s http://127.0.0.1:4000/health \
        -H "Authorization: Bearer sk-cos-local-dev" > /dev/null 2>&1; then
        echo "LiteLLM :4000 ready"
        break
    fi
    sleep 2
done

# Echter Readiness Check
curl -s -X POST http://127.0.0.1:4000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer sk-cos-local-dev" \
    -d '{"model":"granite-tiny","messages":[{"role":"user","content":"hi"}],"max_tokens":3}' \
    > /dev/null 2>&1
echo "LiteLLM -> llama-server ready"

# 6. Agent Server (Port 8002)
echo "Starting Agent Server :8002..."
cd /app/agents/server
uvicorn server:app --host 0.0.0.0 --port 8002 \
    > /var/log/agent-server.log 2>&1 &

sleep 3
echo "=== Local Agent Ready ==="
echo "Agent Server: http://localhost:8002"
echo "LiteLLM:      http://localhost:4000"
echo "Phoenix:      http://localhost:6006"

# Logs im Vordergrund halten
tail -f /var/log/agent-server.log
