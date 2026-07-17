# config/ — Umgebungskonfiguration

Dieses Verzeichnis enthaelt alle Konfigurationsdateien fuer die drei
Umgebungen: Sandbox, Host und Docker.

---

## Prinzip

Kein Code im Projekt enthaelt hardcodierte Werte (URLs, Keys, Pfade).
Alle Werte werden ueber Umgebungsvariablen gesetzt — geladen aus den
`.env` Dateien in diesem Verzeichnis.

---

## Struktur

```
config/
├── sandbox/         <- Claude.ai Sandbox
│   ├── common.env   <- gilt fuer alle Komponenten
│   ├── litellm.env  <- LiteLLM Proxy
│   ├── agent.env    <- Agent Server + Agenten
│   └── phoenix.env  <- Arize Phoenix
├── host/            <- Host-Server (Produktion)
│   ├── common.env
│   ├── litellm.env
│   ├── agent.env
│   └── phoenix.env
└── docker/          <- Docker Container
    ├── common.env
    ├── litellm.env
    ├── agent.env
    └── phoenix.env
```

---

## Laden der Konfiguration

### Sandbox

Die Sandbox-Skripte laden die `.env` Dateien automatisch beim Start:

```bash
cd /home/claude/la && python3 scripts/sandbox/start_full.py
```

### Host

```bash
set -a
source config/host/common.env
source config/host/agent.env
set +a
uvicorn server:app --host 127.0.0.1 --port 8002
```

### Docker

Die `.env` Dateien werden im `Dockerfile` und `entrypoint.sh` geladen.

---

## Platzhalter im Host

Host-`.env` Dateien enthalten `{{PLATZHALTER}}` die vor dem
Deployment befuellt werden muessen:

| Platzhalter | Bedeutung | Beispiel |
|-------------|-----------|---------|
| `{{PROJECT_PATH}}` | Absoluter Pfad zum Repository | `/home/user/la` |
| `{{MODELS_PATH}}` | Absoluter Pfad zu den Modellen | `/home/user/models` |

---

## Neue Umgebungsvariable hinzufuegen

1. Variable in der relevanten `.env` Datei eintragen (alle drei Umgebungen)
2. In `agents/server/config.py` als `os.getenv("VARIABLE", "default")` ergaenzen
3. Diese README aktualisieren
