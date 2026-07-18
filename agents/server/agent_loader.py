"""
agent_loader.py — Generischer Agent-Loader

Liest Agent-Konfiguration aus prompts/agents/*.md (YAML-Frontmatter + Prompt)
und baut daraus einen funktionierenden LangChain-Agenten.

Verwendung:
    from agent_loader import load_agent, load_shared_context

    shared = load_shared_context()
    agent = load_agent("comms", shared)
    response = await agent.ainvoke({"input": "Write an email..."})
"""
import os, re
from pathlib import Path
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR  = PROJECT_ROOT / "prompts"

# ── Frontmatter Parser ────────────────────────────────────────────────────────

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parst YAML-Frontmatter aus einer .md Datei.
    Gibt (metadata_dict, prompt_text) zurueck.
    """
    if not content.startswith("---"):
        return {}, content.strip()

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content.strip()

    yaml_str = parts[1].strip()
    prompt   = parts[2].strip()

    if HAS_YAML:
        try:
            meta = yaml.safe_load(yaml_str) or {}
        except Exception:
            meta = {}
    else:
        # Einfacher Fallback ohne yaml-Paket
        meta = {}
        for line in yaml_str.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                v = v.strip()
                if v.startswith("[") and v.endswith("]"):
                    v = [x.strip().strip('"') for x in v[1:-1].split(",") if x.strip()]
                elif v == "null" or v == "":
                    v = None
                elif v == "true":
                    v = True
                elif v == "false":
                    v = False
                meta[k.strip()] = v

    return meta, prompt


# ── Shared Context ────────────────────────────────────────────────────────────

def load_shared_context() -> dict:
    """Laedt user_profile.md und project_context.md aus prompts/shared/."""
    shared = {}
    for name in ["user_profile", "project_context"]:
        path = PROMPTS_DIR / "shared" / f"{name}.md"
        if path.exists():
            shared[name] = path.read_text(encoding="utf-8").strip()
        else:
            shared[name] = ""
    return shared


def inject_shared(prompt: str, shared: dict) -> str:
    """Ersetzt {{ user_profile }} und {{ project_context }} im Prompt."""
    for key, value in shared.items():
        prompt = prompt.replace(f"{{{{ {key} }}}}", value)
    return prompt


# ── Agent Metadata ────────────────────────────────────────────────────────────

def load_agent_meta(agent_name: str) -> tuple[dict, str]:
    """Laedt Frontmatter und Prompt fuer einen Agenten."""
    path = PROMPTS_DIR / "agents" / f"{agent_name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Agent-Prompt nicht gefunden: {path}")
    content = path.read_text(encoding="utf-8")
    return parse_frontmatter(content)


def list_agents() -> list[dict]:
    """Listet alle verfuegbaren Agenten aus prompts/agents/*.md."""
    agents = []
    agents_dir = PROMPTS_DIR / "agents"
    if not agents_dir.exists():
        return agents
    for md_file in sorted(agents_dir.glob("*.md")):
        if md_file.stem == "router":
            continue
        try:
            meta, _ = parse_frontmatter(md_file.read_text(encoding="utf-8"))
            if meta.get("name"):
                agents.append(meta)
        except Exception:
            pass
    return agents


# ── Router Prompt ─────────────────────────────────────────────────────────────

def build_router_prompt(agents: Optional[list] = None) -> str:
    """
    Baut den Router-Prompt dynamisch aus den Agent-Beschreibungen.
    Laedt zuerst router.md als Template, dann fuegt Agent-Beschreibungen ein.
    """
    if agents is None:
        agents = list_agents()

    # router.md als Basis laden
    router_path = PROMPTS_DIR / "agents" / "router.md"
    if router_path.exists():
        _, base_prompt = parse_frontmatter(router_path.read_text(encoding="utf-8"))
    else:
        base_prompt = "Classify the request into EXACTLY ONE category.\n\n"

    # Agent-Beschreibungen dynamisch anhaengen wenn Placeholder vorhanden
    if "{{ agents }}" in base_prompt:
        agent_lines = "\n".join(
            f"- {a['name']}: {a.get('description', '')}"
            for a in agents
        )
        base_prompt = base_prompt.replace("{{ agents }}", agent_lines)

    return base_prompt


# ── Agent Builder ─────────────────────────────────────────────────────────────

def load_agent(agent_name: str, shared: Optional[dict] = None):
    """
    Laedt einen Agenten aus seiner .md Datei.
    Gibt (meta, system_prompt) zurueck.

    Fuer reine Text-Agenten (comms, code) kann agent_loader
    direkt einen LangChain ChatOpenAI bauen.
    Fuer Logik-Agenten (notes, researcher, handoff) gibt es
    nur meta + prompt zurueck — die Python-Datei baut den Agent selbst.
    """
    if shared is None:
        shared = load_shared_context()

    meta, prompt = load_agent_meta(agent_name)
    prompt = inject_shared(prompt, shared)

    return meta, prompt


def build_llm(meta: dict):
    """Baut einen ChatOpenAI LLM aus Agent-Metadaten."""
    import config
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=f"{config.LITELLM_URL}/v1",
        api_key=config.LITELLM_KEY,
        model=meta.get("model") or config.DEFAULT_LLM,
        temperature=meta.get("temperature", 0.3),
        max_tokens=1024,
    )


def build_simple_agent(agent_name: str, shared: Optional[dict] = None):
    """
    Baut einen einfachen Agenten (kein RAG, keine custom Tools)
    direkt aus der .md Datei — fuer comms und code.
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    meta, system_prompt = load_agent(agent_name, shared)
    llm = build_llm(meta)

    async def invoke(user_message: str, lang: str = "en") -> str:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = await llm.ainvoke(messages)
        return response.content

    return invoke


# ── Self-Test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== agent_loader.py Self-Test ===\n")

    # Shared Context
    shared = load_shared_context()
    print(f"Shared Context geladen:")
    print(f"  user_profile: {len(shared['user_profile'])} Zeichen")
    print(f"  project_context: {len(shared['project_context'])} Zeichen")

    # Alle Agenten listen
    agents = list_agents()
    print(f"\nVerfuegbare Agenten ({len(agents)}):")
    for a in agents:
        print(f"  - {a['name']}: {a.get('description', '')[:60]}")

    # Router-Prompt aufbauen
    router = build_router_prompt(agents)
    print(f"\nRouter-Prompt ({len(router)} Zeichen):")
    print(router[:300])

    # Einzelnen Agenten laden
    meta, prompt = load_agent("comms", shared)
    print(f"\nComms Agent geladen:")
    print(f"  Meta: {meta}")
    print(f"  Prompt (erste 200 Zeichen): {prompt[:200]}")
