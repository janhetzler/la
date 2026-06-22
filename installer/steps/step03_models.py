"""
Étape 03 — Téléchargement des modèles IA via Ollama.

Pull les modèles Granite + embedding utilisés par le projet.
~7-8 GB au total.
"""
import subprocess
import time
from installer.colors import (
    C, print_ok, print_warn, print_err, print_info, prompt_continue
)
from installer.checks import command_exists, check_url_reachable


# Modèles à télécharger (par ordre de priorité, du plus gros au plus petit)
MODELS = [
    ("ibm/granite4:tiny-h", "4.2 GB", "Primary model — used by all agents"),
    ("ibm/granite4:micro-h", "1.9 GB", "Fast model — classification, short outputs"),
    ("granite-embedding:30m", "62 MB", "Embeddings for RAG"),
    ("ibm/granite3.2-guardian:3b", "1.9 GB", "Safety classifier (optional)"),
]

# Modèles optionnels (l'utilisateur peut les skipper)
OPTIONAL_MODELS = {
    "ibm/granite3.2-guardian:3b",
}


def pull_model(model: str, size: str, description: str) -> bool:
    """Pull un modèle Ollama."""
    print(f"\n  {C.CYAN}▸ {model}{C.RESET} ({size})")
    print(f"    {C.DIM}{description}{C.RESET}")

    # Vérifier s'il est déjà présent
    try:
        out = subprocess.check_output(
            ["ollama", "list"],
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).decode()
        if model.split(":")[0] in out and model.split(":")[1] in out:
            print_ok(f"{model} déjà téléchargé")
            return True
    except Exception:
        pass

    # Pull (peut prendre plusieurs minutes selon la connexion)
    print_info(f"Téléchargement... (peut prendre quelques minutes)")
    try:
        result = subprocess.run(
            ["ollama", "pull", model],
            timeout=1800,  # 30 min max par modèle
        )
        if result.returncode == 0:
            print_ok(f"{model} téléchargé")
            return True
        else:
            print_err(f"Échec du téléchargement de {model}")
            return False
    except subprocess.TimeoutExpired:
        print_err(f"Timeout lors du téléchargement de {model}")
        return False
    except Exception as e:
        print_err(f"Erreur : {e}")
        return False


def run() -> bool:
    """Exécute l'étape 03 — pull des modèles."""
    print(f"{C.BOLD}Téléchargement des modèles IA via Ollama...{C.RESET}")
    print(f"{C.DIM}~8 GB au total. Plus rapide en wifi qu'en 4G.{C.RESET}\n")

    # Vérifier qu'Ollama tourne
    if not command_exists("ollama"):
        print_err("Ollama n'est pas installé (étape 02 a échoué).")
        return False

    if not check_url_reachable("http://localhost:11434", timeout=3):
        print_err("Ollama ne répond pas sur le port 11434.")
        print_info("Lance-le manuellement : `ollama serve` (dans un terminal séparé)")
        return False

    # Liste les modèles à télécharger
    print(f"{C.BOLD}Modèles à télécharger :{C.RESET}")
    for model, size, desc in MODELS:
        marker = "(optionnel)" if model in OPTIONAL_MODELS else ""
        print(f"  • {model} — {size} {C.DIM}{marker}{C.RESET}")
    print()

    if not prompt_continue("Lancer les téléchargements ?"):
        return False

    failures = []
    skipped = []
    for model, size, desc in MODELS:
        if model in OPTIONAL_MODELS:
            print()
            if not prompt_continue(f"Télécharger {model} (optionnel) ?"):
                skipped.append(model)
                continue

        if not pull_model(model, size, desc):
            failures.append(model)

    print()
    if skipped:
        print_info(f"Skippés : {', '.join(skipped)}")

    if failures:
        print_err(f"Échec sur : {', '.join(failures)}")
        print_info("Tu peux retenter manuellement : ollama pull <model>")
        return False

    print_ok("Tous les modèles requis sont téléchargés ✨")
    return True