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
## 2026-07-30 — Testlauf final (Commit b22a8d7) — BUG-019 behoben

**Datum:** 2026-07-30
**Repo-Stand:** b22a8d7
**Modell:** Granite 4.0-H-350m-Q4_K_M
**Stack:** llama-server b9895 + :8081 Embedding, LiteLLM, Phoenix, ChromaDB

### Stack-Status

| Service | Status |
|---------|--------|
| llama-server :8080 | ✓ OK (Inference OK) |
| llama-server :8081 | ✓ OK (Embedding OK) |
| Phoenix | ✓ OK (SAWarning harmlos) |
| LiteLLM | ✓ OK |
| Agent Server | ✓ OK |

### Agenten-Test 5/6 OK

| Agent | Status | Zeichen | Anmerkung |
|-------|--------|---------|-----------|
| Supervisor Routing | ✗ FAIL | 6 | BUG-024 — 350m Limit |
| Comms Agent | ✓ OK | 675 | |
| Code Agent | ✓ OK | 312 | |
| Researcher Agent | ✓ OK | 102 | |
| Notes Agent | ✓ OK | 37 | ChromaDB notes: 1 Dokument ✓ BUG-019 behoben |
| Handoff Agent | ✓ OK | 731 | |

### ChromaDB

Collection notes: 1 Dokument ✓
Collection documents: 2 Dokumente

---


## 2026-07-30 — Testlauf 21:38 UTC (Commit c8af4a8)

**Datum:** 2026-07-30 21:42 UTC
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

## 2026-07-30 23:43 UTC — Testlauf (Commit $COMMIT_SHA) — BUG-019 BEHOBEN

**Datum:** 2026-07-30 23:47:46
**Repo-Stand:** $COMMIT_SHA
**Modell:** Granite 4.0-H-350m-Q4_K_M
**Stack:** llama-server b9895, LiteLLM, Phoenix, ChromaDB

### Stack-Status

| Service | Status |
|---------|--------|
| llama-server :8080 | ✓ OK |
| llama-server :8081 | ✓ OK |
| Phoenix | ✓ OK |
| LiteLLM | ✓ OK |
| Agent Server | ✓ OK |

### Agenten-Test 5/6 bestanden ✓

| Agent | Status | Zeichen | Anmerkung |
|-------|--------|---------|-----------|
| Supervisor Routing | ✗ FAIL | 6 | Zu kurz — BUG-024 (350m Limit) |
| Comms Agent | ✓ OK | 675 | Email-Draft |
| Code Agent | ✓ OK | 312 | Python-Funktion |
| Researcher Agent | ✓ OK | 102 | Fallback-Response |
| Notes Agent | ✓ OK | 37 | ✓ ChromaDB 1 Doc — **BUG-019 BEHOBEN** |
| Handoff Agent | ✓ OK | 731 | Claude.ai Prompt |

### ChromaDB Status

**Collections nach Tests:**
- documents: 2 Dokumente
- **notes: 1 Dokument** ✓ (Notes Agent speichert jetzt korrekt)

### Status Update

- **BUG-019** — BEHOBEN ✓ — Notes Agent ruft save_note auf und speichert in ChromaDB
- **BUG-024** — PENDING — Supervisor Routing generiert zu kurze LLM-Responses (350m Limit)
- Phoenix SAWarnings: harmlos

---

## 2026-07-30 21:38 UTC — Testlauf (Commit $COMMIT_SHA)

**Datum:** 2026-07-30 21:45:27
**Repo-Stand:** $COMMIT_SHA
**Modell:** Granite 4.0-H-350m-Q4_K_M
**Stack:** llama-server b9895, LiteLLM, Phoenix, ChromaDB

### Stack-Status

| Service | Status | Warmup | Details |
|---------|--------|--------|---------|
| llama-server :8080 | ✓ OK | 25-27s | Inference OK |
| llama-server :8081 | ✓ OK | 3s | Embedding OK |
| Phoenix | ✓ OK | 25s | Tracing aktiv |
| LiteLLM | ✓ OK | 25s | Proxy OK |
| Agent Server | ✓ OK | 1s | FastAPI port 8002 |

### Agenten-Test 4/6 bestanden

| Agent | Status | Zeichen | Anmerkung |
|-------|--------|---------|-----------|
| Supervisor Routing | ✗ FAIL | 6 | Zu kurz — BUG-024 (350m Limit) |
| Comms Agent | ✓ OK | 483 | Email-Draft |
| Code Agent | ✓ OK | 325 | Python-Funktion |
| Researcher Agent | ✓ OK | 102 | Fallback-Response |
| Notes Agent | ✗ FAIL | 37 | ChromaDB 0 Docs — BUG-019 |
| Handoff Agent | ✓ OK | 702 | Claude.ai Prompt |

### ChromaDB Status

**Collection 'notes':** 0 Dokumente

**Fehler (Deprecated Legacy-Config):**
```
ValueError: You are using a deprecated configuration of Chroma.
If you do not have data you wish to migrate, you only need to change how you construct
your Chroma client. Please see the "New Clients" section of 
https://docs.trychroma.com/deployment/migration.
```

### Bekannte Probleme

- **BUG-024** — Supervisor Routing: 350m generiert zu kurze LLM-Responses
- **BUG-019** — Notes Agent: 350m ruft `save_note` nicht auf
- **ChromaDB** — Legacy-Config API; Migration erforderlich

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
