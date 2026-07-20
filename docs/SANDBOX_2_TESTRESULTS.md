# Local Agent Test Suite — Ergebnisse (Sandbox 2)
**Datum:** 2026-07-20 (aktualisiert — llama-server Binary Swap)
**Umgebung:** Claude Container (AMD EPYC-kompatibel, 1 Kern, ~8 GB RAM frei)
**Modell:** Granite 4.0-H 350m Q4_K_M (Test-Proxy fuer Granite-4.0-H-Tiny auf Host)
**Laufzeit-Backend:** llama-server Binary b9895 (neu seit 2026-07-20, vorher llama-cpp-python 0.3.23)

---

## Stack Konfiguration

```
llama-server Binary b9895 :8080 (--jinja aktiv)
    ↑
LiteLLM :4000 (Gateway + Phoenix Callbacks, master_key ohne DB)
    ↑
Agent Server :8002 (Supervisor + 6 Agenten via agent_loader.py)
    ↓
ChromaDB (embedded, /tmp/chroma_la)
    ↓
Phoenix :6006 (Observability)
```

**Binary-Flags:**
```bash
/tmp/llama-b9895/llama-server \
  -m /tmp/granite-350m-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 \
  --jinja --ctx-size 32768 \
  --parallel 1 --log-disable
```

**Hinweis:** `--log-level error` existiert in b9895 nicht — korrekter Flag ist `--log-disable`.

---

## Agent Test Ergebnisse (4/6 OK)

| Agent | Status | Zeichen | Detail |
|-------|--------|---------|--------|
| Supervisor Routing | ✗ | 6 | Zu kurz — 350m Routing-Limit |
| Comms Agent | ✓ | 492 | E-Mail vollstaendig generiert |
| Code Agent | ✓ | 862 | Python-Funktion korrekt |
| Researcher Agent | ✓ | 347 | LangGraph erklaert |
| Notes Agent | ✗ | 22 | ChromaDB `notes`: 0 Dokumente |
| Handoff Agent | ✓ | 234 | Prompt fuer Claude.ai generiert |

**Routing:** 350m routet unzuverlaessig — bekannte Modellgroeßen-Limitation.
Notes FAIL: Routing-Limit, Notiz nicht in ChromaDB geschrieben.

---

## Performance-Vergleich: Binary vs. Python-Wrapper

| Metrik | llama-cpp-python 0.3.23 | llama-server b9895 |
|--------|------------------------|-------------------|
| Startup-Zeit | ~20s | ~2s |
| Token/Sec | ~24 t/s | ~25 t/s |
| `--jinja` Support | Nein | Ja |
| Echte Log-Datei | Nein (Thread-Logging) | Ja (`--log-disable` noetig) |
| Tool-Calling (native) | Nein | Ja (verifiziert) |

---

## Tool-Calling Verifikation (2026-07-20)

Direkter Test der Binary mit `--jinja` und OpenAI `tools`-API:

```json
{
  "finish_reason": "tool_calls",
  "tool_calls": [{"name": "save_note", "arguments": "{\"text\": \"Test erfolgreich\"}"}]
}
```

**Ergebnis:** Binary mit `--jinja` produziert echte `tool_calls` — verifiziert.
Das 350m-Modell kann Tool-Calling wenn der Server korrekt konfiguriert ist.
Vorherige Annahme ("350m kann kein Tool-Calling") war falsch — war ein Konfigurationsproblem.

---

## Phoenix Observability

**Traces:** ✓ aktiv
**Projekt:** `local-agent`
**Readiness-Check:** ✓ `/v1/projects` (kein TIMEOUT)
**LangChain Auto-Instrumentierung:** Aktiv

---

## Swap-Aenderungen (2026-07-20)

| Datei | Commit | Aenderung |
|-------|--------|-----------|
| `scripts/sandbox/start_full.py` | `719a8cb303f6` | llama-cpp-python → Binary |
| `scripts/sandbox/start_quick.py` | `92feb17b71c0` | llama-cpp-python → Binary |
| `scripts/sandbox/inspect_phoenix.py` | `5f2bbb3c6eb8` | llama-cpp-python → Binary |
| `scripts/sandbox/test_mcp_toolcall.py` | `4b4334e51455` | llama-cpp-python → Binary |

---

## Bekannte Limitierungen

1. **Binary-Pfad hardcoded:** `/tmp/llama-b9895/llama-server` — muss bei jedem Sandbox-Start neu heruntergeladen werden
2. **350m Routing:** Fast alles → meta (Fallback) — auf Host mit Tiny-Modell erwartet besser
3. **Notes/ChromaDB:** Schreibt nicht — Routing-Limit
4. **Embedding-Server (Port 8081):** Nicht gestartet

---

## Naechste Schritte fuer Host (janhet)

1. Binary b9895 auf janhet installieren (oder neuer)
2. Tool-Calling mit Granite-4.0-H-Tiny (4B) testen
3. MCP-Tools (`git_log`, `fetch`) via `bind_tools()` + `--jinja` aktivieren
4. Notes-Agent mit echtem Routing testen
