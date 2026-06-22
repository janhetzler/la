#!/bin/bash
# Wrapper d'installation pour macOS/Linux
# L'installeur principal est install.py — ce wrapper gère juste le bootstrap

set -e

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Chief of Staff — Installation                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. Vérifier qu'on a Python 3.10+
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}❌ Python 3 n'est pas installé.${NC}"
    echo ""
    echo "Installe-le d'abord :"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  ${YELLOW}brew install python@3.12${NC}"
        echo "  (Si Homebrew n'est pas installé : https://brew.sh)"
    else
        echo "  ${YELLOW}sudo apt install python3.12 python3.12-venv${NC} (Ubuntu/Debian)"
        echo "  ${YELLOW}sudo dnf install python3.12${NC} (Fedora)"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✅ Python $PYTHON_VERSION détecté${NC}"

# 2. Vérifier la version (3.10+)
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo -e "${RED}❌ Python 3.10+ requis (tu as $PYTHON_VERSION)${NC}"
    exit 1
fi

# 3. Lancer l'installeur Python
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${BLUE}→ Lancement de l'installeur Python...${NC}"
echo ""

python3 install.py "$@"