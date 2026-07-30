---
type: Reference
status: current
updated_at: 2026-07-30
stale_after: 2027-01-30
environment: all
components: []
---
# OKF.md — Open Knowledge Format in janhetzler/la

Dieses Dokument beschreibt wie das Open Knowledge Format (OKF) im Projekt
janhetzler/la angewendet wird — Motivation, Konzept und Zusammenspiel
aller Teile.

---

## Was ist OKF?

Das [Open Knowledge Format v0.2](https://github.com/janhetzler/knowledge-catalog/blob/main/okf/SPEC.md)
ist ein offenes, vendor-neutrales Format für Wissen in Form von
Markdown-Dateien mit YAML-Frontmatter.

Kernprinzipien:

- **Mensch und Agent lesen dasselbe** — kein SDK, kein Query-Layer
- **Git-nativ** — Diffs, Reviews, Versionierung funktionieren automatisch
- **Strukturiert + unstrukturiert gemischt** — YAML für maschinenlesbare
  Felder, Markdown-Body für Prosa
- **Provenienz und Freshness als First-Class-Felder** — `status`,
  `stale_after`, `updated_at` sind keine Kommentare sondern querybare Daten

---

## Wie LA OKF anwendet

### Minimale Intervention

Wir haben OKF nicht von Grund auf neu eingeführt — die bestehende
Dokumentationsstruktur war bereits gut. Die Anpassung bestand ausschließlich
aus zwei Schritten:

1. **YAML-Frontmatter-Block** oben in jede relevante Datei eingefügt
2. **Neue Navigationsdateien** erstellt (`index.md`, `DOC_CONVENTIONS.md`,
   `docs/templates/`)

Der Markdown-Body jeder Datei wurde nicht verändert. Keine Umstrukturierung,
keine neuen Verzeichnisse, keine Umbenennungen.

### Das Repo ist das Bundle

In OKF-Terminologie ist ein "Bundle" eine Sammlung von Konzeptdokumenten
in einem Verzeichnisbaum. Bei LA ist das gesamte Repository das Bundle —
`docs/` ist der Haupt-Bundle-Pfad, Root-Dateien wie `JOURNAL.md` und
`BUGS.md` gehören ebenfalls dazu.

---

## Dokumenttypen

Alle Dokumente in LA gehören einem von acht Typen an:

| `type` | Zweck | Beispiele |
|--------|-------|-----------|
| `Overview` | Projekteinstieg | `README.md` |
| `Log` | Chronologisches Tagebuch | `JOURNAL.md` |
| `Tracker` | Fortlaufende Sammlung | `BUGS.md` |
| `Runbook` | Schritt-für-Schritt-Anleitung | `SANDBOX.md`, `OPERATIONS_*.md` |
| `Decision` | Architekturentscheidung (ADR) | `LLAMA.md`, `ROADMAP.md` |
| `Reference` | Nachschlagwerk | `DOC_CONVENTIONS.md`, `MCP_SERVERS.md` |
| `Observation` | Testergebnisse, Traces | `SANDBOX_TESTRESULTS.md` |
| `Index` | Navigationseinstieg | `docs/index.md` |

---

## Freshness-Modell

Jedes Dokument trägt drei zeitbezogene Felder:

| Feld | Bedeutung |
|------|-----------|
| `updated_at` | Wann wurde der Inhalt zuletzt geändert? |
| `stale_after` | Ab wann sollte der Inhalt geprüft werden? |
| `status` | Aktueller Zustand: `current`, `draft`, `stale`, `deprecated` |

### Faustregel nach Typ

| Typ | `stale_after` |
|-----|---------------|
| `Runbook` | 8 Wochen — zusätzlich nach jedem Stack-Wechsel prüfen |
| `Decision` | 3 Monate |
| `Reference` | 6 Monate |
| `Log`, `Tracker`, `Observation` | kein `stale_after` — immer aktuell durch Pflege |
| `Overview`, `Index` | kein `stale_after` — zeitlos |

---

## Automatisierung

Das Freshness-Modell wird durch zwei GitHub Actions durchgesetzt:

**Frontmatter Lint** — prüft bei jedem Push ob Pflichtfelder vorhanden
und korrekt sind. Fehlerhafte Commits werden blockiert.

**Stale Docs Check** — läuft wöchentlich und öffnet ein GitHub Issue
wenn `stale_after`-Daten überschritten sind.

Details: [CI.md](CI.md)

---

## Vorlagen

Für jeden Dokumenttyp gibt es eine Vorlage unter `docs/templates/`.
Neue Dokumente immer aus der passenden Vorlage erstellen — so ist
OKF-Konformität von Anfang an sichergestellt.

```
docs/templates/
  runbook.md
  decision.md
  reference.md
  observation.md
  tracker.md
```

---

## Zusammenspiel aller Teile

```
Neues Dokument anlegen
  → Vorlage aus docs/templates/ kopieren
  → Frontmatter ausfüllen (type, status, updated_at, stale_after)
  → docs/index.md aktualisieren
  → Push → Frontmatter Lint prüft automatisch

Bestehendes Dokument ändern
  → updated_at aktualisieren
  → Push → Frontmatter Lint prüft automatisch

Wöchentlich (montags)
  → Stale Docs Check läuft
  → Veraltete Dateien → GitHub Issue
  → Issue bearbeiten → Datei prüfen → updated_at + stale_after setzen → Issue schließen
```

---

## Verwandt

- [DOC_CONVENTIONS.md](DOC_CONVENTIONS.md) — Frontmatter-Schema und Pflegeregeln
- [CI.md](CI.md) — GitHub Actions im Detail
- [index.md](index.md) — Navigationseinstieg
- [OKF SPEC v0.2](https://github.com/janhetzler/knowledge-catalog/blob/main/okf/SPEC.md)
