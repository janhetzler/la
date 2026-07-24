# Local Agent Test Suite — Ergebnisse (Sandbox 1)
**Datum:** 2026-07-24 (fünfter Lauf)
**Umgebung:** Claude.ai Sandbox (Intel Xeon, 1 Core, 4 GB RAM)
**Modell:** Granite 4.0-H 350m Q4_K_M

---

## Stack Konfiguration

```
llama-server b9895 :8080  (Granite 350m, --jinja)
llama-server b9895 :8081  (Granite Embedding 30m)
    ↑
LiteLLM :4000             (Gateway + Phoenix Callbacks)
    ↑
Agent Server :8002         (Supervisor + 5 Agenten)
    ↓
ChromaDB (embedded, /tmp/chroma_la)
    ↓
Phoenix :6006              (Timeout beim Start, OTel direkt aktiv)
```

Headroom: DISABLED

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
| llama-server | b9895 Binary (--jinja) |
| fastapi | 0.139.0 |
| uvicorn | 0.51.0 |
| pydantic | 2.12.5 |
| openai | ≥2.26.0 |

---

## Agent Test Ergebnisse (5/6 OK)

Testlauf: `python3 scripts/sandbox/start_full.py`
Start: 2026-07-24T10:43:25 — Ende: 2026-07-24T10:44:36 (~1:11 min)

| Agent | Status | Zeit | Routing | Antwort |
|-------|--------|------|---------|---------|
| Supervisor Routing | ✓ | 5.8s | meta | OK (65 Zeichen) |
| Comms Agent | ✓ | 11.6s | heuristic→comms | OK (1179 Zeichen) |
| Code Agent | ✓ | 2.8s | heuristic→comms | OK (293 Zeichen) |
| Researcher Agent | ✓ | 29.6s | LLM→researcher | OK (2164 Zeichen) |
| Notes Agent | ✗ | 15.3s | heuristic→notes | ChromaDB notes: 0 Dokumente |
| Handoff Agent | ✓ | 5.9s | heuristic→handoff | OK (731 Zeichen) |

---

## Bekannte Punkte

### 1. Heuristik-Routing stabil
comms, notes, handoff werden per Keyword-Heuristik korrekt geroutet.
researcher wird per LLM korrekt erkannt.
Supervisor Routing ("Can you help me?") → meta korrekt.

### 2. Notes Agent FAIL — ChromaDB schreibt nicht
Korrekt geroutet (heuristic→notes), antwortet mit
"I'm sorry, but I can't save the note as I don't have the
necessary tools to complete the JSON."
Modell ruft kein Write-Tool auf. Bekanntes Tool-Call Problem.
Dokumentiert in BUGS.md.

### 3. Phoenix TIMEOUT beim Start
Phoenix startet nicht innerhalb von 25 Retries (~25s).
OTel-Tracing läuft trotzdem direkt über Collector-Endpoint.
Kein Einfluss auf Testergebnisse.

### 4. Phoenix Log False Positive
SQL `CHECK ... IN ('OK', 'ERROR', ...)` triggert Fehler-Pattern.
Kein echter Fehler. Dokumentiert in BUGS.md.

### 5. Code Agent routet zu comms
Heuristik-Keyword "Write" trifft comms statt code.
Antwort ist trotzdem korrekt (Python Funktion). Test besteht.
Routing-Präzision verbesserbar.

---

## Neu seit letztem Lauf (Commit fa1fb82)

- Embedding-Server :8081 im Stack (granite-embed Readiness-Check)
- ChromaDB notes-Collection explizit initialisiert (cosine)
- Frischer Klon nach Repo-Bereinigung

---

## Historischer Vergleich

| Testlauf | Datum | OK/Gesamt | Routing | llama-server |
|---------|-------|-----------|---------|-------------|
| Sandbox 1 (historisch) | 2026-07-14 | 6/6 ¹ | alles→meta | llama-cpp-python |
| Sandbox 1 (1. Lauf) | 2026-07-17 | 4/6 | alles→meta | llama-cpp-python |
| Sandbox 1 (2. Lauf) | 2026-07-17 | 4/6 | alles→meta | llama-cpp-python |
| Sandbox 1 (3. Lauf) | 2026-07-18 | 5/6 | alles→meta | llama-cpp-python |
| Sandbox 1 (4. Lauf) | 2026-07-23 | 4/6 | heuristic ✓ | Binary b9895 |
| Sandbox 1 (5. Lauf) | 2026-07-24 | 5/6 | heuristic ✓ | Binary b9895 |

¹ Hinweis: 6/6 historisch weil Tests weniger streng waren —
kein ChromaDB-Check, keine Mindestlängen-Validierung.
Nicht vergleichbar mit aktuellem Testlauf.
