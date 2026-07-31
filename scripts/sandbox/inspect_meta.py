"""
inspect_meta.py -- Diagnose-Skript fuer den Meta-Agent-Pfad

Local Agent (LA) -- Sandbox Edition

Testet direkt ob das 350m-Modell den META_REFORMULATION_PROMPT
sinnvoll beantworten kann -- ohne LiteLLM, ohne Agent Server.

Drei Tests:
  A: Voller Prompt, default max_tokens
  B: Voller Prompt, max_tokens=512
  C: Gekuerzter Prompt, max_tokens=512

Ablauf:
  1. llama-server :8080 starten (nur --jinja --ctx-size 32768)
  2. Inference-Readiness-Check abwarten
  3. Test A/B/C -- direkter POST an :8080/v1/chat/completions
  4. Output nach /tmp/inspect_meta_output.txt
  5. Push nach docs/traces/sandbox/ via GH_TOKEN

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/inspect_meta.py

Umgebungsvariablen:
  MODEL_PATH  (default: /tmp/granite-350m-Q4_K_M.gguf)
  GH_TOKEN    (Push nach docs/traces/sandbox/ -- optional)
"""
import time, urllib.request, json, subprocess, sys, os, base64
from datetime import datetime
from pathlib import Path

def load_inspect_config() -> dict:
    """Laedt inspect_config.json aus dem Skript-Verzeichnis.
    Gibt leeres Dict zurueck wenn Datei fehlt oder nicht parsebar.
    """
    cfg_path = Path(__file__).parent / "inspect_config.json"
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

# Konfiguration
MODEL_PATH = os.getenv("MODEL_PATH", "/tmp/granite-350m-Q4_K_M.gguf")
GH_TOKEN   = os.getenv("GH_TOKEN",   "")
LOG_DIR    = "/tmp/logs"
LLAMA_URL  = "http://127.0.0.1:8080/v1/chat/completions"

os.makedirs(LOG_DIR, exist_ok=True)

# Ausgabe-Puffer
output_lines = []

def log(msg: str) -> None:
    """Gibt Nachricht auf Konsole aus und puffert sie fuer die Ausgabedatei."""
    print(msg, flush=True)
    output_lines.append(str(msg))


def wait_for(url: str, label: str, retries: int = 40) -> bool:
    """Wartet bis ein HTTP-Endpunkt antwortet."""
    for i in range(retries):
        try:
            urllib.request.urlopen(url, timeout=2)
            log(f"{label} OK")
            return True
        except Exception:
            time.sleep(1)
            print(f"{i+1}...", end=" ", flush=True)
    log(f"{label} TIMEOUT")
    return False


# ===== Prompts aus supervisor.py (identisch kopiert) =====

SYSTEM_FACTS = """You are the user's personal Local Agent -- a 100% local multi-agent orchestrator running on their local server.

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

FULL_PROMPT = META_REFORMULATION_PROMPT.format(
    facts=SYSTEM_FACTS,
    user_message="What can you do?",
    language="English",
)

SHORT_PROMPT = """You are a local AI assistant with 5 agents: Researcher, Comms, Notes, Code, Handoff.
You run 100% locally.

User's question: What can you do?

Respond in English with a short markdown overview. End with "What can I do for you?"."""


# Tests aus inspect_config.json laden (Fallback: hardcodierte Defaults)
_cfg_meta = load_inspect_config().get("meta", {})
PROMPT_MAP = {"full": FULL_PROMPT, "short": SHORT_PROMPT}
TESTS = _cfg_meta.get("tests", [
    {"label": "A", "prompt": "full",  "max_tokens": None},
    {"label": "B", "prompt": "full",  "max_tokens": 512},
    {"label": "C", "prompt": "short", "max_tokens": 512},
])

# ===== llama-server starten =====
LLAMA_BIN = "/tmp/llama-b9895/llama-server"
LLAMA_LOG = os.path.join(LOG_DIR, "llama-server.log")

log("=== inspect_meta.py ===")
log(f"Modell: {MODEL_PATH}")
log("")

llama_proc = subprocess.Popen(
    [LLAMA_BIN, "-m", MODEL_PATH,
     "--host", "127.0.0.1", "--port", "8080",
     "--jinja", "--ctx-size", "32768",
     "--parallel", "1", "--log-disable"],
    stdout=open(LLAMA_LOG, "w"), stderr=subprocess.STDOUT
)
wait_for("http://127.0.0.1:8080/v1/models", "llama-server", retries=40)

# Inference-Readiness-Check
log("Warte auf Inference-Bereitschaft...")
for _i in range(20):
    try:
        _req = urllib.request.Request(
            LLAMA_URL,
            data=json.dumps({
                "model": "granite",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(_req, timeout=15)
        log("llama-server Inference OK")
        break
    except Exception:
        time.sleep(2)
        print(f"{_i+1}...", end=" ", flush=True)
else:
    log("llama-server Inference TIMEOUT -- Abbruch")
    llama_proc.terminate()
    sys.exit(1)


# ===== Hilfsfunktion: POST an llama-server =====
def run_test(label: str, system_prompt: str, max_tokens=None) -> dict:
    """Schickt einen direkten POST an llama-server und gibt Ergebnis-Dict zurueck."""
    log(f"\n=== TEST {label} ===")
    payload = {
        "model": "granite",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "What can you do?"}
        ],
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    log(f"max_tokens:    {max_tokens if max_tokens is not None else '(default)'}")
    log(f"Prompt-Laenge: {len(system_prompt)} Zeichen")

    t0 = time.time()
    try:
        req = urllib.request.Request(
            LLAMA_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        r = urllib.request.urlopen(req, timeout=120)
        resp = json.loads(r.read())
    except Exception as e:
        log(f"FEHLER: {e}")
        return {"label": label, "error": str(e)}

    elapsed = time.time() - t0
    choice       = resp["choices"][0]
    content      = choice["message"]["content"]
    finish       = choice.get("finish_reason", "?")
    usage        = resp.get("usage", {})
    prompt_tok   = usage.get("prompt_tokens", "?")
    compl_tok    = usage.get("completion_tokens", "?")

    log(f"Dauer:              {elapsed:.1f}s")
    log(f"finish_reason:      {finish}")
    log(f"prompt_tokens:      {prompt_tok}")
    log(f"completion_tokens:  {compl_tok}")
    log(f"Antwortlaenge:      {len(content)} Zeichen")
    log(f"\nRohe Antwort:\n{content}")

    return {
        "label": label,
        "max_tokens": max_tokens,
        "prompt_len": len(system_prompt),
        "elapsed": round(elapsed, 1),
        "finish_reason": finish,
        "prompt_tokens": prompt_tok,
        "completion_tokens": compl_tok,
        "response_len": len(content),
        "response": content,
    }


# ===== Tests A / B / C =====
t_start = time.time()

# Tests aus TESTS-Liste ausfuehren (konfigurierbar via inspect_config.json)
test_results = []
for _t in TESTS:
    _prompt_text = PROMPT_MAP.get(_t.get("prompt", "full"), FULL_PROMPT)
    _label = f"{_t['label']} -- {'Voller' if _t.get('prompt') == 'full' else 'Gekuerzter'} Prompt"
    if _t.get("max_tokens") is not None:
        _label += f", max_tokens={_t['max_tokens']}"
    else:
        _label += ", default max_tokens"
    test_results.append(run_test(_label, _prompt_text, max_tokens=_t.get("max_tokens")))

result_a = test_results[0] if len(test_results) > 0 else {}
result_b = test_results[1] if len(test_results) > 1 else {}
result_c = test_results[2] if len(test_results) > 2 else {}

# ===== Zusammenfassung =====
log("\n=== ZUSAMMENFASSUNG ===")
log(f"{'Test':<40} {'max_tok':>8} {'p_tok':>6} {'c_tok':>6} {'finish':<12} {'len':>6}")
log("-" * 82)
for r in test_results:
    if "error" in r:
        log(f"{r['label']:<40} FEHLER: {r['error']}")
    else:
        log(f"{r['label']:<40} {str(r['max_tokens']):>8} {str(r['prompt_tokens']):>6} "
            f"{str(r['completion_tokens']):>6} {r['finish_reason']:<12} {r['response_len']:>6}")

# ===== Output-Datei =====
output_path = Path("/tmp/inspect_meta_output.txt")
full_output = "\n".join(output_lines)
output_path.write_text(full_output, encoding="utf-8")
log(f"\nOutput gespeichert: {output_path}")

# ===== Trace-MD aufbauen =====
date_str = datetime.now().strftime("%Y-%m-%d")

def md_result(r: dict) -> str:
    if "error" in r:
        return f"**FEHLER:** {r['error']}"
    return (
        f"| max_tokens | {r['max_tokens'] if r['max_tokens'] else 'default'} |\n"
        f"| Prompt-Laenge | {r['prompt_len']} Zeichen |\n"
        f"| prompt_tokens | {r['prompt_tokens']} |\n"
        f"| completion_tokens | {r['completion_tokens']} |\n"
        f"| finish_reason | {r['finish_reason']} |\n"
        f"| Antwortlaenge | {r['response_len']} Zeichen |\n"
        f"| Dauer | {r['elapsed']}s |\n"
        f"\n**Rohe Antwort:**\n```\n{r['response']}\n```"
    )

trace_content = f"""# Meta-Agent Diagnose -- {date_str}

**Modell:** granite-350m-Q4_K_M
**Stack:** llama-server :8080 direkt (kein LiteLLM)
**Gesamtdauer:** {round(time.time()-t_start, 1)}s

---

## Test A -- Voller Prompt, default max_tokens

{md_result(result_a)}

---

## Test B -- Voller Prompt, max_tokens=512

{md_result(result_b)}

---

## Test C -- Gekuerzter Prompt, max_tokens=512

{md_result(result_c)}

---

## Zusammenfassung

| Test | max_tokens | prompt_tokens | completion_tokens | finish_reason | Antwortlaenge |
|------|-----------|--------------|------------------|---------------|--------------|
| A | {result_a.get('max_tokens', 'err')} | {result_a.get('prompt_tokens', 'err')} | {result_a.get('completion_tokens', 'err')} | {result_a.get('finish_reason', 'err')} | {result_a.get('response_len', 'err')} |
| B | {result_b.get('max_tokens', 'err')} | {result_b.get('prompt_tokens', 'err')} | {result_b.get('completion_tokens', 'err')} | {result_b.get('finish_reason', 'err')} | {result_b.get('response_len', 'err')} |
| C | {result_c.get('max_tokens', 'err')} | {result_c.get('prompt_tokens', 'err')} | {result_c.get('completion_tokens', 'err')} | {result_c.get('finish_reason', 'err')} | {result_c.get('response_len', 'err')} |

---

## Konsolen-Output (komplett)

```
{full_output}
```
"""

# ===== Push nach docs/traces/sandbox/ =====
trace_filename  = f"{date_str}_inspect-meta.md"
trace_repo_path = f"docs/traces/sandbox/{trace_filename}"

if GH_TOKEN:
    log(f"Pushe {trace_repo_path} nach GitHub...")
    try:
        existing_sha = None
        try:
            chk = urllib.request.Request(
                f"https://api.github.com/repos/janhetzler/la/contents/{trace_repo_path}",
                headers={"Authorization": f"Bearer {GH_TOKEN}",
                         "Accept": "application/vnd.github+json"}
            )
            existing_sha = json.loads(urllib.request.urlopen(chk).read()).get("sha")
        except Exception:
            pass

        push_payload: dict = {
            "message": f"trace: Meta-Agent inspect run {date_str}",
            "content": base64.b64encode(trace_content.encode("utf-8")).decode("ascii"),
        }
        if existing_sha:
            push_payload["sha"] = existing_sha

        push_req = urllib.request.Request(
            f"https://api.github.com/repos/janhetzler/la/contents/{trace_repo_path}",
            data=json.dumps(push_payload).encode("utf-8"),
            method="PUT",
            headers={"Authorization": f"Bearer {GH_TOKEN}",
                     "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json"}
        )
        push_result = json.loads(urllib.request.urlopen(push_req).read())
        log(f"Push OK: {push_result['commit']['sha'][:8]} -> {trace_repo_path}")
    except Exception as e:
        log(f"Push FAIL: {e}")
else:
    log("GH_TOKEN nicht gesetzt -- kein Push.")

# Cleanup
llama_proc.terminate()
log("llama-server gestoppt.")
