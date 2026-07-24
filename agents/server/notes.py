"""
Notes Agent: Speichert und sucht persoenliche Notizen in ChromaDB.

Tools:
- save_note: Notiz in ChromaDB schreiben
- search_meetings: Notizen aus ChromaDB suchen

Umbau 2026-07-24: create_agent()/bind_tools() ersetzt durch
format_tools_for_model() + parse_tool_call_from_response() aus tool_formatter.py.
MCP-Tools entfernt — Notes-Agent ist rein auf ChromaDB fokussiert.
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import chromadb

import config
from agent_loader import load_agent
from tool_formatter import format_tools_for_model, parse_tool_call_from_response


# Projektpfade
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_PATH = PROJECT_ROOT / "vault"


# LLM
llm = ChatOpenAI(
    base_url=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
    model=config.DEFAULT_LLM,
    temperature=0,
)


# ===== Embedding =====
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


# ===== Tools =====
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


# ===== System prompt =====
def _get_system_prompt(user_language: str = "en") -> str:
    _, prompt = load_agent("notes")
    return prompt.replace("{user_language}", user_language)


# ===== Agent =====
async def invoke_notes(user_message: str, user_language: str = "English") -> str:
    """Notes-Agent mit nativem Granite Tool-Format statt bind_tools()."""
    try:
        return await _invoke_notes_core(user_message, user_language)
    except Exception as e:
        print(f"[notes] Fehler: {e}", flush=True)
        return f"Notes error: {type(e).__name__}: {str(e)[:200]}"


async def _invoke_notes_core(user_message: str, user_language: str) -> str:
    all_tools = [save_note, search_meetings]

    # Tool-Definitionen bauen — args_schema Fix: dict() statt .schema()
    tool_defs = []
    for t in all_tools:
        if hasattr(t, "args_schema"):
            s = t.args_schema
            if isinstance(s, dict):
                schema = s
            elif hasattr(s, "model_json_schema"):
                schema = s.model_json_schema()
            elif hasattr(s, "schema"):
                schema = s.schema()
            else:
                schema = {}
        else:
            schema = {}
        tool_defs.append({
            "name": t.name,
            "description": t.description,
            "parameters": schema,
        })

    # System-Prompt: Agent-Prompt + natives Granite Tool-Format
    tool_system = format_tools_for_model(tool_defs, model_family="granite")
    agent_prompt = _get_system_prompt(user_language)
    agent_prompt = agent_prompt.replace("{vault_path}", str(VAULT_PATH))
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
            print(f"[notes] LLM Fehler: {e}", flush=True)
            return f"Notes error: {type(e).__name__}: {str(e)[:200]}"

        raw = response.content
        tool_call = parse_tool_call_from_response(raw, model_family="granite")

        if tool_call is None:
            # Keine Tool-Call erkannt → finale Antwort
            return raw

        # Tool ausführen
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("arguments", {})
        print(f"[notes] tool_call: {tool_name}({tool_args})", flush=True)

        if tool_name not in tool_map:
            tool_result = f"Unknown tool: {tool_name}"
        else:
            try:
                tool_result = tool_map[tool_name].invoke(tool_args)
            except Exception as e:
                tool_result = f"Tool error: {e}"

        messages.append(AIMessage(content=raw))
        messages.append(HumanMessage(
            content=f"<tool_response>\n{tool_result}\n</tool_response>"
        ))

    return "Notes: Maximale Tool-Runden erreicht."


def invoke_notes_sync(user_message: str, user_language: str = "English") -> str:
    """Synchroner Wrapper fuer die Kommandozeile."""
    return asyncio.run(invoke_notes(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "List my meeting notes"
    print(f"\n❓ {q}\n")
    print(invoke_notes_sync(q, "English"))
