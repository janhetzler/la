# prompts/ -- Agenten-Konfiguration und System-Prompts

Dieses Verzeichnis enthaelt alle Prompts und Konfigurationen fuer die Agenten
des Local Agent Stacks. Kein Prompt steht mehr hartkodiert im Python-Code.

---

## Kompletter Datenfluss

Von der Eingabe bis zur Antwort -- was passiert wo:

```
1. Du tippst in chat.py oder VS Code
        |
        | HTTP POST /v1/chat/completions
        v
2. Agent Server -- agents/server/server.py (Port 8002)
        |
        | ruft invoke_supervisor_sync()
        v
3. Supervisor -- agents/server/supervisor.py
        |
        | liest Router-Prompt aus
        | --> prompts/agents/router.md
        |
        | Spracherkennung (vereinfacht: immer "English")
        |
        | Routing-Entscheidung via LLM:
        | --> LiteLLM (Port 4000)
        |     --> llama-server (Port 8080)
        |
        | je nach Routing-Ergebnis:
        v
4a. Textbasierter Agent (z.B. comms, code)
        |
        | agents/server/comms.py
        | --> agent_loader.load_agent("comms")
        |     --> liest prompts/agents/comms.md
        |     --> liest prompts/shared/user_profile.md
        |     --> liest prompts/shared/project_context.md
        |     --> inject_shared(): ersetzt {{ user_profile }} etc.
        |
        | --> LiteLLM (Port 4000)
        |     --> llama-server (Port 8080)
        |
        v
4b. Logik-Agent (z.B. notes, researcher, handoff)
        |
        | agents/server/notes.py
        | --> agent_loader.load_agent("notes")
        |     --> liest prompts/agents/notes.md
        |     --> Prompt-Injection wie oben
        |
        | --> eigene Tools (ChromaDB, MCP-Server)
        | --> LiteLLM (Port 4000)
        |     --> llama-server (Port 8080)
        |
        v
5. Antwort zurueck an server.py --> chat.py --> Du

Parallel (alle Schritte):
        Phoenix (Port 6006) erfasst alle LangChain-Spans als Traces
```

---

## Verzeichnisstruktur

```
prompts/
├── README.md                  <- Diese Datei
├── shared/
│   ├── README.md              <- Anleitung fuer user_profile + project_context
│   ├── user_profile.md        <- Wer bist du? Praeferenzen, Projekte.
│   └── project_context.md     <- Aktueller Stack, aktive Aufgaben.
└── agents/
    ├── README.md              <- Anleitung fuer Agent-.md Dateien
    ├── TEMPLATE.md            <- Vorlage fuer textbasierte Agenten
    ├── TEMPLATE_LOGIC.md      <- Vorlage fuer Logik-Agenten
    ├── router.md              <- Router-System-Prompt
    ├── comms.md               <- Comms Agent
    ├── code.md                <- Code Agent
    ├── notes.md               <- Notes Agent
    ├── researcher.md          <- Researcher Agent
    └── handoff.md             <- Handoff Agent
```

---

## Neuen Agenten anlegen

### Textbasierter Agent (kein Python noetig)

1. `prompts/agents/TEMPLATE.md` kopieren nach `prompts/agents/<name>.md`
2. Frontmatter ausfuellen (name, description, tools, temperature)
3. System-Prompt schreiben
4. In `agents/server/supervisor.py` den neuen Agenten im `invoke_supervisor()`
   Block eintragen (elif agent_name == "<name>")
5. Fertig -- agent_loader.py laedt ihn automatisch, Router weiss davon

### Logik-Agent (mit eigenem Python)

1. `prompts/agents/TEMPLATE_LOGIC.md` kopieren nach `prompts/agents/<name>.md`
2. `agents/server/TEMPLATE.py` kopieren nach `agents/server/<name>.py`
3. `<agent_name>` in der Python-Datei durch echten Namen ersetzen
4. Eigene Logik implementieren
5. In `supervisor.py` eintragen
6. Import in `supervisor.py` hinzufuegen: `from <name> import invoke_<name>`

---

## Template-Variablen in Prompts

| Variable | Ersetzt durch | Quelle |
|---|---|---|
| `{{ user_profile }}` | Persoenlicher Kontext | `prompts/shared/user_profile.md` |
| `{{ project_context }}` | Projektkontext | `prompts/shared/project_context.md` |
| `{user_language}` | Erkannte Sprache | supervisor.py (aktuell: immer "English") |
| `{vault_path}` | Pfad zur Wissensdatenbank | notes.py (nur Notes Agent) |
| `{project_root}` | Repo-Wurzelpfad | researcher_v2.py (nur Researcher) |

---

## YAML-Frontmatter Felder

| Feld | Pflicht | Beschreibung |
|---|---|---|
| `name` | ja | Agent-Name (muss eindeutig sein) |
| `description` | ja | Kurzbeschreibung fuer Router-Prompt (in Anfuehrungszeichen wenn Doppelpunkt) |
| `tools` | ja | Liste der MCP-Tool-Namen (leer: `[]`) |
| `temperature` | nein | LLM-Temperatur (default: 0.3) |
| `model` | nein | Modell-Override (null = DEFAULT_LLM aus config) |
| `python` | nein | Python-Datei fuer Logik-Agenten (nur Dokumentation) |

---

## Wichtige Hinweise

**Doppelpunkt in description:** Immer in Anfuehrungszeichen setzen:
```yaml
description: "Erstellt Prompts fuer Claude.ai: lange Texte, tiefe Analysen."
```
Ohne Anfuehrungszeichen bricht der YAML-Parser ab (bekannter Bug).

**HTML-Kommentare:** Niemals `<!-- -->` in Prompt-Texten verwenden.
Das 350m Modell interpretiert sie als Chat-Template und produziert Garbage-Tokens.

**Few-Shot fuer 350m:** Funktioniert nicht zuverlaessig -- das Modell gibt
das erste Token der User-Message zurueck. Zero-Shot bleibt die stabile Loesung.
Auf dem Host mit Granite-Tiny koennen Few-Shot Prompts getestet werden.
