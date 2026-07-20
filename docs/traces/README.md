# docs/traces/ — Request Trace Logs

Dieser Ordner enthält vollständige Trace-Logs für einzelne
Request-Durchläufe durch den Local Agent Stack.

## Zweck

Jede Trace-Datei dokumentiert einen kompletten Request von
User-Input bis finale Antwort — mit exakten Strings, Performance-
Daten und Infrastruktur-Logs. Das ermöglicht:

- Prompt-Änderungen messbar machen (vorher/nachher vergleichen)
- Routing-Entscheidungen nachvollziehen
- Performance-Regressions erkennen
- Agenten-Entwicklung: neuen Agenten testen und dokumentieren

## Struktur

| Ordner | Umgebung |
|--------|----------|
| `sandbox/` | Claude Sandbox (bash_tool) |
| `host/` | janhet (AMD EPYC, produktiv) |
| `docker/` | Docker-Container |

## Dateiname

```
YYYY-MM-DD_[request-slug].md
Beispiel: 2026-07-20_email-to-boss.md
```

## Erzeugt von

`scripts/sandbox/inspect_phoenix.py` — erzeugt automatisch
eine Trace-Datei nach jedem Request-Durchlauf.

## Verwandt

- `docs/AGENT_DEVELOPMENT.md` — Anleitung fuer neue Agenten
- `docs/SANDBOX.md` — Stack-Aufbau
