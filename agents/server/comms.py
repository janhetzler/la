"""
Comms agent: drafts emails, messages, short reports.

Tool-less agent — pure synthesis via Granite tiny-h.
Uses the user's profile and project context, and matches the
user's language (passed as a parameter from the supervisor).
"""
import asyncio
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from project_context import PROJECT_CONTEXT
from user_profile import USER_PROFILE


# Granite tiny-h with a touch of creativity for writing
llm = ChatOpenAI(
    base_url=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
    model="granite-tiny",
    temperature=0.3,
)


SYSTEM_PROMPT_TEMPLATE = f"""You are the Comms agent.

═══════════════════════════════════════════════
🌐 LANGUAGE RULE — READ FIRST
You MUST respond ENTIRELY in {{user_language}}.
The PROFILE and CONTEXT below are in English, but your response
must be in {{user_language}}. No mixing of languages.
═══════════════════════════════════════════════

{USER_PROFILE}

{PROJECT_CONTEXT}

Your role: write clear, professional messages — emails, short reports, internal notes.

Output guidelines:
- Emails: tone matches the recipient (formal for clients/management, direct for colleagues),
  clear structure (subject, body, signature)
- Short reports: factual, organized in sections
- Messages: concise, courteous

Rules:
1. Adapt the tone to the audience (formal for clients/hierarchy, more direct for peers)
2. No fluff — go straight to the point
3. When asked for an email, deliver it directly (no "Here is the email:" preamble)
4. Preserve proper names and provided data exactly as given
5. The whole output is in {{user_language}}
"""


async def invoke_comms(user_message: str, user_language: str = "French") -> str:
    """Generate a written response in the user's language."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(user_language=user_language)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    response = await llm.ainvoke(messages)
    return response.content


def invoke_comms_sync(user_message: str, user_language: str = "French") -> str:
    """Synchronous wrapper for CLI use."""
    return asyncio.run(invoke_comms(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Draft an email to cancel a meeting tomorrow morning with Marie."
    print(f"\n❓ {q}\n")
    print(invoke_comms_sync(q, "English"))