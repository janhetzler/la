"""
Étape 01 — Vérification des pré-requis système.

Ne fait rien installer. Détecte ce qui est présent, signale ce qui manque,
fournit les instructions d'installation manuelle pour chaque OS.
"""
from installer.colors import C, print_ok, print_warn, print_err, print_info, prompt_continue
from installer.checks import (
    detect_os,
    get_os_info,
    command_exists,
    get_command_version,
    check_docker_running,
)


# Critères minimums du projet
MIN_RAM_GB = 12  # 16 GB recommandé, 12 acceptable
MIN_DISK_GB = 25  # 25 GB pour modèles + Docker images
MIN_PYTHON = (3, 10)


def check_ram(info: dict) -> bool:
    if info["ram_gb"] >= MIN_RAM_GB:
        print_ok(f"RAM : {info['ram_gb']} GB (min {MIN_RAM_GB} GB)")
        if info["ram_gb"] < 16:
            print_info("16 GB recommandé pour confort. Avec 12-15 GB, ça marchera mais sera lent.")
        return True
    else:
        print_err(f"RAM : {info['ram_gb']} GB — minimum {MIN_RAM_GB} GB requis")
        return False


def check_disk(info: dict) -> bool:
    if info["free_disk_gb"] >= MIN_DISK_GB:
        print_ok(f"Disque libre : {info['free_disk_gb']} GB (min {MIN_DISK_GB} GB)")
        return True
    else:
        print_err(f"Disque libre : {info['free_disk_gb']} GB — il faut au moins {MIN_DISK_GB} GB")
        return False


def check_python() -> bool:
    import sys
    version = sys.version_info
    if version >= MIN_PYTHON:
        print_ok(f"Python : {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_err(f"Python {version.major}.{version.minor} — il faut Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")
        return False


def check_homebrew(os_name: str) -> bool:
    if os_name != "macos":
        return True  # Pas applicable sur Linux/Windows
    if command_exists("brew"):
        version = get_command_version("brew")
        print_ok(f"Homebrew : {version}")
        return True
    else:
        print_err("Homebrew n'est pas installé.")
        print_info("Installer avec :")
        print_info('  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
        print_info("  Puis suis les instructions à la fin (ajout au PATH dans ~/.zshrc)")
        return False


def check_git() -> bool:
    if command_exists("git"):
        version = get_command_version("git")
        print_ok(f"Git : {version}")
        return True
    else:
        print_err("Git n'est pas installé.")
        return False


def check_curl() -> bool:
    if command_exists("curl"):
        print_ok("curl : disponible")
        return True
    else:
        print_err("curl n'est pas installé.")
        return False


def run() -> bool:
    """Exécute l'étape 01 — vérification des pré-requis."""
    info = get_os_info()
    os_name = detect_os()

    print(f"{C.BOLD}Vérification de ton environnement...{C.RESET}\n")

    checks = [
        ("RAM", lambda: check_ram(info)),
        ("Espace disque", lambda: check_disk(info)),
        ("Python 3.10+", check_python),
        ("Homebrew (macOS)", lambda: check_homebrew(os_name)),
        ("Git", check_git),
        ("curl", check_curl),
    ]

    failures = []
    for name, fn in checks:
        try:
            if not fn():
                failures.append(name)
        except Exception as e:
            print_err(f"{name} : erreur de vérification ({e})")
            failures.append(name)

    print()

    if failures:
        print_err(f"{len(failures)} pré-requis manquant(s) : {', '.join(failures)}")
        print()
        print(f"{C.YELLOW}Installe-les manuellement, puis relance l'installeur.{C.RESET}")
        print()
        if os_name == "macos":
            print(f"{C.DIM}Aide rapide pour macOS :{C.RESET}")
            print(f"{C.DIM}  • Homebrew : https://brew.sh{C.RESET}")
            print(f"{C.DIM}  • Python   : brew install python@3.12{C.RESET}")
            print(f"{C.DIM}  • Git      : déjà fourni avec Xcode CLI Tools (xcode-select --install){C.RESET}")
        elif os_name == "linux":
            print(f"{C.DIM}Aide rapide pour Ubuntu/Debian :{C.RESET}")
            print(f"{C.DIM}  • Python : sudo apt install python3.12 python3.12-venv{C.RESET}")
            print(f"{C.DIM}  • Git    : sudo apt install git{C.RESET}")
            print(f"{C.DIM}  • curl   : sudo apt install curl{C.RESET}")
        elif os_name == "windows":
            print(f"{C.DIM}Aide rapide pour Windows :{C.RESET}")
            print(f"{C.DIM}  • Python : https://python.org/downloads/ (coche 'Add to PATH'){C.RESET}")
            print(f"{C.DIM}  • Git    : https://git-scm.com/download/win{C.RESET}")
        return False

    print_ok("Tous les pré-requis sont satisfaits ✨")
    return True