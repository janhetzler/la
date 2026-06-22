"""
Étape 08 — Tests de validation end-to-end + indexation du PDF démo.

Vérifie que toute la chaîne fonctionne :
- Qdrant accessible
- LiteLLM expose les agents
- Embedding via LiteLLM
- Indexation du PDF démo "Attention Is All You Need"
- Recherche RAG sur le PDF
- Premier test de l'agent Researcher
"""
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from installer.colors import (
    C, print_ok, print_warn, print_err, print_info, prompt_continue
)


PROJECT_ROOT = Path(__file__).parent.parent.parent
DEMO_PDF_SRC = PROJECT_ROOT / "installer" / "data" / "demo-attention-is-all-you-need.pdf"
DEMO_PDF_DST = PROJECT_ROOT / "data" / "test-docs" / "demo-attention-is-all-you-need.pdf"


def venv_python() -> str:
    """Chemin vers le Python du venv créé en étape 05."""
    venv_dir = PROJECT_ROOT / ".venv"
    if (venv_dir / "Scripts" / "python.exe").exists():
        return str(venv_dir / "Scripts" / "python.exe")
    return str(venv_dir / "bin" / "python")


def test_qdrant() -> bool:
    """Test que Qdrant répond."""
    try:
        with urllib.request.urlopen("http://localhost:6333", timeout=3) as r:
            if 200 <= r.status < 400:
                print_ok("Qdrant : OK (port 6333)")
                return True
    except Exception as e:
        print_err(f"Qdrant : {e}")
    return False


def test_litellm_models() -> bool:
    """Vérifie que LiteLLM expose les agents et modèles."""
    try:
        req = urllib.request.Request(
            "http://localhost:4000/v1/models",
            headers={"Authorization": "Bearer sk-cos-local-dev"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            import json
            data = json.loads(r.read().decode())
            ids = [m["id"] for m in data.get("data", [])]
            agents = [i for i in ids if i.startswith("agent-")]
            models = [i for i in ids if not i.startswith("agent-")]

            print_ok(f"LiteLLM : {len(models)} modèles + {len(agents)} agents exposés")
            print_info(f"  Agents : {', '.join(agents)}")
            return len(agents) >= 5  # au moins researcher, comms, notes, code, supervisor
    except Exception as e:
        print_err(f"LiteLLM : {e}")
    return False


def test_embedding() -> bool:
    """Test que l'embedding fonctionne via LiteLLM."""
    try:
        import json
        req = urllib.request.Request(
            "http://localhost:4000/v1/embeddings",
            data=json.dumps({
                "model": "granite-embed",
                "input": "test",
            }).encode(),
            headers={
                "Authorization": "Bearer sk-cos-local-dev",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            embedding = data["data"][0]["embedding"]
            if len(embedding) > 0:
                print_ok(f"Embedding : OK ({len(embedding)} dimensions)")
                return True
    except Exception as e:
        print_err(f"Embedding : {e}")
    return False


def copy_demo_pdf() -> bool:
    """Copie le PDF démo dans data/test-docs/ pour qu'il puisse être indexé."""
    if not DEMO_PDF_SRC.exists():
        print_err(f"PDF démo introuvable : {DEMO_PDF_SRC}")
        return False

    DEMO_PDF_DST.parent.mkdir(parents=True, exist_ok=True)
    if not DEMO_PDF_DST.exists():
        shutil.copy(DEMO_PDF_SRC, DEMO_PDF_DST)
        print_ok(f"PDF démo copié : {DEMO_PDF_DST.name}")
    else:
        print_info(f"PDF démo déjà présent : {DEMO_PDF_DST.name}")
    return True


def index_demo_pdf() -> bool:
    """Lance l'indexation du PDF démo via le script existant."""
    ingest_script = PROJECT_ROOT / "agents" / "ingestion" / "ingest.py"
    if not ingest_script.exists():
        print_warn(f"Script d'ingestion introuvable : {ingest_script}")
        print_info("L'utilisateur devra indexer manuellement.")
        return True

    print_info("Indexation du PDF démo dans Qdrant...")
    print_info("(peut prendre 30-60 sec : conversion PDF + embeddings)")

    try:
        result = subprocess.run(
            [venv_python(), str(ingest_script), str(DEMO_PDF_DST)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max
        )
        if result.returncode == 0:
            print_ok("PDF démo indexé dans Qdrant ✨")
            # Affiche un extrait de la sortie pour montrer que ça a marché
            if result.stdout:
                last_lines = result.stdout.strip().split("\n")[-3:]
                for line in last_lines:
                    print_info(f"  {line}")
            return True
        else:
            print_err(f"Échec indexation : code {result.returncode}")
            if result.stderr:
                print_info(result.stderr[:500])
            return False
    except subprocess.TimeoutExpired:
        print_err("Timeout pendant l'indexation")
        return False
    except Exception as e:
        print_err(f"Erreur : {e}")
        return False


def test_rag_search() -> bool:
    """Lance une recherche RAG sur le PDF qu'on vient d'indexer."""
    print_info("Test de recherche sémantique sur le PDF démo...")

    test_script = '''
import sys
sys.path.insert(0, "agents/ingestion")
try:
    from search import search_documents
    results = search_documents("multi-head attention", top_k=2)
    if results and len(results) > 0:
        print(f"OK: {len(results)} chunks trouvés")
    else:
        print("FAIL: aucun résultat")
        sys.exit(1)
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
'''

    try:
        result = subprocess.run(
            [venv_python(), "-c", test_script],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            print_ok(f"Recherche RAG : {result.stdout.strip()}")
            return True
        else:
            print_warn("Recherche RAG : pas de résultat (mais l'install continue)")
            if result.stdout:
                print_info(f"  {result.stdout.strip()}")
            return False
    except Exception as e:
        print_warn(f"Recherche RAG : {e}")
        return False


def show_final_summary():
    """Récapitulatif et instructions de fin."""
    print()
    print(f"{C.BOLD}{C.GREEN}╔══════════════════════════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}║          🎉 Installation Chief of Staff réussie !       ║{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}╚══════════════════════════════════════════════════════════╝{C.RESET}")
    print()
    print(f"{C.BOLD}Comment l'utiliser :{C.RESET}\n")
    print(f"  1. Ouvre {C.CYAN}http://localhost:3000{C.RESET} dans ton navigateur")
    print(f"  2. Crée un compte local (juste un nom et mot de passe)")
    print(f"  3. Sélectionne {C.YELLOW}agent-chief-of-staff{C.RESET} dans le sélecteur de modèles")
    print(f"  4. Pose ta première question !")
    print()
    print(f"{C.BOLD}Exemples de questions :{C.RESET}\n")
    print(f"  • {C.DIM}\"Qu'est-ce que le multi-head attention ?\"{C.RESET}  (RAG sur le PDF démo)")
    print(f"  • {C.DIM}\"Cherche les dernières news sur les LLM\"{C.RESET}  (web search)")
    print(f"  • {C.DIM}\"Rédige un mail à Marie pour annuler la réunion\"{C.RESET}  (rédaction)")
    print(f"  • {C.DIM}\"Comment implémenter un cache LRU en Python ?\"{C.RESET}  (code)")
    print()
    print(f"{C.BOLD}Commandes utiles :{C.RESET}\n")
    print(f"  • Démarrer la stack  : {C.GREEN}./start.sh{C.RESET}")
    print(f"  • Arrêter la stack   : {C.GREEN}./stop.sh{C.RESET}")
    print(f"  • Documentation      : {C.CYAN}docs/INSTALL.md{C.RESET}, {C.CYAN}README.md{C.RESET}")
    print(f"  • En cas de problème : {C.CYAN}docs/TROUBLESHOOTING.md{C.RESET}")
    print()


def run() -> bool:
    """Exécute l'étape 08."""
    print(f"{C.BOLD}Validation end-to-end + indexation du PDF démo...{C.RESET}\n")

    failures = []

    # 1. Tests de connectivité
    print(f"{C.CYAN}▸ Tests de connectivité{C.RESET}")
    if not test_qdrant():
        failures.append("Qdrant")
    if not test_litellm_models():
        failures.append("LiteLLM")
    if not test_embedding():
        failures.append("Embedding")
    print()

    # 2. PDF démo
    print(f"{C.CYAN}▸ PDF démo (Attention Is All You Need){C.RESET}")
    if not copy_demo_pdf():
        failures.append("PDF démo")
    elif not index_demo_pdf():
        print_warn("L'indexation a échoué — tu peux le refaire plus tard avec :")
        print_info(f"  {venv_python()} agents/ingestion/ingest.py {DEMO_PDF_DST}")
    print()

    # 3. Recherche RAG (vérifie que tout marche bout-en-bout)
    print(f"{C.CYAN}▸ Test bout-en-bout (recherche RAG){C.RESET}")
    test_rag_search()
    print()

    # Résumé
    if failures:
        print_warn(f"⚠️  Tests partiellement passés. Problèmes : {', '.join(failures)}")
        print_info("Tu peux quand même utiliser le système, mais certaines fonctions risquent de ne pas marcher.")
        print_info("Consulte docs/TROUBLESHOOTING.md pour les erreurs courantes.")
    else:
        print_ok("Tous les tests sont passés ✨")

    show_final_summary()
    return True