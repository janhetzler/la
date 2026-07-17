# Local Agent Test Suite — Ergebnisse (Sandbox 1)
**Datum:** 2026-07-17 (zweiter Lauf)
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

## Agent Test Ergebnisse (4/6 OK)

Testlauf: `python3 scripts/sandbox/start_full.py`
Start: 2026-07-17T17:52:57 — Ende: 2026-07-17T17:55:23 (~2:26 min)

| Agent | Status | Zeit | Routing | Antwort |
|-------|--------|------|---------|---------|
| Supervisor Routing | ✓ | 21.2s | meta | OK (75 Zeichen) |
| Comms Agent | ✓ | 20.6s | meta | OK (606 Zeichen) |
| Code Agent | ✓ | 28.4s | comms | OK (312 Zeichen) |
| Researcher Agent | ✓ | 24.9s | handoff | OK (620 Zeichen) |
| Notes Agent | ✗ | 18.5s | meta | ChromaDB notes: 0 Dokumente |
| Handoff Agent | ✗ | 30.3s | researcher | Zu kurz (7 Zeichen: "Prepare") |

---

## Bekannte Punkte

### 1. Routing-Limit 350m
Das 350m Modell routet nicht zuverlässig:
- `Save → meta` statt `notes`
- `Prepare → researcher` statt `handoff`
- `Python → comms` statt `code`
- `LangGraph → handoff` statt `researcher`

Ursache: 350m zu klein für zuverlässige Intent-Klassifikation.
Auf janhet mit Granite-Tiny-4B wird Routing korrekt funktionieren.

### 2. Phoenix Log-Check False Positive
`test_stack.py` meldet `⚠️ Fehler gefunden` für `phoenix.log`.
Ursache: Log-Check sucht nach bloßem String `"ERROR"` — Phoenix schreibt
beim Start SQL `CREATE TABLE ... CHECK ... IN ('OK', 'ERROR', ...)`.
Kein echter Fehler. Dokumentiert in `BUGS.md`.

### 3. LiteLLM Traceback beim Cleanup
Finaler Log-Check zeigt Traceback in `litellm.log`.
Tritt auf wenn LiteLLM-Prozess per `lp.terminate()` beendet wird.
Kein Einfluss auf Testergebnisse — nur beim Cleanup.

### 4. supervisor.py Grammar-Experiment (revertiert)
Commits `265ec86` (Few-Shot + grammar constraint) und `d9ee9ef` (revert).
Grammar-Constraint via `extra_body` inkompatibel mit LiteLLM — führte zu
`No connected db.` Fehler. Dokumentiert in `BUGS.md`.

---

## Neu seit letztem Lauf (Commit 0a21a7f)

- `config/` Struktur mit `.env` Dateien für alle Umgebungen
- `arize-phoenix-client` in `requirements.txt`
- `scripts/sandbox/inspect_phoenix.py` — Phoenix Traces auslesen
- `scripts/sandbox/test_mcp_toolcall.py` — MCP Tool-Calling testen
- `BUGS.md` und `docs/ROADMAP.md` aktualisiert
- `supervisor.py` — unverändert (Grammar-Experiment revertiert)

---

## Historischer Vergleich

| Testlauf | Datum | OK/Gesamt | Headroom |
|---------|-------|-----------|---------|
| Sandbox 1 (historisch) | 2026-07-14 | 6/6 ¹ | aktiv |
| Sandbox 1 (erster Lauf) | 2026-07-17 | 4/6 | disabled |
| Sandbox 1 (zweiter Lauf) | 2026-07-17 | 4/6 | disabled |

¹ Hinweis: 6/6 historisch weil Tests weniger streng waren —
kein ChromaDB-Check, keine Mindestlängen-Validierung.
Nicht vergleichbar mit aktuellem Testlauf.
