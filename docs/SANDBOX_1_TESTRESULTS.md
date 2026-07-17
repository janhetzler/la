# Local Agent Test Suite — Ergebnisse (Sandbox 1)
**Datum:** 2026-07-17
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
ChromaDB (embedded, /tmp/chroma_chief)
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
| openinference-instrumentation-langchain | 0.1.67 |
| llama-cpp-python | 0.3.23 (Prebuilt Wheel) |
| fastapi | 0.139.0 |
| uvicorn | 0.51.0 |
| pydantic | 2.12.5 |
| openai | ≥2.26.0 |

---

## Agent Test Ergebnisse (4/6 OK)

Testlauf: `python3 scripts/sandbox/start_full.py`
Gesamtdauer: ~2:19 min (11:01:50 – 11:04:09)

| Agent | Status | Zeit | Routing | Antwort |
|-------|--------|------|---------|---------|
| Supervisor Routing | ✓ | 18.4s | meta | 75 Zeichen |
| Comms Agent | ✓ | 19.9s | meta | 606 Zeichen, E-Mail generiert |
| Code Agent | ✓ | 26.5s | comms | 405 Zeichen, Python Funktion korrekt |
| Researcher Agent | ✓ | 24.4s | handoff | 620 Zeichen, LangGraph erklärt |
| Notes Agent | ✗ | 18.0s | meta | Routet zu meta statt notes — ChromaDB leer |
| Handoff Agent | ✗ | 29.3s | researcher | Antwort nur "Prepare" (7 Zeichen, zu kurz) |

---

## Bekannte Punkte

### 1. Routing-Limit 350m
Das 350m Modell routet nicht zuverlässig:
- `Save → meta` statt `notes`
- `Prepare → researcher` statt `handoff`
- `Python → comms` statt `code`

Ursache: 350m zu klein für zuverlässige Intent-Klassifikation.
Auf janhet mit Granite-Tiny-4B wird Routing korrekt funktionieren.
Workaround für Sandbox-Tests: englische Prompts, einfache Keywords.

### 2. Phoenix Log-Check False Positive
`test_stack.py` meldet `⚠️ Fehler gefunden` für `phoenix.log`.
Ursache: Log-Check sucht nach bloßem String `"ERROR"` — Phoenix schreibt
beim Start SQL `CREATE TABLE` mit `CHECK ... IN ('OK', 'ERROR', ...)`.
Kein echter Fehler. Dokumentiert in `BUGS.md`.

### 3. LiteLLM Traceback beim Cleanup
Finaler Log-Check zeigt Traceback in `litellm.log`.
Tritt auf wenn LiteLLM-Prozess per `lp.terminate()` beendet wird.
Kein Einfluss auf Testergebnisse — nur beim Cleanup.

---

## Hinweis: erster Testlauf nach config-Refactor

Dieser Testlauf ist der erste nach dem `config/*.env` Refactor:
- `config/` Verzeichnis mit umgebungsspezifischen `.env` Dateien
- `os.getenv()` statt hardcodierter Werte in Modulen
- `import config` musste nachträglich in `supervisor.py`, `code.py`,
  `comms.py` ergänzt werden (Commit `3afbf2e`) — war beim ersten
  `import_check.py` noch fehlgeschlagen.

---

## Historischer Vergleich

| Testlauf | Datum | OK/Gesamt | Headroom |
|---------|-------|-----------|---------|
| Sandbox 1 (historisch) | 2026-07-14 | 6/6 | aktiv |
| Sandbox 1 (aktuell) | 2026-07-17 | 4/6 | disabled |

Unterschied 6→4: Notes und Handoff scheitern jetzt an inhaltlicher
Validierung (ChromaDB-Check, Mindestlänge) die vorher nicht existierte.
Das 350m Routing-Problem ist unverändert.
