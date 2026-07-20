# STYLEGUIDE.md -- Programmierrichtlinien Local Agent (LA)

Dieses Dokument definiert verbindliche Konventionen fuer den gesamten Code
im Repository janhetzler/la. Neue Sessions und Agenten lesen dies zuerst.

---

## Sprache

Alle Kommentare, Docstrings und Variablennamen sind auf Deutsch.

- Kommentare: Deutsch
- Docstrings: Deutsch
- Variablennamen: Englisch (Python-Konvention), aber beschreibend
- Fehlermeldungen: Deutsch
- Commit-Messages: Deutsch oder Englisch, konsistent pro Session

Ausnahmen:
- Externe Library-Bezeichnungen bleiben englisch (z.B. ChatOpenAI, LangGraph)
- Umgebungsvariablen bleiben englisch (z.B. LITELLM_URL, LA_ENV)

---

## Datei-Header (Docstring)

Jede Python-Datei beginnt mit einem Docstring:

    """
    supervisor.py -- Orchestrierung und Routing der Benutzeranfragen

    Empfaengt Nachrichten vom Agent Server, erkennt die Sprache,
    routet zur passenden Agenten-Funktion und gibt die Antwort zurueck.

    Abhaengigkeiten: config.py, agent_loader.py, alle Agenten-Module
    """

---

## Kommentare

Abschnitts-Trenner:

    # Konfiguration

    # Hilfsfunktionen

    # Hauptlogik

Inline-Kommentare erklaeren das Warum, nicht das Was:

    time.sleep(3)  # Trace-Delivery abwarten bevor Phoenix abgefragt wird

---

## Funktionen und Methoden

Docstrings einzeilig wenn moeglich:

    def ram_used_mb() -> int:
        """Genutzter RAM in MB via /proc/meminfo."""

    async def invoke_comms(user_message: str, user_language: str = "English") -> str:
        """
        Erstellt eine schriftliche Antwort in der Sprache des Benutzers.
        Laedt Prompt aus prompts/agents/comms.md via agent_loader.
        """

---

## Namenskonventionen

| Element | Konvention | Beispiel |
|---|---|---|
| Funktionen | snake_case | load_agent(), wait_for() |
| Klassen | PascalCase | AgentLoader |
| Konstanten | SCREAMING_SNAKE | LITELLM_KEY, LOG_DIR |
| Private | _underscore | _get_agent(), _cached_tools |
| Dateien | snake_case.py | agent_loader.py |

---

## Fehlerbehandlung

Fehler immer mit Kontext ausgeben:

    try:
        result = await llm.ainvoke(messages)
    except Exception as e:
        print(f"LLM-Aufruf fehlgeschlagen: {e}", flush=True)
        return ""

Nie leere except-Bloecke:

    except:
        pass  # FALSCH

---

## Ausgaben

- flush=True bei allen print() Aufrufen im Stack
- Format: [Komponentenname] Nachricht

    print(f"[supervisor] Routing: {user_lang} -> {agent_name}", flush=True)

---

## Prompts

- Prompts gehoeren nicht in Python-Dateien
- Prompts liegen in prompts/agents/*.md (YAML-Frontmatter + Text)
- Template-Variablen: {user_language}, {{ user_profile }}, {{ project_context }}
- Keine HTML-Kommentare in Prompt-Dateien (verwirren kleine Modelle)

---

## Umgebungsvariablen

Alle Werte via os.getenv(), keine hardcodierten URLs oder Keys:

    # Korrekt
    LITELLM_URL = os.getenv("LITELLM_URL", "http://127.0.0.1:4000")

    # Falsch
    LITELLM_URL = "http://127.0.0.1:4000"

---

## GitHub Pushes

- Niemals Dateiinhalt ueber Shell-Pipes pushen
- Immer: Datei lokal schreiben, dann via Python urllib pushen
- Syntax vor Push mit compile() pruefen
- Nach Push Zeilenzahl im Repo verifizieren

---

## Neue Dateien anlegen

Checkliste:
1. Datei-Header Docstring
2. Imports: stdlib, then third-party, then local
3. Konstanten oben
4. Funktionen/Klassen
5. if __name__ == "__main__": Block

---

## Component Documentation (2026-07-20)

Jede **kritische Infrastruktur-Komponente** erhaelt ein eigenes Dokumentdatei unter `docs/`.
Diese Dokumentation folgt dem **COMPONENT_SWAP_TEMPLATE.md** und dokumentiert:

- Was ist diese Komponente? (Zweck, Version, Rolle im Stack)
- Welche Alternativen/Versionen gibt es?
- Wie sind die Abhängigkeiten strukturiert?
- Welche Config-Dateien muss ich ändern, wenn ich die Komponente austausche?
- Schritt-für-Schritt Swap-Szenarios

**Aktuell dokumentierte Komponenten:**
- `docs/LLAMA.md` — Reasoning Server (llama-cpp-python vs. llama-server Binary)
- `docs/LITELLM.md` — (geplant) API Gateway
- `docs/CHROMADB.md` — (geplant) Vector Database
- `docs/PHOENIX.md` — (geplant) Observability
- etc.

**Warum?** Komponenten-Austausche geschehen regelmäßig (Versionsupgrades, 
alternative Implementierungen, Performance-Optimierungen). Statt jedes Mal 
von vorne zu debuggen, haben wir eine **verbindliche Schablone** die zeigt:
- Welche Scripts/Dateien ändern
- Welche Tests laufen danach
- Welcher Fallback-Plan im Fehlerfall

**Agenten-Entwicklung:**

Neue Agenten und Prompt-Aenderungen folgen `docs/AGENT_DEVELOPMENT.md`:
- Nach jeder Prompt-Aenderung: `scripts/sandbox/inspect_phoenix.py` laufen lassen
- Trace-Datei unter `docs/traces/sandbox/` mit vorheriger vergleichen
- Erst wenn Trace zeigt dass Routing korrekt: pushen

**Neue Komponenten-Doc erstellen:**
1. Kopiere `docs/COMPONENT_SWAP_TEMPLATE.md`
2. Ersetze alle Platzhalter [COMPONENT], [VERSION], etc.
3. Schreibe mindestens Punkt 1-6 (Overview, Versions, Architecture, Config, Swap Scenario, Troubleshooting)
4. Pushe mit Commit-Message: `Add: docs/[COMPONENT].md`

---

## Changelog (STYLEGUIDE.md)

| Datum | Aenderung |
|-------|-----------|
| 2026-07-20 | Added: Component Documentation Sektion |
| 2026-07-20 | Added: Agenten-Entwicklung Sektion + Trace-Workflow |

