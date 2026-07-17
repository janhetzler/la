# CONTRIBUTING.md — Local Agent (janhetzler/la)

Dieses Dokument beschreibt die Struktur des Repositories und wie wir damit arbeiten.

---

## Umgebungen

Das Projekt läuft in drei Umgebungen:

| Umgebung | Beschreibung |
|----------|-------------|
| **Sandbox** | Claude.ai Sandbox — Entwicklung und Testing |
| **Host** | janhet (Hetzner KVM, AMD EPYC, 10 GB RAM) — Produktion |
| **Docker** | Containerisierte Version — portabler Betrieb |

---

## Ordnerstruktur

Überall wo umgebungsspezifische Dateien existieren, gilt folgendes Prinzip:

```
bereich/
├── sandbox/        ← Dateien für die Claude.ai Sandbox
│   └── README.md   ← Erklärt Inhalt, Verwendung, Konventionen
├── host/           ← Dateien für janhet (Produktion)
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

Start- und Hilfsskripte pro Umgebung.

```
scripts/
├── sandbox/
│   ├── README.md
│   ├── import_check.py
│   ├── start_quick.py
│   └── start_full.py
├── host/
│   ├── README.md
│   └── ...
└── docker/
    ├── README.md
    └── ...
```

### `docs/`

Dokumentation pro Umgebung sowie übergreifende Dokumente.

```
docs/
├── SANDBOX.md      ← Aufbauanleitung Sandbox
├── HOST.md         ← Aufbauanleitung Host (janhet)
└── DOCKER.md       ← Aufbauanleitung Docker
```

---

## Übergreifende Dateien im Root

| Datei | Inhalt |
|-------|--------|
| `README.md` | Projekt-Übersicht |
| `CONTRIBUTING.md` | Diese Datei — Struktur und Konventionen |
| `BUGS.md` | Bekannte offene Probleme |
| `requirements.txt` | Python-Abhängigkeiten |
| `Dockerfile` | Docker Image Definition |
