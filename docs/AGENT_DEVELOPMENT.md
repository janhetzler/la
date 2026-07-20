# AGENT_DEVELOPMENT.md — Anleitung: Neuen Agenten entwickeln

Dieses Dokument beschreibt wie ein neuer Agent zum Local Agent Stack
hinzugefuegt wird — von der Konzeption bis zum getesteten Einsatz.

---

## 1. Konzept: Wie Agenten funktionieren

Jeder Agent besteht aus **einer einzigen .md Datei** unter `prompts/agents/`.
Kein Python anfassen — der Stack laedt Agenten automatisch.

```
prompts/agents/
  ├── router.md       ← Supervisor-Routing-Prompt (nicht aendern ohne Test)
  ├── comms.md        ← Kommunikations-Agent
  ├── code.md         ← Code-Agent
  ├── notes.md        ← Notizen-Agent (mit ChromaDB-Tools)
  ├── researcher.md   ← Recherche-Agent (mit MCP-Tools)
  └── handoff.md      ← Handoff-Agent (fuer schwere Aufgaben)
```

Jede Datei kombiniert YAML-Metadaten und System-Prompt:

```yaml
---
name: mein-agent
description: Kurze Beschreibung was dieser Agent tut (1 Satz, Englisch).
tools: []
temperature: 0.3
---
Du bist der Spezialist fuer [Thema].
{{ project_context }}
{{ user_profile }}
```

**Was passiert automatisch:**
- `agent_loader.py` parst das Frontmatter und laedt den Prompt
- `supervisor.py` liest `description` und baut den Router-Prompt dynamisch
- `{{ project_context }}` und `{{ user_profile }}` werden via Template-Injection
  aus `prompts/shared/` befuellt

---

## 2. Schritt-fuer-Schritt: Neuen Agenten hinzufuegen

### Schritt 1 — Agent-Datei erstellen

```bash
# Neue Datei anlegen
cp prompts/agents/comms.md prompts/agents/mein-agent.md
```

Frontmatter anpassen:
```yaml
---
name: mein-agent
description: [Englisch, 1 Satz, praezise — wird vom Router genutzt]
tools: []
temperature: 0.3
---
[System-Prompt hier]
{{ project_context }}
{{ user_profile }}
```

**Wichtig fuer `description`:**
- Englisch (Router-Prompt ist englisch)
- Maximal 1 Satz
- Praezise — das Modell entscheidet anhand dieser Beschreibung ob es routet
- Kein HTML, keine Kommentare (`<!-- -->` verwirren das 350m-Modell)

### Schritt 2 — Router-Prompt ergaenzen (router.md)

`prompts/agents/router.md` enthaelt die Few-Shot-Beispiele fuer den Router.
Nach dem Hinzufuegen eines neuen Agenten: mindestens 2 Beispiele ergaenzen.

```
- "Beispiel-Anfrage 1" -> mein-agent
- "Beispiel-Anfrage 2" -> mein-agent
```

**Achtung:** Englische Beispiele — das Modell routet zuverlaessiger auf Englisch.

### Schritt 3 — Testen

Nach jeder Aenderung an Prompts oder Agent-Dateien:

```bash
# Stack starten + Trace erzeugen
cd /home/claude/la && python3 scripts/sandbox/inspect_phoenix.py
```

Das Script:
1. Startet den kompletten Stack
2. Schickt einen Test-Request
3. Erzeugt automatisch eine Trace-Datei unter `docs/traces/sandbox/`

Die Trace-Datei enthaelt:
- Vollstaendige Span-Kette (was genau ans Modell gesendet wurde)
- Router-Entscheidung (welcher Agent wurde gewaehlt?)
- Finale Antwort
- Performance-Daten
- Aktiver router.md Inhalt

### Schritt 4 — Trace vergleichen

Vergleiche die neue Trace-Datei mit einer vorherigen:

```bash
# Letzte zwei Trace-Dateien vergleichen
ls -lt docs/traces/sandbox/ | head -5
diff docs/traces/sandbox/[alt].md docs/traces/sandbox/[neu].md
```

So siehst du exakt was sich durch die Prompt-Aenderung veraendert hat.

---

## 3. Logik-Agenten (mit Python)

Agenten die Tools oder RAG benoetigen behalten eine Python-Datei:

| Agent | Python-Datei | Grund |
|-------|-------------|-------|
| notes | `agents/server/notes.py` | ChromaDB Tools |
| researcher | `agents/server/researcher_v2.py` | MCP Tools |
| handoff | `agents/server/handoff.py` | Prompt-Aufbereitung |

Fuer diese Agenten:
1. Python-Datei unter `agents/server/` erstellen
2. In `agents/server/server.py` registrieren
3. .md Datei unter `prompts/agents/` erstellen (Prompt + Frontmatter)

---

## 4. Bekannte Grenzen (Sandbox mit 350m Modell)

- **Routing:** Das 350m-Modell routet nicht zuverlaessig — fast alles landet
  bei `meta`. Das ist kein Bug, sondern eine Modellgroessen-Limitation.
  Auf dem Host mit Granite-Tiny (4B) routet es korrekt.
- **Tool-Calling:** Funktioniert mit `--jinja` Flag (bewiesen 2026-07-20).
- **Kontext:** Maximal ~9 Tools gleichzeitig — mehr fuehrt zu Routing-Fehlern.

---

## 5. Checkliste: Neuer Agent

- [ ] `prompts/agents/[name].md` erstellt
- [ ] Frontmatter: name, description (Englisch), tools, temperature
- [ ] Kein HTML-Kommentar im Prompt
- [ ] `router.md` um 2+ Beispiele ergaenzt
- [ ] `inspect_phoenix.py` ausgefuehrt
- [ ] Trace-Datei unter `docs/traces/sandbox/` geprueft
- [ ] Router-Entscheidung korrekt? (oder 350m-Limit — dann auf Host testen)
- [ ] Bei Logik-Agent: Python-Datei + server.py Registrierung

---

## Verwandt

- `docs/SANDBOX.md` — Stack-Aufbau
- `docs/traces/README.md` — Trace-Logs Erklaerung
- `docs/ROADMAP.md` — Architektur-Entscheidungen
- `BUGS.md` — bekannte Probleme (insb. Routing-Limit)
- `scripts/sandbox/inspect_phoenix.py` — Test + Trace-Erzeugung
