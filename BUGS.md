# Known issues

## Researcher tool calls

- **Symptom**: Crash with `EISDIR: illegal operation on a directory, read`
- **Cause**: Granite tiny-h calls `read_text_file` on a path that's actually a directory
- **Workaround**: Reinforce `SYSTEM_PROMPT` to remind Granite to call `list_directory` first
- **Future fix**: Use LangChain's `middleware` system to wrap MCP tools with try/except
  (current version doesn't expose `tool_node_kwargs` on `create_agent`)

## Open WebUI follow-ups

- **Symptom**: Phantom requests `{"follow_ups": [...]}` polluting agent logs
- **Cause**: Open WebUI auto-generates follow-up suggestions
- **Workaround**: Filter in `supervisor.invoke_supervisor` (already in place)
- **Better fix**: Disable Follow Up Generation in Open WebUI Settings → Interface

## mcp.json Pfad nach Ordner-Umstrukturierung (2026-07-16)

- **Symptom**: Agent Server kann `mcp/mcp.json` nicht laden, `FileNotFoundError`
  beim Start — betrifft jede **neue** Sandbox/Docker/Host-Session, die den Code
  frisch von GitHub klont. Die aktuell laufende Sandbox-Session ist nicht
  betroffen, da sie den alten Pfad noch im eigenen Dateisystem hat.
- **Cause**: `agents/server/tools.py` Z.39 hat den Pfad hart codiert:
  `config_path = PROJECT_ROOT / "mcp" / "mcp.json"`. Im Rahmen der
  Aufräumarbeiten wurde die Config-Struktur auf Umgebungs-Ordner umgestellt
  (`mcp/sandbox/mcp.json`, später `mcp/docker/mcp.json`, `mcp/host/mcp.json`),
  `tools.py` wurde dabei noch nicht angepasst.
- **Grundsatz**: Pfade sollen grundsätzlich nicht hart codiert werden, außer
  wenn zwingend nötig.
- **Offene Frage vor dem Fix**: Wie soll der Code erkennen, in welcher der
  drei Umgebungen (Sandbox/Docker/Host) er läuft, um automatisch den
  richtigen Unterordner zu wählen? Z.B. über eine Umgebungsvariable wie
  `LOCAL_AGENT_ENV=sandbox`. Das ist eine bewusste Architektur-Entscheidung,
  noch nicht getroffen — daher noch nicht behoben.
- **Muss behoben sein, bevor**: die nächste neue Sandbox-Session den Code
  frisch klont.

## Phoenix Log-Check False Positive (2026-07-16)

- **Symptom**: `tests/test_stack.py` meldet Fehler in `phoenix.log` beim
  Log-Check, obwohl Phoenix korrekt läuft.
- **Cause**: Die Log-Check-Funktion sucht nach dem bloßen String `"ERROR"`.
  Phoenix schreibt beim Start SQL-`CREATE TABLE`-Statements, deren
  Constraint-Namen den String `"ERROR"` enthalten — z.B.
  `CONSTRAINT "ck_spans_\`valid_status\`" CHECK (status_code IN ('OK', 'ERROR', ...))`.
  Das ist kein Laufzeitfehler, sondern normales Datenbankschema-Logging.
- **Workaround**: Log-Check-Ergebnis für Phoenix manuell ignorieren, wenn
  der Kontext zeigt dass es sich um `CREATE TABLE` oder `CHECK` Statements handelt.
- **Fix**: Log-Check-Funktion in `tests/test_stack.py` präzisieren — z.B.
  auf Muster wie `"ERROR:"` oder `"Exception:"` (mit Doppelpunkt) prüfen
  statt auf bloßes Vorkommen von `"ERROR"`. Alternativ: nur Zeilen ab einem
  bestimmten Log-Level-Präfix (`[ERROR]`, `ERROR -`) scannen.
- **Priorität**: Niedrig — kein Einfluss auf Stack-Funktion, nur auf
  Testübersicht (False Alarm statt echtem Fehler).

---

## Tool-Calling nicht testbar in der Sandbox (llama-cpp-python Limitation)

**Stand:** 2026-07-17
**Schwere:** Bekannte Limitation — kein Fix noetig, nur Dokumentation

### Problem

In der Sandbox wird llama-server ueber den Python-Wrapper `llama-cpp-python` gestartet.
Dieser Wrapper unterstuetzt den `--jinja` Flag nicht — der fuer natives OpenAI-kompatibles
Tool-Calling zwingend erforderlich ist.

Die vollstaendige Tool-Calling-Kette besteht aus drei Teilen die zwingend zusammengehoeren:
1. `supports_tools: true` in `litellm_config.yaml` — damit LiteLLM das tools-Array durchreicht
2. `bind_tools()` in LangChain — strukturierte API statt manueller XML-Tags
3. `--jinja` in llama-server — aktiviert natives Chat-Template fuer Tool-Calling

Punkt 3 ist in der Sandbox nicht verfuegbar.

### Auswirkung

- Tool-Calling mit dem 350m Modell ist in der Sandbox nicht testbar
- Das Modell ignoriert Tool-Prompts und antwortet direkt (bewiesen via Phoenix Trace)
- `tool_formatter.py` (manuelles XML) ist ein Workaround der nicht zuverlaessig funktioniert

### Loesung

Tool-Calling ist ausschliesslich auf dem Host testbar:
- Host nutzt Binary `llama-server` mit `--jinja` Flag
- Granite ist nativ in der llama.cpp Jinja-Template-Liste enthalten
- Dort mit `bind_tools()` + `supports_tools: true` + `--jinja` testen

### Referenz

- llama.cpp Function Calling Docs: https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md
- Granite native support bestaetigt in llama.cpp Server README

---

## Grammar Constraint via LiteLLM nicht nutzbar (extra_body Konflikt)

**Stand:** 2026-07-17
**Getestet in:** Sandbox 2
**Reverted:** Ja — supervisor.py zurueck auf alten Stand

### Was versucht wurde

Router-Prompt in supervisor.py auf Few-Shot + Wenn-Dann-Heuristik umgestellt
und Grammar Constraint ergaenzt um das 350m Modell auf exakt einen gueltigen
Token zu zwingen:

    grammar = 'root ::= "comms" | "researcher" | "notes" | "code" | "meta" | "handoff"'
    response = await router_llm.ainvoke(messages, extra_body={"grammar": grammar})

### Was passiert ist

LiteLLM 1.92.0 behandelt Requests mit  anders als normale Requests.
Der  Parameter triggert eine erneute Key-Validierung gegen die DB.
Da keine DB verbunden ist, kommt 'No connected db.' zurueck — Stack bricht zusammen.
Ergebnis: 3/6 Tests statt vorher 4/6.

### Erkenntnis

-  ist ein llama.cpp-nativer Parameter — nicht LiteLLM-kompatibel via extra_body
- Grammar Constraint muss direkt an llama-server Port 8080 gesendet werden
- Oder: Router-LLM in supervisor.py direkt auf llama-server zeigen lassen (ohne LiteLLM)
- Oder: Grammar-Thema erst auf dem Host angehen wo Granite-Tiny kein Routing-Problem hat

### Status

Reverted. supervisor.py zurueck auf Zero-Shot Prompt ohne grammar Constraint.
Routing bleibt ein bekanntes 350m-Limit — wird auf dem Host behoben.
