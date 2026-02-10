#!/bin/bash
# =============================================================================
# build-appimage.sh - Build de l'AppImage pour PokerTH Tracker
#
# Usage:   ./appimage/build-appimage.sh
# Resultat: PokerTH_Tracker-x86_64.AppImage dans le repertoire du projet
#
# Pre-requis: wget, fuse (ou --appimage-extract-and-run pour les environnements sans FUSE)
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
APP_NAME="PokerTH_Tracker"
PYTHON_VERSION="3.12"
PYTHON_APPIMAGE_VERSION="3.12.8"
ARCH="x86_64"

# Repertoires
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${PROJECT_DIR}/appimage/build"
APPDIR="${BUILD_DIR}/${APP_NAME}.AppDir"

# URLs
PYTHON_APPIMAGE_URL="https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.12-cp312-cp312-manylinux2014_x86_64.AppImage"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"

# --- Fonctions utilitaires ---------------------------------------------------
log_info()  { echo -e "\033[1;32m[INFO]\033[0m  $*"; }
log_warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
log_error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; }

cleanup() {
    log_info "Nettoyage des fichiers temporaires..."
    rm -f "${BUILD_DIR}/python-appimage.AppImage"
}

# --- Verification des pre-requis ---------------------------------------------
check_prerequisites() {
    log_info "Verification des pre-requis..."

    for cmd in wget file; do
        if ! command -v "$cmd" &>/dev/null; then
            log_error "'$cmd' est requis mais n'est pas installe."
            exit 1
        fi
    done

    log_info "Pre-requis OK."
}

# --- Nettoyage de l'ancien build ---------------------------------------------
clean_build() {
    if [ -d "${BUILD_DIR}" ]; then
        log_info "Suppression de l'ancien build..."
        rm -rf "${BUILD_DIR}"
    fi
    mkdir -p "${BUILD_DIR}"
}

# --- Telechargement du Python portable ---------------------------------------
download_python_appimage() {
    local python_appimage="${BUILD_DIR}/python-appimage.AppImage"

    if [ ! -f "${python_appimage}" ]; then
        log_info "Telechargement de Python ${PYTHON_APPIMAGE_VERSION} AppImage..."
        wget -q --show-progress -O "${python_appimage}" "${PYTHON_APPIMAGE_URL}"
        chmod +x "${python_appimage}"
    else
        log_info "Python AppImage deja present, reutilisation."
    fi
}

# --- Extraction du Python AppImage -------------------------------------------
extract_python_appimage() {
    local python_appimage="${BUILD_DIR}/python-appimage.AppImage"

    log_info "Extraction du Python AppImage..."
    cd "${BUILD_DIR}"
    "${python_appimage}" --appimage-extract &>/dev/null
    mv squashfs-root "${APPDIR}"
    cd "${PROJECT_DIR}"

    log_info "Python extrait dans ${APPDIR}"
}

# --- Installation des dependances Python -------------------------------------
install_dependencies() {
    log_info "Installation des dependances Python (PyQt6)..."

    local pip="${APPDIR}/opt/python${PYTHON_VERSION}/bin/pip${PYTHON_VERSION}"

    # Mise a jour de pip
    "${pip}" install --upgrade pip --quiet 2>/dev/null

    # Installation des dependances du projet
    "${pip}" install -r "${PROJECT_DIR}/requirements.txt" --quiet 2>/dev/null

    log_info "Dependances installees."
}

# --- Copie du code source de l'application -----------------------------------
copy_application() {
    log_info "Copie du code source de l'application..."

    local app_dir="${APPDIR}/app"
    mkdir -p "${app_dir}"

    # Copier les fichiers source
    cp "${PROJECT_DIR}/main.py" "${app_dir}/"
    cp "${PROJECT_DIR}/config.py" "${app_dir}/"
    cp -r "${PROJECT_DIR}/src" "${app_dir}/"

    # Supprimer les fichiers __pycache__ copies
    find "${app_dir}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    log_info "Code source copie dans ${app_dir}"
}

# --- Configuration de l'AppDir -----------------------------------------------
configure_appdir() {
    log_info "Configuration de l'AppDir..."

    # Supprimer les metadonnees du Python AppImage d'origine
    rm -f "${APPDIR}"/python*.desktop
    rm -f "${APPDIR}"/python*.png
    rm -f "${APPDIR}"/python*.svg
    rm -f "${APPDIR}/usr/share/metainfo/"python*.xml 2>/dev/null || true
    rm -f "${APPDIR}/usr/share/applications/"python*.desktop 2>/dev/null || true

    # Supprimer le AppRun original (symlink vers python) et copier le notre
    rm -f "${APPDIR}/AppRun"
    cp "${SCRIPT_DIR}/AppRun" "${APPDIR}/AppRun"
    chmod +x "${APPDIR}/AppRun"

    # Copier le fichier .desktop a la racine et dans usr/share/applications
    cp "${SCRIPT_DIR}/pokerth-tracker.desktop" "${APPDIR}/pokerth-tracker.desktop"
    mkdir -p "${APPDIR}/usr/share/applications"
    cp "${SCRIPT_DIR}/pokerth-tracker.desktop" "${APPDIR}/usr/share/applications/pokerth-tracker.desktop"

    # Convertir le SVG en PNG (requis pour l'icone dans les explorateurs de fichiers)
    cp "${SCRIPT_DIR}/pokerth-tracker.svg" "${APPDIR}/pokerth-tracker.svg"
    if command -v rsvg-convert &>/dev/null; then
        rsvg-convert -w 256 -h 256 "${SCRIPT_DIR}/pokerth-tracker.svg" -o "${APPDIR}/pokerth-tracker.png"
    elif command -v convert &>/dev/null; then
        convert -background none -density 256 "${SCRIPT_DIR}/pokerth-tracker.svg" -resize 256x256 "${APPDIR}/pokerth-tracker.png"
    elif command -v magick &>/dev/null; then
        magick -background none -density 256 "${SCRIPT_DIR}/pokerth-tracker.svg" -resize 256x256 "${APPDIR}/pokerth-tracker.png"
    else
        log_warn "Aucun outil de conversion SVG->PNG trouve (rsvg-convert, convert, magick)."
        log_warn "L'AppImage n'aura pas d'icone dans l'explorateur de fichiers."
    fi

    # .DirIcon doit pointer vers le PNG pour les explorateurs
    rm -f "${APPDIR}/.DirIcon"
    if [ -f "${APPDIR}/pokerth-tracker.png" ]; then
        ln -s pokerth-tracker.png "${APPDIR}/.DirIcon"
    fi

    # Icones dans les repertoires standard
    local icon_dir="${APPDIR}/usr/share/icons/hicolor/scalable/apps"
    mkdir -p "${icon_dir}"
    cp "${SCRIPT_DIR}/pokerth-tracker.svg" "${icon_dir}/pokerth-tracker.svg"
    if [ -f "${APPDIR}/pokerth-tracker.png" ]; then
        local icon_png_dir="${APPDIR}/usr/share/icons/hicolor/256x256/apps"
        mkdir -p "${icon_png_dir}"
        cp "${APPDIR}/pokerth-tracker.png" "${icon_png_dir}/pokerth-tracker.png"
    fi

    # Creer un fichier AppStream metainfo valide
    mkdir -p "${APPDIR}/usr/share/metainfo"
    cat > "${APPDIR}/usr/share/metainfo/io.github.pokerth_tracker.appdata.xml" << 'APPDATA'
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>io.github.pokerth_tracker</id>
  <name>PokerTH Tracker</name>
  <summary>Real-time HUD for PokerTH</summary>
  <metadata_license>MIT</metadata_license>
  <project_license>MIT</project_license>
  <url type="homepage">https://github.com/ocau/pokerth-tracker</url>
  <description>
    <p>PokerTH Tracker is a real-time Heads-Up Display (HUD) for the PokerTH poker game. It tracks and displays poker statistics such as VPIP, PFR, AF, 3-Bet, C-Bet and more for all players at the table.</p>
  </description>
  <launchable type="desktop-id">pokerth-tracker.desktop</launchable>
  <provides>
    <binary>pokerth-tracker</binary>
  </provides>
</component>
APPDATA

    log_info "AppDir configure."
}

# --- Telechargement de appimagetool -----------------------------------------
download_appimagetool() {
    local appimagetool="${BUILD_DIR}/appimagetool"

    if [ ! -f "${appimagetool}" ]; then
        log_info "Telechargement de appimagetool..."
        wget -q --show-progress -O "${appimagetool}" "${APPIMAGETOOL_URL}"
        chmod +x "${appimagetool}"
    fi
}

# --- Construction de l'AppImage ----------------------------------------------
build_appimage() {
    local appimagetool="${BUILD_DIR}/appimagetool"
    local output="${PROJECT_DIR}/${APP_NAME}-${ARCH}.AppImage"

    log_info "Construction de l'AppImage..."

    # Supprimer l'ancien AppImage si present
    rm -f "${output}"

    # Construire l'AppImage
    ARCH="${ARCH}" "${appimagetool}" --appimage-extract-and-run "${APPDIR}" "${output}" 2>/dev/null

    if [ -f "${output}" ]; then
        chmod +x "${output}"
        local size
        size=$(du -h "${output}" | cut -f1)
        log_info "AppImage cree avec succes !"
        log_info "  Fichier : ${output}"
        log_info "  Taille  : ${size}"
    else
        log_error "Echec de la creation de l'AppImage."
        exit 1
    fi
}

# --- Main --------------------------------------------------------------------
main() {
    echo ""
    echo "============================================="
    echo "  Build AppImage - PokerTH Tracker"
    echo "============================================="
    echo ""

    check_prerequisites
    clean_build
    download_python_appimage
    extract_python_appimage
    install_dependencies
    copy_application
    configure_appdir
    download_appimagetool
    build_appimage
    cleanup

    echo ""
    log_info "Build termine ! Lancez avec :"
    log_info "  ./${APP_NAME}-${ARCH}.AppImage"
    echo ""
}

main "$@"
