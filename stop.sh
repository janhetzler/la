#!/bin/bash
# Stop the full Chief of Staff stack

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Stopping Chief of Staff ===${NC}\n"

# Kill Python servers via saved PIDs
for service in specialists agents watcher; do
    if [ -f "$PROJECT_ROOT/logs/.$service.pid" ]; then
        PID=$(cat "$PROJECT_ROOT/logs/.$service.pid")
        kill $PID 2>/dev/null && echo -e "${GREEN}✅ $service stopped (PID $PID)${NC}" || echo "   $service already stopped"
        rm "$PROJECT_ROOT/logs/.$service.pid"
    fi
done

# Fallback: kill by process name
pkill -f "uvicorn specialists.main" 2>/dev/null || true
pkill -f "uvicorn server:app" 2>/dev/null || true
pkill -f "ingestion/watcher.py" 2>/dev/null || true

# Kill zombie MCP servers
pkill -f "node.*tavily-mcp" 2>/dev/null || true
pkill -f "node.*server-github" 2>/dev/null || true
pkill -f "node.*server-filesystem" 2>/dev/null || true

# Stop Docker stack
echo ""
cd "$PROJECT_ROOT/docker"
docker compose down
echo -e "\n${GREEN}=== All stopped ===${NC}"
