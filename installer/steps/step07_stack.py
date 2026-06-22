"""
Étape 07 — Démarrage initial de la stack Docker.

Lance docker compose up, attend que les services soient prêts,
puis valide que tout répond correctement.
"""
import subprocess
import time
from pathlib import Path

from installer.colors import (
    C, print_ok, print_warn, print_err, print_info, prompt_continue
)
from installer.checks import check_url_reachable, check_docker_running


PROJECT_ROOT = Path(__file__).parent.parent.parent
DOCKER_DIR = PROJECT_ROOT / "docker"


def docker_compose_up() -> bool:
    """Lance docker compose up -d."""
    if not check_docker_running():
        print_err("Docker daemon ne tourne pas. Lance Docker Desktop d'abord.")
        return False

    print_info("Lancement de la stack Docker...")
    print_info("(Premier lancement : peut prendre 1-3 min, télécharge les images)")

    try:
        subprocess.check_call(
            ["docker", "compose", "up", "-d"],
            cwd=str(DOCKER_DIR),
        )
        print_ok("Containers démarrés")
        return True
    except subprocess.CalledProcessError as e:
        print_err(f"Échec docker compose up : {e}")
        return False


def wait_for_service(name: str, url: str, headers: dict = None, timeout_s: int = 60) -> bool:
    """Attend qu'un service réponde avec polling."""
    print_info(f"Attente {name}...")
    elapsed = 0
    interval = 3
    while elapsed < timeout_s:
        try:
            import urllib.request
            req = urllib.request.Request(url)
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=2) as r:
                if 200 <= r.status < 400:
                    print_ok(f"{name} répond")
                    return True
        except Exception:
            pass
        time.sleep(interval)
        elapsed += interval

    print_err(f"{name} ne répond pas après {timeout_s}s")
    return False


def check_all_services() -> bool:
    """Vérifie que les 4 services Docker sont up."""
    print_info("\nVérification des services...")

    services = [
        ("Qdrant", "http://localhost:6333", None, 30),
        ("LiteLLM", "http://localhost:4000/v1/models",
         {"Authorization": "Bearer sk-cos-local-dev"}, 60),
        ("Open WebUI", "http://localhost:3000", None, 60),
    ]

    failures = []
    for name, url, headers, timeout in services:
        if not wait_for_service(name, url, headers, timeout):
            failures.append(name)

    if failures:
        print_err(f"Services qui ne répondent pas : {', '.join(failures)}")
        print_info("Vérifie les logs : docker compose logs <service>")
        return False

    return True


def warmup_models() -> bool:
    """
    Pré-charge les modèles principaux dans la RAM Ollama.
    Évite la latence au premier appel.
    """
    print_info("\nPréchauffage des modèles principaux...")

    models_to_warmup = [
        "ibm/granite4:tiny-h",
        "granite-embedding:30m",
    ]

    for model in models_to_warmup:
        print_info(f"  Chauffage de {model}...")
        try:
            # Un simple "hello" pour charger le modèle en RAM
            subprocess.run(
                ["ollama", "run", model, "hello"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
                input="\n",
                text=True,
            )
            print_ok(f"  {model} chargé en RAM")
        except subprocess.TimeoutExpired:
            print_warn(f"  {model} : timeout, mais l'install continue")
        except Exception as e:
            print_warn(f"  {model} : {e}")

    return True


def run() -> bool:
    """Exécute l'étape 07."""
    print(f"{C.BOLD}Démarrage initial de la stack Docker...{C.RESET}\n")

    if not docker_compose_up():
        return False

    # Petit délai avant les checks (les containers viennent juste de démarrer)
    print_info("Patientons 10s pour que les services s'initialisent...")
    time.sleep(10)

    if not check_all_services():
        print_warn("Certains services ne sont pas prêts, mais l'install continue.")
        # On ne fait pas échouer ici — l'utilisateur peut debug ensuite
        if not prompt_continue("Continuer quand même ?", default=True):
            return False

    # Préchauffage (optionnel, mais améliore l'UX au premier usage)
    warmup_models()

    print()
    print_ok("Stack Docker opérationnelle ✨")
    print_info(f"Open WebUI : {C.GREEN}http://localhost:3000{C.RESET}")
    return True