"""
Code agent: dev assistance with GitHub access.

Specialized for:
- General programming questions, debugging, code review
- GitHub issue management (list, read, create, comment)

No local filesystem access for now — focus on GitHub.
For local code work, use your IDE or another tool.
"""
import asyncio
import sys

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from project_context import PROJECT_CONTEXT
from tools import get_tools_by_names
from user_profile import USER_PROFILE


# Granite tiny-h, deterministic
llm = ChatOpenAI(
    base_url=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
    model="granite-tiny",
    temperature=0,
)


# Curated GitHub tool subset
CODE_TOOLS = [
    "create_issue",
    "add_issue_comment",
    "get_issue",
    "list_issues",
]


SYSTEM_PROMPT_TEMPLATE = f"""You are the Code agent.

═══════════════════════════════════════════════
🌐 LANGUAGE RULE — READ FIRST
You MUST respond ENTIRELY in {{user_language}}.
Source code, variable names, and inline code comments stay in English
(universal convention), but ALL prose around the code is in {{user_language}}.
═══════════════════════════════════════════════

{USER_PROFILE}

{PROJECT_CONTEXT}

GitHub tools available (limited):
- list_issues(owner, repo): list issues from a repo
- get_issue(owner, repo, issue_number): view a specific issue
- create_issue(owner, repo, title, body): create an issue (useful for TODOs)
- add_issue_comment(owner, repo, issue_number, body): comment on an issue

Rules:
1. For GENERAL programming questions (algorithms, syntax, debugging, explanations,
   examples) → respond DIRECTLY without any tool. This is your main mode.
2. For issue management (list, create, comment) → use the tools above.
3. To SEARCH repos, READ code/README files, or EXPLORE a repo → NOT supported here.
   Reply: "For this task, open GitHub directly in your browser, or use Claude.ai /
   ChatGPT / Gemini for deeper analysis."
4. Format code carefully (```python, ```ts, etc.).
5. Cite GitHub links when relevant.
6. Prose output is in {{user_language}}; code stays in English.
"""


_agents: dict[str, object] = {}


async def _get_agent(user_language: str):
    if user_language not in _agents:
        mcp_tools = await get_tools_by_names(CODE_TOOLS)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(user_language=user_language)
        _agents[user_language] = create_agent(
            model=llm,
            tools=mcp_tools,
            system_prompt=system_prompt,
        )
    return _agents[user_language]


async def invoke_code(user_message: str, user_language: str = "French") -> str:
    agent = await _get_agent(user_language)
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=user_message)],
    })
    return result["messages"][-1].content


def invoke_code_sync(user_message: str, user_language: str = "French") -> str:
    return asyncio.run(invoke_code(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "How do I implement an LRU cache in Python?"
    print(f"\n❓ {q}\n")
    print(invoke_code_sync(q, "English"))