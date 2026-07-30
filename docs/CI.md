---
type: Reference
status: current
updated_at: 2026-07-30
stale_after: 2027-01-30
environment: all
components: []
---
# CI.md — Automatisierung: GitHub Actions

Dieses Dokument beschreibt die zwei GitHub Actions die im Projekt
janhetzler/la die OKF-Dokumentationsqualität automatisch sicherstellen.

---

## Übersicht

| Action | Datei | Trigger | Zweck |
|--------|-------|---------|-------|
| Frontmatter Lint | `.github/workflows/doc-lint.yml` | Jeder Push + PR auf `main` | Pflichtfelder prüfen |
| Stale Docs Check | `.github/workflows/doc-stale.yml` | Montags 07:00 UTC + manuell | Veraltete Docs melden |

---

## Action 1 — Frontmatter Lint

**Script:** `scripts/ci/lint_frontmatter.py`

Prüft bei jedem Push und Pull Request ob alle relevanten Markdown-Dateien
gültiges OKF-Frontmatter enthalten.

### Was geprüft wird

| Feld | Regel |
|------|-------|
| `type` | Pflicht — muss ein erlaubter Wert sein |
| `status` | Pflicht — muss ein erlaubter Wert sein |
| `updated_at` | Pflicht — muss ISO-Format `YYYY-MM-DD` haben |

### Welche Dateien geprüft werden

- Root-Ebene: `README.md`, `BUGS.md`, `JOURNAL.md`, `STYLEGUIDE.md`, `CONTRIBUTING.md`
- `docs/` — vollständig, außer:
  - `docs/templates/` — Vorlagen haben bewusst Platzhalter
  - `docs/traces/` — Rohdaten, kein Frontmatter erwartet
  - `docs/test_results/` — Rohdaten

Alle anderen Verzeichnisse (`prompts/`, `config/`, `deploy/`, `scripts/`)
werden **nicht** geprüft — deren Markdown-Dateien sind keine OKF-Dokumente.

### Verhalten

- **Fehler** → Action schlägt fehl, Commit wird rot markiert, Push ist blockiert
- **Erfolgreich** → grüner Haken, keine weitere Aktion

### Manuelle Ausführung

```bash
cd /pfad/zum/repo
python3 scripts/ci/lint_frontmatter.py
```

---

## Action 2 — Stale Docs Check

**Script:** `scripts/ci/check_stale.py`

Läuft jeden Montag um 07:00 UTC und prüft ob Dokumente ihr
`stale_after`-Datum überschritten haben.

### Was passiert

1. Alle `.md`-Dateien mit `stale_after`-Feld werden gelesen
2. Das Datum wird mit dem heutigen Tag verglichen
3. Bei veralteten Dateien wird ein GitHub Issue geöffnet mit der Liste
   der betroffenen Dokumente, dem Typ und der Anzahl überfälliger Tage

### Was nicht passiert

- Kein automatischer Commit — `status: stale` wird nicht automatisch gesetzt
- Kein Push, keine Dateiänderung
- Kein doppeltes Issue wenn bereits eines offen ist (manuell prüfen)

### Verhalten

- **Keine veralteten Dateien** → grüner Haken, kein Issue
- **Veraltete Dateien gefunden** → grüner Haken + Issue mit Label `doc-stale`

### Issue bearbeiten

Nach dem Prüfen der veralteten Datei:
1. `updated_at` auf das heutige Datum setzen
2. `stale_after` auf das neue Prüfdatum setzen
3. Issue manuell schließen

### Manuelle Ausführung

Über GitHub Actions → Stale Docs Check → "Run workflow" — oder:

```bash
GITHUB_TOKEN=<token> GITHUB_REPOSITORY=janhetzler/la   python3 scripts/ci/check_stale.py
```

---

## GitHub-Voraussetzungen

### Issues aktivieren

Der Stale-Check öffnet GitHub Issues. Issues müssen im Repo aktiviert sein:

**GitHub → Repository → Settings → Features → Issues → Checkbox aktivieren**

Ohne aktivierte Issues schlägt die Action mit HTTP 410 fehl.

### GITHUB_TOKEN

Beide Actions nutzen den automatischen `GITHUB_TOKEN` den GitHub bei
jedem Workflow-Run bereitstellt. Kein manuelles Secret nötig, keine
zusätzliche Konfiguration.

Der Token hat die nötigen Permissions direkt in der Workflow-Datei:

```yaml
permissions:
  contents: read
  issues: write
```

### Label doc-stale

Das Label `doc-stale` muss im Repo existieren. Es wird beim ersten
manuellen Anlegen oder über GitHub → Issues → Labels erstellt.
Farbe: `#e4e669` (gelb).

---

## Verwandt

- [DOC_CONVENTIONS.md](DOC_CONVENTIONS.md) — OKF-Konventionen und Frontmatter-Schema
- [OKF.md](OKF.md) — OKF-Konzept und Gesamtbild
- [index.md](index.md) — Navigationseinstieg
