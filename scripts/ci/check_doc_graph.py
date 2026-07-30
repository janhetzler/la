#!/usr/bin/env python3
"""
check_doc_graph.py - Prueft den OKF-Link-Graphen.

Liest alle Markdown-Links aus dem Body jeder Datei und baut einen
gerichteten Graphen: Datei A verlinkt auf Datei B bedeutet A -> B.

Bei einem Push wird geprueft: Wenn Datei B geaendert wurde, aber
Datei A (die auf B verweist) nicht im selben Commit angefasst wurde,
gibt das Script eine Warnung aus.

Ziel: Verwaiste oder veraltete Einstiegspunkte vermeiden.
Beendet mit Exit-Code 0 (nur Warnungen, kein harter Fehler) --
der Graph-Check ist informativ, nicht blockierend.

Benoetigt: CHANGED_FILES als Umgebungsvariable (newline-separierte Liste)
"""
import sys
import re
import os
from pathlib import Path

# Markdown-Link-Regex: findet [text](pfad.md) im Body
LINK_RE = re.compile(r"\[.*?\]\(([^)]+\.md)\)")

# Dateien die als Einstiegspunkte gelten und bei jeder neuen Datei geprueft
# werden muessen
ENTRY_POINTS = {
    "README.md",
    "docs/index.md",
}

# Verzeichnisse ausschliessen
EXCLUDE_DIRS = {
    "docs/templates",
    "docs/traces",
    "docs/test_results",
}

def should_skip(path):
    p = str(path)
    for d in EXCLUDE_DIRS:
        if p.startswith(d):
            return True
    return False

def extract_links(path):
    """Liest alle ausgehenden Markdown-Links aus dem Body einer Datei."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return set()
    # Frontmatter ueberspringen
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end+3:]
    links = set()
    for match in LINK_RE.finditer(text):
        target = match.group(1)
        # Externe Links ignorieren
        if target.startswith("http"):
            continue
        # Anker ignorieren
        if "#" in target:
            target = target.split("#")[0]
        if target:
            links.add(target)
    return links

def build_graph(root):
    """Baut den vollstaendigen Link-Graphen des Repos.
    Gibt zurueck: {datei: set(dateien_die_auf_datei_verweisen)}
    """
    # Vorwaerts-Graph: wer verlinkt auf wen
    forward = {}  # A -> {B, C}
    for f in sorted(root.rglob("*.md")):
        rel = f.relative_to(root)
        if should_skip(rel):
            continue
        links = extract_links(f)
        forward[str(rel)] = links

    # Rueckwaerts-Graph: wer wird von wem verlinkt
    reverse = {}  # B -> {A, C}
    for src, targets in forward.items():
        for target in targets:
            # Pfad normalisieren relativ zu src
            src_dir = Path(src).parent
            target_path = str((src_dir / target).resolve().relative_to(root.resolve()))
            if target_path not in reverse:
                reverse[target_path] = set()
            reverse[target_path].add(src)

    return forward, reverse

def main():
    root = Path(".")

    # Geaenderte Dateien aus Umgebungsvariable lesen
    changed_raw = os.environ.get("CHANGED_FILES", "")
    if not changed_raw:
        print("Keine geaenderten Dateien angegeben (CHANGED_FILES leer).")
        sys.exit(0)

    changed = set(f.strip() for f in changed_raw.strip().splitlines() if f.strip())
    print(f"Geaenderte Dateien: {len(changed)}")
    for f in sorted(changed):
        print(f"  - {f}")

    # Graph aufbauen
    forward, reverse = build_graph(root)

    warnings = []

    for changed_file in sorted(changed):
        # Wer verlinkt auf diese Datei?
        parents = reverse.get(changed_file, set())
        for parent in sorted(parents):
            if parent not in changed:
                warnings.append(
                    f"WARNUNG: '{changed_file}' wurde geaendert, "
                    f"aber '{parent}' (verweist darauf) wurde nicht aktualisiert."
                )

        # Ist es eine neue Datei? Einstiegspunkte pruefen
        for entry in ENTRY_POINTS:
            if entry not in changed and changed_file not in (
                forward.get(entry, set())
            ):
                # Neue Datei die noch nicht in Einstiegspunkt verlinkt ist
                # Das ist eine Info, keine Warnung
                pass

    if warnings:
        print(f"\n{len(warnings)} Hinweis(e) zum Link-Graphen:\n")
        for w in warnings:
            print(f"  ! {w}")
        print("\nBitte pruefen ob die verlinkenden Dokumente aktualisiert werden muessen.")
        print("Dieser Check ist informativ -- der Commit wird nicht blockiert.")
    else:
        print("\nOK: Link-Graph konsistent -- alle verlinkenden Dokumente wurden mitgepflegt.")

    sys.exit(0)  # Immer Exit 0 -- nur Warnungen, kein harter Fehler

if __name__ == "__main__":
    main()
