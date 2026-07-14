#!/bin/bash
# Chief of Staff — Deploy Script für janhet
# Ausführen als: user@janhet

set -e
CHIEF_DIR="/home/user/chief"
VENV="$CHIEF_DIR/venv"

echo "=== 1. Verzeichnis anlegen ==="
mkdir -p "$CHIEF_DIR/chroma_db"
mkdir -p "$CHIEF_DIR/logs"

echo "=== 2. Repository klonen ==="
if [ ! -d "$CHIEF_DIR/la" ]; then
  git clone https://github.com/janhetzler/la "$CHIEF_DIR/la"
else
  cd "$CHIEF_DIR/la" && git pull
fi

echo "=== 3. Python venv erstellen ==="
python3 -m venv "$VENV"
source "$VENV/bin/activate"

echo "=== 4. Dependencies installieren (kein torch!) ==="
pip install --upgrade pip
pip install -r "$CHIEF_DIR/la/requirements-janhet.txt"

echo "=== 5. .env erstellen ==="
cat << 'ENVEOF' > "$CHIEF_DIR/la/.env"
OPENAI_API_KEY=sk-cos-local-dev
LITELLM_URL=http://localhost:4000
CHROMA_PATH=/home/user/chief/chroma_db
ENVEOF

echo "=== 6. systemd Service erstellen ==="
sudo tee /etc/systemd/system/chief-agent.service << 'SVCEOF'
[Unit]
Description=Chief of Staff Agent Server
After=network.target

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/chief/la/agents/server
Environment="PATH=/home/user/chief/venv/bin"
EnvironmentFile=/home/user/chief/la/.env
ExecStart=/home/user/chief/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8002
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
sudo systemctl enable chief-agent
sudo systemctl start chief-agent

echo "=== FERTIG ==="
echo "Status: sudo systemctl status chief-agent"
echo "Logs:   journalctl -u chief-agent -f"
