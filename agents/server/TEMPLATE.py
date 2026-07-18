"""
<agent_name>.py -- <Agent Name> Agent

Logik-Agent: hat eigene Python-Logik (z.B. ChromaDB, RAG, Tools).
System-Prompt wird aus prompts/agents/<agent_name>.md geladen via agent_loader.

Ablauf:
  supervisor.py -> invoke_<agent_name>() -> agent_loader.load_agent() -> LLM
"""
import asyncio
import sys

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

import config
from agent_loader import load_agent, build_llm
from tools import get_tools_by_names


# Agent-Cache: einmal pro Sprache erstellen, dann wiederverwenden
_agents: dict[str, object] = {}


async def _get_agent(user_language: str):
    """Laedt oder erstellt den Agenten fuer die gegebene Sprache."""
    if user_language not in _agents:
        # Prompt und Metadaten aus .md Datei laden
        meta, system_prompt = load_agent("<agent_name>")
        system_prompt = system_prompt.replace("{user_language}", user_language)

        # LLM aus Frontmatter-Metadaten erstellen
        llm = build_llm(meta)

        # Tools aus Frontmatter laden (tools: [...] im YAML)
        tool_names = meta.get("tools") or []
        mcp_tools = await get_tools_by_names(tool_names) if tool_names else []

        # Hier eigene Tools hinzufuegen falls noetig:
        # from <agent_name>_tools import my_custom_tool
        # all_tools = [my_custom_tool] + mcp_tools

        _agents[user_language] = create_agent(
            model=llm,
            tools=mcp_tools,
            system_prompt=system_prompt,
        )
    return _agents[user_language]


async def invoke_<agent_name>(user_message: str, user_language: str = "en") -> str:
    """Hauptfunktion -- wird von supervisor.py aufgerufen."""
    agent = await _get_agent(user_language)
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=user_message)],
    })
    return result["messages"][-1].content


def invoke_<agent_name>_sync(user_message: str, user_language: str = "en") -> str:
    """Synchroner Wrapper fuer CLI-Nutzung."""
    return asyncio.run(invoke_<agent_name>(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "<Beispiel-Anfrage>"
    print(f"\n{q}\n")
    print(invoke_<agent_name>_sync(q, "English"))
