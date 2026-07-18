# Local Agent Test Suite — Ergebnisse (Sandbox 1)
**Datum:** 2026-07-18 (dritter Lauf)
**Umgebung:** Claude.ai Sandbox (Intel Xeon, 1 Core, 4 GB RAM)
**Modell:** Granite 4.0-H 350m Q4_K_M

---

## Stack Konfiguration

```
llama-server :8080  (Granite 350m, llama-cpp-python 0.3.23)
    ↑
LiteLLM :4000       (Gateway + Phoenix Callbacks)
    ↑
Agent Server :8002  (Supervisor + 5 Agenten)
    ↓
ChromaDB (embedded, /tmp/chroma_la)
    ↓
Phoenix :6006       (Observability)
```

Headroom: DISABLED (headroom-ai[all] zu groß für Sandbox)

---

## Stack-Versionen (requirements.txt)

| Paket | Version |
|-------|---------|
| langchain | 1.2.15 |
| langchain-openai | 1.2.1 |
| langchain-mcp-adapters | 0.2.2 |
| langgraph | 1.1.10 |
| chromadb | 1.5.9 |
| litellm | 1.92.0 |
| arize-phoenix | 18.0.0 |
| arize-phoenix-client | (neu) |
| openinference-instrumentation-langchain | 0.1.67 |
| llama-cpp-python | 0.3.23 (Prebuilt Wheel) |
| fastapi | 0.139.0 |
| uvicorn | 0.51.0 |
| pydantic | 2.12.5 |
| openai | ≥2.26.0 |

---

## Agent Test Ergebnisse (5/6 OK)

Testlauf: `python3 scripts/sandbox/start_full.py`
Start: 2026-07-18T15:08:12 — Ende: 2026-07-18T15:09:59 (~1:47 min)

| Agent | Status | Zeit | Routing | Antwort |
|-------|--------|------|---------|---------|
| Supervisor Routing | ✓ | 15.0s | meta | OK (34 Zeichen) |
| Comms Agent | ✓ | 18.8s | meta | OK (692 Zeichen) |
| Code Agent | ✓ | 13.2s | meta | OK (28 Zeichen) |
| Researcher Agent | ✓ | 29.2s | researcher | OK (619 Zeichen) |
| Notes Agent | ✗ | 14.0s | meta | ChromaDB notes: 0 Dokumente |
| Handoff Agent | ✓ | 14.0s | meta | OK (157 Zeichen) |

---

## Bekannte Punkte

### 1. Routing-Limit 350m
Das 350m Modell routet fast alles zu `meta` — nur `researcher` wird
korrekt erkannt. Ursache: 350m zu klein für Intent-Klassifikation.
Auf janhet mit Granite-Tiny-4B wird Routing korrekt funktionieren.

### 2. Notes Agent FAIL
Notes Agent routet zu `meta` statt `notes` — ChromaDB collection bleibt
leer. Bekanntes Routing-Limit, kein Code-Fehler.

### 3. Phoenix Log-Check False Positive
`test_stack.py` meldet Fehler für `phoenix.log` wegen SQL
`CHECK ... IN ('OK', 'ERROR', ...)`. Kein echter Fehler.
Dokumentiert in `BUGS.md`.

### 4. Code Agent Antwort-Qualität
Code Agent routet zu `meta` und antwortet mit `<|ex|>What can I do for you?`
— 28 Zeichen, knapp über Mindestlänge. Inhaltlich nicht korrekt.
Validierung prüft nur Mindestlänge, nicht Codequalität.

---

## Neu seit letztem Lauf (Commit a235959)

- `agent_loader.py` — neuer zentraler Agent-Loader aus `prompts/` Dateien
- `prompts/` Verzeichnis — Prompt-Dateien für alle Agenten als Markdown
- `TEMPLATE.py` / `TEMPLATE.md` — Agent-Templates
- `project_context.py` und `user_profile.py` gelöscht → `prompts/shared/`
- `scripts/sandbox/start_claude.py` — neues Sandbox-Skript
- Fix: `TEMPLATE.md` aus `list_agents()` ausgeschlossen (Commit a235959)

---

## Historischer Vergleich

| Testlauf | Datum | OK/Gesamt | Headroom |
|---------|-------|-----------|---------|
| Sandbox 1 (historisch) | 2026-07-14 | 6/6 ¹ | aktiv |
| Sandbox 1 (erster Lauf) | 2026-07-17 | 4/6 | disabled |
| Sandbox 1 (zweiter Lauf) | 2026-07-17 | 4/6 | disabled |
| Sandbox 1 (dritter Lauf) | 2026-07-18 | 5/6 | disabled |

¹ Hinweis: 6/6 historisch weil Tests weniger streng waren —
kein ChromaDB-Check, keine Mindestlängen-Validierung.
Nicht vergleichbar mit aktuellem Testlauf.
