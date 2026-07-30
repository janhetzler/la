#!/usr/bin/env python3
"""
check_stale.py - Prueft ob Dokumente ihr stale_after-Datum ueberschritten haben.
Oeffnet ein GitHub Issue mit der Liste veralteter Dokumente.
Benoetigt: GITHUB_TOKEN, GITHUB_REPOSITORY als Umgebungsvariablen.
"""
import sys
import re
import os
import json
import urllib.request
from pathlib import Path
from datetime import date

EXCLUDE_DIRS = {
    "docs/templates",
    "docs/traces",
    "docs/test_results",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISSUE_LABEL = "doc-stale"

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
    return False

def find_stale():
    today = date.today()
    stale = []
    root = Path(".")
    for f in sorted(root.rglob("*.md")):
        rel = f.relative_to(root)
        if should_skip(rel):
            continue
        text = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if not fm:
            continue
        sa = fm.get("stale_after", "")
        if not sa or not DATE_RE.match(sa):
            continue
        stale_date = date.fromisoformat(sa)
        if stale_date < today:
            stale.append({
                "file": str(rel),
                "type": fm.get("type", "?"),
                "stale_after": sa,
                "days_overdue": (today - stale_date).days,
            })
    return stale

def open_issue(stale_files):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN oder GITHUB_REPOSITORY nicht gesetzt.")
        sys.exit(1)

    lines = ["| Datei | Typ | Stale after | Tage ueberfaellig |",
             "|-------|-----|-------------|-------------------|"]
    for f in stale_files:
        lines.append(
            f"| `{f['file']}` | {f['type']} | {f['stale_after']} | {f['days_overdue']} |"
        )

    body = f"""## Veraltete Dokumentation

Diese Dokumente haben ihr `stale_after`-Datum ueberschritten und sollten geprueft werden.

{chr(10).join(lines)}

Nach der Pruefung bitte `updated_at` und `stale_after` in der jeweiligen Datei aktualisieren
und dieses Issue schliessen.

---
*Automatisch erstellt von `scripts/ci/check_stale.py`*
"""

    url = f"https://api.github.com/repos/{repo}/issues"
    payload = json.dumps({
        "title": f"Dokumentation pruefen: {len(stale_files)} Datei(en) veraltet",
        "body": body,
        "labels": [ISSUE_LABEL],
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req) as r:
        result = json.load(r)
        print(f"Issue geoeffnet: {result['html_url']}")

def main():
    stale = find_stale()
    if not stale:
        print("Alle Dokumente sind aktuell.")
        sys.exit(0)

    print(f"{len(stale)} veraltete Datei(en) gefunden:")
    for f in stale:
        print(f"  ✗ {f['file']} (stale_after: {f['stale_after']}, {f['days_overdue']} Tage)")

    open_issue(stale)

if __name__ == "__main__":
    main()
