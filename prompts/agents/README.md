# prompts/agents/ -- Agent-Konfigurationsdateien

Jede `.md` Datei hier definiert einen Agenten vollstaendig:
YAML-Frontmatter (Metadaten) + Markdown-Text (System-Prompt).

---

## Dateiformat

```markdown
---
name: comms
description: "E-Mails, Nachrichten, Kurzberichte."
tools: []
temperature: 0.3
model: null
---
Du bist der Kommunikations-Spezialist.

{{ project_context }}

{{ user_profile }}

Deine Aufgabe: ...
```

---

## Vorhandene Agenten

| Datei | Agent | Typ | Tools |
|---|---|---|---|
| `router.md` | Router | System | -- |
| `comms.md` | Comms | textbasiert | keine |
| `code.md` | Code | textbasiert | git_log, git_status, fetch |
| `notes.md` | Notes | Logik (notes.py) | ChromaDB |
| `researcher.md` | Researcher | Logik (researcher_v2.py) | fetch, git_log |
| `handoff.md` | Handoff | Logik (handoff.py) | keine |

---

## Templates

| Datei | Verwenden fuer |
|---|---|
| `TEMPLATE.md` | Neuen textbasierten Agenten anlegen |
| `TEMPLATE_LOGIC.md` | Neuen Logik-Agenten anlegen (mit Python) |

---

## Neuen Agenten anlegen

Schritt-fuer-Schritt Anleitung: siehe `prompts/README.md`

---

## Wichtige Regeln

1. `description` immer in Anfuehrungszeichen wenn ein Doppelpunkt enthalten ist
2. Keine HTML-Kommentare `<!-- -->` im Prompt-Text
3. Template-Variablen: `{{ user_profile }}`, `{{ project_context }}`, `{user_language}`
4. Nach dem Anlegen: Agent in `supervisor.py` eintragen
