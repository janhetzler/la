"""
start_full.py — vollständiger Stack-Start + kompletter 6-Agenten-Testlauf.

Ruft tests/run_tests.py auf, statt es zu duplizieren.
run_tests.py ist die kanonische Quelle — start_full.py ist nur ein
Wrapper der den richtigen Pfad und die Umgebungsvariablen setzt.

ACHTUNG: Dauert ~3 Minuten. Knapp innerhalb des bash_tool-Limits (~5 Min).
Noch NICHT live getestet in scripts/sandbox/ — basiert auf run_tests.py
das bereits mehrfach erfolgreich gelaufen ist.

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/start_full.py

Umgebungsvariablen:
  MODEL_PATH  (default: /tmp/granite-350m-Q4_K_M.gguf)
  CHROMA_PATH (default: /tmp/chroma_chief)
"""
import sys, os, runpy

# Sicherstellen dass der Repo-Root korrekt ist
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
os.chdir(REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "agents/server"))
sys.path.insert(0, os.path.join(REPO_ROOT, "agents/ingestion"))

print(f"Repo-Root: {REPO_ROOT}", flush=True)
print(f"Starte: tests/run_tests.py\n", flush=True)

run_tests_path = os.path.join(REPO_ROOT, "tests/run_tests.py")
runpy.run_path(run_tests_path, run_name="__main__")
