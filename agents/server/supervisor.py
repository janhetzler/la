"""
Supervisor — orchestrator that routes the user's request to the right agent.

For meta questions (presentation, capabilities, how to record a meeting),
the supervisor uses Granite to reformulate FACTS in the user's language,
instead of having fixed multi-language responses.

The user's language is detected once and passed to every downstream agent,
so that all agents respond in the same language consistently.
"""
import asyncio
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from code import invoke_code
from comms import invoke_comms
from handoff import invoke_handoff
from meeting import invoke_meeting
from notes import invoke_notes
from researcher_v2 import invoke_researcher_v2


# ===== LLM for routing and reformulations =====
router_llm = ChatOllama(
    base_url="http://localhost:11434",
    model="ibm/granite4:tiny-h",
    temperature=0,
)


# ===== Routing prompt =====
ROUTER_PROMPT = """You are a router. Pick ONE agent to handle the user's request.

Available agents:
- meta: meta questions about the system itself (who are you, what can you do, introduce yourself, help, how does it work, capabilities)
- meta_recording: ABSTRACT questions about how to record/transcribe/summarize a meeting (Teams, Zoom, Meet, audio, capture, transcription pipeline)
- researcher: information lookup (indexed papers, web, general filesystem). Technical or factual questions, documentation.
- comms: pure writing (email, message, announcement, short note). No retrieval.
- notes: exploration and search inside the Obsidian vault (meetings, personal projects, daily notes). Questions about "my notes", "my meetings".
- code: programming questions, algorithms, debugging, GitHub issue management.
- handoff: builds an enriched prompt for Claude.ai/ChatGPT. Use for HEAVY tasks beyond local capabilities: long-form writing (>1000 words), deep analyses, complex reasoning, large document analysis, scientific articles.
- meeting: to PILOT a meeting recording in real time ("start the recording", "stop", "end the meeting", "where is the recording", "recording status"). DIFFERENT from meta_recording, which answers ABSTRACT questions about the pipeline.

Reply with ONLY the agent name, in one word, no quotes, no explanation.

Examples:
- "Hi, what can you do?" → meta
- "Who are you?" → meta
- "Présente-toi" → meta
- "How does it work?" → meta
- "Apresenta-te" → meta
- "How can I record my Teams meeting?" → meta_recording
- "Comment enregistrer l'audio d'une réunion ?" → meta_recording
- "Como gravar uma reunião?" → meta_recording
- "What's the difference between RNN and Transformer?" → researcher
- "Draft an email to cancel the meeting" → comms
- "Search news about Granite 4" → researcher
- "What meeting notes do I have on project X?" → notes
- "List my vault notes" → notes
- "How do I implement an LRU cache in Python?" → code
- "Create an issue on repo Y for this bug" → code
- "Write a message to my team announcing the project" → comms
- "Write a 5000-word scientific article on transformers" → handoff
- "Do a deep analysis of this paper on attention" → handoff
- "Prepare a prompt for Claude.ai on this topic" → handoff
- "Start the recording for the Q2 meeting" → meeting
- "Démarre l'enregistrement, projet research" → meeting
- "Stop the recording" → meeting
- "Termine la réunion" → meeting
- "Where is the recording?" → meeting
- "Recording status?" → meeting
"""


VALID_AGENTS = {"meta", "meta_recording", "researcher", "comms", "notes", "code", "handoff", "meeting"}


# ===== System facts (used by meta questions) =====
SYSTEM_FACTS = """You are the user's personal Chief of Staff — a 100% local multi-agent orchestrator running on their Mac.

You have 6 specialists you delegate to:
- Researcher: searches indexed documents (papers, meeting notes) and the web (Tavily)
- Comms: drafts emails, messages, and short reports
- Notes: explores the Obsidian vault (meetings, projects, daily notes)
- Code: programming, algorithms, debugging, GitHub issue management
- Handoff: prepares rich prompts for Claude.ai or ChatGPT (for tasks beyond local 7B)
- Meeting: pilots meeting recordings (start/stop/status) directly from chat

Example requests:
- Question about an indexed paper → Researcher searches the local RAG base
- Recent news → Researcher uses the web
- Question about meetings/personal notes → Notes explores the Obsidian vault
- Drafting (email, message) → Comms writes
- Programming question → Code answers
- Heavy task (5000-word article, deep analysis) → Handoff prepares a prompt for Claude.ai
- "Start recording the meeting" → Meeting pilots the recorder

Important characteristics:
- Runs 100% locally (Granite models via Ollama), no paid API calls
- Data stays on your machine (except via Handoff, under explicit user control)
- Multilingual (adapts to user's language: French, English, Spanish, Portuguese, etc.)
- For volumic tasks or complex reasoning, naturally suggest Claude.ai or ChatGPT (existing subscriptions)"""


MEETING_FACTS = """The system offers 2 ways to record a meeting (Teams, Zoom, Meet, etc.):

OPTION 1 — Local automated pipeline (RECOMMENDED for daily needs):
Captures audio + auto-transcribes + generates a structured meeting note + saves to the Obsidian vault.

Prerequisites (one-time setup):
- BlackHole 2ch installed (already done in the project)
- Multi-Output Device configured in Audio MIDI Setup: combines MacBook Air Speakers + BlackHole 2ch
- Set this Multi-Output as the system output before the meeting

During the meeting:

(a) Easiest — pilot from the chat itself:
    Just say to the assistant: "start the recording, project X, topic Y"
    When done: "stop"

(b) From the terminal:
    cd <project-root>
    source .venv/bin/activate  # or your venv name
    python agents/notes/recorder.py start --project P --topic T
    Stop with Ctrl+C.

What happens automatically afterwards:
- Transcription via whisper.cpp (Medium model, Metal acceleration)
- Structured summary generated by Granite tiny-h (summary, decisions, actions, open questions)
- Saved to vault/meetings/YYYY/MM/
- Auto-indexed in Qdrant for future semantic search

OPTION 2 — Native Teams recording:
- More actions (•••) in the Teams toolbar → Record meeting
- Stored in OneDrive → Recordings
- All participants get a notification
- Requires the organization to allow it

Local pipeline advantages: auto summary, locally indexed, data on the Mac, no notification to participants, Markdown output in Obsidian.
Native Teams advantages: no terminal needed, MP4 video format."""


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

Use emojis on agent names: 📚 Researcher, 📝 Comms, 🗒️ Notes, 💻 Code, 🔀 Handoff, 🎙️ Meeting."""


MEETING_REFORMULATION_PROMPT = """The user is asking how to record a meeting.

═══════════════════════════════════════════════
🌐 LANGUAGE: You MUST respond in {language}.
The FACTS below are in English, but your ENTIRE response MUST be in {language}.
═══════════════════════════════════════════════

FACTS about the available recording options:

---
{facts}
---

User's question:
{user_message}

Now present these options to the user in {language}:
1. ⚠️ EVERY WORD of your response must be in {language} — do NOT mix languages
2. Highlight OPTION 1 (local automated pipeline) as the main recommendation
3. Mention BOTH ways inside Option 1: piloting from chat AND piloting from terminal
4. Structured markdown: sections, lists, code blocks for terminal commands
5. Include a comparison table if relevant
6. KEEP terminal commands EXACTLY AS WRITTEN (cd ~/Desktop/..., python recorder.py, etc.) — do NOT translate commands
7. Helpful and clear tone"""


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

    elif agent_name == "meta_recording":
        prompt = MEETING_REFORMULATION_PROMPT.format(
            facts=MEETING_FACTS,
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
    elif agent_name == "meeting":
        return await invoke_meeting(user_message, user_lang)
    else:
        return await invoke_researcher_v2(user_message, user_lang)


def invoke_supervisor_sync(user_message: str) -> str:
    return asyncio.run(invoke_supervisor(user_message))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Présente-toi"
    print(f"\n❓ {q}\n")
    print(invoke_supervisor_sync(q))