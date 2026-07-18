"""
Code agent: dev assistance with MCP Git/Fetch tools.

Prompt wird aus prompts/agents/code.md geladen via agent_loader.
Tools aus dem Frontmatter via tools.get_tools_by_names().
"""
import asyncio
import sys

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

import config
from agent_loader import load_agent, build_llm
from tools import get_tools_by_names


_agents: dict[str, object] = {}


async def _get_agent(user_language: str):
    if user_language not in _agents:
        meta, system_prompt = load_agent("code")
        system_prompt = system_prompt.replace("{user_language}", user_language)

        llm = build_llm(meta)
        tool_names = meta.get("tools") or []
        mcp_tools = await get_tools_by_names(tool_names) if tool_names else []

        _agents[user_language] = create_agent(
            model=llm,
            tools=mcp_tools,
            system_prompt=system_prompt,
        )
    return _agents[user_language]


async def invoke_code(user_message: str, user_language: str = "en") -> str:
    agent = await _get_agent(user_language)
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=user_message)],
    })
    return result["messages"][-1].content


def invoke_code_sync(user_message: str, user_language: str = "en") -> str:
    return asyncio.run(invoke_code(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "How do I implement an LRU cache in Python?"
    print(f"\n{q}\n")
    print(invoke_code_sync(q, "English"))
