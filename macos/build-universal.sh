#!/bin/bash
set -e

# Script de build universel pour PokerTH Tracker (Intel + Apple Silicon)
# Ce script crée un binaire universel compatible macOS 13+

echo "=========================================="
echo "PokerTH Tracker - Build Universal Binary"
echo "=========================================="

# Couleurs pour le terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MACOS_DIR="$PROJECT_DIR/macos"
BUILD_DIR="$MACOS_DIR/build"
DIST_DIR="$MACOS_DIR/dist"
APP_NAME="PokerTH Tracker"

# Nettoyage des builds précédents
echo -e "${YELLOW}Nettoyage des builds précédents...${NC}"
rm -rf "$BUILD_DIR"
rm -rf "$DIST_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Vérification des prérequis
echo -e "${YELLOW}Vérification des prérequis...${NC}"
if ! command_exists python3; then
    echo -e "${RED}Erreur: python3 n'est pas installé${NC}"
    exit 1
fi

if ! command_exists pyinstaller; then
    echo -e "${RED}Erreur: PyInstaller n'est pas installé${NC}"
    echo "Installez-le avec: pip3 install pyinstaller"
    exit 1
fi

# Détection de l'architecture du système
SYSTEM_ARCH=$(uname -m)
echo "Architecture du système: $SYSTEM_ARCH"

# Build pour les deux architectures
echo ""
echo -e "${GREEN}=== Build Intel (x86_64) ===${NC}"
cd "$MACOS_DIR"
TARGET_ARCH=x86_64 python3 -m PyInstaller \
    --clean \
    --noconfirm \
    pokerth-tracker.spec

# Renommer le build Intel
if [ -d "dist/$APP_NAME.app" ]; then
    mv "dist/$APP_NAME.app" "dist/$APP_NAME-x86_64.app"
    echo -e "${GREEN}✓ Build Intel terminé${NC}"
else
    echo -e "${RED}✗ Échec du build Intel${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Build Apple Silicon (arm64) ===${NC}"
TARGET_ARCH=arm64 python3 -m PyInstaller \
    --clean \
    --noconfirm \
    pokerth-tracker.spec

# Renommer le build ARM
if [ -d "dist/$APP_NAME.app" ]; then
    mv "dist/$APP_NAME.app" "dist/$APP_NAME-arm64.app"
    echo -e "${GREEN}✓ Build Apple Silicon terminé${NC}"
else
    echo -e "${RED}✗ Échec du build Apple Silicon${NC}"
    exit 1
fi

# Création du binaire universel avec lipo
echo ""
echo -e "${GREEN}=== Création du binaire universel ===${NC}"

# Copier la structure de l'app ARM comme base
cp -R "dist/$APP_NAME-arm64.app" "dist/$APP_NAME.app"

# Fusionner les exécutables avec lipo
X86_EXECUTABLE="dist/$APP_NAME-x86_64.app/Contents/MacOS/$APP_NAME"
ARM_EXECUTABLE="dist/$APP_NAME-arm64.app/Contents/MacOS/$APP_NAME"
UNIVERSAL_EXECUTABLE="dist/$APP_NAME.app/Contents/MacOS/$APP_NAME"

if [ -f "$X86_EXECUTABLE" ] && [ -f "$ARM_EXECUTABLE" ]; then
    lipo -create "$X86_EXECUTABLE" "$ARM_EXECUTABLE" -output "$UNIVERSAL_EXECUTABLE"
    echo -e "${GREEN}✓ Binaire universel créé${NC}"

    # Vérification
    echo ""
    echo "Architectures contenues dans le binaire:"
    lipo -info "$UNIVERSAL_EXECUTABLE"

    # Nettoyage des builds intermédiaires
    rm -rf "dist/$APP_NAME-x86_64.app"
    rm -rf "dist/$APP_NAME-arm64.app"
else
    echo -e "${RED}✗ Impossible de créer le binaire universel${NC}"
    exit 1
fi

# Informations finales
echo ""
echo -e "${GREEN}=========================================="
echo "Build universel terminé avec succès!"
echo "==========================================${NC}"
echo "Application: $DIST_DIR/$APP_NAME.app"
echo ""
echo "Pour créer un DMG, exécutez:"
echo "  ./macos/create-dmg.sh"
