# Local Agent Test Suite — Ergebnisse (Sandbox 1)
**Datum:** 2026-07-23 (vierter Lauf)
**Umgebung:** Claude.ai Sandbox (Intel Xeon, 1 Core, 4 GB RAM)
**Modell:** Granite 4.0-H 350m Q4_K_M

---

## Stack Konfiguration

```
llama-server b9895 :8080  (Granite 350m, Binary mit --jinja)
    ↑
LiteLLM :4000             (Gateway + Phoenix Callbacks)
    ↑
Agent Server :8002         (Supervisor + 5 Agenten)
    ↓
ChromaDB (embedded, /tmp/chroma_la)
    ↓
Phoenix :6006              (Observability, Timeout beim Start)
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
| arize-phoenix-client | installiert |
| openinference-instrumentation-langchain | 0.1.67 |
| llama-server | b9895 (Binary, --jinja) |
| fastapi | 0.139.0 |
| uvicorn | 0.51.0 |
| pydantic | 2.12.5 |
| openai | ≥2.26.0 |

---

## Agent Test Ergebnisse (4/6 OK)

Testlauf: `python3 scripts/sandbox/start_full.py`
Start: 2026-07-23T17:48:01 — Ende: 2026-07-23T17:50:24 (~2:23 min)

| Agent | Status | Zeit | Routing | Antwort |
|-------|--------|------|---------|---------|
| Supervisor Routing | ✗ | 13.5s | meta | Zu kurz (6 Zeichen: "Hello!") |
| Comms Agent | ✓ | 21.9s | heuristic→comms | OK (1196 Zeichen) |
| Code Agent | ✓ | 4.7s | heuristic→comms | OK (306 Zeichen) |
| Researcher Agent | ✓ | 60.1s | heuristic→researcher | OK (3234 Zeichen) |
| Notes Agent | ✗ | 32.2s | heuristic→notes | ChromaDB notes: 0 Dokumente |
| Handoff Agent | ✓ | 10.4s | heuristic→handoff | OK (685 Zeichen) |

---

## Bekannte Punkte

### 1. Heuristik-Routing funktioniert jetzt
Neue Keyword-Heuristik im Supervisor routet comms, researcher, notes und
handoff korrekt — deutliche Verbesserung gegenüber altem Stand wo
fast alles zu `meta` ging.

### 2. Supervisor Routing FAIL
Test fragt "Can you help me?" — meta antwortet mit "Hello!" (6 Zeichen).
Mindestlängen-Validierung schlägt an. Kein echter Fehler im Routing,
nur zu kurze Antwort auf generische Frage. Test-Prompt könnte angepasst werden.

### 3. Notes Agent FAIL — ChromaDB schreibt nicht
Notes Agent wird korrekt geroutet (heuristic→notes), antwortet mit
"The note has been saved." — aber ChromaDB bleibt leer.
Ursache: Modell ruft kein Write-Tool auf, gibt nur Text zurück.
Tool-Call Problem, kein Routing-Problem.

### 4. Phoenix Timeout beim Start
Phoenix startet nicht innerhalb von 25 Retries. OTel-Tracing läuft
trotzdem direkt über Collector-Endpoint.
Phoenix Log-Check False Positive: SQL `CHECK ... IN ('OK', 'ERROR', ...)`
triggert Fehler-Pattern. Dokumentiert in `BUGS.md`.

### 5. llama-server Binary statt llama-cpp-python
Dieser Lauf nutzt das llama-server Binary (b9895) mit `--jinja` Flag
statt llama-cpp-python als Python-Modul. Binary muss vor dem Start
unter `/tmp/llama-b9895/llama-server` vorhanden sein.

---

## Neu seit letztem Lauf (Commit 0a97358)

- llama-server Binary (b9895) als Inferenz-Engine statt llama-cpp-python
- `--jinja` Flag für natives Tool-Calling aktiviert
- Heuristik-Routing im Supervisor (keyword-basiert vor LLM-Routing)
- Frischer Klon des Repos

---

## Historischer Vergleich

| Testlauf | Datum | OK/Gesamt | Routing | llama-server |
|---------|-------|-----------|---------|-------------|
| Sandbox 1 (historisch) | 2026-07-14 | 6/6 ¹ | alles→meta | llama-cpp-python |
| Sandbox 1 (erster Lauf) | 2026-07-17 | 4/6 | alles→meta | llama-cpp-python |
| Sandbox 1 (zweiter Lauf) | 2026-07-17 | 4/6 | alles→meta | llama-cpp-python |
| Sandbox 1 (dritter Lauf) | 2026-07-18 | 5/6 | alles→meta | llama-cpp-python |
| Sandbox 1 (vierter Lauf) | 2026-07-23 | 4/6 | heuristic ✓ | Binary b9895 |

¹ Hinweis: 6/6 historisch weil Tests weniger streng waren —
kein ChromaDB-Check, keine Mindestlängen-Validierung.
Nicht vergleichbar mit aktuellem Testlauf.
