"""
Étape 02 — Installation des dépendances système.

Vérifie Docker, Ollama, Node.js. Sur macOS, propose l'install via Homebrew.
Sur Linux/Windows, donne les instructions manuelles.
"""
import subprocess
import sys
import time

from installer.colors import (
    C, print_ok, print_warn, print_err, print_info, prompt_continue
)
from installer.checks import (
    detect_os, command_exists, get_command_version, check_docker_running, check_url_reachable
)


def install_via_brew(package: str, cask: bool = False) -> bool:
    """Lance brew install."""
    cmd = ["brew", "install"]
    if cask:
        cmd.append("--cask")
    cmd.append(package)
    print_info(f"$ {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError:
        return False


def check_docker(os_name: str) -> bool:
    """Vérifie ou installe Docker."""
    if not command_exists("docker"):
        print_err("Docker n'est pas installé.")
        if os_name == "macos":
            print_info("Installation via Homebrew...")
            if prompt_continue("Installer Docker Desktop maintenant ?"):
                if install_via_brew("docker-desktop", cask=True):
                    print_ok("Docker Desktop installé")
                    print_warn("Lance Docker Desktop manuellement (Spotlight → Docker), puis attends que la baleine soit stable.")
                    input(f"  {C.CYAN}Appuie sur Entrée quand Docker Desktop est lancé...{C.RESET}")
                else:
                    print_err("L'installation de Docker Desktop a échoué.")
                    return False
            else:
                return False
        elif os_name == "linux":
            print_info("Pour Linux, installe Docker Engine :")
            print_info("  curl -fsSL https://get.docker.com | sh")
            print_info("  sudo usermod -aG docker $USER")
            print_info("  Puis déconnecte/reconnecte ta session.")
            input(f"  {C.CYAN}Appuie sur Entrée quand c'est fait...{C.RESET}")
        elif os_name == "windows":
            print_info("Pour Windows, télécharge Docker Desktop :")
            print_info("  https://www.docker.com/products/docker-desktop/")
            print_info("  Lance-le et active WSL2 si demandé.")
            input(f"  {C.CYAN}Appuie sur Entrée quand c'est fait...{C.RESET}")

    # Re-vérifier
    if not command_exists("docker"):
        print_err("Docker introuvable même après installation.")
        return False

    print_ok(f"Docker : {get_command_version('docker')}")

    # Vérifier que le daemon tourne
    if not check_docker_running():
        print_warn("Docker est installé mais le daemon ne tourne pas.")
        if os_name == "macos" or os_name == "windows":
            print_info("Lance Docker Desktop et attends que la baleine soit stable.")
        else:
            print_info("Lance le daemon : sudo systemctl start docker")
        input(f"  {C.CYAN}Appuie sur Entrée quand le daemon tourne...{C.RESET}")

        if not check_docker_running():
            print_err("Le daemon Docker ne répond toujours pas.")
            return False

    print_ok("Daemon Docker en marche")
    return True


def check_ollama(os_name: str) -> bool:
    """Vérifie ou installe Ollama."""
    if not command_exists("ollama"):
        print_err("Ollama n'est pas installé.")
        if os_name == "macos":
            print_info("Installation via Homebrew...")
            if prompt_continue("Installer Ollama maintenant ?"):
                if install_via_brew("ollama", cask=False):
                    print_ok("Ollama installé")
                else:
                    print_err("L'installation d'Ollama a échoué.")
                    return False
            else:
                return False
        elif os_name == "linux":
            print_info("Pour Linux, lance le script officiel :")
            print_info("  curl -fsSL https://ollama.com/install.sh | sh")
            input(f"  {C.CYAN}Appuie sur Entrée quand c'est fait...{C.RESET}")
        elif os_name == "windows":
            print_info("Pour Windows, télécharge depuis :")
            print_info("  https://ollama.com/download/windows")
            input(f"  {C.CYAN}Appuie sur Entrée quand c'est fait...{C.RESET}")

    if not command_exists("ollama"):
        print_err("Ollama introuvable.")
        return False

    print_ok(f"Ollama : {get_command_version('ollama')}")

    # Démarrer Ollama (sur macOS, c'est un service launchd ; sur Linux, systemd)
    if os_name == "macos":
        # On essaie de démarrer le service
        try:
            subprocess.run(
                ["brew", "services", "start", "ollama"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except Exception:
            pass

    # Vérifier qu'Ollama répond sur le port 11434
    print_info("Vérification qu'Ollama répond sur le port 11434...")
    for attempt in range(10):
        if check_url_reachable("http://localhost:11434", timeout=2):
            print_ok("Ollama répond sur http://localhost:11434")
            return True
        time.sleep(2)

    print_warn("Ollama ne répond pas sur le port 11434.")
    print_info("Lance-le manuellement : `ollama serve` (dans un terminal séparé)")
    input(f"  {C.CYAN}Appuie sur Entrée quand Ollama tourne...{C.RESET}")
    return check_url_reachable("http://localhost:11434", timeout=5)


def check_node(os_name: str) -> bool:
    """Vérifie ou installe Node.js (pour les serveurs MCP via npx)."""
    if not command_exists("node") or not command_exists("npx"):
        print_err("Node.js / npx ne sont pas installés.")
        if os_name == "macos":
            print_info("Installation via Homebrew...")
            if prompt_continue("Installer Node.js maintenant ?"):
                if install_via_brew("node"):
                    print_ok("Node.js installé")
                else:
                    print_err("L'installation de Node.js a échoué.")
                    return False
            else:
                return False
        elif os_name == "linux":
            print_info("Pour Ubuntu/Debian :")
            print_info("  sudo apt install nodejs npm")
            print_info("Pour Fedora :")
            print_info("  sudo dnf install nodejs npm")
            input(f"  {C.CYAN}Appuie sur Entrée quand c'est fait...{C.RESET}")
        elif os_name == "windows":
            print_info("Pour Windows, télécharge depuis :")
            print_info("  https://nodejs.org/ (version LTS recommandée)")
            input(f"  {C.CYAN}Appuie sur Entrée quand c'est fait...{C.RESET}")

    if not command_exists("node"):
        print_err("Node.js introuvable.")
        return False

    print_ok(f"Node.js : {get_command_version('node')}")
    print_ok(f"npx : {get_command_version('npx')}")
    return True


def run() -> bool:
    """Exécute l'étape 02 — installation système."""
    os_name = detect_os()

    print(f"{C.BOLD}Installation des dépendances système...{C.RESET}")
    print(f"{C.DIM}Composants : Docker, Ollama, Node.js{C.RESET}\n")

    failures = []

    # 1. Docker
    print(f"{C.CYAN}▸ Docker{C.RESET}")
    if not check_docker(os_name):
        failures.append("Docker")
    print()

    # 2. Ollama
    print(f"{C.CYAN}▸ Ollama{C.RESET}")
    if not check_ollama(os_name):
        failures.append("Ollama")
    print()

    # 3. Node.js
    print(f"{C.CYAN}▸ Node.js{C.RESET}")
    if not check_node(os_name):
        failures.append("Node.js")
    print()

    if failures:
        print_err(f"Échec sur : {', '.join(failures)}")
        return False

    print_ok("Toutes les dépendances système sont prêtes ✨")
    return True