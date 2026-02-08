# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PokerTH Tracker (Windows)
Creates a standalone executable for Windows
"""

import sys
from pathlib import Path

block_cipher = None

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
    hookspath=['.'],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PokerTH Tracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Pas de fenêtre console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='pokerth-tracker.ico',
)
