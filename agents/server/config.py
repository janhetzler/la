"""
Configuration centralisée des agents.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Endpoints internes
LITELLM_URL = "http://localhost:4000"
LITELLM_KEY = "sk-cos-local-dev"
SPECIALISTS_URL = "http://localhost:8001"
CHROMA_PATH = "/home/user/chief/chroma_db"

# Modèles par défaut
DEFAULT_LLM = "granite-tiny"
EMBED_MODEL = "granite-embed"

# Collection Qdrant pour le RAG
CHROMA_COLLECTION = "documents"

# Port du serveur d'agents
AGENT_SERVER_PORT = 8002