"""
Supervisor — orchestrator that routes the user's request to the right agent.

Router-Prompt wird dynamisch aus prompts/agents/*.md aufgebaut via agent_loader.
Neuen Agenten hinzufuegen: neue .md Datei in prompts/agents/ anlegen, fertig.
"""
import asyncio
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

import config
from agent_loader import build_router_prompt, list_agents, load_agent_meta

from code import invoke_code
from comms import invoke_comms
from handoff import invoke_handoff
from notes import invoke_notes
from researcher_v2 import invoke_researcher_v2


# ===== LLM fuer Routing und Reformulierungen =====
router_llm = ChatOpenAI(
    base_url=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
    model=config.DEFAULT_LLM,
    temperature=0,
)


# ===== Router-Prompt dynamisch aus prompts/agents/*.md =====
def _build_router_prompt() -> str:
    """Baut den Router-Prompt aus allen verfuegbaren Agent-.md Dateien."""
    agents = list_agents()
    return build_router_prompt(agents)


def _build_valid_agents() -> set:
    """Liest alle gueltigen Agent-Namen aus prompts/agents/*.md."""
    return {a["name"] for a in list_agents()} | {"meta"}


# Beim Start einmal laden
ROUTER_PROMPT  = _build_router_prompt()
VALID_AGENTS   = _build_valid_agents()

print(f"[supervisor] Router geladen: {sorted(VALID_AGENTS)}", flush=True)


# ===== System Facts fuer Meta-Fragen =====
SYSTEM_FACTS = """You are the user's personal Local Agent — a 100% local multi-agent orchestrator running on their local server.

You have 5 specialists you delegate to:
- Researcher: searches indexed documents and the web
- Comms: drafts emails, messages, and short reports
- Notes: explores ChromaDB (personal notes, projects, meetings)
- Code: programming, algorithms, debugging, GitHub issue management
- Handoff: prepares rich prompts for Claude.ai or ChatGPT (for tasks beyond local model capacity)

Important characteristics:
- Runs 100% locally (Granite models via llama-server + LiteLLM), no paid API calls by default
- Data stays on your machine (except via Handoff, under explicit user control)
- Multilingual (adapts to user's language)
- For heavy tasks or complex reasoning, naturally suggest Claude.ai or ChatGPT"""


# ===== Reformulation Prompt fuer Meta-Fragen =====
META_REFORMULATION_PROMPT = """The user is asking a meta question about you (who you are, capabilities, help, etc.).

LANGUAGE: You MUST respond in {language}.
The FACTS below are in English, but your ENTIRE response MUST be in {language}.

FACTS about your system:

---
{facts}
---

User's question:
{user_message}

Present these facts to the user in {language}:
1. Every word of your response must be in {language}
2. Warm and natural tone
3. Well-structured markdown (headings, bullets)
4. End with an open question equivalent to "What can I do for you?" in {language}

Use emojis on agent names: Researcher, Comms, Notes, Code, Handoff."""


# ===== Spracherkennung =====
async def detect_user_language(user_message: str) -> str:
    """
    Spracherkennung — vereinfacht fuer kleine Modelle.
    Gibt immer English zurueck bis Granite-Tiny auf dem Host verfuegbar.
    TODO: LLM-basierte Erkennung auf dem Host reaktivieren.
    """
    return "English"


# ===== Routing =====
async def route(user_message: str) -> str:
    """Fragt das LLM welcher Agent die Anfrage bearbeiten soll."""
    messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=user_message),
    ]
    response = await router_llm.ainvoke(messages)
    raw = response.content.strip()

    tokens = raw.split()
    if tokens:
        first_token = tokens[0].strip("\"'.,;:{}[]()").lower()
    else:
        first_token = ""

    if first_token in VALID_AGENTS:
        return first_token

    print(f"[supervisor] unparseable router response '{raw[:100]}', falling back to meta")
    return "meta"


# ===== Supervisor =====
async def invoke_supervisor(user_message: str) -> str:
    """Erkennt Sprache, routet und delegiert an den gewaehlten Agenten."""
    msg_stripped = user_message.strip()
    if msg_stripped.startswith("{") and (
        '"follow_ups"' in msg_stripped
        or '"title"' in msg_stripped
        or '"tags"' in msg_stripped
        or "Generate" in msg_stripped[:200]
    ):
        print("[supervisor] skipping Open WebUI auto-request")
        return "[]"

    user_lang = await detect_user_language(user_message)
    agent_name = await route(user_message)
    print(f"[supervisor] language={user_lang} -> {agent_name}", flush=True)

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
    q = sys.argv[1] if len(sys.argv) > 1 else "What can you do?"
    print(f"\n{q}\n")
    print(invoke_supervisor_sync(q))
