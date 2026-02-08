# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PokerTH Tracker on macOS
Note: Ce fichier doit être exécuté depuis le répertoire macos/
"""

import sys
import os

block_cipher = None

# Chemins relatifs depuis le répertoire macos/ (où PyInstaller est exécuté)
a = Analysis(
    ['../main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../src', 'src'),
        ('../config.py', '.'),
    ],
    hiddenimports=[
        'PyQt6',
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
    target_arch=None,
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
    icon='icon.icns',
    bundle_identifier='io.github.pokerth-tracker',
    info_plist='Info.plist',
    version='1.0.0',
)
