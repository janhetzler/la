"""
Zentralisierte Konfiguration — Local Agent (LA)

Alle Werte werden ausschliesslich ueber Umgebungsvariablen gesetzt.
Keine hardcodierten Werte. Laden der .env Dateien:
  config/sandbox/*.env  — Sandbox
  config/host/*.env     — Host
  config/docker/*.env   — Docker
"""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# .env Dateien laden — Reihenfolge: common zuerst, dann komponentenspezifisch
# Umgebung wird ueber ENV-Variable LA_ENV bestimmt (default: sandbox)
LA_ENV = os.getenv("LA_ENV", "sandbox")
env_dir = PROJECT_ROOT / "config" / LA_ENV

for env_file in ["common.env", "agent.env"]:
    env_path = env_dir / env_file
    if env_path.exists():
        load_dotenv(env_path, override=False)

# LiteLLM
LITELLM_URL = os.getenv("LITELLM_URL", "http://127.0.0.1:4000")
LITELLM_KEY = os.getenv("LITELLM_KEY", "sk-cos-local-dev")

# Agent Server
AGENT_PORT  = int(os.getenv("AGENT_PORT", "8002"))

# ChromaDB
CHROMA_PATH       = os.getenv("CHROMA_PATH", "/tmp/chroma_la")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "documents")

# Modelle
DEFAULT_LLM  = os.getenv("DEFAULT_LLM",  "granite-tiny")
EMBED_MODEL  = os.getenv("EMBED_MODEL",  "granite-embed")

# MCP
MCP_CONFIG_PATH = os.getenv("MCP_CONFIG_PATH",
                             str(PROJECT_ROOT / "mcp" / "sandbox" / "mcp.json"))

# Phoenix
PHOENIX_HOST = os.getenv("PHOENIX_HOST", "http://127.0.0.1:6006")
