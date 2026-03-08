# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Keep hidden imports minimal and focused on runtime-dynamic conversion modules.
hiddenimports = [
    "packaging.version",
    "requests",
]
hiddenimports += collect_submodules("markitdown")
for package in (
    "azure.ai.documentintelligence",
    "azure.identity",
    "pypdfium2",
    "pypdfium2_raw",
    "pytesseract",
):
    try:
        hiddenimports += collect_submodules(package)
    except Exception as e:
        print(f"Warning: Could not collect hidden imports for {package}: {e}")

datas = [
    ("markitdowngui/resources/markitdown-gui.ico", "markitdowngui/resources"),
    ("markitdowngui/resources/moon.svg", "markitdowngui/resources"),
    ("markitdowngui/resources/sun.svg", "markitdowngui/resources"),
    ("LICENSE", "."),
]

try:
    datas += collect_data_files("magika")
except Exception as e:
    print(f"Warning: Could not collect magika data files: {e}")

for package in ("pypdfium2", "pypdfium2_raw"):
    try:
        datas += collect_data_files(package)
    except Exception as e:
        print(f"Warning: Could not collect data files for {package}: {e}")

a = Analysis(
    ["markitdowngui/main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "_tkinter",
        "pytest", "_pytest", "pygments",
    ],
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
