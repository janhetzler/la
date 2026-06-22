"""
Chargement des outils MCP pour les agents.
Lit mcp.json, démarre les serveurs MCP en stdio, expose les tools en LangChain.
"""
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

import config


# ===== Charge le .env (GITHUB_TOKEN, TAVILY_API_KEY) =====
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ===== Lecture du mcp.json + substitution des variables =====
ENV_VAR_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _substitute_env_vars(value: str) -> str:
    """Remplace ${VAR_NAME} par os.environ['VAR_NAME']. Strict : nom de var en MAJ."""
    def replace(match):
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise ValueError(f"Variable d'environnement manquante : {var_name}")
        return env_value
    return ENV_VAR_RE.sub(replace, value)


def load_mcp_config() -> dict:
    """Charge mcp.json brut (sans substitution texte)."""
    config_path = PROJECT_ROOT / "mcp" / "mcp.json"
    return json.loads(config_path.read_text())


def get_mcp_client() -> MultiServerMCPClient:
    """Construit un client MCP avec tous les serveurs déclarés dans mcp.json."""
    raw_config = load_mcp_config()

    servers = {}
    for name, cfg in raw_config["mcpServers"].items():
        # Merge os.environ + env spécifiques au serveur
        env = dict(os.environ)
        for key, value in cfg.get("env", {}).items():
            if isinstance(value, str):
                env[key] = _substitute_env_vars(value)
            else:
                env[key] = value

        servers[name] = {
            "command": cfg["command"],
            "args": cfg["args"],
            "transport": "stdio",
            "env": env,
        }

    return MultiServerMCPClient(servers)

# ===== Cache des outils chargés (singleton) =====
_cached_tools = None


async def get_all_tools():
    """Retourne tous les outils MCP, chargés une seule fois."""
    global _cached_tools
    if _cached_tools is None:
        client = get_mcp_client()
        _cached_tools = await client.get_tools()
    return _cached_tools

async def get_tools_by_names(names: list[str]):
    """Retourne uniquement les outils dont le nom est dans la liste."""
    all_tools = await get_all_tools()
    name_set = set(names)
    return [t for t in all_tools if t.name in name_set]

# ===== Test CLI =====
if __name__ == "__main__":
    import asyncio

    async def main():
        print("🔧 Chargement des outils MCP...\n")
        tools = await get_all_tools()
        print(f"✅ {len(tools)} outils chargés\n")
        for t in sorted(tools, key=lambda x: x.name):
            print(f"   - {t.name}")

    asyncio.run(main())