# Beispiel: Schlechtes Runbook

**Annotation:** So sieht ein Dokument aus das nur "gestempelt" wurde
ohne Qualitätsprüfung. Lies die Kommentare um zu verstehen was falsch ist.

---

```markdown
---
type: Runbook          ← OK
status: current        ← FALSCH: Inhalt wurde nicht geprüft
updated_at: 2026-04-24 ← FALSCH: Datum geraten, nicht aus Inhalt gelesen
stale_after: 2026-10-24 ← OK formal, aber sinnlos wenn Inhalt veraltet
environment: host      ← OK
topic: llama           ← SCHWACH: zu vage, kein Kontext
tags: []               ← FALSCH: keine Tags gesetzt
---

# LLaMA
← FALSCH: kein Verb, kein Objekt — was wird hier gemacht?

Hier wird beschrieben wie man llama startet.
← FALSCH: passive Sprache, sagt nichts aus was der Titel nicht schon sagt

Man muss zuerst sicherstellen dass der Container läuft.
← FALSCH: "Man muss" — direkt ansprechen: "Prüfe ob..."

Dann den Server starten.
← FALSCH: kein Befehl, kein erwartetes Ergebnis

Es sollte dann funktionieren.
← FALSCH: "sollte" ist keine Aussage — was ist das Ergebnis?
```

---

## Was ist falsch?

| Problem | Regel |
|---------|-------|
| Titel "LLaMA" — zu vage | Verb + Objekt + Kontext |
| Passive Sprache durchgehend | Google Style: aktiv und direkt |
| Keine Befehle, kein erwartetes Ergebnis | Ein Schritt = ein Ziel + Ergebnis |
| Tags leer | Tags aus echtem Inhalt ableiten |
| `status: current` ohne Prüfung | Qualitätstor vor Frontmatter |
| Datum geraten | `updated_at` = tatsächliches Änderungsdatum |
