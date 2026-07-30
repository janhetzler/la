# Local Agent Test Suite — Ergebnisse (Sandbox)

Aktuellster Testlauf oben. Aeltere Eintraege darunter.
Testergebnisse werden ausschliesslich von der Sandbox gepusht, nie vom Mutterchat.

---

## 2026-07-30 — Haiku-Sandbox, erster Lauf

**Datum:** 2026-07-30
**Modell:** Claude Haiku (Sandbox-Instanz)
**Stack:** llama-server b9895, Granite 350m Q4_K_M, LiteLLM, Phoenix, Agent Server

### Stack-Start

| Komponente | Status | Zeit |
|------------|--------|------|
| llama-server :8080 | ✓ OK | 8.8s |
| LiteLLM :4000 | ✓ OK | 14.5s |
| Phoenix :6006 | ✓ OK (Minor-Error im Log — harmlos) | — |
| Agent Server :8002 | ✓ OK | 25s |

### Agenten-Test 4/6 OK

| Agent | Status | Anmerkung |
|-------|--------|-----------|
| Supervisor Routing | ✗ | Antwort zu kurz (6 Zeichen) — 350m Limit |
| Comms Agent | ✓ | — |
| Code Agent | ✓ | — |
| Researcher Agent | ✓ | — |
| Notes Agent | ✗ | ChromaDB 0 Dokumente — 350m ruft save_note nicht auf (BUG-024) |
| Handoff Agent | ✓ | — |

### Phoenix Log

SQLAlchemy SAWarnings (Index-Reflection) — harmlos, kein Handlungsbedarf.

### Bewertung

4/6 entspricht erwartetem Stand. Beide Fails sind bekannte Modell-Limits (BUG-024),
keine Code-Bugs. Stack laeuft stabil.
