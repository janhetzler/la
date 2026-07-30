---
type: Reference
status: current
updated_at: 2026-07-30
stale_after: 2027-01-30
environment: all
components: []
---
# DOC_CONVENTIONS.md — Dokumentationskonventionen

Dieses Dokument beschreibt verbindlich, wie Dokumentation in janhetzler/la
erstellt und gepflegt wird. Neue Sessions und Agenten lesen dies nach
`STYLEGUIDE.md` als zweites.

---

## Warum OKF?

Alle Dokumente in diesem Repository folgen dem
[Open Knowledge Format (OKF)](https://github.com/janhetzler/knowledge-catalog/blob/main/okf/SPEC.md).
Das Kernprinzip: Markdown + YAML-Frontmatter — Mensch und Agent lesen
dasselbe, Git-Diffs funktionieren ohne Tooling, Provenienz und Aktualität
sind maschinenlesbar.

Für LA bedeutet das: **minimale Intervention**. Kein Umbau bestehender
Strukturen — jede Datei bekommt einen schlanken Frontmatter-Block oben drauf,
der Body bleibt unverändert.

---

## Frontmatter-Schema

Jede Dokumentationsdatei beginnt mit einem YAML-Frontmatter-Block:

```yaml
---
type: Runbook
status: current
updated_at: 2026-07-30
stale_after: 2026-09-25
environment: sandbox
components: [llama-server, litellm]
---
```

### Felder

| Feld | Pflicht | Sprache | Erlaubte Werte |
|------|---------|---------|----------------|
| `type` | ja | EN | siehe Dokumenttypen unten |
| `status` | ja | EN | `current` · `draft` · `stale` · `deprecated` |
| `updated_at` | ja | EN | ISO-Datum `YYYY-MM-DD` |
| `stale_after` | nein | EN | ISO-Datum `YYYY-MM-DD` — weglassen wenn nicht anwendbar |
| `environment` | nein | EN | `sandbox` · `docker` · `host` · `all` |
| `components` | nein | EN | Liste: `[llama-server, litellm, chromadb, phoenix, fastapi]` |

**Sprache:** Frontmatter-Werte immer auf Englisch. Alle Fließtexte,
Überschriften und Erklärungen im Body auf Deutsch.

---

## Dokumenttypen

| `type` | Zweck | `stale_after` |
|--------|-------|---------------|
| `Overview` | Projekteinstieg, README | — |
| `Log` | Chronologisches Entwicklungstagebuch | — |
| `Tracker` | Fortlaufende Sammlung (Bugs, Issues) | — |
| `Runbook` | Schritt-für-Schritt-Anleitung zum Ausführen | 8 Wochen |
| `Decision` | Architekturentscheidung, Komponentenwahl (ADR) | 3 Monate |
| `Reference` | Nachschlagwerk, Konventionen, API-Beschreibung | 6 Monate |
| `Observation` | Testergebnisse, Traces, Messwerte | — |
| `Index` | Navigationseinstieg für ein Verzeichnis | — |

### Wann `stale_after` weglassen?

- `Log` und `Tracker`: immer weglassen — diese Dokumente sind durch
  kontinuierliche Pflege per Definition aktuell.
- `Observation`: weglassen — Testergebnisse sind historische Fakten,
  sie veralten nicht, sie werden ergänzt.
- `Overview` und `Index`: weglassen — werden bei Bedarf aktualisiert.

---

## Faustregel: Runbooks und Stack-Wechsel

Der `stale_after`-Standardwert für Runbooks beträgt **8 Wochen**.
Zusätzlich gilt: Nach jedem größeren Stack-Wechsel (neues Modell, neue
Komponente, Architektur-Pivot) alle betroffenen Runbooks sofort prüfen —
unabhängig vom gesetzten Datum. Beim Prüfen `updated_at` und `stale_after`
aktualisieren.

---

## Pflegeregeln

1. **`updated_at` bei jedem inhaltlichen Push aktualisieren.** Reine
   Formatkorrekturen zählen nicht.
2. **`status: stale` setzen** wenn `stale_after` überschritten und der
   Inhalt noch nicht geprüft wurde.
3. **`status: deprecated` setzen** wenn ein Dokument dauerhaft nicht mehr
   gilt — nicht löschen, damit die Git-Historie erhalten bleibt.
4. **`docs/index.md` aktualisieren** wenn eine neue Datei in `docs/`
   hinzukommt oder ein Status sich ändert.

---

## Nach jeder Aenderung — Workflow

Jede Aenderung an einer Markdown-Datei folgt diesem Ablauf:

### Vor dem Push

```bash
CHANGED_FILES="pfad/zur/datei.md" python3 scripts/ci/check_doc_graph.py
```

Zeigt welche Dokumente auf die geaenderte Datei verweisen und
mitgepflegt werden muessen.

### Nach dem Push

**GitHub → Actions → Doc Graph Check** oeffnen und Warnungen pruefen.
Auch bei gruenem Haken koennen Warnungen im Log stehen — diese sind
verbindlich zu pruefen.

Die drei Actions im Ueberblick:

| Action | Trigger | Bedeutung |
|--------|---------|-----------|
| Frontmatter Lint | Push + PR | Pflichtfelder pruefen — blockiert bei Fehler |
| Doc Graph Check | Push + PR | Link-Graph pruefen — informativ, nicht blockierend |
| Stale Docs Check | Montags | Veraltete Docs melden — Issue wird geoeffnet |

Details zu allen Actions: [CI.md](CI.md)

---

## Vorlagen

Für jeden Dokumenttyp gibt es eine Vorlage unter `docs/templates/`.
Neue Dokumente immer aus der passenden Vorlage erstellen:

```
docs/templates/
  runbook.md
  decision.md
  reference.md
  observation.md
  tracker.md
```

---

## Beziehungen zwischen Dokumenten

OKF ist graphenbasiert — Beziehungen zwischen Dokumenten werden als
gewoehnliche Markdown-Links im Textkörper ausgedrueckt, nicht als
Frontmatter-Felder. Das erlaubt Werkzeugen den Link-Graphen automatisch
auszuwerten.

**Regel:** Wenn ein neues Dokument erstellt wird, muessen alle Dokumente
die darauf verweisen sollen einen Markdown-Link im Body erhalten.
Besonders wichtig: [README.md](../README.md) und [index.md](index.md)
sind Einstiegspunkte — sie muessen bei jeder neuen Datei geprueft und
ggf. aktualisiert werden.

Ein eigenes `related`-Feld im YAML-Frontmatter ist ausdruecklich nicht
vorgesehen — das waere ein Bruch mit der OKF-Architektur.

---

## Verwandt

- [OKF.md](OKF.md) — OKF-Konzept und Gesamtbild
- [CI.md](CI.md) — GitHub Actions und Link-Graph-Pruefung
- [STYLEGUIDE.md](../STYLEGUIDE.md) — Coding-Konventionen
- [index.md](index.md) — Navigationseinstieg
- [OKF SPEC.md](https://github.com/janhetzler/knowledge-catalog/blob/main/okf/SPEC.md)
