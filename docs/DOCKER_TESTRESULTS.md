# DOCKER_TESTRESULTS.md -- Testergebnisse Docker-Umgebung

---

## Docker Test Run #1 -- 2026-07-20

**Image:** ghcr.io/janhetzler/la:latest (Build #27, 2026-07-20)
**Umgebung:** QEMU Guest VM (Debian 6.12, Docker 29.6.2)
**Modell:** Granite 4.0-H-1B Q4_K_M (859 MB) -- ersetzt 350m fuer diesen Test
**Script:** scripts/docker/test_docker.py

### Testergebnisse

| Agent | Frage | Status | Zeichen | Zeit |
|-------|-------|--------|---------|------|
| Supervisor Routing | Can you help me? | ✓ OK | 65 | 1.9s |
| Comms Agent | Write a short professional email... | ✓ OK | 786 | 7.3s |
| Code Agent | Write a Python function... | ✓ OK | 313 | 2.8s |
| Researcher Agent | What is LangGraph... | ✓ OK | 3957 | 13.6s |
| Notes Agent | Save this note: Docker Test... | ✗ FAIL | 2 | 1.4s |
| Handoff Agent | Prepare a prompt for Claude.ai... | ✓ OK | 142 | 1.9s |

**Ergebnis: 5/6 OK**

### Beobachtungen

**Verbesserungen gegenueber 350m:**
- Comms Agent: vollstaendige professionelle E-Mail (786 Zeichen statt "Hello!")
- Researcher Agent: ausfuehrliche Antwort (3957 Zeichen)
- Supervisor: korrekte Selbstidentifikation als "Granite, your Local Agent"

**Notes Agent Fehler:**
- Antwort: Emoji (2 Zeichen) -- Routing-Problem
- Ursache: mcp/docker/mcp.json fehlte (BUG-016)
- Nach Fix: Notes-Agent antwortet, aber ChromaDB-Suche findet nichts

### ChromaDB Status

- Collection `documents`: 0 Dokumente (leer)
- Collection `notes`: nicht vorhanden

### Infrastruktur-Logs

- llama-server: laeuft mit Binary b9895, --jinja aktiv
- LiteLLM: laeuft auf 0.0.0.0:4000
- Phoenix: laeuft auf 0.0.0.0:6006, Traces werden gesammelt
- Agent Server: laeuft auf 0.0.0.0:8002

### ChromaDB RAG Test (manuell, nach Test-Run)

Nach manuellem Schreiben und Lesen:
- Schreiben mit Granite Embedding + cosine Collection: ✓
- Lesen via Notes-Agent: ✓ (score 0.84)
- Probleme gefunden: BUG-017, BUG-018, BUG-019

### Offene Punkte

- mcp/docker/mcp.json mit fetch-Server ins Repo (BUG-016)
- ChromaDB Collection mit cosine erstellen (BUG-017)
- Notes-Agent Source-Filter generalisieren (BUG-018)
- save_note Tool implementieren (BUG-019)

### Naechste Schritte

- Fixes fuer BUG-016 bis BUG-019 implementieren
- Neues Image bauen mit 1B Modell als Default
- Vollstaendiger 6/6 Test-Lauf anstreben
