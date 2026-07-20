# COMPONENT_SWAP_TEMPLATE.md — Leitfaden für Komponenten-Dokumentation

**Zweck:** Dieses Template definiert die Standardstruktur für alle Komponenten-Dokumentationen im Projekt. 
Jede kritische Infrastruktur-Komponente (llama, LiteLLM, ChromaDB, Phoenix, etc.) erhält ein eigenes 
Dokument nach diesem Schema. Dadurch wird Komponenten-Austausch reproduzierbar und wartbar.

---

## 1. Component Overview

**Name:** [KOMPONENTEN-NAME]

**Beschreibung:** Was macht diese Komponente? Welche Rolle im Stack?

**Aktuelle Version:** [VERSION]

**Kritische Abhängigkeiten:** Was muss installiert sein, damit die Komponente läuft?

**Wo läuft sie?**
- [ ] Sandbox (Claude Sandbox)
- [ ] Docker (containerisiert)
- [ ] Host (janhet oder ähnlicher Server)

**Standard-Ports:** [LISTE]

---

## 2. Supported Versions & Alternatives

| Version | Status | Notes |
|---------|--------|-------|
| [V1] | Aktuell | [Grund warum wir diese Version nutzen] |
| [V2] | Getestet | [Limitierungen] |
| [V3] | Geplant | [Wann? Warum?] |

**Alternative Tools/Implementierungen:**
- [Alternative 1]: Pros / Cons im Vergleich
- [Alternative 2]: Pros / Cons im Vergleich

---

## 3. Architecture & Integration

**Rolle im Stack:** Wie interagiert diese Komponente mit anderen?

```
[Komponente] ←→ [andere Komponente]
      ↓
   [Datenfluss/API]
```

**Kritische APIs/Schnittstellen:**
- Endpoint 1: `[URL/Port]` — [Zweck]
- Endpoint 2: `[URL/Port]` — [Zweck]

**Daten-Persistierung:**
- Wo landen die Daten? (File, DB, Memory?)
- Wie lange bleiben sie?
- Multi-Session-Support?

---

## 4. Configuration Files & Dependencies

### 4.1 Files that Reference This Component

| Datei | Zeile(n) | Was ändert sich? |
|-------|----------|-----------------|
| `requirements.txt` | Z.X | Abhängigkeiten |
| `config.yaml` | Z.Y | Startparameter |
| `start_full.py` | Z.Z | Import/Start-Code |

### 4.2 Environment Variables

| Variable | Zweck | Wert (Sandbox) | Wert (Host) |
|----------|-------|--------|---------|
| `[ENV_VAR_1]` | [Beschreibung] | Sandbox-Wert | Host-Wert |

### 4.3 Dependencies in requirements.txt

```
[Paketname]==[Version]  # Grund
```

---

## 5. Swap Scenarios

### Scenario: [Version/Implementierung A] → [Version/Implementierung B]

**Wann würdest du diesen Wechsel machen?** [Grund]

**Impact Assessment:**
- [ ] Neue Abhängigkeiten hinzufügen/entfernen?
- [ ] Code-Änderungen in >2 Scripts nötig?
- [ ] Ports ändern sich?
- [ ] Datenformat-Migrationen nötig?

**Step-by-Step Implementation:**

#### Phase 1: Vorbereitung (Sandbox/Test)
```bash
# Schritt 1
[Befehl oder Code-Änderung]

# Schritt 2
[Nächster Befehl]
```

#### Phase 2: Migration
```python
# Code-Beispiel für die Änderung
# ALT:
[Alter Code]

# NEU:
[Neuer Code]
```

**Dateien die ändern müssen:**
- [ ] `[Datei 1]` — Z.XX: [Was ändert sich]
- [ ] `[Datei 2]` — Z.YY: [Was ändert sich]

**Tests nach dem Swap:**
```bash
[Test-Befehl 1]
[Test-Befehl 2]
```

**Erwartete Output:**
```
[Was sollte funktionieren?]
```

**Fallback Plan (wenn's bricht):**
```bash
# Git revert zur alten Version
git revert [COMMIT]
# Und dann:
[Rollback-Befehl]
```

---

## 6. Known Issues & Troubleshooting

| Problem | Symptom | Workaround | Fix |
|---------|---------|-----------|-----|
| [BUG-XXX] | [Fehlermeldung] | [Temporäre Lösung] | [Permanente Lösung] |

---

## 7. Performance & Resource Requirements

| Metrik | Sandbox | Docker | Host |
|--------|---------|--------|------|
| RAM | [MB] | [MB] | [MB] |
| CPU | [Cores] | [Cores] | [Cores] |
| Disk I/O | [Charakteristik] | [Charakteristik] | [Charakteristik] |
| Startup Time | [Sekunden] | [Sekunden] | [Sekunden] |

---

## 8. References & Related Components

**Externe Dokumentation:**
- [Link zu offizieller Doku]

**Verwandte Komponenten:**
- `[Komponente 1]` — wie hängt sie zusammen?
- `[Komponente 2]` — wie hängt sie zusammen?

**Relevant Bugs/Issues:**
- [BUGS.md#BUG-XXX]
- [ROADMAP.md#Abschnitt]

---

## Changelog

| Datum | Version | Änderung |
|-------|---------|----------|
| 2026-07-20 | Template v1 | Initial template created |

