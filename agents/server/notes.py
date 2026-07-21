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
from langchain_openai import ChatOpenAI
import chromadb

import config
from agent_loader import load_agent
from tools import get_tools_by_names


# Projektpfade (werden als absolute Pfade in den System-Prompt injiziert)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_PATH = PROJECT_ROOT / "vault"


# Granite tiny-h, deterministisch fuer Tool-Calls
llm = ChatOpenAI(
    base_url=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
    model="granite-tiny",
    temperature=0,
)


# ===== Custom tool: RAG search filtered to meeting notes =====
def _embed_query(text: str) -> list[float]:
    """Embedding ueber den LiteLLM-Proxy."""
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
        client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        collection = client.get_or_create_collection(
            name=config.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=top_k,
            where={"category": "notes"},
            include=["documents", "distances", "metadatas"],
        )

        meetings = []
        if results and results["documents"]:
            for doc, dist, meta in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0],
            ):
                source = meta.get("source", "unknown")
                score = 1 - dist
                meetings.append(f"[{source}, score {score:.2f}]\n{doc[:500]}")

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
# Prompt wird aus prompts/agents/notes.md geladen
_shared_cache = {}



@tool
def save_note(text: str, title: str = "") -> str:
    """Speichert eine Notiz in ChromaDB.

    Args:
        text:  Inhalt der Notiz.
        title: Optionaler Titel (wird als source-Feld gespeichert).
    """
    from datetime import datetime
    vec = _embed_query(text)
    source = f"note-{title}" if title else "note"
    note_id = f"note-{datetime.now().isoformat()}"
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=config.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )
    collection.add(
        documents=[text],
        embeddings=[vec],
        metadatas=[{"category": "notes", "source": source}],
        ids=[note_id]
    )
    preview = text[:50] + ("..." if len(text) > 50 else "")
    return f"Notiz gespeichert: {preview}"


def _get_system_prompt(user_language: str = "en") -> str:
    _, prompt = load_agent("notes")
    return prompt.replace("{user_language}", user_language)



# Cached agents per language (avoid rebuilding on every call)
_agents: dict[str, object] = {}


async def _get_agent(user_language: str):
    """Erstellt den Notes-Agenten mit gefilterten Tools, gecacht pro Sprache."""
    if user_language not in _agents:
        mcp_tools = await get_tools_by_names(NOTES_TOOLS)
        all_tools = [search_meetings, save_note] + mcp_tools
        system_prompt = _get_system_prompt(user_language)
        system_prompt = system_prompt.replace("{vault_path}", str(VAULT_PATH))
        _agents[user_language] = create_agent(
            model=llm,
            tools=all_tools,
            system_prompt=system_prompt,
        )
    return _agents[user_language]


async def invoke_notes(user_message: str, user_language: str = "English") -> str:
    """Asynchroner Einstiegspunkt fuer den Notes-Agenten."""
    agent = await _get_agent(user_language)
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=user_message)],
    })
    return result["messages"][-1].content


def invoke_notes_sync(user_message: str, user_language: str = "English") -> str:
    """Synchroner Wrapper fuer die Kommandozeile."""
    return asyncio.run(invoke_notes(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "List my meeting notes"
    print(f"\n❓ {q}\n")
    print(invoke_notes_sync(q, "English"))