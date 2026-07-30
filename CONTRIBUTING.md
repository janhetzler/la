---
type: Reference
status: current
updated_at: 2026-07-30
stale_after: 2027-01-30
environment: all
components: []
---
# CONTRIBUTING.md — Local Agent (janhetzler/la)

Dieses Dokument beschreibt die Struktur des Repositories und wie wir damit arbeiten.

---

## Umgebungen

Das Projekt läuft in drei Umgebungen:

| Umgebung | Beschreibung |
|----------|-------------|
| **Sandbox** | Claude.ai Sandbox — Entwicklung und Testing |
| **Host** | Host-Server (AMD EPYC, 10 GB RAM, Debian 12) — Produktion |
| **Docker** | Containerisierte Version — portabler Betrieb |

---

## Ordnerstruktur

Überall wo umgebungsspezifische Dateien existieren, gilt folgendes Prinzip:

```
bereich/
├── sandbox/        ← Dateien für die Claude.ai Sandbox
│   └── README.md   ← Erklärt Inhalt, Verwendung, Konventionen
├── host/           ← Dateien für den Host (Produktion)
│   └── README.md
└── docker/         ← Dateien für den Docker-Container
    └── README.md
```

Jede `README.md` in einem Unterordner beantwortet:
- Was liegt hier?
- Wie wird es verwendet?
- Wie werden neue Dateien angelegt und benannt?

---

## Bereiche mit dieser Struktur

### `mcp/`

MCP Server Konfigurationen pro Umgebung.

```
mcp/
├── sandbox/
│   ├── README.md
│   └── mcp.json
├── host/
│   ├── README.md
│   └── mcp.json
└── docker/
    ├── README.md
    └── mcp.json
```

### `scripts/`

Start- und Hilfsskripte pro Umgebung. Allgemeine Skripte liegen direkt in `scripts/`.

```
scripts/
├── chat.py                    ← allgemein — Terminal Chat Client
├── test_tool_formatter.py     ← allgemein — Unit-Test, kein Stack nötig
├── start_litellm.sh           ← allgemein
├── start_phoenix.sh           ← allgemein
└── sandbox/
    ├── README.md
    ├── import_check.py        ← ~2s, nur Modul-Import-Check
    ├── start_quick.py         ← ~90s, schlanker Stack-Start
    └── start_full.py          ← ~3 Min, vollständiger Stack + Testlauf
```

### `docs/`

Dokumentation pro Umgebung sowie übergreifende Dokumente.

```
docs/
├── SANDBOX.md                 ← Aufbauanleitung Sandbox
├── DOCKER.md                  ← Aufbauanleitung Docker
├── INSTALL_HOST.md            ← Installationsanleitung Host
├── ROADMAP.md                 ← Architekturentscheidungen und Phasenplan
└── MCP_SERVERS.md             ← MCP Server Dokumentation
```

---

## Testergebnisse

Nach jedem vollständigen Testlauf (`scripts/sandbox/start_full.py`) werden
die Ergebnisse als Markdown-Datei in `docs/` abgelegt.

**Namenskonvention:** `<UMGEBUNG>_<SESSION>_TESTRESULTS.md`

Beispiele:
- `docs/SANDBOX_1_TESTRESULTS.md` — Ergebnisse aus Sandbox Session 1
- `docs/SANDBOX_2_TESTRESULTS.md` — Ergebnisse aus Sandbox Session 2
- `docs/HOST_TESTRESULTS.md` — Ergebnisse vom Host (sobald deployed)

Die Datei enthält: Datum, Umgebung, Modell, Testergebnisse pro Agent,
ChromaDB-Status, Log-Check-Ergebnisse.

---

## Übergreifende Dateien im Root

| Datei | Inhalt |
|-------|--------|
| `README.md` | Projekt-Übersicht |
| `CONTRIBUTING.md` | Diese Datei — Struktur und Konventionen |
| `BUGS.md` | Bekannte offene Probleme |
| `requirements.txt` | Python-Abhängigkeiten |
| `Dockerfile` | Docker Image Definition |

---

## Arbeitsablauf: Markdown-Dateien aendern

Wenn du eine `.md`-Datei aenderst oder neu erstellst, gilt dieser Ablauf:

### 1. Vor dem Push — lokal pruefen

```bash
CHANGED_FILES="pfad/zur/datei.md" python3 scripts/ci/check_doc_graph.py
```

Zeigt welche anderen Dokumente auf deine Datei verweisen und
moeglicherweise mitgepflegt werden muessen.

### 2. Neue Datei anlegen

- Vorlage aus `docs/templates/` kopieren
- Frontmatter ausfuellen (`type`, `status`, `updated_at`, ggf. `stale_after`)
- `docs/index.md` aktualisieren — neue Datei in der richtigen Tabelle eintragen
- `README.md` pruefen — gehoert die neue Datei in den Dokumentationsabschnitt?

### 3. Nach dem Push — Actions pruefen

**GitHub → Repository → Actions** — drei Actions laufen bei jedem Push:

| Action | Ergebnis rot | Ergebnis gruen mit Warnungen |
|--------|-------------|------------------------------|
| Frontmatter Lint | Pflichtfelder fehlen — sofort korrigieren | — |
| Doc Graph Check | — | Verlinkende Dokumente pruefen |
| Stale Docs Check | — | Laeuft nur montags |

Der **Doc Graph Check** ist besonders wichtig: Er listet alle Dokumente
die auf deine geaenderte Datei verweisen. Pruefen ob dort eine
inhaltliche Aktualisierung noetig ist — z.B. ob `README.md` oder
`docs/index.md` angepasst werden muessen.

### 4. Dokumentation zu OKF und Konventionen

- [docs/DOC_CONVENTIONS.md](docs/DOC_CONVENTIONS.md) — Frontmatter-Schema, Typen, Pflegeregeln
- [docs/OKF.md](docs/OKF.md) — Konzept und Gesamtbild
- [docs/CI.md](docs/CI.md) — Alle drei Actions im Detail
