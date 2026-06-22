"""
Étape 06 — Configuration des clés API (GitHub, Tavily).

Wizard interactif :
- Demande chaque clé
- Permet de skipper (mode local pur)
- Crée le .env et corrige le mcp.json en conséquence
"""
import json
from pathlib import Path

from installer.colors import (
    C, print_ok, print_warn, print_err, print_info, prompt_continue, prompt_secret
)


PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
MCP_FILE = PROJECT_ROOT / "mcp" / "mcp.json"


def explain_keys():
    """Explique pourquoi on demande ces clés."""
    print(f"{C.BOLD}Pourquoi ces clés ?{C.RESET}\n")
    print(f"  {C.CYAN}GitHub Personal Access Token{C.RESET}")
    print(f"    Permet à l'agent Code d'accéder à GitHub (issues, repos, etc.)")
    print(f"    Si tu skip : l'agent Code marchera mais sans accès GitHub.")
    print()
    print(f"  {C.CYAN}Tavily API Key{C.RESET}")
    print(f"    Permet à l'agent Researcher de faire des recherches web.")
    print(f"    Si tu skip : pas de recherche web, mais le RAG local marchera.")
    print()


def get_github_token() -> str:
    """Demande le token GitHub."""
    print(f"{C.BOLD}1. GitHub Personal Access Token{C.RESET}")
    print(f"   Crée-le sur : {C.CYAN}https://github.com/settings/tokens?type=beta{C.RESET}")
    print(f"   Permissions minimales (repo {C.DIM}peut être public ou privé selon tes besoins{C.RESET}) :")
    print(f"     • Contents: Read")
    print(f"     • Issues: Read and Write")
    print(f"     • Pull requests: Read and Write")
    print(f"     • Metadata: Read")
    print()
    return prompt_secret("Colle ton token GitHub", allow_skip=True)


def get_tavily_key() -> str:
    """Demande la clé Tavily."""
    print(f"\n{C.BOLD}2. Tavily API Key (recherche web){C.RESET}")
    print(f"   Inscris-toi gratuitement sur : {C.CYAN}https://tavily.com{C.RESET}")
    print(f"   Le plan gratuit donne 1000 requêtes/mois (largement suffisant).")
    print(f"   Connexion Google ou GitHub directe, pas de carte bancaire requise.")
    print()
    print(f"   Une fois inscrit, ta clé est dans Dashboard → API Keys.")
    print(f"   Format : commence par {C.DIM}tvly-...{C.RESET} (~40-65 caractères)")
    print()
    return prompt_secret("Colle ta clé Tavily", allow_skip=True)


def validate_github_token(token: str) -> bool:
    """Sanity check : un token GitHub commence par github_pat_, ghp_, gho_, etc."""
    if not token:
        return False
    valid_prefixes = ("github_pat_", "ghp_", "gho_", "ghu_", "ghs_", "ghr_")
    return any(token.startswith(p) for p in valid_prefixes)


def validate_tavily_key(key: str) -> bool:
    """Sanity check : une clé Tavily commence par tvly-."""
    if not key:
        return False
    if key.count("tvly-") > 1:
        # Le piège qu'on a eu : tvly-tvly-...
        return False
    return key.startswith("tvly-")


def write_env_file(github_token: str, tavily_key: str) -> bool:
    """Écrit le fichier .env."""
    lines = ["# Chief of Staff — variables d'environnement", "# Ne pas commiter ce fichier (déjà dans .gitignore)\n"]

    if github_token:
        lines.append(f"GITHUB_TOKEN={github_token}")
    else:
        lines.append("# GITHUB_TOKEN=  # à remplir si tu veux activer l'agent Code")

    if tavily_key:
        lines.append(f"TAVILY_API_KEY={tavily_key}")
    else:
        lines.append("# TAVILY_API_KEY=  # à remplir si tu veux activer la recherche web")

    try:
        ENV_FILE.write_text("\n".join(lines) + "\n")
        # Permissions restrictives
        os_chmod_safe(ENV_FILE, 0o600)
        print_ok(f"Fichier .env créé : {ENV_FILE}")
        return True
    except Exception as e:
        print_err(f"Échec écriture .env : {e}")
        return False


def os_chmod_safe(path: Path, mode: int):
    """Change les permissions, sans échouer sur Windows."""
    try:
        import os
        os.chmod(path, mode)
    except Exception:
        pass  # Windows ne supporte pas chmod Unix


def update_mcp_config(github_token: str, tavily_key: str) -> bool:
    """Met à jour mcp.json pour activer/désactiver les serveurs selon les clés."""
    if not MCP_FILE.exists():
        # Créer une config par défaut
        MCP_FILE.parent.mkdir(parents=True, exist_ok=True)
        config = {"mcpServers": {}}
    else:
        try:
            config = json.loads(MCP_FILE.read_text())
        except Exception as e:
            print_err(f"Erreur lecture mcp.json : {e}")
            return False

    servers = config.setdefault("mcpServers", {})

    # filesystem (toujours actif)
    project_root_abs = str(PROJECT_ROOT.resolve())
    servers["filesystem"] = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", project_root_abs],
    }

    # github
    if github_token:
        servers["github"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
        }
    else:
        servers.pop("github", None)
        print_info("Pas de token GitHub : serveur github désactivé dans mcp.json")

    # tavily
    if tavily_key:
        servers["tavily"] = {
            "command": "npx",
            "args": ["-y", "tavily-mcp@latest"],
            "env": {"TAVILY_API_KEY": "${TAVILY_API_KEY}"},
        }
    else:
        servers.pop("tavily", None)
        print_info("Pas de clé Tavily : serveur tavily désactivé dans mcp.json")

    try:
        MCP_FILE.write_text(json.dumps(config, indent=2) + "\n")
        os_chmod_safe(MCP_FILE, 0o600)
        print_ok(f"mcp.json mis à jour : {MCP_FILE}")
        return True
    except Exception as e:
        print_err(f"Échec écriture mcp.json : {e}")
        return False


def run() -> bool:
    """Exécute l'étape 06."""
    print(f"{C.BOLD}Configuration des clés API...{C.RESET}\n")

    # Si .env existe déjà avec du contenu, demander si on garde
    if ENV_FILE.exists():
        content = ENV_FILE.read_text()
        if "GITHUB_TOKEN=" in content or "TAVILY_API_KEY=" in content:
            print_warn(f"Un fichier .env existe déjà : {ENV_FILE}")
            if not prompt_continue("L'écraser ?", default=False):
                print_info("On garde le .env existant.")
                return True

    explain_keys()

    if not prompt_continue("Configurer les clés maintenant ?"):
        print_info("Tu pourras ajouter les clés plus tard manuellement dans .env")
        # On crée quand même un .env vide pour que l'install puisse continuer
        write_env_file("", "")
        update_mcp_config("", "")
        return True

    # GitHub
    github_token = get_github_token()
    if github_token and not validate_github_token(github_token):
        print_warn("Le token ne commence pas par github_pat_/ghp_/etc. — bizarre.")
        if not prompt_continue("L'utiliser quand même ?", default=False):
            github_token = ""

    # Tavily
    tavily_key = get_tavily_key()
    if tavily_key and not validate_tavily_key(tavily_key):
        if tavily_key.count("tvly-") > 1:
            print_err("Erreur fréquente : ta clé contient 'tvly-' deux fois (préfixe en double).")
            print_info("Vérifie sur https://tavily.com et recopie soigneusement.")
        else:
            print_warn("La clé ne ressemble pas à un format Tavily standard (devrait commencer par 'tvly-').")
        if not prompt_continue("L'utiliser quand même ?", default=False):
            tavily_key = ""

    # Écrire les fichiers
    if not write_env_file(github_token, tavily_key):
        return False

    if not update_mcp_config(github_token, tavily_key):
        return False

    # Récap
    print()
    print(f"{C.BOLD}Récapitulatif :{C.RESET}")
    print(f"  GitHub  : {C.GREEN if github_token else C.DIM}{'✓ configuré' if github_token else '✗ non configuré'}{C.RESET}")
    print(f"  Tavily  : {C.GREEN if tavily_key else C.DIM}{'✓ configuré' if tavily_key else '✗ non configuré'}{C.RESET}")

    if not github_token and not tavily_key:
        print_warn("Aucune clé configurée — tu seras en mode 100% local (pas de web search, pas de GitHub).")

    print_ok("Configuration terminée ✨")
    return True