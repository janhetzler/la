"""
Étape 04 — Compilation de whisper.cpp + téléchargement du modèle Medium.

Utilisé pour la transcription audio des réunions.
Sur macOS Apple Silicon, utilise Metal pour l'accélération GPU.
Sur Linux/Windows : CPU only par défaut, peut être lent.
"""
import os
import subprocess
import urllib.request
from pathlib import Path

from installer.colors import (
    C, print_ok, print_warn, print_err, print_info, prompt_continue
)
from installer.checks import detect_os


PROJECT_ROOT = Path(__file__).parent.parent.parent
WHISPER_DIR = PROJECT_ROOT / "models" / "whisper.cpp"
MODELS_DIR = PROJECT_ROOT / "models" / "whisper"

WHISPER_REPO = "https://github.com/ggerganov/whisper.cpp.git"
WHISPER_MODEL = "ggml-medium.bin"
WHISPER_MODEL_URL = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{WHISPER_MODEL}"
WHISPER_MODEL_SIZE_MB = 1500


def clone_or_update_whisper() -> bool:
    """Clone le repo whisper.cpp ou met à jour s'il existe déjà."""
    if WHISPER_DIR.exists():
        print_info("whisper.cpp déjà cloné, on met à jour...")
        try:
            subprocess.check_call(
                ["git", "-C", str(WHISPER_DIR), "pull"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print_ok("whisper.cpp à jour")
            return True
        except subprocess.CalledProcessError:
            print_warn("Impossible de mettre à jour, on garde la version actuelle.")
            return True
    else:
        print_info("Clonage de whisper.cpp...")
        WHISPER_DIR.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.check_call(
                ["git", "clone", "--depth", "1", WHISPER_REPO, str(WHISPER_DIR)],
            )
            print_ok("whisper.cpp cloné")
            return True
        except subprocess.CalledProcessError:
            print_err("Échec du clonage de whisper.cpp")
            return False


def build_whisper(os_name: str) -> bool:
    """Compile whisper.cpp avec les bonnes options selon l'OS."""
    print_info("Compilation de whisper.cpp...")

    # whisper.cpp utilise CMake pour la compilation
    build_dir = WHISPER_DIR / "build"
    build_dir.mkdir(exist_ok=True)

    try:
        # Configure
        cmake_args = ["cmake", "-B", "build"]
        if os_name == "macos":
            # Activer Metal (par défaut sur Apple Silicon)
            cmake_args.extend(["-DGGML_METAL=ON"])
        cmake_args.append(".")

        subprocess.check_call(
            cmake_args,
            cwd=str(WHISPER_DIR),
        )

        # Build
        subprocess.check_call(
            ["cmake", "--build", "build", "-j", "--config", "Release"],
            cwd=str(WHISPER_DIR),
        )

        # Vérifier que le binaire existe
        binary = WHISPER_DIR / "build" / "bin" / "whisper-cli"
        if not binary.exists():
            # Anciennes versions utilisent "main"
            binary = WHISPER_DIR / "build" / "bin" / "main"
        if not binary.exists():
            # Très anciennes versions
            binary = WHISPER_DIR / "main"

        if binary.exists():
            print_ok(f"Binaire whisper compilé : {binary}")
            return True
        else:
            print_err("Binaire whisper introuvable après compilation")
            return False
    except subprocess.CalledProcessError as e:
        print_err(f"Échec de la compilation : {e}")
        return False


def download_model() -> bool:
    """Télécharge le modèle Whisper Medium (~1.5 GB)."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target = MODELS_DIR / WHISPER_MODEL

    if target.exists():
        size_mb = target.stat().st_size / (1024 * 1024)
        if size_mb > 1000:  # sanity check : au moins 1 GB
            print_ok(f"Modèle Whisper Medium déjà présent ({size_mb:.0f} MB)")
            return True
        else:
            print_warn(f"Modèle existant mais incomplet ({size_mb:.0f} MB), retéléchargement.")
            target.unlink()

    print_info(f"Téléchargement du modèle Whisper Medium (~{WHISPER_MODEL_SIZE_MB} MB)...")
    print_info(f"URL : {WHISPER_MODEL_URL}")

    try:
        # Téléchargement avec barre de progression simple
        def report_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 / total_size)
                bar_len = 30
                filled = int(bar_len * percent / 100)
                bar = "█" * filled + "░" * (bar_len - filled)
                mb_done = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r  {bar} {percent:5.1f}% ({mb_done:.0f}/{mb_total:.0f} MB)", end="", flush=True)

        urllib.request.urlretrieve(WHISPER_MODEL_URL, target, reporthook=report_progress)
        print()  # newline après la barre
        print_ok(f"Modèle Whisper téléchargé : {target}")
        return True
    except Exception as e:
        print()
        print_err(f"Échec du téléchargement : {e}")
        return False


def run() -> bool:
    """Exécute l'étape 04 — whisper.cpp."""
    os_name = detect_os()

    print(f"{C.BOLD}Compilation de whisper.cpp + téléchargement du modèle...{C.RESET}\n")

    # Avertissement plateforme
    if os_name == "macos":
        print_ok("macOS détecté — compilation avec Metal (accélération GPU)")
    elif os_name == "linux":
        print_warn("Linux détecté — compilation CPU uniquement (pas de CUDA configuré)")
    elif os_name == "windows":
        print_warn(
            "Windows détecté — la compilation peut être complexe.\n"
            "    Tu peux skipper cette étape et désactiver la fonctionnalité réunion,\n"
            "    ou suivre https://github.com/ggerganov/whisper.cpp pour Windows."
        )
        if not prompt_continue("Continuer quand même ?", default=False):
            print_info("Étape skippée. Le pipeline réunion ne marchera pas.")
            return True  # On considère ça comme OK volontaire

    # 1. Cloner / mettre à jour whisper.cpp
    if not clone_or_update_whisper():
        return False

    # 2. Compiler
    if not build_whisper(os_name):
        return False

    # 3. Télécharger le modèle
    if not download_model():
        return False

    print()
    print_ok("whisper.cpp prêt pour transcription audio ✨")
    return True