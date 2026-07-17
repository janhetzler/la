# deploy/systemd/ — systemd Service Templates

Dieses Verzeichnis enthält **Templates** für systemd Unit-Files.
Sie sind Vorlagen — keine fertigen, einsatzbereiten Dateien.

---

## Wichtig

> ⚠️ Diese Dateien sind Templates (Endung `.template`).
> Vor dem Einsatz müssen alle Platzhalter `{{...}}` mit echten Werten befüllt werden.
> Niemals eine `.template`-Datei direkt als systemd Unit verwenden.

---

## Platzhalter

| Platzhalter | Bedeutung | Beispiel |
|-------------|-----------|---------|
| `{{USER}}` | Systembenutzer unter dem der Dienst läuft | `user` |
| `{{PROJECT_PATH}}` | Absoluter Pfad zum geklonten Repository | `/home/user/la` |
| `{{VENV_PATH}}` | Absoluter Pfad zur Python Virtual Environment | `/home/user/venv` |
| `{{LITELLM_KEY}}` | LiteLLM Master Key | `sk-local-dev` |
| `{{CHROMA_PATH}}` | Absoluter Pfad zur ChromaDB Datenbank | `/home/user/chroma` |

---

## Services

| Template | Dienst | Port |
|----------|--------|------|
| `agent.service.template` | Local Agent — FastAPI Agent Server | 8002 |
| `litellm.service.template` | LiteLLM Proxy Gateway | 4000 |
| `phoenix.service.template` | Arize Phoenix Observability | 6006 |

llama-server wird **nicht** über systemd verwaltet — siehe `docs/HOST.md`.

---

## Neue Templates anlegen

Neue Service-Templates folgen demselben Muster:
- Dateiname: `<dienst>.service.template`
- Platzhalter: `{{GROSSBUCHSTABEN}}`
- Eintrag in dieser README ergänzen

---

## Deployment

Vollständige Anleitung: `docs/HOST.md`
