# Qualitätscheckliste — vor jedem Frontmatter

Diese Checkliste ist ein Pflichtschritt vor dem Setzen von OKF-Frontmatter.
Kein Dokument bekommt einen Stempel bevor alle Punkte geprüft sind.

## Inhalt

- [ ] Ist der Inhalt vollständig genug um nützlich zu sein?
- [ ] Ist der Inhalt aktuell — stimmen Befehle, Pfade, Versionen?
- [ ] Behandelt das Dokument genau ein Thema?
- [ ] Gibt es bereits ein Dokument zu diesem Thema?
      → Falls ja: erweitern statt neu erstellen

## Titel

- [ ] Folgt der Titel der DITA-Regel für diesen Typ?
      Task: Verb + Objekt
      Concept: Substantiv + Beschreibung
- [ ] Ist der Titel spezifisch genug — kein "LLaMA", "Netzwerk", "Setup"?

## Struktur

- [ ] Hat das Dokument die Pflichtabschnitte für seinen Typ?
- [ ] Ist die Sprache aktiv und direkt?

## Frontmatter

- [ ] Ist `type` korrekt gewählt?
- [ ] Ist `status` ehrlich — ist es wirklich `current`?
- [ ] Ist `updated_at` das heutige Datum?
- [ ] Ist `stale_after` gesetzt wenn nötig?
- [ ] Sind `tags` aus dem tatsächlichen Inhalt abgeleitet?

## Verlinkung

- [ ] Ist das Dokument in `index.md` oder `docs/index.md` eingetragen?
- [ ] Ist das Dokument in der `README.md` des Zielordners verlinkt?
- [ ] Gibt es ein übergeordnetes Konzeptdokument?
      → Falls ja: Link von dort auf dieses Dokument setzen

## Letzter Check

- [ ] Würde ein Mensch der dieses Dokument zum ersten Mal sieht
      sofort verstehen worum es geht?
- [ ] Würde ein Agent der dieses Dokument liest die richtige
      Handlung ableiten können?

Wenn alle Punkte ✓ — Frontmatter setzen.
