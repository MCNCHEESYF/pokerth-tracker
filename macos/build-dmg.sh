#!/bin/bash
set -e

# Script principal pour builder et créer le DMG en une seule commande

echo "================================================="
echo "PokerTH Tracker - Build complet Apple Silicon"
echo "================================================="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Étape 1: Build pour l'architecture native
echo ""
echo "Étape 1/2: Build de l'application..."
"$SCRIPT_DIR/build.sh"

# Étape 2: Création du DMG
echo ""
echo "Étape 2/2: Création du DMG..."
"$SCRIPT_DIR/create-dmg.sh"

echo ""
echo "================================================="
echo "Build complet terminé avec succès!"
echo "================================================="
