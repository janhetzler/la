"""Affichage console coloré et utilitaires de prompt."""
import sys


class C:
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    @staticmethod
    def disable_if_no_tty():
        """Désactive les couleurs si on n'est pas dans un terminal (CI, redirection)."""
        if not sys.stdout.isatty():
            for attr in dir(C):
                if attr.isupper() and not attr.startswith("_"):
                    setattr(C, attr, "")


C.disable_if_no_tty()


def print_header(text: str):
    """Affiche un titre encadré."""
    line = "═" * (len(text) + 4)
    print(f"\n{C.CYAN}╔{line}╗{C.RESET}")
    print(f"{C.CYAN}║  {C.BOLD}{text}{C.RESET}{C.CYAN}  ║{C.RESET}")
    print(f"{C.CYAN}╚{line}╝{C.RESET}\n")


def print_step(num: str, title: str):
    """Affiche une étape numérotée."""
    print(f"\n{C.BLUE}━━━ Étape {num} : {C.BOLD}{title}{C.RESET}\n")


def print_ok(msg: str):
    print(f"  {C.GREEN}✅{C.RESET} {msg}")


def print_warn(msg: str):
    print(f"  {C.YELLOW}⚠️  {msg}{C.RESET}")


def print_err(msg: str):
    print(f"  {C.RED}❌ {msg}{C.RESET}")


def print_info(msg: str):
    print(f"  {C.DIM}{msg}{C.RESET}")


def prompt_continue(question: str = "Continuer ?", default: bool = True) -> bool:
    """Demande une confirmation oui/non."""
    suffix = "[O/n]" if default else "[o/N]"
    answer = input(f"  {C.CYAN}? {question} {suffix} {C.RESET}").strip().lower()
    if not answer:
        return default
    return answer in ("o", "oui", "y", "yes")


def prompt_input(question: str, default: str = "", required: bool = False) -> str:
    """Demande une valeur (avec défaut optionnel)."""
    suffix = f" [{default}]" if default else ""
    while True:
        answer = input(f"  {C.CYAN}? {question}{suffix} : {C.RESET}").strip()
        if not answer:
            answer = default
        if not required or answer:
            return answer
        print_err("Cette valeur est requise.")


def prompt_secret(question: str, allow_skip: bool = True) -> str:
    """Demande une valeur sensible (clé API). Affiche en clair pour vérification."""
    skip_hint = " (ou 'skip' pour passer)" if allow_skip else ""
    answer = input(f"  {C.CYAN}? {question}{skip_hint} : {C.RESET}").strip()
    if allow_skip and answer.lower() == "skip":
        return ""
    return answer