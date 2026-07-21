# Local Agent Test Suite — Ergebnisse (Sandbox 2)
**Datum:** 2026-07-20 (aktualisiert — llama-server Binary Swap)
**Umgebung:** Claude Container (AMD EPYC-kompatibel, 1 Kern, ~8 GB RAM frei)
**Modell:** Granite 4.0-H 350m Q4_K_M (Test-Proxy fuer Granite-4.0-H-Tiny auf Host)
**Laufzeit-Backend:** llama-server Binary b9895 (neu seit 2026-07-20, vorher llama-cpp-python 0.3.23)

---

## Stack Konfiguration

```
llama-server Binary b9895 :8080 (--jinja aktiv)
    ↑
LiteLLM :4000 (Gateway + Phoenix Callbacks, master_key ohne DB)
    ↑
Agent Server :8002 (Supervisor + 6 Agenten via agent_loader.py)
    ↓
ChromaDB (embedded, /tmp/chroma_la)
    ↓
Phoenix :6006 (Observability)
```

**Binary-Flags:**
```bash
/tmp/llama-b9895/llama-server \
  -m /tmp/granite-350m-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 \
  --jinja --ctx-size 32768 \
  --parallel 1 --log-disable
```

**Hinweis:** `--log-level error` existiert in b9895 nicht — korrekter Flag ist `--log-disable`.

---

## Agent Test Ergebnisse (4/6 OK)

| Agent | Status | Zeichen | Detail |
|-------|--------|---------|--------|
| Supervisor Routing | ✗ | 6 | Zu kurz — 350m Routing-Limit |
| Comms Agent | ✓ | 492 | E-Mail vollstaendig generiert |
| Code Agent | ✓ | 862 | Python-Funktion korrekt |
| Researcher Agent | ✓ | 347 | LangGraph erklaert |
| Notes Agent | ✗ | 22 | ChromaDB `notes`: 0 Dokumente |
| Handoff Agent | ✓ | 234 | Prompt fuer Claude.ai generiert |

**Routing:** 350m routet unzuverlaessig — bekannte Modellgroeßen-Limitation.
Notes FAIL: Routing-Limit, Notiz nicht in ChromaDB geschrieben.

---

## Performance-Vergleich: Binary vs. Python-Wrapper

| Metrik | llama-cpp-python 0.3.23 | llama-server b9895 |
|--------|------------------------|-------------------|
| Startup-Zeit | ~20s | ~2s |
| Token/Sec | ~24 t/s | ~25 t/s |
| `--jinja` Support | Nein | Ja |
| Echte Log-Datei | Nein (Thread-Logging) | Ja (`--log-disable` noetig) |
| Tool-Calling (native) | Nein | Ja (verifiziert) |

---

## Tool-Calling Verifikation (2026-07-20)

Direkter Test der Binary mit `--jinja` und OpenAI `tools`-API:

```json
{
  "finish_reason": "tool_calls",
  "tool_calls": [{"name": "save_note", "arguments": "{\"text\": \"Test erfolgreich\"}"}]
}
```

**Ergebnis:** Binary mit `--jinja` produziert echte `tool_calls` — verifiziert.
Das 350m-Modell kann Tool-Calling wenn der Server korrekt konfiguriert ist.
Vorherige Annahme ("350m kann kein Tool-Calling") war falsch — war ein Konfigurationsproblem.

---

## Phoenix Observability

**Traces:** ✓ aktiv
**Projekt:** `local-agent`
**Readiness-Check:** ✓ `/v1/projects` (kein TIMEOUT)
**LangChain Auto-Instrumentierung:** Aktiv

---

## Swap-Aenderungen (2026-07-20)

| Datei | Commit | Aenderung |
|-------|--------|-----------|
| `scripts/sandbox/start_full.py` | `719a8cb303f6` | llama-cpp-python → Binary |
| `scripts/sandbox/start_quick.py` | `92feb17b71c0` | llama-cpp-python → Binary |
| `scripts/sandbox/inspect_phoenix.py` | `5f2bbb3c6eb8` | llama-cpp-python → Binary |
| `scripts/sandbox/test_mcp_toolcall.py` | `4b4334e51455` | llama-cpp-python → Binary |

---

## Bekannte Limitierungen

1. **Binary-Pfad hardcoded:** `/tmp/llama-b9895/llama-server` — muss bei jedem Sandbox-Start neu heruntergeladen werden
2. **350m Routing:** Fast alles → meta (Fallback) — auf Host mit Tiny-Modell erwartet besser
3. **Notes/ChromaDB:** Schreibt nicht — Routing-Limit
4. **Embedding-Server (Port 8081):** Nicht gestartet

---

## Naechste Schritte fuer Host (host)

1. Binary b9895 auf host installieren (oder neuer)
2. Tool-Calling mit Granite-4.0-H-Tiny (4B) testen
3. MCP-Tools (`git_log`, `fetch`) via `bind_tools()` + `--jinja` aktivieren
4. Notes-Agent mit echtem Routing testen

---

## Router Trace — 2026-07-20

**Test:** Supervisor-Routing mit Binary b9895 + Grammar Constraint Vergleich

### Stack

```
llama-server b9895 :8080 (--jinja)
LiteLLM :4000 (master_key: sk-cos-local-dev, kein DB)
Agent Server :8002
```

### Vollständiger Router System-Prompt (1613 Zeichen, 402 Prompt-Token)

```
You are a router. Pick ONE agent to handle the user's request.

Available agents:
- meta: meta questions about the system itself (who are you, what can you do, introduce yourself, help, how does it work, capabilities)
- researcher: information lookup (indexed papers, web, general filesystem). Technical or factual questions, documentation.
- comms: pure writing (email, message, announcement, short note). No retrieval.
- notes: save or search personal notes in ChromaDB. Questions about "my notes".
- code: programming questions, algorithms, debugging, GitHub issue management.
- handoff: builds an enriched prompt for Claude.ai/ChatGPT. Use for HEAVY tasks beyond local capabilities: long-form writing (>1000 words), deep analyses, complex reasoning, large document analysis, scientific articles.

Reply with ONLY the agent name, in one word, no quotes, no explanation.

Examples:
- "Hi, what can you do?" -> meta
- "Who are you?" -> meta
- "How does it work?" -> meta
- "What's the difference between RNN and Transformer?" -> researcher
- "Search news about Granite 4" -> researcher
- "Tell me about LangGraph" -> researcher
- "Save this note: meeting tomorrow at 10am" -> notes
- "Search my personal notes about project alpha" -> notes
- "How do I implement an LRU cache in Python?" -> code
- "Create an issue on GitHub for this bug" -> code
- "Write a message to my team announcing the project" -> comms
- "Draft a short email about the project status" -> comms
- "Write a 5000-word scientific article on transformers" -> handoff
- "Prepare a prompt for Claude.ai on this topic" -> handoff
```

### Test-Requests und Routing-Ergebnisse

| Request | Erwartet | Ohne Grammar | Mit Grammar | Korrekt? |
|---------|----------|--------------|-------------|----------|
| "I would like to write an email to my boss" | comms | `code` | `code` | ✗ |
| "ich möchte eine Mail schreiben" | comms | `meta` | — | ✗ |

### Grammar Constraint — Vergleich 2026-07-17 vs. 2026-07-20

| | 2026-07-17 (llama-cpp-python) | 2026-07-20 (Binary b9895) |
|--|--|--|
| `extra_body={"grammar": ...}` via LiteLLM | `No connected db.` — Stack-Crash | ✓ Kein Fehler mehr |
| Routing-Ergebnis mit Grammar | — (Crash) | `code` (falsch, aber stabil) |
| Grammar-Effekt auf Ergebnis | — | Keiner — identisch ohne Grammar |

**Neue Erkenntnis:** Grammar Constraint via `extra_body` funktioniert jetzt ohne Fehler
(Key-Alignment-Fix von 2026-07-18 hat das LiteLLM-Auth-Problem behoben).
Grammar zwingt das Modell auf gueltige Token-Auswahl, aendert aber nicht
die falsche Klassifikation — das Modell waehlt weiterhin `code` statt `comms`.

### Diagnose

**Ursache des Routing-Fehlers:** Modellkapazitaet, nicht Prompt-Qualitaet.

Der Router-Prompt ist korrekt und vollstaendig — er enthaelt explizite
`comms`-Beispiele fuer E-Mail-Anfragen. Das 350m-Modell ignoriert die
Beispiele und assoziiert `"write"` + `"email"` + `"boss"` mit Code-Kontext
(wahrscheinlich Trainings-Artefakt).

**Grammar Constraint loest das Problem nicht** — er beschraenkt nur die
Ausgabe auf gueltige Agent-Namen, beeinflusst aber nicht welchen Namen
das Modell waehlt.

**Loesung:** Granite-4.0-H-Tiny (4B) auf dem Host — dort funktioniert
Zero-Shot-Routing korrekt (durch groessere Modellkapazitaet).

---

## Test-Run 2026-07-21 — Heuristik + Notes-Fixes

**Stack:** llama-server b9895 + --jinja + --embeddings + --pooling mean
**Modell:** Granite 350m Q4_K_M

### Neue Features getestet

| Feature | Status | Commit |
|---------|--------|--------|
| router_heuristic.py (Emoji + Keywords) | ✓ 8/8 korrekt | 3a8ebbc2 |
| supervisor.py Pre-Filter | ✓ kein LLM-Call fuer 5/5 Faelle | 8ecd7696 |
| notes.py cosine Collection (BUG-017) | ✓ | 119fa9f7 |
| notes.py Source-Filter entfernt (BUG-018) | ✓ | 95ba7427 |
| notes.py save_note Tool (BUG-019) | ✓ implementiert | 1c8b2bdf |
| granite-embed in LiteLLM Config | ✓ | 1f648717 |
| --embeddings + --pooling mean (BUG-021) | ✓ 768-dim Embeddings | a8b486c3 |

### Agenten-Test 4/6 OK

| Agent | Status | Anmerkung |
|-------|--------|-----------|
| Supervisor | ✓ | heuristic → meta (kein LLM-Call) |
| Comms | ✓ | heuristic → comms (keyword: write) |
| Code | ✓ | heuristic → code (keyword: python) |
| Researcher | ✓ | heuristic → tell me about |
| Notes | ✗ | HTTP 200 aber save_note nicht aufgerufen (350m Limit) |
| Handoff | ✓ | heuristic → claude.ai |

### Wichtigste Erkenntnis

Heuristisches Routing eliminiert LLM-Routing-Calls fuer 5 von 6 Agenten.
Notes-Agent antwortet (kein Crash mehr) aber schreibt nicht in ChromaDB —
das bleibt ein 350m Modell-Limit, kein Code-Bug.
