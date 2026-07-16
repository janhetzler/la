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
