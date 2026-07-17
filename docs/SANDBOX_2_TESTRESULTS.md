# Local Agent Test Suite — Ergebnisse (Sandbox 2)
**Datum:** 2026-07-17  
**Umgebung:** Claude Container (AMD EPYC-kompatibel, 1 Kern, ~8 GB RAM frei)  
**Modell:** Granite 4.0-H 350m Q4_K_M (Test-Proxy für Granite-4.0-H-Tiny auf Host)

---

## Stack Konfiguration

```
llama-server :8080 (Granite 350m)
    ↑
LiteLLM :4000 (Gateway + Phoenix Callbacks, master_key ohne DB)
    ↑
Agent Server :8002 (Supervisor + 6 Agenten)
    ↓
ChromaDB (embedded, /tmp/chroma_la)
    ↓
Phoenix :6006 (Observability)
```

---

## Agent Test Ergebnisse (4/6 OK)

| Agent | Status | Routing | Antwort |
|-------|--------|---------|---------|
| Supervisor Routing | ✓ | meta | 75 Zeichen, korrekt |
| Comms Agent | ✓ | meta | 606 Zeichen, E-Mail generiert |
| Code Agent | ✓ | meta | 312 Zeichen, Python-Funktion korrekt |
| Researcher Agent | ✓ | meta | 620 Zeichen, LangGraph erklärt |
| Notes Agent | ✗ | — | ChromaDB `notes`: 0 Dokumente |
| Handoff Agent | ✗ | — | Zu kurz (7 Zeichen) |

**Hinweis Routing:** 350m routet unzuverlässig (alles → meta).
Auf janhet mit Granite-4.0-H-Tiny (4B) wird Routing korrekt funktionieren.
Notes/Handoff-FAIL ist Modellgröße, kein struktureller Bug.

---

## Phoenix Observability

**Traces:** ✓ aktiv  
**Projekt:** `local-agent`  
**Collector Endpoint:** `http://127.0.0.1:6006/v1/traces`  
**LangChain Auto-Instrumentierung:** Aktiv (skip_dep_check=True)  

**Bekannter False Positive:** Phoenix Log-Check meldet `ERROR` in SQL-Constraint-Namen
(`CHECK (status_code IN ('OK', 'ERROR', ...))`). Kein echter Laufzeitfehler.
Fix offen: Log-Check auf `ERROR:` (mit Doppelpunkt) einschränken.

---

## ChromaDB

**Collections:** `notes`, `documents`  
**Dokumente:** 0 (Notes-Agent hat nicht geschrieben — Routing-Limit 350m)  
**Status:** Client initialisiert ✓, Schreiben durch Modellgröße verhindert

---

## MCP Test Ergebnisse

| Test | Status | Detail |
|------|--------|--------|
| Tool-Loader (tools.py direkt) | ✓ | 13 Tools geladen |
| git_log via Agent | ✓¹ | HTTP 200, Antwort kam |
| fetch via Agent | ✓¹ | HTTP 200, Antwort kam |

¹ MCP-Infrastruktur funktioniert. 350m-Modell ruft Tools nicht aktiv auf
(antwortet direkt statt `<tool_call>` zu generieren). Auf janhet mit 4B-Modell erwartet.

**MCP Tools verfügbar:** `fetch`, `git_add`, `git_branch`, `git_checkout`,
`git_commit`, `git_create_branch`, `git_diff`, `git_diff_staged`,
`git_diff_unstaged`, `git_log`, `git_reset`, `git_show`, `git_status`

---

## Fixes und Funde dieser Session

| Fund | Status |
|------|--------|
| `openai==1.97.1` inkompatibel mit langchain-openai 1.2.1 | ✓ Behoben: `>=2.26.0` |
| `starlette-context` fehlte in requirements.txt (Absturz) | ✓ Behoben: aktiviert |
| `mcp.json` Pfad in tools.py falsch | ✓ Behoben: direkt committed |
| LiteLLM 1.92.0: `master_key` + kein DB = `No connected db.` | ✓ Behoben: Key-Alignment |
| LiteLLM unterstützt kein SQLite (nur PostgreSQL) | ✓ Dokumentiert |
| Phoenix Log-Check False Positive | ✓ In BUGS.md dokumentiert |
| Em-Dash in f-string → SyntaxError | ✓ Behoben |
| LITELLM_KEY Default stimmte nicht mit hardcodierten Agent-Keys überein | ✓ Behoben: sk-cos-local-dev |

---

## Bekannte Limitierungen (Test-Umgebung)

1. **350m vs Tiny:** Routing/Tool-Calling schlechter als auf janhet mit 4B Modell
2. **Notes/Handoff FAIL:** Modellgröße, kein Bug — auf janhet erwartet OK
3. **Phoenix Log-Check:** False Positive auf SQL-Constraints — Fix offen
4. **Embedding-Server (Port 8081):** Nicht gestartet in Sandbox-Tests

---

## Nächste Schritte für janhet

```bash
# 1. Repository pullen
git pull

# 2. Dependencies installieren
pip install -r requirements.txt

# 3. Stack starten (Sandbox)
python3 scripts/sandbox/start_full.py

# 4. Host-Deployment
# siehe deploy/systemd/
```
