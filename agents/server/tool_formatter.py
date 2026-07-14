"""
Generic Tool Formatter — janhet Edition

Übersetzt OpenAI tool-call Format in das native Chat-Template Format
des jeweiligen Modells. Sitzt zwischen LangChain und LiteLLM.

Unterstützte Modelle:
- granite   → <tools>...</tools> / <tool_call>...</tool_call> XML Format
- qwen      → ChatML mit <tool_call> Tags  
- llama     → Python function call Format
- default   → OpenAI Format (pass-through)

Verwendung in telemetry.py:
    from tool_formatter import format_tools_for_model
    system = format_tools_for_model(tools, model_family="granite")
"""

import json
from typing import List, Dict, Any, Optional

# ── Modell-Familie Erkennung ─────────────────────────────────────
MODEL_FAMILIES = {
    "granite":  ["granite", "ibm"],
    "qwen":     ["qwen"],
    "llama":    ["llama", "meta"],
    "mistral":  ["mistral", "mixtral"],
}

def detect_model_family(model_name: str) -> str:
    """Erkennt die Modell-Familie anhand des Namens."""
    name_lower = model_name.lower()
    for family, keywords in MODEL_FAMILIES.items():
        if any(kw in name_lower for kw in keywords):
            return family
    return "default"


# ── Granite Format ───────────────────────────────────────────────
def _granite_system_prompt(tools: List[Dict]) -> str:
    """
    Granite 4.0 natives Tool-Format.
    Quelle: https://huggingface.co/ibm-granite/granite-4.0-h-350M
    """
    tools_json = "\n".join(json.dumps(t) for t in tools)
    return (
        "You are a helpful assistant with access to the following tools. "
        "You may call one or more tools to assist with the user query.\n\n"
        "You are provided with function signatures within <tools></tools> XML tags:\n"
        f"<tools>\n{tools_json}\n</tools>\n\n"
        "For each tool call, return a json object with function name and arguments "
        "within <tool_call></tool_call> XML tags:\n"
        "<tool_call>\n"
        '{"name": <function-name>, "arguments": <args-json-object>}\n'
        "</tool_call>. "
        "If a tool does not exist in the provided list of tools, notify the user "
        "that you do not have the ability to fulfill the request."
    )


# ── Qwen Format ──────────────────────────────────────────────────
def _qwen_system_prompt(tools: List[Dict]) -> str:
    """Qwen natives Tool-Format (ChatML)."""
    tools_json = "\n".join(json.dumps(t, ensure_ascii=False) for t in tools)
    return (
        "You are a helpful assistant.\n\n"
        "# Tools\n\n"
        "You may call one or more functions to assist with the user query.\n\n"
        f"<tools>\n{tools_json}\n</tools>"
    )


# ── Llama Format ─────────────────────────────────────────────────
def _llama_system_prompt(tools: List[Dict]) -> str:
    """Llama 3.x natives Tool-Format."""
    tools_json = json.dumps(tools, indent=2, ensure_ascii=False)
    return (
        "You are a helpful assistant with tool access.\n\n"
        f"You have access to the following functions:\n{tools_json}\n\n"
        "To call a function, respond with JSON in this format:\n"
        '{"name": "function_name", "parameters": {"key": "value"}}'
    )


# ── Default (OpenAI pass-through) ────────────────────────────────
def _default_system_prompt(tools: List[Dict]) -> Optional[str]:
    """OpenAI Format — kein Custom System Prompt nötig."""
    return None


# ── Öffentliche API ──────────────────────────────────────────────
FORMATTERS = {
    "granite": _granite_system_prompt,
    "qwen":    _qwen_system_prompt,
    "llama":   _llama_system_prompt,
    "default": _default_system_prompt,
}

def format_tools_for_model(
    tools: List[Dict],
    model_name: str = "",
    model_family: Optional[str] = None,
) -> Optional[str]:
    """
    Gibt einen System-Prompt zurück der die Tools im nativen Format
    des Modells einbettet. None = OpenAI pass-through (bind_tools reicht).
    
    Args:
        tools:        Liste von OpenAI-Format Tool-Definitionen
        model_name:   Modell-Name zur automatischen Familie-Erkennung
        model_family: Explizite Familie (überschreibt Erkennung)
    
    Returns:
        System-Prompt String oder None für OpenAI pass-through
    """
    if not tools:
        return None
    
    family = model_family or detect_model_family(model_name)
    formatter = FORMATTERS.get(family, _default_system_prompt)
    return formatter(tools)


def parse_tool_call_from_response(
    response_text: str,
    model_family: str = "default",
) -> Optional[Dict]:
    """
    Parst einen Tool-Call aus der Modell-Antwort zurück ins
    OpenAI-kompatible Format.
    
    Für Granite: extrahiert <tool_call>...</tool_call>
    Für andere: pass-through (LiteLLM/LangChain parst selbst)
    """
    if model_family == "granite":
        import re
        match = re.search(
            r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
            response_text,
            re.DOTALL,
        )
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
    return None
