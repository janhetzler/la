"""
Supervisor — orchestrator that routes the user's request to the right agent.

For meta questions (presentation, capabilities), the supervisor uses Granite
to reformulate FACTS in the user's language, instead of having fixed
multi-language responses.

The user's language is detected once and passed to every downstream agent,
so that all agents respond in the same language consistently.
"""
import asyncio
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

import config

from code import invoke_code
from comms import invoke_comms
from handoff import invoke_handoff
from notes import invoke_notes
from researcher_v2 import invoke_researcher_v2


# ===== LLM for routing and reformulations =====
router_llm = ChatOpenAI(
    base_url=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
    model=config.DEFAULT_LLM,
    temperature=0,
)


# ===== Routing prompt =====
ROUTER_PROMPT = """You are a router. Pick ONE agent to handle the user's request.

Available agents:
- meta: meta questions about the system itself (who are you, what can you do, introduce yourself, help, how does it work, capabilities)
- researcher: information lookup (indexed papers, web, general filesystem). Technical or factual questions, documentation.
- comms: pure writing (email, message, announcement, short note). No retrieval.
- notes: exploration and search inside the Obsidian vault (personal projects, daily notes). Questions about "my notes".
- code: programming questions, algorithms, debugging, GitHub issue management.
- handoff: builds an enriched prompt for Claude.ai/ChatGPT. Use for HEAVY tasks beyond local capabilities: long-form writing (>1000 words), deep analyses, complex reasoning, large document analysis, scientific articles.

Reply with ONLY the agent name, in one word, no quotes, no explanation.

Examples:
- "Hi, what can you do?" → meta
- "Who are you?" → meta
- "Présente-toi" → meta
- "How does it work?" → meta
- "Apresenta-te" → meta
- "What's the difference between RNN and Transformer?" → researcher
- "Search news about Granite 4" → researcher
- "List my vault notes" → notes
- "How do I implement an LRU cache in Python?" → code
- "Create an issue on repo Y for this bug" → code
- "Write a message to my team announcing the project" → comms
- "Write a 5000-word scientific article on transformers" → handoff
- "Do a deep analysis of this paper on attention" → handoff
- "Prepare a prompt for Claude.ai on this topic" → handoff
"""


VALID_AGENTS = {"meta", "researcher", "comms", "notes", "code", "handoff"}


# ===== System facts (used by meta questions) =====
SYSTEM_FACTS = """You are the user's personal Local Agent — a 100% local multi-agent orchestrator running on their local server.

You have 5 specialists you delegate to:
- Researcher: searches indexed documents and the web (Tavily)
- Comms: drafts emails, messages, and short reports
- Notes: explores the Obsidian vault (projects, daily notes)
- Code: programming, algorithms, debugging, GitHub issue management
- Handoff: prepares rich prompts for Claude.ai or ChatGPT (for tasks beyond local 7B)

Example requests:
- Question about an indexed paper → Researcher searches the local RAG base
- Recent news → Researcher uses the web
- Question about personal notes → Notes explores the Obsidian vault
- Drafting (email, message) → Comms writes
- Programming question → Code answers
- Heavy task (5000-word article, deep analysis) → Handoff prepares a prompt for Claude.ai

Important characteristics:
- Runs 100% locally (Granite models via llama-server + LiteLLM), no paid API calls
- Data stays on your machine (except via Handoff, under explicit user control)
- Multilingual (adapts to user's language: French, English, Spanish, Portuguese, etc.)
- For volumic tasks or complex reasoning, naturally suggest Claude.ai or ChatGPT (existing subscriptions)"""


# ===== Reformulation prompts for meta questions =====
META_REFORMULATION_PROMPT = """The user is asking a meta question about you (who you are, capabilities, help, etc.).

═══════════════════════════════════════════════
🌐 LANGUAGE: You MUST respond in {language}.
The FACTS below are in English, but your ENTIRE response MUST be in {language}.
═══════════════════════════════════════════════

FACTS about your system (translate these into {language} when presenting):

---
{facts}
---

User's question:
{user_message}

Now present these facts to the user in {language}:
1. ⚠️ EVERY WORD of your response must be in {language} — do NOT mix languages
2. Warm and natural tone (not a literal translation)
3. Well-structured markdown (headings, bullets, tables if relevant)
4. End with an open question equivalent to "What can I do for you?" in {language}

Use emojis on agent names: 📚 Researcher, 📝 Comms, 🗒️ Notes, 💻 Code, 🔀 Handoff."""


# ===== Language detection =====
async def detect_user_language(user_message: str) -> str:
    """
    Ask Granite to detect the language of the user message in one word.
    Returns the language name in English (English, French, Spanish, etc.).
    """
    detection_prompt = """Detect the language of the user's message.
Respond with ONLY the language name in English, in one word.
Examples: English, French, Spanish, Portuguese, German, Italian, Dutch, Japanese, Chinese, Arabic.
No other text, just the language name."""

    messages = [
        SystemMessage(content=detection_prompt),
        HumanMessage(content=user_message),
    ]
    response = await router_llm.ainvoke(messages)
    lang = response.content.strip().split()[0].rstrip(".,!?;:")
    return lang


# ===== Routing logic =====
async def route(user_message: str) -> str:
    """Ask the LLM which agent should handle the request."""
    messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=user_message),
    ]
    response = await router_llm.ainvoke(messages)
    raw = response.content.strip()

    # Extract just the first non-empty token, lowercased, stripped of punctuation
    tokens = raw.split()
    if tokens:
        first_token = tokens[0].strip("\"'.,;:{}[]()").lower()
    else:
        first_token = ""

    if first_token in VALID_AGENTS:
        return first_token

    # If the response looks like JSON or anything weird, fall back to "meta"
    # (safe — just a presentation) instead of "researcher" (can call RAG/web tools).
    print(f"[supervisor] ⚠️ unparseable router response '{raw[:100]}', falling back to meta")
    return "meta"


async def invoke_supervisor(user_message: str) -> str:
    """Detect language, route, and delegate to the chosen agent."""
    # Filter out Open WebUI auto-generated requests (follow-ups, titles, tags)
    # that look like JSON instructions rather than real user messages.
    msg_stripped = user_message.strip()
    if msg_stripped.startswith("{") and (
        '"follow_ups"' in msg_stripped
        or '"title"' in msg_stripped
        or '"tags"' in msg_stripped
        or "Generate" in msg_stripped[:200]
    ):
        print(f"[supervisor] ⏭️  skipping Open WebUI auto-request")
        return "[]"
    # Detect language ONCE per request, pass it everywhere
    user_lang = await detect_user_language(user_message)
    agent_name = await route(user_message)
    print(f"[supervisor] language={user_lang} → {agent_name}")

    if agent_name == "meta":
        prompt = META_REFORMULATION_PROMPT.format(
            facts=SYSTEM_FACTS,
            user_message=user_message,
            language=user_lang,
        )
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_message),
        ]
        response = await router_llm.ainvoke(messages)
        return response.content

    elif agent_name == "researcher":
        return await invoke_researcher_v2(user_message, user_lang)
    elif agent_name == "comms":
        return await invoke_comms(user_message, user_lang)
    elif agent_name == "notes":
        return await invoke_notes(user_message, user_lang)
    elif agent_name == "code":
        return await invoke_code(user_message, user_lang)
    elif agent_name == "handoff":
        return await invoke_handoff(user_message, user_lang)
    else:
        return await invoke_researcher_v2(user_message, user_lang)


def invoke_supervisor_sync(user_message: str) -> str:
    return asyncio.run(invoke_supervisor(user_message))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Présente-toi"
    print(f"\n❓ {q}\n")
    print(invoke_supervisor_sync(q))