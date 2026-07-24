"""
Researcher Agent (v2): Natives Granite Tool-Format statt bind_tools().

Tools:
- search_local_documents / search_by_category: semantic search over the user's library
- MCP-Tools: tavily_search, tavily_extract, list_directory, read_text_file

Umbau 2026-07-24: create_agent()/bind_tools() ersetzt durch
format_tools_for_model() + parse_tool_call_from_response() aus tool_formatter.py.
Grund: 350m Modell kann OpenAI Function-Calling-Format nicht zuverlaessig bedienen,
aber natives Granite XML-Format funktioniert.
"""
import asyncio
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import chromadb

import config
from agent_loader import load_agent
from tool_formatter import format_tools_for_model, parse_tool_call_from_response
from tools import get_tools_by_names


# ===== Import aus dem Ingestion-Paket ermoeglichen =====
INGESTION_PATH = Path(__file__).resolve().parent.parent / "ingestion"
sys.path.insert(0, str(INGESTION_PATH))
from search import search as rag_search, VALID_CATEGORIES  # noqa: E402


# ===== Load .env (GITHUB_TOKEN, TAVILY_API_KEY, etc.) =====
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# Project root (used to inject paths into prompts)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ===== LLM =====
llm = ChatOpenAI(
    base_url=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
    model=config.DEFAULT_LLM,
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


# ===== System prompt =====
def _get_system_prompt(user_language: str = "en") -> str:
    _, prompt = load_agent("researcher")
    return prompt.replace("{user_language}", user_language)


async def invoke_researcher_v2(user_message: str, user_language: str = "French") -> str:
    """Researcher-Agent mit nativem Granite Tool-Format statt bind_tools()."""
    try:
      return await _invoke_researcher_core(user_message, user_language)
    except Exception as e:
        print(f"[researcher] Fehler: {e}", flush=True)
        return f"Researcher error: {type(e).__name__}: {str(e)[:200]}"


async def _invoke_researcher_core(user_message: str, user_language: str) -> str:
    # Tools laden
    mcp_tools = await get_tools_by_names(RESEARCHER_TOOLS)
    all_tools = mcp_tools + [search_local_documents, search_by_category]

    # Tool-Definitionen bauen — args_schema Fix: dict() statt .schema()
    tool_defs = []
    for t in all_tools:
        schema = dict(t.args_schema) if hasattr(t, "args_schema") else {}
        tool_defs.append({
            "name": t.name,
            "description": t.description,
            "parameters": schema,
        })

    # System-Prompt: Agent-Prompt + natives Granite Tool-Format
    tool_system = format_tools_for_model(tool_defs, model_family="granite")
    agent_prompt = _get_system_prompt(user_language)
    agent_prompt = agent_prompt.replace("{project_root}", str(PROJECT_ROOT))
    system_content = f"{agent_prompt}\n\n{tool_system}" if tool_system else agent_prompt

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_message),
    ]

    tool_map = {t.name: t for t in all_tools}

    # ReAct Loop — max 5 Runden
    for step in range(5):
        try:
            response = await llm.ainvoke(messages)
        except Exception as e:
            print(f"[researcher] LLM Fehler: {e}", flush=True)
            return f"Researcher error: {type(e).__name__}: {str(e)[:200]}"

        raw = response.content
        tool_call = parse_tool_call_from_response(raw, model_family="granite")

        if tool_call is None:
            # Keine Tool-Call erkannt → finale Antwort
            return raw

        # Tool ausführen
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("arguments", {})
        print(f"[researcher] tool_call: {tool_name}({tool_args})", flush=True)

        if tool_name not in tool_map:
            tool_result = f"Unknown tool: {tool_name}"
        else:
            try:
                tool_result = tool_map[tool_name].invoke(tool_args)
            except Exception as e:
                tool_result = f"Tool error: {e}"

        # Tool-Ergebnis in Konversation einhängen
        messages.append(AIMessage(content=raw))
        messages.append(HumanMessage(
            content=f"<tool_response>\n{tool_result}\n</tool_response>"
        ))

    return "Researcher: Maximale Tool-Runden erreicht."


def invoke_researcher_v2_sync(user_message: str, user_language: str = "French") -> str:
    """Synchroner Wrapper fuer die Kommandozeile."""
    return asyncio.run(invoke_researcher_v2(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "List the files in my vault"
    print(f"\n❓ {q}\n")
    print(invoke_researcher_v2_sync(q, "English"))
