"""
Notes agent: searches and explores the Obsidian vault.

Specialized for:
- Finding relevant meeting notes
- Listing notes by folder/project
- Reading the contents of a specific note
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from qdrant_client import QdrantClient

import config
from project_context import PROJECT_CONTEXT
from tools import get_tools_by_names
from user_profile import USER_PROFILE


# Project paths (used to inject absolute paths into the system prompt)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_PATH = PROJECT_ROOT / "vault"


# Granite tiny-h, deterministic for tool calls
llm = ChatOllama(
    base_url="http://localhost:11434",
    model="ibm/granite4:tiny-h",
    temperature=0,
)


# ===== Custom tool: RAG search filtered to meeting notes =====
def _embed_query(text: str) -> list[float]:
    """Embed via the LiteLLM proxy."""
    with httpx.Client(timeout=60) as client:
        r = client.post(
            f"{config.LITELLM_URL}/v1/embeddings",
            headers={"Authorization": f"Bearer {config.LITELLM_KEY}"},
            json={"model": config.EMBED_MODEL, "input": text},
        )
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]


@tool
def search_meetings(query: str, top_k: int = 5) -> str:
    """
    Search the indexed meeting notes.
    Use this to retrieve a meeting by topic, participants, or content.

    Args:
        query: Keywords or natural-language question (e.g., "meeting about project X",
               "decisions from last week").
        top_k: Maximum number of results (default 5).

    Returns:
        Relevant meeting notes with their source.
    """
    try:
        query_vec = _embed_query(query)
        client = QdrantClient(url=config.QDRANT_URL)
        results = client.query_points(
            collection_name=config.QDRANT_COLLECTION,
            query=query_vec,
            limit=top_k,
            with_payload=True,
        ).points

        # Filter Python-side to keep only meetings
        meetings = []
        for p in results:
            payload = p.payload or {}
            meta_type = payload.get("type", "")
            source = payload.get("source", "")
            if meta_type == "meeting" or "meeting" in source.lower():
                text = payload.get("text", "")
                if not text and "_node_content" in payload:
                    try:
                        node = json.loads(payload["_node_content"])
                        text = node.get("text", "")
                    except Exception:
                        text = ""
                meetings.append(
                    f"[{source}, score {p.score:.2f}]\n{text[:500]}"
                )

        if not meetings:
            return "No relevant meeting notes found."

        return "\n\n---\n\n".join(meetings)
    except Exception as e:
        return f"Search error: {e}"


# ===== MCP filesystem tools (vault read access) =====
NOTES_TOOLS = [
    "list_directory",
    "read_text_file",
    "search_files",
    "directory_tree",
]


# ===== System prompt template =====
SYSTEM_PROMPT_TEMPLATE = f"""You are the Notes agent.

═══════════════════════════════════════════════
🌐 LANGUAGE RULE — READ FIRST
You MUST respond ENTIRELY in {{user_language}}.
The PROFILE and CONTEXT below are in English, but your response
must be in {{user_language}}. No mixing of languages.
═══════════════════════════════════════════════

{USER_PROFILE}

{PROJECT_CONTEXT}

Tools available to you:
- search_meetings(query): RAG search over meeting notes
- list_directory(path): list a folder (absolute path)
- read_text_file(path): read a specific note
- search_files(path, pattern): find files by pattern (e.g., "*.md")
- directory_tree(path): tree view of a folder

IMPORTANT — paths:
- Always use ABSOLUTE paths starting with {vault_path}
- The vault is at: {vault_path}
- Subfolders: meetings/, projects/, people/, daily/, inbox/

Rules:
1. To find a meeting by content/topic → search_meetings
2. To explore the vault structure → list_directory or directory_tree
3. To read a specific note → read_text_file
4. To search by filename → search_files
5. Cite paths or filenames in your response
6. Final output is in {{user_language}}
"""


# Cached agents per language (avoid rebuilding on every call)
_agents: dict[str, object] = {}


async def _get_agent(user_language: str):
    """Build the Notes agent with its filtered tools, cached per language."""
    if user_language not in _agents:
        mcp_tools = await get_tools_by_names(NOTES_TOOLS)
        all_tools = [search_meetings] + mcp_tools
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            user_language=user_language,
            vault_path=str(VAULT_PATH),
        )
        _agents[user_language] = create_agent(
            model=llm,
            tools=all_tools,
            system_prompt=system_prompt,
        )
    return _agents[user_language]


async def invoke_notes(user_message: str, user_language: str = "French") -> str:
    """Async entry point for the Notes agent."""
    agent = await _get_agent(user_language)
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=user_message)],
    })
    return result["messages"][-1].content


def invoke_notes_sync(user_message: str, user_language: str = "French") -> str:
    """Synchronous wrapper for CLI use."""
    return asyncio.run(invoke_notes(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "List my meeting notes"
    print(f"\n❓ {q}\n")
    print(invoke_notes_sync(q, "English"))