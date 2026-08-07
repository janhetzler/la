# Beispiel: Process Documentation (How-to Guide)

**Quelle:** Janey Annis, Technical Writer bei GitHub (2022)
**Warum dieses Beispiel:** Zeigt professionelle Prozessdokumentation —
klare Schritte, definierte Audience, konkreter Kontext.

---

## Was macht dieses Dokument gut?

- **Audience und Context explizit definiert** — der Autor weiß vor dem
  Schreiben für wen und mit welchem Vorwissen
- **Schritte sind nummeriert und atomar** — ein Schritt, ein Ziel
- **Ergebnis ist sichtbar** — der Leser sieht was nach dem Schritt passiert
- **Sprache ist direkt** — "Add a FUNDING.yml file" nicht
  "A FUNDING.yml file should be added"

---

## Original (gekürzt, Text-Extrakt)

**Audience:** Open source developers, students, anyone who contributes
to open source and meets requirements for receiving funding

**Context:** Instructions assume working knowledge of GitHub and
creation of supporting files for projects hosted on the platform

---

### How do I display my GitHub Sponsors profile on a project?

As a sponsored developer, you can display a sponsor button on your
repository, so others can support your project.

1. Add a `FUNDING.yml` file to your repository:

```yaml
github: [your_github_handle, friend]
```

2. Enable **Sponsorships** in the Settings page.

3. Visit your repository — the Sponsor button is now displayed.

---

### How do I give credit to other team members?

Update the `FUNDING.yml` file to add their GitHub Sponsors profile:

```yaml
github: [your_github_handle, colleague]
```

---

## Was wir daraus übernehmen

| Prinzip | Anwendung in unserem Skill |
|---------|---------------------------|
| Audience vor dem Schreiben definieren | Qualitätstor Step 2 |
| "How do I..." als Titelmuster | Titelregel für Runbooks |
| Ein Schritt = ein Ziel | Task-Template Struktur |
| Ergebnis nach jedem Schritt | ✓ Erwartetes Ergebnis in task.md |
