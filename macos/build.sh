#!/bin/bash
set -e

# Script de build pour l'architecture native uniquement
# Utile quand Python ne supporte qu'une seule architecture

echo "=========================================="
echo "PokerTH Tracker - Build pour Apple Silicon"
echo "=========================================="

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MACOS_DIR="$PROJECT_DIR/macos"
BUILD_DIR="$MACOS_DIR/build"
DIST_DIR="$MACOS_DIR/dist"
APP_NAME="PokerTH Tracker"

# Nettoyage
echo -e "${YELLOW}Nettoyage des builds précédents...${NC}"
rm -rf "$BUILD_DIR"
rm -rf "$DIST_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Vérifications
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}Erreur: python3 n'est pas installé${NC}"
    exit 1
fi

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo -e "${RED}Erreur: PyInstaller n'est pas installé${NC}"
    exit 1
fi

# Détection de l'architecture
SYSTEM_ARCH=$(uname -m)
echo "Architecture du système: $SYSTEM_ARCH"
echo "Build pour: $SYSTEM_ARCH uniquement"

# Build
echo ""
echo -e "${GREEN}=== Build en cours... ===${NC}"
cd "$MACOS_DIR"
TARGET_ARCH=$SYSTEM_ARCH python3 -m PyInstaller \
    --clean \
    --noconfirm \
    pokerth-tracker.spec

# Vérification
if [ -d "dist/$APP_NAME.app" ]; then
    echo -e "${GREEN}✓ Build terminé avec succès${NC}"

    # Vérification de l'architecture
    EXECUTABLE="dist/$APP_NAME.app/Contents/MacOS/$APP_NAME"
    if [ -f "$EXECUTABLE" ]; then
        echo ""
        echo "Architecture du binaire:"
        lipo -info "$EXECUTABLE"
    fi
else
    echo -e "${RED}✗ Échec du build${NC}"
    exit 1
fi

# Informations finales
echo ""
echo -e "${GREEN}=========================================="
echo "Build terminé!"
echo "==========================================${NC}"
echo "Application: $DIST_DIR/$APP_NAME.app"
echo "Architecture: $SYSTEM_ARCH"
echo ""
echo -e "${YELLOW}Note: Optimisé pour Apple Silicon (M1/M2/M3/M4) $SYSTEM_ARCH${NC}"
echo ""
echo "Pour créer un DMG:"
echo "  cd macos && ./create-dmg.sh"
