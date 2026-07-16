# scripts/sandbox/ — Sandbox Start-Skripte

Administrative Skripte für die Claude-Sandbox-Umgebung.
Destilliert aus dem was in dieser Session erprobt wurde.

---

## Wichtiger Hintergrund

**Alles stirbt wenn ein bash_tool-Call endet.**
Threads, Subprocesses, nohup — alles. Es gibt keinen Weg,
Prozesse über mehrere Calls hinweg am Leben zu halten.

Das bedeutet: jedes dieser Skripte muss vollständig in einem
einzigen Aufruf laufen. Nichts kann "im Hintergrund laufen bleiben".

---

## Wann welches Skript

### 1. `import_check.py` — Schnellster Check, ~2 Sekunden

```bash
cd /home/claude/la && python3 scripts/sandbox/import_check.py
```

**Wann:** Bevor überhaupt etwas gestartet wird. Nach Git-Pulls, nach
Code-Änderungen, immer als erstes. Prüft ob alle zentralen Module
fehlerfrei importieren, ohne den Stack zu starten.

Zeigt auch: VALID_AGENTS vs. registrierte Modelle in server.py —
Diskrepanzen werden sofort sichtbar.

### 2. `start_quick.py` — Schlanker Stack, ~90 Sekunden

```bash
cd /home/claude/la && python3 scripts/sandbox/start_quick.py
```

**Wann:** Wenn man sehen will ob der Stack grundsätzlich läuft und
ein Request durchgeht — ohne den vollen 6-Agenten-Testlauf.
Kein Phoenix (spart 20s Startzeit). Ein gezielter Request über
LiteLLM → Agent Server (Port 4000 → 8002).

Zeitlich sicher: ~90s, weit unter dem bash_tool-Limit von ~5 Min.

### 3. `start_full.py` — Vollständig, ~3 Minuten

```bash
cd /home/claude/la && python3 scripts/sandbox/start_full.py
```

**Wann:** Wenn alle 6 Agenten, ChromaDB, Phoenix und Logs geprüft
werden sollen. Ruft `tests/run_tests.py` auf — die kanonische
Quelle für den vollständigen Testlauf.

ACHTUNG: Knapp innerhalb des bash_tool-Limits. Nicht starten wenn
der Context schon viel verbraucht hat oder andere zeitintensive
Operationen folgen sollen.

---

## Log-Dateien

Alle Logs landen in `/tmp/logs/`:

| Datei | Inhalt |
|-------|--------|
| `litellm.log` | HTTP-Requests, Routing-Entscheidungen |
| `phoenix.log` | Trace-Empfang, Start-Status |
| `llama-server.log` | Aktuell leer (uvicorn-Thread-Problem) |
| `agent-server.log` | Aktuell leer (uvicorn-Thread-Problem) |

llama-server und Agent Server Output landet in stderr des
Python-Prozesses — sichtbar im bash_tool-Ergebnis selbst.

---

## Für janhet (Produktion)

Diese Skripte sind **nur für die Sandbox**. Auf janhet:
- llama-server läuft als Binary (`/home/user/restart_llamaorgakt.sh`)
- Dienste werden über systemd oder `scripts/start_*.sh` gestartet
- Vollständige Anleitung: `docs/INSTALL_JANHET.md`
