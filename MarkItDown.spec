# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from markitdowngui.build_config import build_datas, build_excludes, build_hiddenimports
from markitdowngui import __version__

hiddenimports = build_hiddenimports(collect_submodules, warn=print)
datas = build_datas(collect_data_files, warn=print)
excludes = build_excludes()

a = Analysis(
    ["markitdowngui/main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MarkItDown",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.abspath("markitdowngui/resources/markitdown-gui.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MarkItDown",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="MarkItDown.app",
        icon=None,
        bundle_identifier="com.imadreamerboy.markitdown-gui",
        info_plist={
            "CFBundleName": "MarkItDown",
            "CFBundleDisplayName": "MarkItDown",
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "NSHighResolutionCapable": True,
        },
    )
