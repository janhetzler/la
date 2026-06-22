#!/bin/bash
# Start the full Chief of Staff stack
# Usage: ./start.sh
# Optional env var: VENV_NAME (default: .venv)

set -e

# Resolve project root from script location (portable)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
cd "$PROJECT_ROOT"

VENV_NAME="${VENV_NAME:-.venv}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Chief of Staff — starting ===${NC}\n"

# 1. Check container runtime (Docker Desktop / OrbStack / Colima / Docker Engine)
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ No Docker daemon running.${NC}"
    echo "   Start Docker Desktop / OrbStack / Colima first, then re-run this script."
    exit 1
fi
echo -e "${GREEN}✅ Container runtime OK${NC}"

# 2. Bring up the Docker stack
echo -e "\n${YELLOW}→ Starting containers (Qdrant, Postgres, LiteLLM, Open WebUI)...${NC}"
cd "$PROJECT_ROOT/docker"
docker compose up -d
sleep 5

RUNNING=$(docker compose ps --services --filter "status=running" | wc -l | tr -d ' ')
EXPECTED=4
if [ "$RUNNING" -lt "$EXPECTED" ]; then
    echo -e "${RED}⚠️  Only $RUNNING/$EXPECTED containers running. Check 'docker compose ps'.${NC}"
else
    echo -e "${GREEN}✅ $RUNNING containers up${NC}"
fi

# 3. Activate venv and launch Python servers in background
echo -e "\n${YELLOW}→ Starting Python servers (specialists + agents + watcher)...${NC}"
cd "$PROJECT_ROOT"

if [ ! -d "$VENV_NAME" ]; then
    echo -e "${RED}❌ Python venv '$VENV_NAME' not found.${NC}"
    echo "   Run ./install.sh first, or create the venv manually:"
    echo "     python3 -m venv $VENV_NAME && source $VENV_NAME/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source "$VENV_NAME/bin/activate"
mkdir -p logs

# Specialists API (port 8001)
nohup uvicorn specialists.main:app --host 127.0.0.1 --port 8001 --reload > logs/specialists.log 2>&1 &
SPECIALISTS_PID=$!
echo "   Specialists PID: $SPECIALISTS_PID (logs: logs/specialists.log)"

# Agents API (port 8002)
cd "$PROJECT_ROOT/agents/server"
nohup uvicorn server:app --host 127.0.0.1 --port 8002 --reload > "$PROJECT_ROOT/logs/agents.log" 2>&1 &
AGENTS_PID=$!
echo "   Agents PID: $AGENTS_PID (logs: logs/agents.log)"

# Library watcher
cd "$PROJECT_ROOT"
nohup python agents/ingestion/watcher.py > logs/watcher.log 2>&1 &
WATCHER_PID=$!
echo "   Watcher PID: $WATCHER_PID (logs: logs/watcher.log)"
echo "$WATCHER_PID" > "$PROJECT_ROOT/logs/.watcher.pid"

sleep 5

# 4. Health checks
echo -e "\n${YELLOW}→ Health checks (up to 45 sec)...${NC}"

wait_for() {
    local name=$1
    local url=$2
    local headers=$3
    local max_attempts=15
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if [ -n "$headers" ]; then
            if curl -s -H "$headers" "$url" >/dev/null 2>&1; then
                echo -e "${GREEN}✅ $name${NC}"
                return 0
            fi
        else
            if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -qE "^(200|301|302|307|308)$"; then
                echo -e "${GREEN}✅ $name${NC}"
                return 0
            fi
        fi
        attempt=$((attempt + 1))
        sleep 3
    done
    echo -e "${RED}⚠️  $name not responding after $((max_attempts * 3))s${NC}"
    return 1
}

wait_for "Specialists API (port 8001)" "http://localhost:8001/health" ""
wait_for "Agents API (port 8002)" "http://localhost:8002/health" ""
wait_for "LiteLLM proxy (port 4000)" "http://localhost:4000/v1/models" "Authorization: Bearer sk-cos-local-dev"
wait_for "Open WebUI (port 3000)" "http://localhost:3000" ""

# 5. Save PIDs for clean shutdown
echo "$SPECIALISTS_PID" > "$PROJECT_ROOT/logs/.specialists.pid"
echo "$AGENTS_PID" > "$PROJECT_ROOT/logs/.agents.pid"

echo -e "\n${GREEN}=== Started ===${NC}"
echo -e "Open in your browser:"
echo -e "  ${GREEN}http://localhost:3000${NC}"
echo -e "  → select ${YELLOW}agent-chief-of-staff${NC} in the model picker"
echo -e ""
echo -e "To stop:    ${YELLOW}./stop.sh${NC}"
echo -e "Python logs: tail -f logs/agents.log"
