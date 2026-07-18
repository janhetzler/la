# Local Agent Test Suite — Ergebnisse (Sandbox 2)
**Datum:** 2026-07-18 (aktualisiert)
**Umgebung:** Claude Container (AMD EPYC-kompatibel, 1 Kern, ~8 GB RAM frei)
**Modell:** Granite 4.0-H 350m Q4_K_M (Test-Proxy fuer Granite-4.0-H-Tiny auf Host)

---

## Stack Konfiguration

```
llama-server :8080 (Granite 350m)
    ↑
LiteLLM :4000 (Gateway + Phoenix Callbacks, master_key ohne DB)
    ↑
Agent Server :8002 (Supervisor + 6 Agenten via agent_loader.py)
    ↓
ChromaDB (embedded, /tmp/chroma_la)
    ↓
Phoenix :6006 (Observability)
```

**Neues System seit 2026-07-18:**
- `agent_loader.py` laedt Agenten dynamisch aus `prompts/agents/*.md`
- Gemeinsamer Kontext via `prompts/shared/user_profile.md` + `project_context.md`
- Template-Injection: `{{ user_profile }}` und `{{ project_context }}` werden
  in jeden Agenten-Prompt eingefuegt
- Router-Prompt aus `prompts/agents/router.md` (Zero-Shot)

---

## Agent Test Ergebnisse (5/6 OK)

| Agent | Status | Routing | Antwort |
|-------|--------|---------|---------|
| Supervisor Routing | ✓ | → meta | 34 Zeichen |
| Comms Agent | ✓ | → meta | 692 Zeichen (E-Mail vollstaendig) |
| Code Agent | ✓ | → meta | 28 Zeichen |
| Researcher Agent | ✓ | → researcher | 619 Zeichen |
| Notes Agent | ✗ | → meta | ChromaDB `notes`: 0 Dokumente |
| Handoff Agent | ✓ | → meta | 157 Zeichen |

**Routing-Hinweis:** 350m routet fast alles zu `meta` (Fallback).
Nur `researcher` wird zuverlässig korrekt geroutet.
Comms/Code/Handoff landen auf `meta` — der meta-Agent antwortet trotzdem
sinnvoll weil er den System-Kontext kennt.
Notes FAIL: Routing-Limit, Notiz nicht in ChromaDB geschrieben.

---

## Template-Injection

**Status:** Infrastruktur funktioniert korrekt.

- `agent_loader.py` laedt `user_profile.md` (1380 Zeichen) und
  `project_context.md` (2034 Zeichen)
- `inject_shared()` ersetzt `{{ user_profile }}` und `{{ project_context }}`
- Comms-Prompt: 4381 Zeichen mit Template-Inhalt

**Offen:** `prompts/shared/user_profile.md` enthaelt noch Template-Platzhalter
(`[Your name]` etc.) — muss mit echten Daten gefuellt werden.

---

## Phoenix Observability

**Traces:** ✓ aktiv
**Projekt:** `local-agent`
**Readiness-Check:** ✓ `/v1/projects` (kein TIMEOUT mehr)
**LangChain Auto-Instrumentierung:** Aktiv (skip_dep_check=True)

---

## ChromaDB

**Collections:** `notes`, `documents`
**Dokumente:** 0 (Notes-Agent schreibt nicht — Routing-Limit 350m)
**Status:** Client initialisiert ✓

---

## Bugs gefunden und dokumentiert (2026-07-18)

| Bug | Status |
|-----|--------|
| `handoff.md` YAML-Fehler (Doppelpunkt in description) | ✓ Behoben: Commit `95c059d` |
| HTML-Kommentare in `.md` Prompts -> Garbage-Tokens | ✓ Behoben: Commit `9cf389b` |
| Few-Shot Prompt -> Modell gibt User-Message-Token zurueck | ✓ Reverted: Commit `02012de` |
| `supervisor.py` hardcoded `granite-tiny` statt `config.DEFAULT_LLM` | ✓ Behoben: Commit `d72cbea` |
| `LITELLM_KEY` Default `sk-local-dev` != Agent-Key `sk-cos-local-dev` | ✓ Behoben: Commit `5fb757b` |
| LiteLLM `master_key` + SQLite = `No connected db.` | ✓ Behoben: Commit `b113858` |
| `list_agents()` findet `handoff` nicht (YAML-Exception verschluckt) | ✓ Behoben: Commit `95c059d` |

---

## Bekannte Limitierungen (Test-Umgebung)

1. **350m vs Tiny:** Routing fast immer `meta`, Tiny auf Host routet korrekt
2. **Notes/ChromaDB:** Schreiben schlaegt fehl durch Routing-Limit
3. **user_profile.md:** Noch nicht mit echten Daten gefuellt
4. **Embedding-Server (Port 8081):** Nicht gestartet in Sandbox-Tests
5. **Spracherkennung:** Deaktiviert (350m gibt User-Message-Tokens zurueck)

---

## Naechste Schritte fuer Host (janhet)

1. `prompts/shared/user_profile.md` mit echten Daten fuellen
2. Few-Shot Router-Prompt auf Granite-4.0-H-Tiny testen (4B, korrekte Tool-Calls)
3. Notes-Agent mit echtem Routing testen (ChromaDB schreiben/lesen)
4. MCP Tool-Calling: `git_log`, `fetch` mit Granite-Tiny aktivieren
5. `scripts/sandbox/start_claude.py` mit echtem Anthropic API-Key testen
