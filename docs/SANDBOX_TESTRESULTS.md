---
type: Observation
status: current
updated_at: 2026-07-30
environment: sandbox
components: [llama-server, litellm, chromadb, phoenix, fastapi]
---
# Local Agent Test Suite — Ergebnisse (Sandbox)

Aktuellster Testlauf oben. Aeltere Eintraege darunter.
Testergebnisse werden ausschliesslich von der Sandbox gepusht, nie vom Mutterchat.

---

## 2026-07-30 — Testlauf 21:38 UTC (Commit c8af4a8)

**Datum:** 2026-07-30 2026-07-30 21:42:34
**Repo-Stand:** c8af4a8
**Modell:** Granite 4.0-H-350m-Q4_K_M
**Stack:** llama-server b9895, LiteLLM, Phoenix, ChromaDB

### Stack-Status

| Service | Status | Details |
|---------|--------|---------|
| llama-server :8080 | ✓ OK | Inference OK, 25-27s warmup |
| llama-server :8081 | ✓ OK | Embedding, 3s warmup |
| Phoenix | ✓ OK | Tracing aktiv, 25s warmup |
| LiteLLM | ✓ OK | 25s warmup, Proxy OK |
| Agent Server | ✓ OK | FastAPI, 1s |
| ChromaDB | ✗ FAIL | Deprecated Legacy-Config erkannt |

### Agenten-Test 4/6 OK

| Agent | Status | Char | Anmerkung |
|-------|--------|------|-----------|
| Supervisor Routing | ✗ FAIL | 6 | Zu kurz — BUG-024 (350m Limit) |
| Comms Agent | ✓ OK | 483 | Email-Draft OK |
| Code Agent | ✓ OK | 325 | Python-Funktion OK |
| Researcher Agent | ✓ OK | 102 | Fallback-Response |
| Notes Agent | ✗ FAIL | 37 | ChromaDB 0 Docs — BUG-019 (save_note nicht aufgerufen) |
| Handoff Agent | ✓ OK | 702 | Prompt generiert |

### ChromaDB Status

**Fehler (Deprecated Legacy-Config):**


**Dokumente:** 0 in 'notes' Collection

### Bekannte Limitierungen

- **BUG-024** — Supervisor Routing: 350m Modell generiert zu kurze LLM-Responses
- **BUG-019** — Notes Agent: 350m Modell ruft  Tool nicht auf
- **ChromaDB Migration** — Legacy-Config erkennt Deprecated API; Migration erforderlich für persistente Speicherung

### Phoenix Logs

Minor SQLAlchemy SAWarnings (Index-Reflection): harmlos, keine funktionalen Fehler.

---

## 2026-07-30 — Haiku-Sandbox, erster Lauf

**Datum:** 2026-07-30
**Modell:** Claude Haiku
**Stack:** llama-server b9895, Granite 350m Q4_K_M

### Agenten-Test 4/6 OK

| Agent | Status | Anmerkung |
|-------|--------|-----------|
| Supervisor Routing | FAIL | Antwort zu kurz (6 Zeichen) — BUG-024 |
| Comms Agent | OK | |
| Code Agent | OK | |
| Researcher Agent | OK | |
| Notes Agent | FAIL | ChromaDB 0 Dokumente — BUG-019 |
| Handoff Agent | OK | |

Phoenix SAWarnings: harmlos.
