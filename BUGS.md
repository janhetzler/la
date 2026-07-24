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

## HTML-Kommentare in .md Prompts verwirren 350m Modell (2026-07-18)

### Symptom

`router.md` hatte einen HTML-Kommentar-Block (`<!-- ... -->`). Das 350m-Modell
generierte danach Garbage-Tokens statt einem gueltigen Agent-Namen:
- `<|` — Chat-Template-Start-Token
- `<code>` — HTML-Tag
- `<` — unvollstaendiges Token

### Ursache

Das 350m-Modell interpretiert `<!--` als Beginn eines Chat-Templates und
wechselt in den Modus "generiere Assistant-Tokens", statt den Router-Prompt
zu befolgen. Der Kommentar-Block erschien am Ende von `router.md` nach dem
eigentlichen Prompt-Inhalt.

### Fix

HTML-Kommentar-Block aus `router.md` entfernt. Zero-Shot Prompt wieder sauber.
Commit: `9cf389b`

### Regel

Keine HTML-Kommentare (`<!-- -->`) in `.md`-Prompt-Dateien die ans Modell gehen.
Fuer Entwickler-Notizen: separate Datei oder YAML-Frontmatter-Felder verwenden.

---

## Few-Shot + Heuristik funktioniert nicht mit 350m Modell (2026-07-18)

### Symptom

Versuch: `router.md` mit Few-Shot-Beispielen und Wenn-Dann-Heuristik
("Wenn die Frage mit 'Write' beginnt -> comms").
Ergebnis: Modell gibt erstes Token der User-Message zurueck statt Agent-Namen:
- `"Can you help me?"` -> `"Help"`
- `"Write a short..."` -> `"<|exactly one word>"`
- `"Prepare a prompt..."` -> die gesamte User-Message

### Ursache

Das 350m-Modell ist zu klein um Few-Shot-Beispiele korrekt zu interpretieren
und daraus ein Output-Format abzuleiten. Es "sieht" die Beispiele als Teil der
Konversation und setzt die Mustervervollstaendigung fort — statt den
Instruktionen zu folgen.

Ausserdem: der `<|exactly one word>` Instruction-Marker aus dem Prompt wird
literal wiedergegeben — das Modell "zitiert" Prompt-Fragmente statt zu generieren.

### Fix

Reverted auf Zero-Shot Prompt. Commit: `02012de`

### Erkenntnis

- Zero-Shot ist zuverlaessiger als Few-Shot fuer 350m Modelle
- Instruction-Marker wie `<|exactly one word>` nicht im Prompt verwenden —
  werden von kleinen Modellen literal kopiert
- Few-Shot Router-Prompt auf dem Host mit Granite-4.0-H-Tiny (4B) testen
  wo das Routing nachweislich korrekt funktioniert

### Status

Offen fuer Host-Test. Auf 350m: Zero-Shot bleibt die stabile Loesung.

---

## BUG-008: Bifrost NPX-Binary ist statisch gelinkt -- kein Custom Plugin Support

**Status:** Bestaetigt
**Datum:** 2026-07-19

**Problem:** Die Bifrost Binary die via NPX () heruntergeladen wird ist statisch gelinkt. Go's Plugin-System benoetigt eine dynamisch gelinkte Binary. Custom Plugins (.so Dateien) werden nicht geladen -- kein Fehler, kein Log-Eintrag, einfach ignoriert.

**Symptom:** Plugin steht in config_plugins SQLite-Tabelle mit enabled=1, aber kein "plugin status: llmtrim - active" im Log.

**Direkter Binary-Start:** Crasht mit Segfault bei plugin._Cfunc_pluginOpen -- bestaetigt dass Binary versucht Plugin zu laden aber scheitert.

**Workaround:** Keiner bekannt ohne eigene Bifrost-Kompilierung.

**Verwandt:** Bifrost OSS kann nicht kompiliert werden wegen fehlendem framework/webhooks Paket (Enterprise-only).

---

## BUG-009: Bifrost OSS nicht kompilierbar -- framework/webhooks fehlt

**Status:** Bestaetigt
**Datum:** 2026-07-19

**Problem:**  ist im OSS-Repository nicht vorhanden. Das Paket wird von  und  importiert. Kompilierung schlaegt fehl mit: 

**Getestete Versionen:** transports/v1.6.4 (aktuell), transports/v1.5.4 hatte noch keine Webhook-Abhaengigkeit -- aber v1.5.4 NPX-Binary laeuft nicht unter Node 20.

**Workaround:** Keiner ohne Enterprise-Lizenz oder vollstaendigen Fork.

---

## BUG-010: Go-Version-Mismatch bei Bifrost Plugins

**Status:** Bestaetigt, Workaround bekannt
**Datum:** 2026-07-19

**Problem:** Go Plugin-System erfordert exakt gleiche Go-Version zwischen Binary und Plugin. Mismatch fuehrt zu Crash.

**Loesung:** Go-Version der Binary via  ermitteln, dann Plugin mit exakt dieser Version kompilieren.

**Bifrost v1.6.4 Binary:** go1.26.4


---

## BUG-011: Bifrost Docker Binary ebenfalls statisch gelinkt -- Plugin-System nur zur Compile-Zeit

**Status:** Bestaetigt via Sandbox-Test (2026-07-19)
**Getestete Binary:** https://github.com/janhetzler/la/releases/download/granite-models/bifrost-http-0

**Analyse:**
-  →  -- statisch gelinkt
- / Symbole: nicht vorhanden
- Plugin-Code (, , ) ist vorhanden aber zur Compile-Zeit gebunden
- Go-Version: go1.26.4
- Keine CLI-Flags fuer Plugin-Pfade

**Fazit:** Bifrost Plugin-System ist statisch eingebaut. Externe Go Plugins (.so Dateien)
koennen zur Runtime nicht geladen werden -- weder via NPX-Binary noch via Docker-Binary.
Custom Plugins sind nur moeglich wenn Bifrost mit CGO_ENABLED=1 dynamisch kompiliert wird.

**Naechster Schritt:** Python FastAPI-Wrapper als HTTP-Proxy mit llmtrim-Kompression.

---

## BUG-012: entrypoint.sh -- Phoenix und LiteLLM auf 127.0.0.1 statt 0.0.0.0

**Status:** Bestaetigt via Docker-Run (2026-07-20)
**Umgebung:** Docker Container ghcr.io/janhetzler/la:latest

**Symptom:** Phoenix (:6006) und LiteLLM (:4000) sind nicht vom Host erreichbar,
obwohl die Ports im `docker run` Befehl gemappt sind. Nur Agent Server (:8002)
ist erreichbar weil er als einziger auf `0.0.0.0` lauscht.

**Ursache:** `docker/entrypoint.sh` startet Phoenix und LiteLLM mit `--host 127.0.0.1`.
Port-Mapping funktioniert nur wenn der Prozess auf `0.0.0.0` lauscht.

**Fix:** In `docker/entrypoint.sh`:
- Phoenix: `--host 127.0.0.1` → `0.0.0.0`
- LiteLLM: `--host 127.0.0.1` → `0.0.0.0`

**Status:** Fix eingeplant fuer naechsten Docker Build.

---

## BUG-013: entrypoint.sh -- Embedding Server startet nicht (--embedding Syntax falsch)

**Status:** Bestaetigt via Docker-Run (2026-07-20)
**Umgebung:** Docker Container ghcr.io/janhetzler/la:latest

**Symptom:** Embedding Server (:8081) startet nicht.
Log: `__main__.py: error: argument --embedding: expected one argument`

**Ursache:** `docker/entrypoint.sh` ruft `--embedding` ohne Argument auf.
Der llama-cpp-python Server erwartet `--embedding True`.

**Fix:** In `docker/entrypoint.sh`:
- `--embedding \` → `--embedding True \`

**Status:** Fix eingeplant fuer naechsten Docker Build.

---

## BUG-014: entrypoint.sh -- llama-cpp-python statt llama-server Binary (kein --jinja)

**Status:** Bestaetigt via Docker-Run (2026-07-20)
**Umgebung:** Docker Container ghcr.io/janhetzler/la:latest

**Symptom:** Reasoning Server (:8080) laeuft mit `llama_cpp.server` (Python-Wrapper).
`--jinja` Flag ist nicht aktiv -- Tool-Calling funktioniert nicht im Docker.

**Ursache:** `docker/entrypoint.sh` nutzt noch den alten Python-Wrapper.
Der Binary Swap (2026-07-20) wurde nur fuer Sandbox Scripts durchgefuehrt,
nicht fuer `docker/entrypoint.sh`.

**Fix:**
- `Dockerfile`: llama-server Binary b9895 herunterladen nach `/app/bin/llama-server`
- `docker/entrypoint.sh`: `python3 -m llama_cpp.server` → `/app/bin/llama-server --jinja`

**Status:** Fix eingeplant fuer naechsten Docker Build.

---

## BUG-015: Phoenix gRPC Port 4317 Konflikt beim Neustart im Container

**Status:** Bestaetigt via Docker-Run (2026-07-20)
**Umgebung:** Docker Container ghcr.io/janhetzler/la:latest

**Symptom:** Wenn Phoenix neu gestartet wird (z.B. mit anderem --host),
schlaegt der Start fehl:
`RuntimeError: Failed to bind to address [::]:4317`

**Ursache:** Der originale Phoenix-Prozess (PID 24, gestartet via entrypoint.sh)
haelt Port 4317 (gRPC). Ein zweiter Phoenix-Start kann diesen Port nicht binden.
`pkill -f phoenix` killt PID 24 nicht weil er Kind von PID 1 ist.

**Workaround:** `kill -9 24` direkt, dann neuen Phoenix-Prozess starten.

**Fix:** entrypoint.sh: Phoenix direkt auf `0.0.0.0` starten -- dann ist kein
Neustart noetig.

**Status:** Wird durch BUG-012 Fix behoben.

---

## BUG-016: mcp/docker/mcp.json fehlt im Docker Image

**Status:** Bestaetigt via Docker-Run (2026-07-20)
**Umgebung:** Docker Container ghcr.io/janhetzler/la:latest

**Symptom:** Researcher-Agent und Notes-Agent schlagen fehl mit:
`FileNotFoundError: /app/mcp/docker/mcp.json`

**Ursache:** Die Datei `mcp/docker/mcp.json` existiert nicht im Repo und
wurde daher nicht ins Image gebaut.

**Workaround:** Im laufenden Container:
```bash
mkdir -p /app/mcp/docker
echo '{"mcpServers": {}}' > /app/mcp/docker/mcp.json
```

**Fix:** `mcp/docker/mcp.json` mit `fetch`-Server ins Repo pushen.
`mcp_server_git` nicht verwenden — kein Git-Repo im Container.

**Status:** Workaround aktiv, permanenter Fix ausstehend.

---

## BUG-017: ChromaDB Collection nutzt euklidische statt Kosinus-Distanz

**Status:** Bestaetigt via Docker-Run (2026-07-20)
**Umgebung:** Docker + Sandbox

**Symptom:** Notes-Agent findet keine Dokumente obwohl ChromaDB sie enthaelt.
Direkte Suche ohne Agent findet sie (Distance ~820).

**Ursache:** ChromaDB erstellt Collections standardmaessig mit euklidischer
Distanz (L2). Bei nicht-normalisierten Granite-Embeddings (Norm ~50) ergibt
das eine Distance von ~820 statt ~0.16 (Kosinus).
Kosinus-Aehnlichkeit der gleichen Vektoren: 0.84 — eigentlich sehr gut.

**Fix:** Collection mit Kosinus-Distanz erstellen:
```python
client.create_collection(name, metadata={"hnsw:space": "cosine"})
```

In `entrypoint.sh` und `notes.py` anpassen.

**Status:** Manuell gefixt im laufenden Container, Code-Fix ausstehend.

---

## BUG-018: Notes-Agent search_meetings filtert zu restriktiv

**Status:** Bestaetigt via Docker-Run (2026-07-20)
**Umgebung:** Docker + Sandbox

**Symptom:** `search_meetings` gibt keine Ergebnisse zurueck obwohl
ChromaDB Dokumente enthaelt und die Kosinus-Aehnlichkeit 0.84 betraegt.

**Ursache:** In `agents/server/notes.py` Z.88:
```python
if "meeting" in source.lower() or meta.get("type") == "meeting":
```
Nur Dokumente mit "meeting" im Source-Feld werden zurueckgegeben.
Alle anderen Dokumente werden still verworfen.

**Fix:** Filter entfernen oder generalisieren:
```python
meetings.append(f"[{source}, score {score:.2f}]
{doc[:500]}")
```

**Status:** Manuell umgangen (source auf "meeting-docker-test" gesetzt),
Code-Fix ausstehend.

---

## BUG-019: save_note Tool fehlt — kein Agent kann in ChromaDB schreiben

**Status:** Bestaetigt (2026-07-20)
**Umgebung:** Alle Umgebungen

**Symptom:** Kein Agent kann Notizen in ChromaDB speichern. Notes-Agent
antwortet "I can't save the note as it requires access to a tool I don't have."

**Ursache:** `agents/server/notes.py` hat nur Lese-Tools:
- `search_meetings` — RAG-Suche
- `list_directory`, `read_text_file`, etc. — Vault-Lesen

Ein `save_note` Tool mit `collection.add()` wurde nie implementiert.
Das Original-Projekt (xaviervasques/chief-of-staff) nutzt Qdrant, nicht
ChromaDB — ChromaDB-Schreiben ist ein komplett neues Feature.

**Fix:** Neues Tool in `notes.py`:
```python
@tool
def save_note(text: str, title: str = "") -> str:
    """Speichert eine Notiz in ChromaDB."""
    vec = _embed_query(text)
    collection.add(
        documents=[text],
        embeddings=[vec],
        metadatas=[{"category": "notes", "source": f"meeting-{title}"}],
        ids=[f"note-{datetime.now().isoformat()}"]
    )
    return f"Notiz gespeichert: {text[:50]}..."
```

**Status:** Fix ausstehend — hohe Prioritaet.

---

## BUG-020: Researcher-Agent ruft read_text_file auf Verzeichnis auf (EISDIR)

**Status:** Gemeldet via externes Review (2026-07-20)
**Umgebung:** Alle Umgebungen

**Symptom:** LLM ruft `read_text_file(path)` mit einem Verzeichnis-Pfad auf
statt mit einer Datei. Ergebnis: `EISDIR` Fehler (Is a directory).

**Ursache:** Das Modell unterscheidet nicht zuverlaessig zwischen Dateien
und Verzeichnissen. Es sollte zuerst `list_directory` aufrufen und dann
`read_text_file` auf einzelne Dateien.

**Fix:** In `prompts/agents/researcher.md` explizit dokumentieren:
"Always use list_directory first, then read_text_file on individual files."
Zusaetzlich: LangChain Tool-Wrapper mit Try/Except fuer robustere Tool-Calls.

**Status:** Fix ausstehend.

---

## BUG-021: llama-server braucht --embeddings und --pooling mean fuer OAI-kompatible Embeddings

**Status:** Bestaetigt via Sandbox-Test (2026-07-21)
**Umgebung:** Sandbox + Docker

**Symptom 1:** `/v1/embeddings` gibt 501 zurueck ohne `--embeddings` Flag.

**Symptom 2:** Mit `--embeddings` aber ohne `--pooling`: llama-server antwortet mit
`Pooling type 'none' is not OAI compatible`.

**Fix:** llama-server mit beiden Flags starten:
```bash
/tmp/llama-b9895/llama-server ... --embeddings --pooling mean
```

**Betrifft:**
- `scripts/sandbox/start_full.py` — behoben (Commit a8b486c3f083)
- `docker/entrypoint.sh` — Fix ausstehend
- `docs/LLAMA.md` und `docs/OPERATIONS_SANDBOX.md` — Dokumentation ausstehend

**Status:** In Sandbox gefixt, Docker und Doku ausstehend.

---

## BUG-022: Researcher-Agent schlaegt bei "What is the Local Agent?" fehl

**Status:** ✅ Behoben (2026-07-21) — Commit 31bd71618517
**Umgebung:** Sandbox

**Symptom:** Researcher-Agent antwortet mit
"I couldn't find any Local Agent in the current library"
statt einer echten Recherche-Antwort.

**Ursache:** Researcher-Agent versucht intern MCP-Tools oder ChromaDB
zu nutzen und bekommt einen LiteLLM-Fehler zurueck. Der Heuristic-Router
hat korrekt zu `researcher` geroutet — der Fehler liegt im Agent selbst.

**Betroffene Frage:** "What is the Local Agent?" → heuristic → researcher
(keyword: "what is" matched researcher)

**Moegliche Ursache:** "what is" als Keyword fuer researcher ist zu breit —
allgemeine Wissensfragen sollten zu `meta` gehen, nicht zu `researcher`.

**Fix-Optionen:**
1. "what is" aus ROUTING_KEYWORDS researcher entfernen
2. Researcher-Agent robuster machen gegen LiteLLM-Fehler
3. Beide kombinieren

**Status:** Fix ausstehend.

---

## BUG-023: Supervisor-Test-Validator zu streng fuer meta-Agent

**Status:** ✅ Behoben (2026-07-21) — 'what is' aus Heuristik entfernt, meta antwortet jetzt vollstaendig
**Umgebung:** Sandbox

**Symptom:** Supervisor-Test schlaegt fehl mit "zu kurz (6 Zeichen)"
weil `meta` auf "Can you help me?" mit "Hello!" antwortet.

**Ursache:** Test-Validator prueft min. 10 Zeichen fuer alle Agenten.
Aber `meta` gibt bei generischen Fragen kurze Antworten — das ist
korrektes Verhalten, kein Bug.

**Beweis:** "Hi, what can you do?" → meta → 107 Zeichen, vollstaendig korrekt.
"Can you help me?" → meta → "Hello!" — kurz aber valide.

**Fix:** In `start_full.py` Supervisor-Test-Case auf laengere Frage aendern:
"Can you help me?" → "Hi, what can you do for me today?"
Oder: min_length fuer Supervisor-Test auf 3 Zeichen setzen.

**Status:** Fix ausstehend.
