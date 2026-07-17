"""
Test: tool_formatter.py
Testet alle Modell-Familien und den Parser.
"""
import sys, json
sys.path.insert(0, '/home/claude/la/agents/server')

from tool_formatter import (
    detect_model_family,
    format_tools_for_model,
    parse_tool_call_from_response,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Show git commit history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "max_count": {"type": "integer", "default": 5}
                },
                "required": ["repo_path"]
            }
        }
    }
]

results = []

def test(name, condition, detail=""):
    status = "✓" if condition else "✗"
    results.append((status, name, detail))
    print(f"{status} {name}", f"  {detail}" if detail else "", flush=True)

print("=== TEST: tool_formatter.py ===\n", flush=True)

# 1. Modell-Familie Erkennung
test("detect granite-tiny", detect_model_family("granite-tiny") == "granite")
test("detect Qwen3.5-4B",  detect_model_family("Qwen3.5-4B") == "qwen")
test("detect llama-3.1",   detect_model_family("llama-3.1-8B") == "llama")
test("detect unknown",     detect_model_family("unknown-model") == "default")

# 2. Granite Format
granite_prompt = format_tools_for_model(TOOLS, model_name="granite-tiny")
test("granite: nicht None",       granite_prompt is not None)
test("granite: <tools> vorhanden", "<tools>" in granite_prompt)
test("granite: <tool_call> Hinweis", "<tool_call>" in granite_prompt)
test("granite: git_log enthalten",  "git_log" in granite_prompt)

# 3. Qwen Format
qwen_prompt = format_tools_for_model(TOOLS, model_name="Qwen3.5-4B")
test("qwen: nicht None",      qwen_prompt is not None)
test("qwen: <tools> vorhanden", "<tools>" in qwen_prompt)
test("qwen: git_log enthalten", "git_log" in qwen_prompt)

# 4. Default (OpenAI pass-through)
default_prompt = format_tools_for_model(TOOLS, model_name="gpt-4")
test("default: None (pass-through)", default_prompt is None)

# 5. Leere Tools
empty_prompt = format_tools_for_model([], model_name="granite-tiny")
test("leere tools: None", empty_prompt is None)

# 6. Explizite Familie
explicit = format_tools_for_model(TOOLS, model_family="granite")
test("explizite Familie granite", "<tools>" in explicit)

# 7. Tool-Call Parser
granite_response = '''
Ich werde git_log aufrufen.
<tool_call>
{"name": "git_log", "arguments": {"repo_path": "/home/user/chief/la", "max_count": 3}}
</tool_call>
'''
parsed = parse_tool_call_from_response(granite_response, model_family="granite")
test("granite parser: nicht None",       parsed is not None)
test("granite parser: name korrekt",     parsed and parsed.get("name") == "git_log")
test("granite parser: args korrekt",     parsed and parsed.get("arguments", {}).get("max_count") == 3)

# 8. Parser mit leerem Response
empty_parsed = parse_tool_call_from_response("Keine tool_call hier", model_family="granite")
test("parser: None bei fehlendem Tag", empty_parsed is None)

print(f"\n=== ERGEBNIS: {sum(1 for s,_,_ in results if s=='✓')}/{len(results)} OK ===")
