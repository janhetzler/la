# DITA light — Titel- und Strukturregeln

Minimale Adaption des DITA-Standards für kleine Open-Source-Projekte.
Kein XML, kein Tooling — nur die Kernprinzipien.

## Grundprinzipien

1. **Ein Dokument = ein Thema** — kein Mischmasch
2. **Titel beschreibt Handlung oder Gegenstand** — nie zu vage
3. **Struktur folgt dem Typ** — jeder Typ hat feste Abschnitte
4. **Sprache ist aktiv und direkt** — "Führe aus" nicht "Es wird ausgeführt"

---

## Task (Runbook) — Schritt-für-Schritt-Anleitung

**Titel:** Verb + Objekt + optionaler Kontext

```
✓ "LLaMA-Server auf dem KVM-Host starten"
✓ "Cloudflare-Tunnel zwischen Host und Webserver einrichten"
✓ "Incus auf Version 7.0 LTS migrieren"
✗ "LLaMA" — zu vage
✗ "Netzwerk Setup" — keine Handlung
```

**Pflichtabschnitte:**

```markdown
## Kontext
Ein Satz: warum, wann wird das gemacht?

## Voraussetzungen
- Was muss vorhanden sein?

## Schritte
1. Schritt — ein einziges Ziel pro Schritt

## Ergebnis
Was gilt nach Abschluss?

## Bekannte Probleme (optional)
| Problem | Ursache | Lösung |
```

---

## Concept (Reference / Decision) — Erklärung oder Entscheidung

**Titel:** Substantiv + Beschreibung

```
✓ "Cloudflare-Tunnel: Netzwerktopologie zwischen Host und Webserver"
✓ "Granite 4.0: Modellauswahl und Limitierungen"
✓ "Incus: Container-Strategie auf dem Webserver"
✗ "Infos zu Cloudflare" — zu vage
✗ "Warum wir Granite nehmen" — kein Substantiv
```

**Pflichtabschnitte:**

```markdown
## Kontext
Warum existiert dieses Dokument?

## Konzept / Architektur
Was ist es? Wie funktioniert es?

## Komponenten (optional)
| Komponente | Rolle | Ort |

## Erkenntnisse & Trade-offs
Was hat funktioniert? Was nicht?

## Verwandt
- Links zu verwandten Dokumenten
```

---

## Reference (Observation / Tracker) — Strukturierte Nachschlagedaten

**Titel:** Substantiv, selbsterklärend

```
✓ "Bekannte Probleme: LLaMA-Server"
✓ "Testergebnisse: Sandbox 2026-08-07"
✓ "API-Endpunkte: Agent Server"
```

**Pflichtabschnitte:**

```markdown
## Übersicht
Ein Satz Kontext.

## Daten
Tabelle oder strukturierte Liste — kein Fließtext.
```

---

## Sprache

| Falsch | Richtig |
|--------|---------|
| "Es wird ausgeführt" | "Führe aus" |
| "Der Server sollte gestartet werden" | "Starte den Server" |
| "Man kann hier sehen" | "Die Ausgabe zeigt" |
| "Wurde implementiert" | "Implementiert" oder aktiv umformulieren |
