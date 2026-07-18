"""
Library watcher: monitors data/library/* folders and auto-ingests new documents.

How it works:
- Watches data/library/{IdN, research, personal, admin, inbox} every 5 seconds
- Each subfolder maps to a Qdrant metadata category
- New files are indexed via ingest_document() then moved to data/library/_indexed/
- Failed files are moved to data/library/_errors/

Run with:
  python agents/ingestion/watcher.py
"""
import sys
import time
from datetime import datetime
from pathlib import Path

# Skript unabhaengig vom Aufrufpfad machen
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from ingest import ingest_document, SUPPORTED_EXTENSIONS

# ===== Configuration =====
LIBRARY = PROJECT_ROOT / "data" / "library"
INDEXED = LIBRARY / "_indexed"
ERRORS = LIBRARY / "_errors"

# Unterordner die einer ChromaDB-Kategorie entsprechen
CATEGORY_FOLDERS = ["idn", "research", "personal", "admin", "inbox"]

# Folders to skip
SKIP_FOLDERS = {"_indexed", "_errors"}

POLL_INTERVAL_SEC = 5
SETTLE_DELAY_SEC = 2  # wait between size checks to confirm file is stable


def log(msg: str):
    """Timestamped logging."""
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def is_file_stable(filepath: Path) -> bool:
    """Prueft ob eine Datei nicht mehr beschrieben wird."""
    try:
        size1 = filepath.stat().st_size
        if size1 == 0:
            return False
        time.sleep(SETTLE_DELAY_SEC)
        size2 = filepath.stat().st_size
        return size1 == size2
    except FileNotFoundError:
        return False


def ensure_dirs():
    """Erstellt die Bibliotheksstruktur falls sie noch nicht existiert."""
    for folder in CATEGORY_FOLDERS:
        (LIBRARY / folder).mkdir(parents=True, exist_ok=True)
    INDEXED.mkdir(parents=True, exist_ok=True)
    ERRORS.mkdir(parents=True, exist_ok=True)


def safe_move(src: Path, dst_dir: Path, category: str) -> Path:
    """
    Move src to dst_dir/<category>/<filename>, adding a timestamp if a name
    collision occurs.
    """
    target_dir = dst_dir / category
    target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / src.name
    if target.exists():
        stem, suffix = src.stem, src.suffix
        target = target_dir / f"{stem}_{int(time.time())}{suffix}"
    src.rename(target)
    return target


def process_file(filepath: Path, category: str) -> bool:
    """Indiziert eine Datei und verschiebt sie. Gibt True bei Erfolg zurueck."""
    log(f"→ indexing {filepath.name} (category: {category})")
    try:
        chunks = ingest_document(filepath, category=category)
        target = safe_move(filepath, INDEXED, category)
        log(f"✅ {chunks} chunks → moved to _indexed/{category}/{target.name}\n")
        return True
    except Exception as e:
        log(f"❌ failed: {e}")
        try:
            target = safe_move(filepath, ERRORS, category)
            log(f"   moved to _errors/{category}/{target.name}\n")
        except Exception as move_err:
            log(f"   could not move to errors folder: {move_err}\n")
        return False


def watch():
    """Main loop: scan all category folders for new files."""
    ensure_dirs()

    log(f"📁 Watching {LIBRARY}")
    log(f"   Categories: {CATEGORY_FOLDERS}")
    log(f"   Poll interval: {POLL_INTERVAL_SEC}s")
    log(f"   Drop files into the relevant subfolder, they'll be indexed automatically.\n")

    seen = set()  # tracks paths already being processed (avoid re-processing)

    while True:
        try:
            for category in CATEGORY_FOLDERS:
                folder = LIBRARY / category
                if not folder.is_dir():
                    continue

                for filepath in folder.iterdir():
                    # Skip directories, hidden files, unsupported extensions
                    if not filepath.is_file():
                        continue
                    if filepath.name.startswith("."):
                        continue
                    if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
                        continue
                    if filepath in seen:
                        continue

                    # Verify the file is fully written
                    if not is_file_stable(filepath):
                        continue

                    seen.add(filepath)
                    process_file(filepath, category)
                    seen.discard(filepath)

        except Exception as e:
            log(f"⚠️  loop error: {e}")

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    try:
        watch()
    except KeyboardInterrupt:
        log("👋 watcher stopped.")