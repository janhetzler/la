---
type: Reference
status: current
updated_at: 2026-07-31
stale_after: 2027-01-31
environment: all
components: [llama-server]
---
# MODELS.md — Modell-Wissen und Erkenntnisse

Dieses Dokument fasst zusammen was wir ueber die eingesetzten Modelle
wissen — aus Herstellerdokumentation, Praxistests und eigenen Traces.

---

## Granite 4.0-H-350M (aktuell in Sandbox)

**Modell:** `granite-4.0-h-350m-Q4_K_M.gguf` (213 MB)
**Hersteller:** IBM Research
**Lizenz:** Apache 2.0
**Architektur:** Dense-Hybrid — wechselt zwischen Mamba State Space Blocks
(Layer 0-9, 11-12, 14-16) und Grouped Query Attention (Layer 10, 13, 17-27)
plus Sparse Mixture of Experts. 768-dim Embeddings, 32 Decoder-Layer.

### Tool-Calling

**BFCL v3 Score:** 43.32 (Benchmark unter optimalen Bedingungen)

**Natives Format** laut IBM HuggingFace Modellcard:
```
<tool_call>
{"name": "tool_name", "arguments": {"param": "value"}}
</tool_call>
```

**Wichtig:** IBM demonstriert Tool-Calling direkt via `apply_chat_template`
mit Transformers — nicht ueber einen API-Stack. In unserem Stack
(llama-server → LiteLLM → LangChain) gibt es mehrere Schichten die
das native Format abfangen muessen.

**Erkenntnisse aus unseren Traces (2026-07-30/31):**
- Modell produziert korrekte `<tool_call>`-Bloecke
- `arguments` wird haeufig als JSON-String statt JSON-Objekt uebergeben:
  `"arguments": "{\"text\": \"...\"}"` statt `"arguments": {"text": "..."}`
- Schließendes `</tool_call>` fehlt manchmal (finish_reason: stop mitten im Tag)
- Beide Probleme sind in `tool_formatter.py` gefixt (Commit 1f297d3d)
- Nach Fix: Tool-Calling funktioniert zuverlaessig (BUG-019 behoben)

**LLM-Routing:** Funktioniert korrekt mit Grammar Constraint
(`root ::= "comms" | "researcher" | ...`). Router gibt saubere
Einwort-Antworten. 2 Completion-Tokens pro Routing-Entscheidung.

### Staerken

- Instruction Following (IFEval Average: 61.63)
- Tool-Calling mit korrektem Format wenn Stack korrekt konfiguriert
- Schnell: ~27 t/s auf Sandbox-CPU
- Multilingual: 12 Sprachen inkl. Deutsch (Uebersetzungsqualitaet variiert)
- Summarization und Workflow Automation (IBM-Empfehlung)
- Embeddings via `--embeddings --pooling mean`: 768-dim

### Grenzen

- Komplexes Multi-Step Reasoning eingeschraenkt
- Meta-Agent gibt zu kurze Antworten (BUG-024, in Untersuchung)
- Nicht geeignet fuer Long-Form Writing oder Deep Analysis

### IBM Positionierung

Laut IBM Developer Tutorial: Granite Nano explizit fuer
**Summarization und Workflow Automation** — kombiniert mit staerkeren
Modellen (Claude Sonnet, GPT-120B) fuer komplexes Reasoning.
Unser Ansatz entspricht genau dieser Empfehlung:
- 350m fuer einfache Agent-Tasks in der Sandbox
- Granite-Tiny 4B auf dem Host fuer Tool-Calling und Routing

### Chat Template (offiziell, laut IBM Prompt Engineering Guide)

Granite 4.0 verwendet folgende Sonderzeichen:
- `<|start_of_role|>`, `<|end_of_role|>`, `<|end_of_text|>` — Role-Control-Tags
- Tools werden automatisch im System-Prompt zwischen `<tools>` und `</tools>` eingebettet
- Tool-Calls kommen als `<tool_call>...</tool_call>` im Assistant-Turn
- Tool-Responses kommen als `<tool_response>...</tool_response>` im User-Turn

**Bestätigt:** `notes.py` verwendet HumanMessage mit `<tool_response>` Tags —
das entspricht exakt dem offiziellen Chat-Template. Unser Stack ist korrekt.

**Wichtig fuer llama-server:** `--jinja` Flag aktiviert das native Chat-Template.
Ohne `--jinja` werden die Sonderzeichen nicht korrekt verarbeitet.

**Tool-Response Format (offiziell):**
```
<|start_of_role|>user<|end_of_role|>
<tool_response>
{"result": "Notiz gespeichert"}
</tool_response>
<|end_of_text|>
```

### Quellen

- IBM HuggingFace Modellcard: https://huggingface.co/ibm-granite/granite-4.0-h-350M
- IBM GitHub README: https://github.com/ibm-granite/granite-4.0-nano-language-models
- IBM Developer Tutorial: https://developer.ibm.com/learningpaths/watsonx-orchestrate-multiagent-orchestration/combnine-groq-anthropic-granite/
- YouTube Praxistest (Fahd Mirza): https://www.youtube.com/watch?v=bGpzgRJHZOQ
- Eigene Traces: docs/traces/sandbox/ (2026-07-30/31)

---

## Granite-Embedding-30M (Sandbox Port 8081)

**Modell:** `granite-embedding-30m-english-Q4_0.gguf` (28 MB)
**Zweck:** Spezialisiertes Embedding-Modell fuer ChromaDB-Writes
**Port:** 8081 (separater llama-server, seit Commit f4cfa01f)

**Erkenntnisse:**
- Liefert zuverlaessige Embeddings fuer ChromaDB
- Kein Reasoning, kein Chat — nur `/v1/embeddings` Endpoint
- `--embeddings --pooling mean` Flags erforderlich
- LiteLLM `granite-embed` zeigt auf Port 8081

---

## Granite-4.0-H-Tiny 4B (geplant fuer Host)

**Status:** Noch nicht in Sandbox getestet, auf Host geplant
**Bewiesen:** Tool-Calling funktioniert zuverlaessig (in cptr/HuggingFace Space getestet)
**Zweck:** Ersetzt 350m als Reasoning-Modell auf dem Host (janhet)

**Erwartete Verbesserungen gegenueber 350m:**
- Zuverlaessiges Tool-Calling ohne Parser-Workarounds
- Besseres Multi-Step Reasoning
- Stabileres Routing ohne Grammar Constraint

---

## Verwandt

- [LLAMA.md](LLAMA.md) — llama-server Binary Dokumentation
- [ROADMAP.md](ROADMAP.md) — Architektur-Entscheidungen
- [BUGS.md](../BUGS.md) — BUG-019, BUG-024
- [docs/traces/sandbox/](traces/sandbox/) — Phoenix Traces
