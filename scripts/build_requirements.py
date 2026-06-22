"""
Génère un requirements.txt propre à partir des imports trouvés dans le code.

Stratégie :
1. Scan tous les .py du projet
2. Extrait les imports top-level
3. Filtre les modules de la stdlib et les modules locaux
4. Pour chaque package externe, va chercher sa version dans pip freeze
5. Écrit requirements.txt
"""
import ast
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Modules locaux du projet (à exclure)
LOCAL_MODULES = {
    "config", "tools", "researcher", "researcher_v2", "comms", "notes",
    "code", "supervisor", "handoff", "server", "main",
    "specialists", "agents", "installer",
}

# Mapping import name → pip package name (quand ils diffèrent)
IMPORT_TO_PIP = {
    "yaml": "PyYAML",
    "PIL": "Pillow",
    "dotenv": "python-dotenv",
    "fitz": "PyMuPDF",
    "cv2": "opencv-python",
    "skimage": "scikit-image",
    "sklearn": "scikit-learn",
    "qdrant_client": "qdrant-client",
    "langchain_core": "langchain-core",
    "langchain_openai": "langchain-openai",
    "langchain_ollama": "langchain-ollama",
    "langchain_mcp_adapters": "langchain-mcp-adapters",
    "langgraph": "langgraph",
    "langchain": "langchain",
    "pydantic_settings": "pydantic-settings",
    "llama_index": "llama-index",
    "llama_index": [
        "llama-index-core",
        "llama-index-embeddings-litellm",
        "llama-index-vector-stores-qdrant",
        "llama-index-workflows",
        "llama-index-instrumentation",
    ],
    "torch_xla": None,
}

STDLIB = set(sys.stdlib_module_names)


def extract_imports(filepath: Path) -> set[str]:
    """Extrait les imports top-level d'un fichier Python."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except Exception:
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:  # ignore relative imports
                imports.add(node.module.split(".")[0])
    return imports


def get_installed_version(pkg: str) -> str | None:
    """Retourne la version installée de pkg ou None."""
    try:
        out = subprocess.check_output(
            [sys.executable, "-m", "pip", "show", pkg],
            stderr=subprocess.DEVNULL,
        ).decode()
        for line in out.split("\n"):
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        return None
    return None


def main():
    print(f"Scan des imports dans {PROJECT_ROOT}...")

    all_imports = set()
    for py_file in PROJECT_ROOT.rglob("*.py"):
        # Skip venv, build, tests, scripts utilitaires
        parts = py_file.parts
        if any(p in parts for p in ("xavier-staff", ".venv", "venv", "__pycache__", "scripts")):
            continue
        all_imports.update(extract_imports(py_file))

    # Filtre stdlib et modules locaux
    third_party = sorted(
        imp for imp in all_imports
        if imp not in STDLIB and imp not in LOCAL_MODULES
    )

    print(f"\n{len(third_party)} packages tiers détectés.\n")

    # Récupère les versions
    requirements = []
    not_found = []

    for imp in third_party:
        pip_name = IMPORT_TO_PIP.get(imp, imp)
        if pip_name is None:
            print(f"  ⊘ {imp} (volontairement ignoré)")
            continue
        # Permet une liste de packages pour un seul import (ex: llama_index)
        pkg_list = pip_name if isinstance(pip_name, list) else [pip_name]
        for pkg in pkg_list:
            version = get_installed_version(pkg)
            if version:
                requirements.append(f"{pkg}=={version}")
                print(f"  ✓ {pkg}=={version}")
            else:
                not_found.append(pkg)
                print(f"  ✗ {pkg} (pas trouvé via pip)")

    # Écrit requirements.txt
    req_file = PROJECT_ROOT / "requirements.txt"
    header = """# Chief of Staff — dépendances Python
# Généré automatiquement via scripts/build_requirements.py
# Ne pas éditer à la main, relancer le script si besoin.

"""
    req_file.write_text(header + "\n".join(requirements) + "\n")

    print(f"\n→ Écrit dans {req_file}")
    print(f"  {len(requirements)} packages, {len(not_found)} non résolus")

    if not_found:
        print(f"\n⚠️  Imports non résolus : {', '.join(not_found)}")
        print("   Vérifier manuellement dans requirements.txt")


if __name__ == "__main__":
    main()