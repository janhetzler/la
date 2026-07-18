"""
Comms agent: drafts emails, messages, short reports.

Tool-less agent — pure synthesis.
Prompt wird aus prompts/agents/comms.md geladen via agent_loader.
"""
import asyncio
import sys

from langchain_core.messages import HumanMessage, SystemMessage

import config
from agent_loader import load_agent, build_llm


async def invoke_comms(user_message: str, user_language: str = "en") -> str:
    """Generate a written response in the user's language."""
    meta, system_prompt = load_agent("comms")

    # Sprache injizieren
    system_prompt = system_prompt.replace("{user_language}", user_language)

    llm = build_llm(meta)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    response = await llm.ainvoke(messages)
    return response.content


def invoke_comms_sync(user_message: str, user_language: str = "en") -> str:
    """Synchronous wrapper for CLI use."""
    return asyncio.run(invoke_comms(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Draft an email to cancel a meeting tomorrow morning."
    print(f"\n{q}\n")
    print(invoke_comms_sync(q, "English"))
