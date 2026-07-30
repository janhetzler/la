#!/usr/bin/env python3
"""
lint_frontmatter.py - Prueft OKF-Frontmatter in Markdown-Dateien.
Gibt Fehler aus und beendet mit Exit-Code 1 wenn Pflichtfelder fehlen
oder ungueltiger Werte enthalten.
"""
import sys
import re
from pathlib import Path

ALLOWED_TYPES = {
    "Overview", "Log", "Tracker", "Runbook",
    "Decision", "Reference", "Observation", "Index"
}
ALLOWED_STATUS = {"current", "draft", "stale", "deprecated"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

EXCLUDE_DIRS = {
    "docs/templates",
    "docs/traces",
    "docs/test_results",
}

EXCLUDE_FILES = {
    "CHANGELOG.md",
}

def parse_frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    fields = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip()
    return fields

def should_skip(path):
    p = str(path)
    for d in EXCLUDE_DIRS:
        if p.startswith(d):
            return True
    if path.name in EXCLUDE_FILES:
        return True
    return False

def lint_file(path):
    errors = []
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)

    if fm is None:
        return [f"{path}: Kein Frontmatter gefunden"]

    # type
    t = fm.get("type", "")
    if not t:
        errors.append(f"{path}: Pflichtfeld 'type' fehlt")
    elif t not in ALLOWED_TYPES:
        errors.append(f"{path}: 'type: {t}' unbekannt (erlaubt: {sorted(ALLOWED_TYPES)})")

    # status
    s = fm.get("status", "")
    if not s:
        errors.append(f"{path}: Pflichtfeld 'status' fehlt")
    elif s not in ALLOWED_STATUS:
        errors.append(f"{path}: 'status: {s}' unbekannt (erlaubt: {sorted(ALLOWED_STATUS)})")

    # updated_at
    u = fm.get("updated_at", "")
    if not u:
        errors.append(f"{path}: Pflichtfeld 'updated_at' fehlt")
    elif not DATE_RE.match(u):
        errors.append(f"{path}: 'updated_at: {u}' kein gueltiges ISO-Datum (YYYY-MM-DD)")

    return errors

def main():
    root = Path(".")
    md_files = sorted(root.rglob("*.md"))
    errors = []

    for f in md_files:
        rel = f.relative_to(root)
        if should_skip(rel):
            continue
        errors.extend(lint_file(rel))

    if errors:
        print(f"FEHLER: {len(errors)} Frontmatter-Problem(e) gefunden:\n")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print(f"OK: Alle Markdown-Dateien haben gueltiges OKF-Frontmatter.")
        sys.exit(0)

if __name__ == "__main__":
    main()
