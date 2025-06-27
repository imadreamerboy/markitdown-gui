# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from importlib.util import find_spec
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

def get_magika_model_path():
    """Find the path to the installed magika models."""
    try:
        spec = find_spec("magika")
        if spec and spec.origin:
            magika_path = os.path.dirname(spec.origin)
            model_path = os.path.join(magika_path, "models")
            if os.path.isdir(model_path):
                return model_path
    except Exception:
        pass
    return None

# Collect hidden imports
hiddenimports = []
hiddenimports += collect_submodules('markitdowngui')
hiddenimports += collect_submodules('PySide6')
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
]

# Collect data files
datas = []

# Add magika models if available
magika_model_path = get_magika_model_path()
if magika_model_path:
    datas.append((magika_model_path, 'magika/models'))

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
    icon=None,  # You can add an icon file path here if you have one
)
