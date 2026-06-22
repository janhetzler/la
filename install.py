"""
Chief of Staff — Installeur principal cross-OS.

Lance ce script via :
  - macOS/Linux : ./install.sh
  - Windows :     install.bat

Ou directement : python3 install.py
"""
import os
import sys
import platform
from pathlib import Path

# Ajoute le dossier installer/ au PYTHONPATH
INSTALLER_DIR = Path(__file__).parent / "installer"
sys.path.insert(0, str(INSTALLER_DIR.parent))

from installer.colors import C, print_header, print_step, print_ok, print_warn, print_err, prompt_continue
from installer.checks import detect_os, get_os_info


# ===== Détection OS =====
def show_os_info():
    info = get_os_info()
    print(f"  Système          : {C.BOLD}{info['system']}{C.RESET}")
    print(f"  Version          : {info['release']}")
    print(f"  Architecture     : {info['arch']}")
    print(f"  RAM              : {info['ram_gb']} GB")
    print(f"  Espace disque    : {info['free_disk_gb']} GB libres sur {info['home']}")
    print()


def warn_about_os_limits(os_name: str):
    """Avertit honnêtement sur les limites selon l'OS."""
    if os_name == "macos":
        print_ok("macOS détecté — support complet, y compris pipeline réunion (BlackHole + whisper.cpp + Metal)")
    elif os_name == "linux":
        print_warn(
            "Linux détecté — support partiel :\n"
            "    • Stack Docker, agents, RAG : 100% fonctionnel\n"
            "    • Pipeline réunion (capture audio) : nécessite PulseAudio loopback (config manuelle)\n"
            "    • whisper.cpp tournera en CPU uniquement (sauf si tu as CUDA)"
        )
    elif os_name == "windows":
        print_warn(
            "Windows détecté — support partiel :\n"
            "    • Stack Docker, agents, RAG : fonctionnel via Docker Desktop ou WSL2\n"
            "    • Pipeline réunion (capture audio) : nécessite VB-Cable (config manuelle)\n"
            "    • whisper.cpp tournera en CPU uniquement (sauf si tu as CUDA)"
        )
    else:
        print_warn(f"OS non reconnu ({os_name}) — l'install peut ne pas marcher.")


# ===== Étapes (à implémenter dans installer/steps/) =====
STEPS = [
    ("01", "Vérification des pré-requis système", "step01_prereqs"),
    ("02", "Installation des dépendances système", "step02_system"),
    ("03", "Téléchargement des modèles IA (Ollama)", "step03_models"),
    ("04", "Compilation de whisper.cpp + modèle Whisper", "step04_whisper"),
    ("05", "Environnement Python + dépendances", "step05_python"),
    ("06", "Configuration des clés API (GitHub, Tavily)", "step06_secrets"),
    ("07", "Démarrage de la stack Docker", "step07_stack"),
    ("08", "Tests de validation end-to-end", "step08_validate"),
]


def main():
    print_header("Chief of Staff — Installation")

    print(f"{C.BOLD}Bienvenue !{C.RESET} Cet installeur va te guider pas à pas pour configurer")
    print("ton chief-of-staff personnel local.")
    print()
    print("Durée estimée : ~30-45 minutes (selon ta connexion internet)")
    print("Espace requis : ~25 GB (modèles + Docker images)")
    print()

    show_os_info()
    os_name = detect_os()
    warn_about_os_limits(os_name)
    print()

    if not prompt_continue("Prêt à commencer l'installation ?"):
        print("Installation annulée.")
        sys.exit(0)

    print()
    print_header("Étapes d'installation")
    for num, title, _ in STEPS:
        print(f"  {num}. {title}")
    print()

    # Lancement séquentiel des étapes
    for num, title, module_name in STEPS:
        print()
        print_step(num, title)

        try:
            # Import dynamique du module de l'étape
            module = __import__(f"installer.steps.{module_name}", fromlist=["run"])
            success = module.run()
            if not success:
                print_err(f"L'étape {num} a échoué.")
                if not prompt_continue("Continuer quand même ?"):
                    sys.exit(1)
        except ImportError:
            print_warn(f"Étape {num} pas encore implémentée (module {module_name})")
            # En mode développement, on continue
        except Exception as e:
            print_err(f"Erreur dans l'étape {num} : {e}")
            if not prompt_continue("Continuer ?"):
                sys.exit(1)

    print()
    print_header("✨ Installation terminée !")
    print(f"Pour démarrer ton chief-of-staff : {C.GREEN}./start.sh{C.RESET}")
    print(f"Pour ouvrir l'interface :          {C.GREEN}http://localhost:3000{C.RESET}")
    print(f"Documentation complète :           {C.CYAN}docs/INSTALL.md{C.RESET}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warn("Installation interrompue par l'utilisateur.")
        sys.exit(130)