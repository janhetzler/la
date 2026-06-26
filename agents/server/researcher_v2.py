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
from langchain_ollama import ChatOllama
from qdrant_client import QdrantClient

import config
from project_context import PROJECT_CONTEXT
from tools import get_tools_by_names
from user_profile import USER_PROFILE


# ===== Allow importing from the ingestion package =====
INGESTION_PATH = Path(__file__).resolve().parent.parent / "ingestion"
sys.path.insert(0, str(INGESTION_PATH))
from search import search as rag_search, VALID_CATEGORIES  # noqa: E402


# ===== Load .env (GITHUB_TOKEN, TAVILY_API_KEY, etc.) =====
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# Project root (used to inject paths into prompts)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ===== LLM (Granite tiny-h via Ollama) =====
llm = ChatOllama(
    base_url="http://localhost:11434",
    model="ibm/granite4:tiny-h",
    temperature=0,
)


# ===== Custom tools: RAG search over the local library =====
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
        output.append(
            f"[{i}] {r['source']} (category: {r['category']}, score: {r['score']:.2f})\n"
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
        output.append(
            f"[{i}] {r['source']} (score: {r['score']:.2f})\n"
            f"{r['text'][:500]}"
        )
    return "\n\n---\n\n".join(output)


# ===== Curated subset of MCP tools for the Researcher =====
RESEARCHER_TOOLS = [
    "tavily_search",
    "tavily_extract",
    "list_directory",
    "read_text_file",
]


# ===== System prompt template =====
SYSTEM_PROMPT_TEMPLATE = f"""You are the Researcher agent, serving a math/neuroscience researcher.

═══════════════════════════════════════════════
🌐 LANGUAGE RULE — READ FIRST
You MUST respond ENTIRELY in {{user_language}}.
The PROFILE and CONTEXT below are in English, but your response
must be in {{user_language}}. No mixing of languages.
═══════════════════════════════════════════════

{USER_PROFILE}

{PROJECT_CONTEXT}

Tools available to you:
- search_local_documents(query): global RAG search across the entire indexed library
- search_by_category(query, category): RAG filtered by category
  (idn, research, personal, admin, inbox)
- tavily_search(query): web search for recent information
- tavily_extract(url): extract content from a specific URL
- list_directory(path): list a folder (absolute path)
- read_text_file(path): read a text file (absolute path)

Library structure (RAG categories):
- idn: institutional documents, slides, internal memos, references
- research: scientific papers, arXiv preprints
- personal: personal notes, CV, letters
- admin: invoices, contracts, official correspondence
- inbox: unsorted documents

Search strategy:
1. General questions across all documents → search_local_documents
2. Targeted questions ("in my work documents", "in my research papers") → search_by_category with the right category
3. Recent web information → tavily_search
4. Specific URL analysis → tavily_extract
5. Project filesystem exploration → list_directory with an absolute path starting at {{project_root}}/

General rules:
- Use ONE tool per question, unless absolutely necessary
- Cite sources in your response (filename + category when relevant)
- If a question concerns a local system capability (meeting, notes, RAG),
  mention it before suggesting external solutions
- Final output is in {{user_language}}
"""


# ===== Cached agents per language =====
_agents: dict[str, object] = {}


async def _get_agent(user_language: str):
    """Build the agent with a curated tool subset, cached per language."""
    if user_language not in _agents:
        mcp_tools = await get_tools_by_names(RESEARCHER_TOOLS)
        all_tools = mcp_tools + [search_local_documents, search_by_category]
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            user_language=user_language,
            project_root=str(PROJECT_ROOT),
        )
        _agents[user_language] = create_agent(
            model=llm,
            tools=all_tools,
            system_prompt=system_prompt,
        )
    return _agents[user_language]


async def invoke_researcher_v2(user_message: str, user_language: str = "French") -> str:
    """Async entry point for the Researcher agent."""
    agent = await _get_agent(user_language)
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=user_message)],
    })
    return result["messages"][-1].content


def invoke_researcher_v2_sync(user_message: str, user_language: str = "French") -> str:
    """Synchronous wrapper for CLI use."""
    return asyncio.run(invoke_researcher_v2(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "List the files in my vault"
    print(f"\n❓ {q}\n")
    print(invoke_researcher_v2_sync(q, "English"))