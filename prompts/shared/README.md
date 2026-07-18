# prompts/shared/ -- Geteilter Kontext fuer alle Agenten

Die Dateien hier werden beim Start automatisch in jeden Agenten injiziert.
Sie muessen von dir manuell mit deinen echten Daten befuellt werden.

---

## Dateien

### user_profile.md

Wer bist du? Deine Rolle, Praeferenzen, Projekte.

Wird injiziert via `{{ user_profile }}` in jedem Agent-Prompt.

**Ausfuellen:** Oeffne `prompts/shared/user_profile.md` und ersetze alle
`[Platzhalter]` mit deinen echten Daten.

### project_context.md

Was laeuft gerade? Aktueller Stack, aktive Aufgaben, Architektur.

Wird injiziert via `{{ project_context }}` in jedem Agent-Prompt.

**Ausfuellen:** Halte diese Datei aktuell wenn sich dein Stack oder
deine aktiven Projekte aendern.

---

## Wie die Injection funktioniert

```python
# agent_loader.py
shared = load_shared_context()
# shared["user_profile"]    = Inhalt von user_profile.md
# shared["project_context"] = Inhalt von project_context.md

meta, prompt = load_agent_meta("comms")
prompt = inject_shared(prompt, shared)
# {{ user_profile }} -> Inhalt von user_profile.md
# {{ project_context }} -> Inhalt von project_context.md
```

---

## Tipps

- Je praeziser dein `user_profile.md`, desto besser passen sich die
  Agenten an deinen Stil und deine Beduerfnisse an
- `project_context.md` regelmaessig aktualisieren -- die Agenten
  wissen sonst nicht was gerade aktuell ist
- Beide Dateien sind reine Markdown -- kein YAML, kein Frontmatter
