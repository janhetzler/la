# doc-structure — Dokumentstruktur und Sprachstandard

## Sprachstandard

**[Google Developer Documentation Style Guide](https://developers.google.com/style)**
— unser verbindlicher Sprachstandard. Aktiv gepflegt, Markdown-nativ,
für Entwicklerdokumentation gemacht.

Kernregeln die sofort gelten:

| Falsch | Richtig |
|--------|---------|
| "Es wird ausgeführt" | "Führe aus" |
| "Der Server sollte gestartet werden" | "Starte den Server" |
| "Man kann hier sehen" | "Die Ausgabe zeigt" |
| "wurde implementiert" | aktiv umformulieren |
| Lange Einleitung vor dem Schritt | Schritt sofort, Kontext danach |

---

## Dokumenttypen (Diátaxis-basiert)

Vier Typen — jeder hat einen klaren Zweck und eine feste Struktur.
Quelle: [Diátaxis Framework](https://diataxis.fr)

### How-to Guide → OKF `Runbook`

Ziel: Leser durch eine konkrete Aufgabe führen.

**Titel:** "Wie + Verb + Objekt" oder "Verb + Objekt"
```
✓ "LLaMA-Server auf dem KVM-Host starten"
✓ "Cloudflare-Tunnel zwischen Host und Webserver einrichten"
✗ "LLaMA" — zu vage
✗ "Netzwerk Setup" — keine Handlung
```

**Pflichtabschnitte:**
```markdown
## Kontext
Ein Satz: warum, wann?

## Voraussetzungen
- Was muss vorhanden sein?

## Schritte
1. Erster Schritt — ein Ziel pro Schritt

## Ergebnis
Was gilt nach Abschluss?
```

---

### Explanation → OKF `Reference` / `Decision`

Ziel: Verstehen — nicht ausführen.

**Titel:** Substantiv + Beschreibung
```
✓ "Cloudflare-Tunnel: Netzwerktopologie zwischen Host und Webserver"
✓ "Granite 4.0: Modellauswahl und Limitierungen"
✗ "Infos zu Cloudflare" — zu vage
```

**Pflichtabschnitte:**
```markdown
## Kontext
Warum existiert dieses Dokument?

## Konzept
Was ist es, wie funktioniert es?

## Erkenntnisse & Trade-offs
Was hat funktioniert? Was nicht?
```

---

### Reference → OKF `Observation` / `Tracker`

Ziel: Nachschlagen — keine Erklärung, keine Schritte.

**Titel:** Substantiv, selbsterklärend
```
✓ "Bekannte Probleme: LLaMA-Server"
✓ "API-Endpunkte: Agent Server"
```

**Pflichtabschnitte:**
```markdown
## Übersicht
Ein Satz Kontext.

## Daten
Tabelle oder Liste — kein Fließtext.
```

---

## Audience und Context

Vor jedem Dokument definieren:

```markdown
<!-- Audience: Entwickler mit Grundkenntnissen Debian -->
<!-- Context: Setzt laufenden KVM-Host voraus -->
```

Diese Felder müssen nicht im finalen Dokument sichtbar sein —
aber der Autor muss sie vor dem Schreiben kennen.

---

## Verwandt

- [Google Developer Documentation Style Guide](https://developers.google.com/style)
- [Diátaxis Framework](https://diataxis.fr)
- [okf-schema.md](okf-schema.md)
