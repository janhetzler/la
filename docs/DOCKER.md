# DOCKER.md — Local Agent, Docker-Umgebung

**Zuletzt aktualisiert:** 2026-07-16
**Zweck:** Portable, containerisierte Version der Sandbox-Umgebung — für
jeden x86_64 Linux-Server ohne manuellen Setup-Aufwand.

Diese Datei beschreibt ausschließlich die **Docker-Umgebung**. Für die
anderen beiden Umgebungen siehe [SANDBOX.md](SANDBOX.md) und [HOST.md](HOST.md).

Das Docker-Image ist im Kern eine gebaute, eigenständige Kopie dessen was
in der Sandbox entwickelt und getestet wurde — gleiches Modell
(Granite-350m), gleicher Inferenz-Stack (llama-cpp-python), gleiche
Hardware-Anforderungen wie die Sandbox.

---

## Image beziehen

Das Image wird über GitHub Actions gebaut und liegt in der GitHub
Container Registry:

```bash
docker pull ghcr.io/janhetzler/la:latest
```

⚠️ **Build ist aktuell nur manuell auslösbar** — der Workflow wurde von
automatischem Trigger (bei jedem Push) auf `workflow_dispatch` umgestellt,
um nicht bei jeder kleinen Doku-Änderung einen Build zu starten. Ein neues
Image entsteht nur wenn jemand mit `workflow`-Scope-Token den Workflow in
GitHub Actions manuell auslöst.

**Hinweis zum aktuellen Image-Stand:** Das zuletzt gebaute Image enthält
noch nicht zwingend den aktuellsten Sandbox-Stand (z.B. das
`agent-local`-Rename oder das erweiterte Logging). Vor produktiver Nutzung
prüfen, welcher Commit-SHA-Tag zuletzt gebaut wurde, und bei Bedarf neu
bauen.

---

## Image lokal bauen

```bash
git clone https://github.com/janhetzler/la
cd la

docker build \
  --build-arg GITHUB_TOKEN=<dein-token> \
  -t la:local .
```

Der `GITHUB_TOKEN` wird beim Build gebraucht um die Modell-Dateien aus den
GitHub Release Assets herunterzuladen (siehe [SANDBOX.md](SANDBOX.md) —
gleiche Situation wie beim Sandbox-Aufbau, Token wird für den Download
benötigt).

---

## Container starten

```bash
docker run -d \
  --name local-agent \
  -p 8080:8080 -p 8081:8081 -p 4000:4000 -p 6006:6006 -p 8002:8002 \
  ghcr.io/janhetzler/la:latest
```

Der Container startet beim Hochfahren automatisch alle Komponenten in
Reihenfolge (`docker/entrypoint.sh`):

1. llama-server Reasoning (Port 8080)
2. llama-server Embedding (Port 8081)
3. Wartet auf llama-server Readiness
4. Phoenix (Port 6006)
5. LiteLLM (Port 4000)
6. Wartet auf LiteLLM Readiness (echter Chat-Request, kein reiner Port-Check)
7. Agent Server (Port 8002)

Logs liegen im Container unter `/var/log/*.log` und werden zusätzlich im
Vordergrund über `tail -f /var/log/agent-server.log` ausgegeben — sichtbar
über `docker logs local-agent`.

---

## Hardware-Anforderungen

Wie in der README beschrieben — an der Sandbox orientiert, nicht am Host:

| | Wert |
|---|---|
| CPU | x86_64, 1+ Cores |
| RAM | 4 GB |
| Disk | ~3 GB für das Image inkl. Modelle |

---

## Was im Image steckt

- Basis: `python:3.12-slim-bookworm`
- Rust-Toolchain (für ChromaDB-Build) — bewusst im Image belassen,
  bewährter Build-Prozess, Größenoptimierung ist nachrangig
- `llama-cpp-python==0.3.23` als Prebuilt Wheel (bewusst diese Version,
  `0.3.34` verursachte in Tests ein Timing-Problem zwischen llama-server
  und LiteLLM — siehe [SANDBOX.md](SANDBOX.md))
- Beide Granite-Modelle fest im Image (`/app/models/`)
- Kompletter Agent-Code, MCP-Konfiguration, Test-Suite

---

## Bekannte offene Punkte

- `entrypoint.sh` prüft beim Start noch gegen `model="granite-tiny"`,
  nicht gegen den neueren `agent-local` Endpoint — funktional unkritisch
  (reiner Reasoning-Server-Check), aber nicht mehr ganz konsistent mit dem
  aktuellen Sandbox-Stand.
- Agent Server läuft im Container mit `--host 0.0.0.0` (anders als die
  Sandbox mit `127.0.0.1`) — das ist für Docker korrekt so, da der Port
  von außerhalb des Containers erreichbar sein muss.
- Wie in [SANDBOX.md](SANDBOX.md) dokumentiert: Notes/Handoff-Routing ist
  mit dem 350m-Modell unzuverlässig — betrifft das Docker-Image genauso,
  da dasselbe Modell verwendet wird.
- Das Image wurde bisher **nicht auf einem echten Server getestet** —
  nur der Build-Prozess über GitHub Actions lief erfolgreich durch.

---

## Referenzen

- Repository: https://github.com/janhetzler/la
- Dockerfile: [Dockerfile](../Dockerfile)
- Entrypoint: [docker/entrypoint.sh](../docker/entrypoint.sh)
- Sandbox-Dokumentation: [SANDBOX.md](SANDBOX.md)
