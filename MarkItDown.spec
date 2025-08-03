# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from importlib.util import find_spec
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect hidden imports
hiddenimports = []
hiddenimports += collect_submodules('markitdowngui')
hiddenimports += collect_submodules('PySide6')
hiddenimports += collect_submodules('magika')
hiddenimports += [
    'PySide6.QtCore',
    'PySide6.QtWidgets', 
    'PySide6.QtGui',
    'markitdown',
    'markitdowngui.main',
    'markitdowngui.ui.main_window',
    'markitdowngui.utils.update_checker',
    'packaging.version',
    'requests',
    'magika',
    'magika.magika',
]

# Collect data files
datas = []
datas += [
    ('markitdowngui/resources/markitdown-gui.ico', 'markitdowngui/resources'),
    ('markitdowngui/resources/moon.svg', 'markitdowngui/resources'),
    ('markitdowngui/resources/sun.svg', 'markitdowngui/resources'),
    ('LICENSE', '.'), # Add LICENSE file to the root of the bundle
]

# Add all magika data files (models, config, etc.)
try:
    datas += collect_data_files('magika')
except Exception as e:
    print(f"Warning: Could not collect magika data files: {e}")

# Collect PySide6 data files
try:
    datas += collect_data_files('PySide6')
except Exception:
    pass

a = Analysis(
    ['markitdowngui/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MarkItDown',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Changed from True to False - this removes the CMD window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.abspath('markitdowngui/resources/markitdown-gui.ico'),
)
