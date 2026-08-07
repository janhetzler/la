# doc — Documentation Skill

## Description

Use this skill whenever a documentation task is involved:
creating new documents, updating existing ones, applying OKF
frontmatter, reviewing document quality, or navigating the
documentation structure of a project.

---

## Activation

Load this skill when the user says or implies:
- "dokumentiere das", "doc das", "schreib das auf"
- "aktualisiere die Doku", "füge das zur Doku hinzu"
- "was haben wir dazu dokumentiert?"
- any task that produces or modifies a `.md` file

---

## Step 1 — Orient Before You Write

Before creating or modifying any document, read the project
structure first:

1. Read `docs/index.md` or `doc/index.md` — understand what
   already exists
2. Read the relevant `README.md` in the target folder
3. Ask: does a document on this topic already exist?
   - YES → extend or update it, do not create a duplicate
   - NO  → continue to Step 2

---

## Step 2 — Quality Gate

Before setting any frontmatter, answer these questions about
the content:

- [ ] Is the content complete enough to be useful?
- [ ] Is the title clear and specific? (DITA rule: Task titles
      use Verb + Object, Concept titles use Noun + Description)
- [ ] Is the content still accurate and current?
- [ ] Is this one topic only — no mixing of concerns?
- [ ] Does it belong to an existing parent document?
      If yes: add a link from the parent to this document.

If any answer is NO — fix the content first, then set frontmatter.
Never stamp a weak document.

---

## Step 3 — Choose the Right Type

| Content is... | DITA type | OKF `type` | Template |
|---------------|-----------|------------|----------|
| Step-by-step instructions | Task | `Runbook` | `templates/task.md` |
| Explanation, architecture, decision | Concept | `Reference` or `Decision` | `templates/concept.md` |
| Structured lookup data, tables, lists | Reference | `Observation` or `Tracker` | `templates/reference.md` |
| Project entry point | — | `Overview` or `Index` | — |
| Chronological log | — | `Log` | — |

---

## Step 4 — Title Rules (DITA light)

**Task / Runbook:**
> Verb + Object + optional Context
> ✓ "LLaMA-Server auf dem KVM-Host starten"
> ✓ "Cloudflare-Tunnel zwischen Host und Webserver einrichten"
> ✗ "LLaMA" — zu vage
> ✗ "Walkthrough Netzwerk" — keine Handlung, kein Objekt

**Concept / Reference / Decision:**
> Noun + Description
> ✓ "Cloudflare-Tunnel: Netzwerktopologie zwischen Host und Webserver"
> ✓ "Granite 4.0: Modellauswahl und Limitierungen"
> ✗ "Infos zu Cloudflare" — zu vage

**Log / Tracker / Overview:**
> Einfaches Substantiv, selbsterklärend
> ✓ "Admin-Logbuch", "Bekannte Probleme", "Projektübersicht"

---

## Step 5 — Set Frontmatter

Use the schema from `references/okf-schema.md`.

Rules:
- Frontmatter values always in English
- Body, headings, explanations always in German
- One blank line between closing `---` and first heading
- `updated_at` = today
- `stale_after` = today + 6 months for Runbooks,
  today + 12 months for Reference/Decision
- `tags`: plain words, no prefixes, derived from actual content
  Examples: `[llama, debian, incus, nginx, cloudflare, python]`
- Log, Tracker, Overview, Index: no `stale_after`

---

## Step 6 — Link Into the Structure

After creating or updating a document:

1. Does `docs/index.md` or `doc/index.md` list this file?
   → If not: add it to the correct group
2. Does the parent folder have a `README.md`?
   → If yes: add a link to this document there
3. Does a parent concept document exist?
   → If yes: add a Markdown link from parent to this document
4. Does `PROJECT.md` or `README.md` (root) need updating?
   → Only if this is a significant new document

---

## References

- `references/okf-schema.md` — full frontmatter schema
- `references/dita-light.md` — title and structure rules
- `references/checklist.md` — quality checklist
- `templates/task.md` — Runbook template
- `templates/concept.md` — Reference/Decision template
- `templates/reference.md` — Observation/Tracker template
