"""
Étape 05 — Création du venv Python + install des dépendances.

Crée le venv '.venv' à la racine du projet et installe
les ~23 packages listés dans requirements.txt.
"""
import os
import subprocess
import sys
import venv
from pathlib import Path

from installer.colors import (
    C, print_ok, print_warn, print_err, print_info, prompt_continue
)
from installer.checks import detect_os


PROJECT_ROOT = Path(__file__).parent.parent.parent
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"


def venv_python() -> str:
    """Retourne le chemin de l'interpréteur Python du venv."""
    if detect_os() == "windows":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def venv_pip() -> str:
    """Retourne le chemin du pip du venv."""
    if detect_os() == "windows":
        return str(VENV_DIR / "Scripts" / "pip.exe")
    return str(VENV_DIR / "bin" / "pip")


def create_venv() -> bool:
    """Crée le venv si nécessaire."""
    if VENV_DIR.exists():
        # Vérifier qu'il est utilisable
        py = venv_python()
        if Path(py).exists():
            print_ok(f"Venv déjà existant : {VENV_DIR}")
            return True
        else:
            print_warn(f"Venv corrompu (pas de Python à {py}), recréation.")
            import shutil
            shutil.rmtree(VENV_DIR)

    print_info(f"Création du venv : {VENV_DIR}")
    try:
        venv.create(VENV_DIR, with_pip=True)
        print_ok("Venv créé")
        return True
    except Exception as e:
        print_err(f"Échec création venv : {e}")
        return False


def upgrade_pip() -> bool:
    """Met à jour pip dans le venv."""
    print_info("Mise à jour de pip dans le venv...")
    try:
        subprocess.check_call(
            [venv_python(), "-m", "pip", "install", "--upgrade", "pip"],
            stdout=subprocess.DEVNULL,
        )
        print_ok("pip à jour")
        return True
    except subprocess.CalledProcessError:
        print_warn("Mise à jour de pip échouée (pas bloquant)")
        return True


def install_requirements() -> bool:
    """Installe les dépendances depuis requirements.txt."""
    if not REQUIREMENTS.exists():
        print_err(f"requirements.txt introuvable à {REQUIREMENTS}")
        return False

    print_info(f"Installation des dépendances ({REQUIREMENTS})...")
    print_info("Cela peut prendre 5-10 min (torch, transformers sont gros).")

    try:
        # Pas de --quiet pour que l'utilisateur voie ce qui se passe
        subprocess.check_call([
            venv_pip(), "install", "-r", str(REQUIREMENTS),
        ])
        print_ok("Toutes les dépendances Python installées")
        return True
    except subprocess.CalledProcessError as e:
        print_err(f"Échec de pip install : {e}")
        print_info("Retente manuellement avec :")
        print_info(f"  source {VENV_DIR}/bin/activate")
        print_info(f"  pip install -r {REQUIREMENTS}")
        return False


def verify_critical_imports() -> bool:
    """Smoke test : vérifie que les imports critiques marchent."""
    print_info("Vérification des imports critiques...")

    test_script = """
import langgraph
import langchain
import langchain_ollama
import qdrant_client
import httpx
import fastapi
print('OK')
"""
    try:
        result = subprocess.check_output(
            [venv_python(), "-c", test_script],
            stderr=subprocess.STDOUT,
            timeout=30,
        ).decode().strip()
        if "OK" in result:
            print_ok("Imports OK")
            return True
        else:
            print_err(f"Imports KO : {result}")
            return False
    except subprocess.CalledProcessError as e:
        print_err(f"Erreur imports : {e.output.decode() if e.output else e}")
        return False


def run() -> bool:
    """Exécute l'étape 05."""
    print(f"{C.BOLD}Création du venv Python + dépendances...{C.RESET}\n")

    if not create_venv():
        return False

    if not upgrade_pip():
        return False

    if not install_requirements():
        return False

    if not verify_critical_imports():
        print_warn("Les imports ne marchent pas, mais l'install continue.")
        # On ne fait pas échouer ici — l'utilisateur peut debug ensuite

    print()
    print_ok("Environnement Python prêt ✨")

    # Conseil pour activer manuellement le venv plus tard
    if detect_os() != "windows":
        print_info(f"Pour activer manuellement : source {VENV_DIR}/bin/activate")
    else:
        print_info(f"Pour activer manuellement : {VENV_DIR}\\Scripts\\activate")

    return True