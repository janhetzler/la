"""
Handoff agent: prepares an enriched prompt for Claude.ai or ChatGPT.

Pipeline:
1. Pulls relevant context from the local vault (RAG)
2. Builds an optimized prompt structure
3. Returns the prompt + direct links to external services

Typical use:
- Long-form scientific writing
- Deep analysis of a paper
- Complex multi-step reasoning
- Tasks beyond local 7B models
"""
import asyncio
import json
import sys

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import chromadb

import config
from agent_loader import load_agent


# Granite for prompt structuring — no tool calling needed
llm = ChatOpenAI(
    base_url=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
    model="granite-tiny",
    temperature=0.2,
)


# ===== Local context retrieval (RAG) =====
def _embed_query(text: str) -> list[float]:
    with httpx.Client(timeout=60) as client:
        r = client.post(
            f"{config.LITELLM_URL}/v1/embeddings",
            headers={"Authorization": f"Bearer {config.LITELLM_KEY}"},
            json={"model": config.EMBED_MODEL, "input": text},
        )
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]


def _fetch_context(query: str, top_k: int = 3) -> str:
    """Retrieve relevant chunks to enrich the outgoing prompt."""
    try:
        query_vec = _embed_query(query)
        client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        results = client.query_points(
            collection_name=config.QDRANT_COLLECTION,
            query=query_vec,
            limit=top_k,
            with_payload=True,
        ).points

        if not results:
            return ""

        chunks = []
        for p in results:
            if p.score < 0.5:  # ignore weakly-relevant results
                continue
            payload = p.payload or {}
            text = payload.get("text", "")
            if not text and "_node_content" in payload:
                try:
                    node = json.loads(payload["_node_content"])
                    text = node.get("text", "")
                except Exception:
                    text = ""
            source = payload.get("source", "?")
            chunks.append(f"[Source: {source}]\n{text[:600]}")

        return "\n\n---\n\n".join(chunks) if chunks else ""
    except Exception:
        return ""


# ===== Prompt builder =====
# Prompt wird aus prompts/agents/handoff.md geladen
_shared_cache = {}


def _get_system_prompt(user_language: str = "en") -> str:
    _, prompt = load_agent("handoff")
    return prompt.replace("{user_language}", user_language)



# Wrapper text translations (kept short — added around the structured prompt)
WRAPPER_TEMPLATES = {
    "French": {
        "title": "## 📋 Prompt préparé pour Claude.ai / ChatGPT",
        "intro": "Copie le bloc ci-dessous et colle-le dans une nouvelle conversation :",
        "where": "## 🚀 Où l'envoyer",
        "claude": "**Claude.ai** (Opus 4.7 recommandé pour rédaction longue, raisonnement, analyse) → https://claude.ai/new",
        "chatgpt": "**ChatGPT** (GPT-5 recommandé pour code complexe, analyse de données) → https://chatgpt.com/",
        "tips": "## 💡 Astuces",
        "with_context": "✅ Ce prompt inclut du contexte de tes documents locaux",
        "without_context": "ℹ️ Aucun contexte local pertinent ajouté — la requête repose uniquement sur la connaissance générale du modèle",
        "claude_files": "Pour Claude.ai : tu peux ajouter des fichiers sources directement à la conversation",
        "follow_up": "Reviens ici si tu veux que je traite la réponse externe (résumé, tri, classement dans le vault)",
    },
    "English": {
        "title": "## 📋 Prompt prepared for Claude.ai / ChatGPT",
        "intro": "Copy the block below and paste it into a new conversation:",
        "where": "## 🚀 Where to send it",
        "claude": "**Claude.ai** (Opus 4.7 recommended for long-form writing, reasoning, analysis) → https://claude.ai/new",
        "chatgpt": "**ChatGPT** (GPT-5 recommended for complex code, data analysis) → https://chatgpt.com/",
        "tips": "## 💡 Tips",
        "with_context": "✅ This prompt includes context from your local documents",
        "without_context": "ℹ️ No relevant local context added — the request relies on the model's general knowledge alone",
        "claude_files": "For Claude.ai: you can attach source files directly to the conversation",
        "follow_up": "Come back here if you want me to process the external response (summarize, sort, file in the vault)",
    },
}


def _wrapper(user_language: str) -> dict:
    """Return wrapper labels for a given language, falling back to English."""
    return WRAPPER_TEMPLATES.get(user_language, WRAPPER_TEMPLATES["English"])


async def invoke_handoff(user_message: str, user_language: str = "French") -> str:
    """Build an enriched prompt for Claude.ai/ChatGPT in the user's language."""
    # 1. Pull relevant local context
    context = _fetch_context(user_message, top_k=3)

    # 2. Ask the LLM to reformulate the request
    builder_system = _get_system_prompt(user_language)
    builder_input = f"""User request:
{user_message}

Relevant local context (integrate if useful):
{context if context else "(no relevant local context)"}

Reformulate this into a structured, rich prompt ready to paste into Claude.ai or ChatGPT.
The output prompt must be in {user_language}."""

    messages = [
        SystemMessage(content=builder_system),
        HumanMessage(content=builder_input),
    ]
    response = await llm.ainvoke(messages)
    structured_prompt = response.content.strip()

    # 3. Wrap with localized labels
    w = _wrapper(user_language)
    has_context = bool(context)
    context_line = w["with_context"] if has_context else w["without_context"]

    output = f"""{w["title"]}

{w["intro"]}

---

{structured_prompt}

---

{w["where"]}

- {w["claude"]}
- {w["chatgpt"]}

{w["tips"]}

- {context_line}
- {w["claude_files"]}
- {w["follow_up"]}"""

    return output


def invoke_handoff_sync(user_message: str, user_language: str = "French") -> str:
    return asyncio.run(invoke_handoff(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Write a 5000-word scientific article on transformers"
    print(f"\n❓ {q}\n")
    print(invoke_handoff_sync(q, "English"))