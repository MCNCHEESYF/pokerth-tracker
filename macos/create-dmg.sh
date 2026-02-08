#!/bin/bash
set -e

# Script pour créer un DMG de PokerTH Tracker
# Crée un DMG avec une belle présentation et un lien vers Applications

echo "========================================"
echo "PokerTH Tracker - Création du DMG"
echo "========================================"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MACOS_DIR="$PROJECT_DIR/macos"
DIST_DIR="$MACOS_DIR/dist"
APP_NAME="PokerTH Tracker"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
VERSION="1.0.0"
DMG_NAME="PokerTH-Tracker-$VERSION-Universal"
DMG_TEMP="$DIST_DIR/dmg_temp"
DMG_FINAL="$DIST_DIR/$DMG_NAME.dmg"

# Vérification que l'app existe
if [ ! -d "$APP_BUNDLE" ]; then
    echo -e "${RED}Erreur: L'application n'existe pas à $APP_BUNDLE${NC}"
    echo "Exécutez d'abord: ./macos/build-universal.sh"
    exit 1
fi

# Nettoyage
echo -e "${YELLOW}Nettoyage...${NC}"
rm -rf "$DMG_TEMP"
rm -f "$DMG_FINAL"
mkdir -p "$DMG_TEMP"

# Copie de l'application dans le dossier temporaire
echo -e "${YELLOW}Copie de l'application...${NC}"
cp -R "$APP_BUNDLE" "$DMG_TEMP/"

# Création du lien vers Applications
echo -e "${YELLOW}Création du lien vers Applications...${NC}"
ln -s /Applications "$DMG_TEMP/Applications"

# Création d'un fichier .DS_Store personnalisé pour la présentation
echo -e "${YELLOW}Configuration de la présentation...${NC}"

# Note: Pour une présentation personnalisée complète, vous pouvez:
# 1. Créer un .DS_Store avec les positions des icônes
# 2. Ajouter une image de fond personnalisée
# Pour l'instant, nous créons un DMG basique mais fonctionnel

# Création du DMG temporaire
echo -e "${YELLOW}Création du DMG...${NC}"
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$DMG_TEMP" \
    -ov \
    -format UDRW \
    "$DIST_DIR/temp.dmg"

# Montage du DMG pour configuration
echo -e "${YELLOW}Configuration du DMG...${NC}"
DEVICE=$(hdiutil attach -readwrite -noverify -noautoopen "$DIST_DIR/temp.dmg" | \
         egrep '^/dev/' | sed 1q | awk '{print $1}')

# Attendre que le volume soit monté
sleep 2

VOLUME_PATH="/Volumes/$APP_NAME"

# Personnalisation du volume (si vous avez une image de fond)
if [ -f "$MACOS_DIR/assets/dmg-background.png" ]; then
    mkdir -p "$VOLUME_PATH/.background"
    cp "$MACOS_DIR/assets/dmg-background.png" "$VOLUME_PATH/.background/"
fi

# Application des paramètres Finder via AppleScript
osascript <<EOF
tell application "Finder"
    tell disk "$APP_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {100, 100, 740, 500}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 72
        set position of item "$APP_NAME.app" of container window to {160, 220}
        set position of item "Applications" of container window to {480, 220}
        close
        open
        update without registering applications
        delay 2
    end tell
end tell
EOF

# Synchronisation
sync

# Démontage
echo -e "${YELLOW}Finalisation...${NC}"
hdiutil detach "$DEVICE"

# Conversion en DMG compressé final
echo -e "${YELLOW}Compression du DMG...${NC}"
hdiutil convert "$DIST_DIR/temp.dmg" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "$DMG_FINAL"

# Nettoyage
rm -f "$DIST_DIR/temp.dmg"
rm -rf "$DMG_TEMP"

# Calcul de la taille du fichier
DMG_SIZE=$(du -h "$DMG_FINAL" | cut -f1)

# Affichage des informations
echo ""
echo -e "${GREEN}=========================================="
echo "DMG créé avec succès!"
echo "==========================================${NC}"
echo "Fichier: $DMG_FINAL"
echo "Taille: $DMG_SIZE"
echo ""
echo "Le DMG contient un binaire universel compatible:"
echo "  • Intel (x86_64)"
echo "  • Apple Silicon (arm64)"
echo "  • macOS 13.0 (Ventura) et supérieur"
echo ""
echo -e "${GREEN}Pour distribuer l'application, partagez ce fichier DMG.${NC}"
