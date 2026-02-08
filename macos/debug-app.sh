#!/bin/bash
# =============================================================================
# debug-app.sh - Script de débogage pour PokerTH Tracker sur macOS
# =============================================================================

set -euo pipefail

APP_PATH="/Applications/PokerTH Tracker.app"
EXECUTABLE="${APP_PATH}/Contents/MacOS/PokerTH Tracker"
LOG_DIR="${HOME}/Library/Logs/DiagnosticReports"

# Couleurs
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  PokerTH Tracker - Debug Helper${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# Vérifier si l'app est installée
if [ ! -d "${APP_PATH}" ]; then
    echo -e "${RED}[ERREUR]${NC} Application non trouvée dans /Applications"
    echo -e "${YELLOW}[INFO]${NC} Assurez-vous d'avoir installé l'application depuis le DMG"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Application trouvée: ${APP_PATH}"
echo ""

# Afficher les informations du bundle
echo -e "${BLUE}--- Informations du bundle ---${NC}"
if [ -f "${APP_PATH}/Contents/Info.plist" ]; then
    echo "Version: $(defaults read "${APP_PATH}/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null || echo 'N/A')"
    echo "Identifier: $(defaults read "${APP_PATH}/Contents/Info.plist" CFBundleIdentifier 2>/dev/null || echo 'N/A')"
fi
echo ""

# Vérifier les permissions
echo -e "${BLUE}--- Permissions ---${NC}"
if [ -x "${EXECUTABLE}" ]; then
    echo -e "${GREEN}[OK]${NC} L'exécutable a les permissions d'exécution"
else
    echo -e "${RED}[ERREUR]${NC} L'exécutable n'a pas les permissions d'exécution"
    echo "Correction: chmod +x '${EXECUTABLE}'"
fi
echo ""

# Vérifier les crash reports récents
echo -e "${BLUE}--- Crash Reports récents ---${NC}"
if [ -d "${LOG_DIR}" ]; then
    recent_crashes=$(find "${LOG_DIR}" -name "PokerTH*.crash" -o -name "PokerTH*.ips" -mtime -1 2>/dev/null | head -5)
    if [ -n "${recent_crashes}" ]; then
        echo -e "${YELLOW}[ATTENTION]${NC} Crash reports trouvés (dernières 24h):"
        echo "${recent_crashes}"
        echo ""
        echo "Pour voir le dernier crash:"
        latest_crash=$(echo "${recent_crashes}" | head -1)
        echo "  cat '${latest_crash}'"
    else
        echo -e "${GREEN}[OK]${NC} Aucun crash report récent"
    fi
else
    echo "Répertoire de logs non trouvé"
fi
echo ""

# Proposition de lancement
echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}Choisissez une option de débogage:${NC}"
echo ""
echo "1) Lancer l'application avec logs complets"
echo "2) Lancer avec uniquement les erreurs"
echo "3) Vérifier les dépendances Python"
echo "4) Ouvrir Console.app pour voir les logs système"
echo "5) Afficher le dernier crash report"
echo "6) Quitter"
echo ""
read -p "Votre choix [1-6]: " choice

case ${choice} in
    1)
        echo ""
        echo -e "${GREEN}[INFO]${NC} Lancement avec logs complets..."
        echo -e "${YELLOW}--- Sortie de l'application ---${NC}"
        "${EXECUTABLE}" 2>&1
        ;;
    2)
        echo ""
        echo -e "${GREEN}[INFO]${NC} Lancement avec logs d'erreurs uniquement..."
        echo -e "${YELLOW}--- Erreurs de l'application ---${NC}"
        "${EXECUTABLE}" 2>&1 | grep -i "error\|exception\|traceback\|failed" || echo "Aucune erreur trouvée"
        ;;
    3)
        echo ""
        echo -e "${GREEN}[INFO]${NC} Vérification des dépendances Python..."

        # Trouver le Python embarqué
        PYTHON_BIN=$(find "${APP_PATH}/Contents" -name "python*" -type f -perm +111 2>/dev/null | grep -v "\.pyc" | head -1)

        if [ -n "${PYTHON_BIN}" ]; then
            echo "Python trouvé: ${PYTHON_BIN}"
            echo ""
            echo "Modules installés:"
            "${PYTHON_BIN}" -c "import sys; print('\n'.join(sys.path))" 2>/dev/null || echo "Erreur lors de la vérification"
            echo ""
            echo "Test d'import PyQt6:"
            "${PYTHON_BIN}" -c "import PyQt6; print('PyQt6 version:', PyQt6.QtCore.PYQT_VERSION_STR)" 2>&1
        else
            echo -e "${RED}[ERREUR]${NC} Python embarqué non trouvé dans le bundle"
        fi
        ;;
    4)
        echo ""
        echo -e "${GREEN}[INFO]${NC} Ouverture de Console.app..."
        open -a Console
        echo ""
        echo "Dans Console.app:"
        echo "1. Recherchez 'PokerTH' dans la barre de recherche"
        echo "2. Ou allez dans Rapports de diagnostic > PokerTH Tracker"
        ;;
    5)
        echo ""
        latest_crash=$(find "${LOG_DIR}" -name "PokerTH*.crash" -o -name "PokerTH*.ips" -mtime -1 2>/dev/null | head -1)
        if [ -n "${latest_crash}" ]; then
            echo -e "${GREEN}[INFO]${NC} Dernier crash report:"
            echo "${latest_crash}"
            echo ""
            cat "${latest_crash}"
        else
            echo -e "${YELLOW}[INFO]${NC} Aucun crash report récent trouvé"
        fi
        ;;
    6)
        echo "Au revoir!"
        exit 0
        ;;
    *)
        echo -e "${RED}[ERREUR]${NC} Choix invalide"
        exit 1
        ;;
esac
