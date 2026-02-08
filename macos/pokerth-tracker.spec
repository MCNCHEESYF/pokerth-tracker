# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PokerTH Tracker (macOS Universal Binary)
Supports both Intel (x86_64) and Apple Silicon (arm64) architectures
Minimum macOS version: 13.0 (Ventura)
"""

import sys
from pathlib import Path

block_cipher = None

# Détermination de l'architecture cible via variable d'environnement
import os
import platform

target_arch = os.environ.get('TARGET_ARCH')
if not target_arch:
    target_arch = 'arm64' if platform.machine() == 'arm64' else 'x86_64'

print(f"Building for architecture: {target_arch}")

# Configuration de base
a = Analysis(
    ['../main.py'],
    pathex=[str(Path.cwd().parent)],
    binaries=[],
    datas=[
        # Ajoutez ici vos ressources supplémentaires si nécessaire
        # ('path/to/resources', 'destination_folder'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PokerTH Tracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PokerTH Tracker',
)

app = BUNDLE(
    coll,
    name='PokerTH Tracker.app',
    icon='assets/icon.icns',
    bundle_identifier='com.pthtracker.pokerthttracker',
    version='1.0.0',
    info_plist={
        'CFBundleName': 'PokerTH Tracker',
        'CFBundleDisplayName': 'PokerTH Tracker',
        'CFBundleGetInfoString': 'Real-time HUD for PokerTH',
        'CFBundleIdentifier': 'com.pthtracker.pokerthtacker',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 PTHTracker',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '13.0',
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'NSAppleEventsUsageDescription': 'PokerTH Tracker needs to access system events.',
        'NSAppleScriptEnabled': False,
    },
)
