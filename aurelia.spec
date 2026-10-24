# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for AURELIA — Bulk Certificate Generator.
Supports packaging standalone desktop executables on macOS, Windows, and Linux.
"""

import sys
import os
import customtkinter

block_cipher = None

# CustomTkinter asset directory
ctk_path = os.path.dirname(customtkinter.__file__)

added_datas = [
    ('assets', 'assets'),
    ('presets', 'presets'),
    ('sample.csv', '.'),
    (ctk_path, 'customtkinter'),
]

added_binaries = []

hidden_imports = [
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageTk',
    'pymupdf',
    'pandas',
    'customtkinter',
    'reportlab',
    'darkdetect',
]

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=added_binaries,
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'IPython', 'notebook'],
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
    name='Aurelia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
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
    name='Aurelia',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Aurelia.app',
        icon=None,
        bundle_identifier='com.aurelia.certificategenerator',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleName': 'Aurelia',
            'CFBundleDisplayName': 'AURELIA Studio',
            'CFBundleGetInfoString': 'AURELIA — Bulk Certificate Generator',
            'CFBundleIdentifier': 'com.aurelia.certificategenerator',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
