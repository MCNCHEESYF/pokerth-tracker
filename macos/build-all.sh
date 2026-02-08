#!/bin/bash
set -e

# Script principal pour builder et créer le DMG en une seule commande

echo "================================================="
echo "PokerTH Tracker - Build complet (Universal + DMG)"
echo "================================================="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Étape 1: Build universel
echo ""
echo "Étape 1/2: Création du binaire universel..."
"$SCRIPT_DIR/build-universal.sh"

# Étape 2: Création du DMG
echo ""
echo "Étape 2/2: Création du DMG..."
"$SCRIPT_DIR/create-dmg.sh"

echo ""
echo "================================================="
echo "Build complet terminé avec succès!"
echo "================================================="
