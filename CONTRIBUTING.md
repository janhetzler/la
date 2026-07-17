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
