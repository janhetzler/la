"""
Researcher Agent (v2): ReAct agent with curated tools + Qdrant RAG.

Tools:
- search_local_documents / search_by_category: semantic search over the user's library
- tavily_search / tavily_extract: web search and URL content extraction
- list_directory / read_text_file: filesystem exploration of the project
"""
import asyncio
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import chromadb

import config
from agent_loader import load_agent
from tools import get_tools_by_names


# ===== Import aus dem Ingestion-Paket ermoeglichen =====
INGESTION_PATH = Path(__file__).resolve().parent.parent / "ingestion"
sys.path.insert(0, str(INGESTION_PATH))
from search import search as rag_search, VALID_CATEGORIES  # noqa: E402


# ===== Load .env (GITHUB_TOKEN, TAVILY_API_KEY, etc.) =====
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# Project root (used to inject paths into prompts)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ===== LLM (Granite tiny-h via Ollama) =====
llm = ChatOpenAI(
    base_url=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
    model="granite-tiny",
    temperature=0,
)


# ===== Eigene Tools: RAG-Suche ueber die lokale Bibliothek =====
@tool
def search_local_documents(query: str, top_k: int = 5) -> str:
    """
    Search the local document base (RAG). Returns the most relevant
    passages with their source and category.

    Use this to answer questions grounded in the user's indexed library
    (research papers, work documents, personal notes, admin documents, etc.).

    Args:
        query: Natural-language question.
        top_k: Number of chunks to retrieve (default 5).

    Returns:
        A formatted string with the top results.
    """
    try:
        results = rag_search(query, top_k=top_k)
    except Exception as e:
        return f"Search error: {e}"

    if not results:
        return "No relevant document found in the library."

    output = []
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        source = meta.get("source", meta.get("filename", "unknown"))
        category = meta.get("category", "unknown")
        output.append(
            f"[{i}] {source} (category: {category}, score: {r['score']:.2f})\n"
            f"{r['text'][:500]}"
        )
    return "\n\n---\n\n".join(output)


@tool
def search_by_category(query: str, category: str, top_k: int = 5) -> str:
    """
    Search only within a specific category of the user's library.

    Use this when the user explicitly asks about one of the indexed library categories
    (e.g. work documents, research papers,
    personal notes, or admin documents.

    Args:
        query: Natural-language question.
        category: One of: idn, research, personal, admin, inbox.
        top_k: Number of chunks to retrieve (default 5).

    Returns:
        A formatted string with the top results.
    """
    if category not in VALID_CATEGORIES:
        return (
            f"Invalid category '{category}'. "
            f"Must be one of: {sorted(VALID_CATEGORIES - {'default'})}."
        )

    try:
        results = rag_search(query, top_k=top_k, category=category)
    except Exception as e:
        return f"Search error: {e}"

    if not results:
        return f"No relevant document found in category '{category}'."

    output = []
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        source = meta.get("source", meta.get("filename", "unknown"))
        output.append(
            f"[{i}] {source} (score: {r['score']:.2f})\n"
            f"{r['text'][:500]}"
        )
    return "\n\n---\n\n".join(output)


# ===== Ausgewaehlte MCP-Tools fuer den Researcher =====
RESEARCHER_TOOLS = [
    "tavily_search",
    "tavily_extract",
    "list_directory",
    "read_text_file",
]


# ===== System prompt template =====
# Prompt wird aus prompts/agents/researcher.md geladen
_shared_cache = {}


def _get_system_prompt(user_language: str = "en") -> str:
    _, prompt = load_agent("researcher")
    return prompt.replace("{user_language}", user_language)



# ===== Cached agents per language =====
_agents: dict[str, object] = {}


async def _get_agent(user_language: str):
    """Erstellt den Agenten mit ausgewaehlten Tools, gecacht pro Sprache."""
    if user_language not in _agents:
        mcp_tools = await get_tools_by_names(RESEARCHER_TOOLS)
        all_tools = mcp_tools + [search_local_documents, search_by_category]
        system_prompt = _get_system_prompt(user_language)
        system_prompt = system_prompt.replace("{project_root}", str(PROJECT_ROOT))
        _agents[user_language] = create_agent(
            model=llm,
            tools=all_tools,
            system_prompt=system_prompt,
        )
    return _agents[user_language]


async def invoke_researcher_v2(user_message: str, user_language: str = "French") -> str:
    """Asynchroner Einstiegspunkt fuer den Researcher-Agenten."""
    agent = await _get_agent(user_language)
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=user_message)],
    })
    return result["messages"][-1].content


def invoke_researcher_v2_sync(user_message: str, user_language: str = "French") -> str:
    """Synchroner Wrapper fuer die Kommandozeile."""
    return asyncio.run(invoke_researcher_v2(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "List the files in my vault"
    print(f"\n❓ {q}\n")
    print(invoke_researcher_v2_sync(q, "English"))