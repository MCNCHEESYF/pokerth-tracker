#!/bin/bash
# =============================================================================
# build-dmg.sh - Build de l'image DMG pour PokerTH Tracker sur macOS
#
# Usage:   ./macos/build-dmg.sh
# Resultat: PokerTH_Tracker-macOS.dmg dans le repertoire du projet
#
# Pre-requis: Python 3.12+, pip, pyinstaller
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
APP_NAME="PokerTH Tracker"
APP_BUNDLE_NAME="PokerTH Tracker.app"
DMG_NAME="PokerTH_Tracker-macOS"
VERSION="1.0.0"

# Repertoires
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
DIST_DIR="${SCRIPT_DIR}/dist"

# --- Fonctions utilitaires ---------------------------------------------------
log_info()  { echo -e "\033[1;32m[INFO]\033[0m  $*"; }
log_warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
log_error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; }

# --- Verification des pre-requis ---------------------------------------------
check_prerequisites() {
    log_info "Verification des pre-requis..."

    # Verifier que nous sommes sur macOS
    if [ "$(uname)" != "Darwin" ]; then
        log_error "Ce script doit etre execute sur macOS."
        exit 1
    fi

    # Verifier Python
    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 n'est pas installe."
        exit 1
    fi

    # Verifier la version de Python
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    log_info "Python version: ${PYTHON_VERSION}"

    # Verifier pip
    if ! python3 -m pip --version &>/dev/null; then
        log_error "pip n'est pas installe."
        exit 1
    fi

    log_info "Pre-requis OK."
}

# --- Installation des dépendances --------------------------------------------
install_dependencies() {
    log_info "Installation des dependances du projet..."

    # Installer les dépendances depuis requirements.txt
    if [ -f "${PROJECT_DIR}/requirements.txt" ]; then
        log_info "Installation depuis requirements.txt..."
        python3 -m pip install -r "${PROJECT_DIR}/requirements.txt" --quiet
    else
        log_warn "Fichier requirements.txt non trouve."
    fi

    log_info "Dependances du projet installees."
}

# --- Installation de PyInstaller ---------------------------------------------
install_pyinstaller() {
    log_info "Verification de PyInstaller..."

    if ! python3 -m pip show pyinstaller &>/dev/null; then
        log_info "Installation de PyInstaller..."
        python3 -m pip install pyinstaller
    else
        log_info "PyInstaller est deja installe."
    fi
}

# --- Vérification de PyQt6 ---------------------------------------------------
verify_pyqt6() {
    log_info "Verification de PyQt6..."

    if ! python3 -c "import PyQt6" &>/dev/null; then
        log_error "PyQt6 n'est pas installe ou n'est pas accessible."
        log_error "Installez-le avec: pip3 install PyQt6"
        exit 1
    fi

    local pyqt6_version=$(python3 -c "import PyQt6.QtCore; print(PyQt6.QtCore.PYQT_VERSION_STR)" 2>/dev/null)
    log_info "PyQt6 version: ${pyqt6_version}"
}

# --- Nettoyage de l'ancien build ---------------------------------------------
clean_build() {
    log_info "Nettoyage de l'ancien build..."

    rm -rf "${BUILD_DIR}"
    rm -rf "${DIST_DIR}"
    rm -f "${PROJECT_DIR}/${DMG_NAME}.dmg"

    log_info "Nettoyage termine."
}

# --- Creation de l'icone .icns -----------------------------------------------
create_icon() {
    log_info "Creation de l'icone .icns..."

    local svg_icon="${PROJECT_DIR}/appimage/pokerth-tracker.svg"
    local icns_icon="${SCRIPT_DIR}/icon.icns"

    if [ ! -f "${svg_icon}" ]; then
        log_warn "Fichier SVG non trouve: ${svg_icon}"
        log_warn "L'icone par defaut sera utilisee."
        return
    fi

    # Verifier si nous avons les outils pour convertir SVG en ICNS
    if command -v rsvg-convert &>/dev/null && command -v iconutil &>/dev/null; then
        log_info "Conversion SVG -> ICNS..."

        local iconset_dir="${SCRIPT_DIR}/icon.iconset"
        mkdir -p "${iconset_dir}"

        # Generer les differentes tailles d'icones
        for size in 16 32 128 256 512; do
            rsvg-convert -w ${size} -h ${size} "${svg_icon}" -o "${iconset_dir}/icon_${size}x${size}.png"
            rsvg-convert -w $((size * 2)) -h $((size * 2)) "${svg_icon}" -o "${iconset_dir}/icon_${size}x${size}@2x.png"
        done

        # Creer le fichier .icns
        iconutil -c icns "${iconset_dir}" -o "${icns_icon}"
        rm -rf "${iconset_dir}"

        log_info "Icone .icns creee avec succes."
    elif command -v sips &>/dev/null; then
        log_info "Conversion SVG -> PNG -> ICNS avec sips..."

        # Alternative avec sips (disponible par defaut sur macOS)
        local iconset_dir="${SCRIPT_DIR}/icon.iconset"
        mkdir -p "${iconset_dir}"

        # Convertir SVG en PNG haute resolution
        local temp_png="${SCRIPT_DIR}/temp_icon.png"

        # Si qlmanage est disponible, l'utiliser pour convertir le SVG
        if command -v qlmanage &>/dev/null; then
            qlmanage -t -s 1024 -o "${SCRIPT_DIR}" "${svg_icon}" &>/dev/null
            mv "${SCRIPT_DIR}/pokerth-tracker.svg.png" "${temp_png}" 2>/dev/null || true
        fi

        if [ -f "${temp_png}" ]; then
            # Generer les differentes tailles
            for size in 16 32 128 256 512; do
                sips -z ${size} ${size} "${temp_png}" --out "${iconset_dir}/icon_${size}x${size}.png" &>/dev/null
                sips -z $((size * 2)) $((size * 2)) "${temp_png}" --out "${iconset_dir}/icon_${size}x${size}@2x.png" &>/dev/null
            done

            # Creer le fichier .icns
            iconutil -c icns "${iconset_dir}" -o "${icns_icon}"
            rm -rf "${iconset_dir}"
            rm -f "${temp_png}"

            log_info "Icone .icns creee avec succes."
        else
            log_warn "Impossible de convertir le SVG. L'icone par defaut sera utilisee."
        fi
    else
        log_warn "Outils de conversion d'icones non disponibles."
        log_warn "L'icone par defaut sera utilisee."
        log_warn "Pour creer une icone personnalisee, installez: brew install librsvg"
    fi
}

# --- Construction du bundle .app avec PyInstaller ----------------------------
build_app_bundle() {
    log_info "Construction du bundle .app avec PyInstaller..."

    cd "${SCRIPT_DIR}"

    # Executer PyInstaller avec le fichier spec
    python3 -m PyInstaller \
        --clean \
        --noconfirm \
        pokerth-tracker.spec

    if [ ! -d "${DIST_DIR}/${APP_BUNDLE_NAME}" ]; then
        log_error "Echec de la creation du bundle .app"
        exit 1
    fi

    log_info "Bundle .app cree avec succes: ${DIST_DIR}/${APP_BUNDLE_NAME}"

    cd "${PROJECT_DIR}"
}

# --- Creation de l'image DMG -------------------------------------------------
create_dmg() {
    log_info "Creation de l'image DMG..."

    local temp_dmg="${PROJECT_DIR}/${DMG_NAME}-temp.dmg"
    local final_dmg="${PROJECT_DIR}/${DMG_NAME}.dmg"
    local volume_name="${APP_NAME} ${VERSION}"
    local dmg_dir="${SCRIPT_DIR}/dmg_contents"

    # Creer un repertoire temporaire pour le contenu du DMG
    mkdir -p "${dmg_dir}"

    # Copier le bundle .app
    cp -R "${DIST_DIR}/${APP_BUNDLE_NAME}" "${dmg_dir}/"

    # Creer un lien vers /Applications
    ln -s /Applications "${dmg_dir}/Applications"

    # Creer un fichier .DS_Store pour personnaliser l'apparence (optionnel)
    # Ce fichier peut etre cree manuellement et ajoute ici

    # Calculer la taille necessaire
    local dmg_size=$(du -sm "${dmg_dir}" | awk '{print $1}')
    dmg_size=$((dmg_size + 50))  # Ajouter 50MB de marge

    # Creer l'image DMG temporaire
    hdiutil create \
        -volname "${volume_name}" \
        -srcfolder "${dmg_dir}" \
        -ov \
        -format UDRW \
        -size ${dmg_size}m \
        "${temp_dmg}"

    # Monter l'image temporaire
    local device=$(hdiutil attach -readwrite -noverify -noautoopen "${temp_dmg}" | grep -E '^/dev/' | sed 1q | awk '{print $1}')
    local mount_point="/Volumes/${volume_name}"

    # Attendre que le volume soit monte
    sleep 2

    # Personnaliser l'apparence du Finder (optionnel)
    if [ -d "${mount_point}" ]; then
        # Definir la taille et la position de la fenetre
        echo '
           tell application "Finder"
             tell disk "'${volume_name}'"
                   open
                   set current view of container window to icon view
                   set toolbar visible of container window to false
                   set statusbar visible of container window to false
                   set the bounds of container window to {400, 100, 900, 450}
                   set viewOptions to the icon view options of container window
                   set arrangement of viewOptions to not arranged
                   set icon size of viewOptions to 128
                   set position of item "'${APP_BUNDLE_NAME}'" of container window to {125, 180}
                   set position of item "Applications" of container window to {375, 180}
                   close
                   open
                   update without registering applications
                   delay 2
             end tell
           end tell
        ' | osascript || log_warn "Impossible de personnaliser l'apparence du DMG"
    fi

    # Demonter le volume
    hdiutil detach "${device}" -force || true
    sleep 2

    # Convertir en image DMG compresse finale
    rm -f "${final_dmg}"
    hdiutil convert "${temp_dmg}" \
        -format UDZO \
        -imagekey zlib-level=9 \
        -o "${final_dmg}"

    # Nettoyer
    rm -f "${temp_dmg}"
    rm -rf "${dmg_dir}"

    if [ -f "${final_dmg}" ]; then
        local size=$(du -h "${final_dmg}" | cut -f1)
        log_info "Image DMG creee avec succes !"
        log_info "  Fichier : ${final_dmg}"
        log_info "  Taille  : ${size}"
    else
        log_error "Echec de la creation de l'image DMG."
        exit 1
    fi
}

# --- Main --------------------------------------------------------------------
main() {
    echo ""
    echo "============================================="
    echo "  Build DMG - PokerTH Tracker (macOS)"
    echo "============================================="
    echo ""

    check_prerequisites
    install_dependencies
    install_pyinstaller
    verify_pyqt6
    clean_build
    create_icon
    build_app_bundle
    create_dmg

    echo ""
    log_info "Build termine !"
    log_info "Pour installer l'application :"
    log_info "  1. Ouvrir ${DMG_NAME}.dmg"
    log_info "  2. Glisser '${APP_BUNDLE_NAME}' vers Applications"
    echo ""
}

main "$@"
