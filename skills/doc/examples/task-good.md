# Beispiel: Gutes Runbook

**Annotation:** Dieses Dokument folgt allen Regeln des doc-Skills.
Lies es als Referenz bevor du ein neues Runbook schreibst.

---

```markdown
---
type: Runbook
status: current
updated_at: 2026-08-07
stale_after: 2027-02-07
environment: host
topic: llama-server-start
tags: [llama, debian, host, granite]
---

# LLaMA-Server auf dem KVM-Host starten

## Kontext

Startet den llama-server mit dem Granite 4B Modell im Incus-Container.
Ausführen nach jedem Reboot oder wenn der Server nicht erreichbar ist.

## Voraussetzungen

- Incus-Container `llama` läuft (`incus list`)
- Modell-Datei vorhanden unter `/models/granite-4b-Q4_K_M.gguf`
- Port 8080 ist frei

## Schritte

### 1. Container-Status prüfen

incus exec llama -- systemctl status llama-server

✓ Status: active (running)

### 2. Server starten falls nicht aktiv

incus exec llama -- systemctl start llama-server

✓ Kein Fehler in der Ausgabe

### 3. Erreichbarkeit prüfen

curl http://localhost:8080/health

✓ {"status": "ok"}

## Ergebnis

Der LLaMA-Server ist erreichbar auf Port 8080 und bereit
für Anfragen von LiteLLM.

## Bekannte Probleme

| Problem | Ursache | Lösung |
|---------|---------|--------|
| Port 8080 belegt | Alter Prozess hängt | `pkill llama-server` |
| Modell nicht gefunden | Pfad falsch | Pfad in config.yaml prüfen |
```

---

## Warum ist das gut?

- Titel: Verb + Objekt + Kontext ✓
- Frontmatter vollständig, Tags aus echtem Inhalt ✓
- Kontext: ein Satz, beantwortet wann und warum ✓
- Schritte nummeriert, jeder mit einem Ziel und Ergebnis ✓
- Bekannte Probleme als Tabelle ✓
