---
name: doc
description: "Use this skill whenever a documentation task is involved: creating new documents, updating existing ones, applying OKF frontmatter, reviewing document quality, or navigating the documentation structure of a project. Triggers: 'dokumentiere das', 'doc das', 'schreib das auf', 'aktualisiere die Doku', 'was haben wir dazu dokumentiert?', or any task that produces or modifies a .md file. Follows OKF (Open Knowledge Format), Google Developer Documentation Style Guide, and Diátaxis structure principles."
license: MIT
---

# doc — Documentation Skill

## Hard Rules — Read First

**Allowed `type` values — no others:**
`Overview` · `Log` · `Tracker` · `Runbook` · `Decision` · `Reference` · `Observation` · `Index`

Never invent a new type. `Concept`, `Task`, `Guide`, `Walkthrough` do not exist.
If unsure: `Runbook` for instructions, `Reference` for explanations, `Decision` for architecture choices.

**Never:**
- Delete or shorten existing content
- Change commands, paths, or technical details
- Invent content not in the original
- Set `status: current` without verifying content is actually current
- Push directly to `main`
- Use a `type` not in the list above

**Rule conflict — always resolve in this order:**
When two rules conflict, the higher rule wins:

1. Never delete content ← highest priority
2. Never invent content
3. Apply correct structure (Runbook/Reference/Decision)

If applying structure would require deleting content:
keep the content as-is, skip the structural change,
and escalate with explanation.
Example: "Content cannot be restructured as Runbook without
losing original text — escalating for human decision." 

**Always:**
- Create a branch for any documentation change
- Open a PR — never merge yourself
- Update `index.md` and folder `README.md` after any rename
- Read `references/okf-schema.md` before setting any frontmatter

---

## Activation

Load this skill when the user says or implies:
- "dokumentiere das", "doc das", "schreib das auf"
- "aktualisiere die Doku", "füge das zur Doku hinzu"
- any task that produces or modifies a `.md` file

---

## Workflow

### Step 1 — Orient
1. Read `docs/index.md` or `doc/index.md`
2. Read the relevant folder `README.md`
3. Does a document on this topic already exist? → extend it, don't duplicate

### Step 2 — Quality Gate
Before setting frontmatter:
- [ ] Content complete enough to be useful?
- [ ] Title specific? (not "LLaMA", not "Netzwerk")
- [ ] Content current and accurate?
- [ ] One topic only?
- [ ] Parent document exists? → link from parent to this document

If any NO → fix content first, then set frontmatter.

### Step 3 — Choose Type
See `references/okf-schema.md` — allowed types only.

| Content | type |
|---------|------|
| Step-by-step instructions | `Runbook` |
| Architecture decision with trade-offs | `Decision` |
| Explanation, best practices, inventory | `Reference` |
| Test results, measurements | `Observation` |
| Ongoing collection | `Tracker` |
| Project entry point | `Overview` |
| Folder navigation | `Index` |
| Chronological log | `Log` |

### Step 4 — Title Rules
**Runbook:** Verb + Object → "LLaMA-Server auf dem KVM-Host starten"
**Reference/Decision:** Noun + Description → "RAM-Architektur: KVM-Host Speicheraufteilung"
**Never:** "Walkthrough Netzwerk", "LLaMA", "Setup"

### Step 5 — Frontmatter
Full schema: `references/okf-schema.md`
- `updated_at` = today
- `stale_after` = +6 months (Runbook), +12 months (Reference/Decision)
- `tags` = from actual content, not type description
  Wrong: `[navigation, overview]` · Right: `[kvm, incus, cloudflare]`

### Step 6 — Link Structure
1. `index.md` updated?
2. Folder `README.md` updated?
3. Parent concept document links here?

---

## Autonomous Mode

**Decide without asking:**
- Set frontmatter when all fields are clear from content
- Fix title per Step 4 rules
- Restructure existing content into required sections — never invent
- Update links after rename

**Escalate — stop and report:**
- Content appears outdated or factually wrong
- Two topics in one file — split needed?
- `status: current` questionable
- Content needs rewriting, not restructuring

---

## End Report Format

```
## OKF Review — Abschlussbericht

### Geändert
| Datei | Was geändert |
|-------|-------------|

### Nicht geändert
| Datei | Warum |
|-------|-------|

### Eskalation erforderlich
| Datei | Problem |
|-------|---------|
```

Then wait. Do not merge.

---

## References
- `references/okf-schema.md` — full schema, allowed values
- `references/doc-structure.md` — title and structure rules
- `references/checklist.md` — quality checklist
- `examples/task-good.md` — good Runbook example
- `examples/task-bad.md` — bad Runbook example
