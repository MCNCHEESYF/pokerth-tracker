#!/bin/bash
# Script pour convertir une image PNG en icône ICNS pour macOS
# Usage: ./create-icns.sh input.png output.icns

if [ $# -ne 2 ]; then
    echo "Usage: $0 <input.png> <output.icns>"
    echo "L'image PNG doit être au moins 1024x1024 pixels"
    exit 1
fi

INPUT="$1"
OUTPUT="$2"

if [ ! -f "$INPUT" ]; then
    echo "Erreur: Le fichier $INPUT n'existe pas"
    exit 1
fi

# Créer un dossier temporaire pour les iconset
ICONSET="${OUTPUT%.icns}.iconset"
mkdir -p "$ICONSET"

# Générer toutes les tailles nécessaires
sips -z 16 16     "$INPUT" --out "$ICONSET/icon_16x16.png"
sips -z 32 32     "$INPUT" --out "$ICONSET/icon_16x16@2x.png"
sips -z 32 32     "$INPUT" --out "$ICONSET/icon_32x32.png"
sips -z 64 64     "$INPUT" --out "$ICONSET/icon_32x32@2x.png"
sips -z 128 128   "$INPUT" --out "$ICONSET/icon_128x128.png"
sips -z 256 256   "$INPUT" --out "$ICONSET/icon_128x128@2x.png"
sips -z 256 256   "$INPUT" --out "$ICONSET/icon_256x256.png"
sips -z 512 512   "$INPUT" --out "$ICONSET/icon_256x256@2x.png"
sips -z 512 512   "$INPUT" --out "$ICONSET/icon_512x512.png"
sips -z 1024 1024 "$INPUT" --out "$ICONSET/icon_512x512@2x.png"

# Créer l'icône ICNS
iconutil -c icns "$ICONSET" -o "$OUTPUT"

# Nettoyer
rm -rf "$ICONSET"

echo "Icône ICNS créée: $OUTPUT"
