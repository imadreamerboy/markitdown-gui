from pathlib import Path

from markitdowngui import build_config


def test_build_hiddenimports_includes_charset_normalizer_mypyc_runtime():
    calls = []

    def fake_collect(package: str) -> list[str]:
        calls.append(package)
        return {
            "markitdown": ["markitdown._markdown"],
            "charset_normalizer": ["charset_normalizer.api"],
        }[package]

    hiddenimports = build_config.build_hiddenimports(fake_collect)

    assert "charset_normalizer" in hiddenimports
    assert "charset_normalizer.md" in hiddenimports
    assert "charset_normalizer.md__mypyc" in hiddenimports
    assert "markitdown._markdown" in hiddenimports
    assert "azure.ai.documentintelligence.aio" in hiddenimports
    assert "glmocr.api" in hiddenimports
    assert "markitdown_pdf_images.converter" in hiddenimports
    assert "pdf_inspector.pdf_inspector" in hiddenimports
    assert "anydoc" in hiddenimports
    assert "anydoc._anydoc" in hiddenimports
    assert calls[:2] == ["markitdown", "charset_normalizer"]


def test_build_hiddenimports_keeps_required_modules_without_collecting_optional_packages():
    def fake_collect(package: str) -> list[str]:
        if package == "markitdown":
            return []
        if package == "charset_normalizer":
            return []
        raise AssertionError(f"Unexpected package: {package}")

    hiddenimports = build_config.build_hiddenimports(fake_collect)

    assert "charset_normalizer.md__mypyc" in hiddenimports
    assert "glmocr.maas_client" in hiddenimports
    assert "docling_parse.pdf_parser" in hiddenimports


def test_build_datas_keeps_base_files_and_warns_for_missing_optional_packages():
    warnings = []

    def fake_collect(package: str) -> list[tuple[str, str]]:
        if package == "docling_parse":
            return [
                (
                    "docling_parse/pdf_resources/fonts",
                    "docling_parse/pdf_resources/fonts",
                )
            ]
        if package == "magika":
            return [("magika/model.onnx", "magika")]
        if package == "pypdfium2":
            raise RuntimeError("missing pdf runtime")
        if package == "pypdfium2_raw":
            return [("pdfium.dll", "pypdfium2_raw")]
        raise AssertionError(f"Unexpected package: {package}")

    datas = build_config.build_datas(fake_collect, warn=warnings.append)

    assert ("LICENSE", ".") in datas
    assert ("THIRD_PARTY_NOTICES.md", ".") in datas
    assert (
        "markitdowngui/resources/icons",
        "markitdowngui/resources/icons",
    ) in datas
    assert (
        "markitdowngui/resources/markitdown-gui.png",
        "markitdowngui/resources",
    ) in datas
    assert (
        "docling_parse/pdf_resources/fonts",
        "docling_parse/pdf_resources/fonts",
    ) in datas
    assert ("magika/model.onnx", "magika") in datas
    assert ("pdfium.dll", "pypdfium2_raw") in datas
    assert warnings == [
        "Warning: Could not collect data files for pypdfium2: missing pdf runtime"
    ]


def test_build_excludes_contains_default_and_optional_ml_packages():
    excludes = build_config.build_excludes()

    assert "tkinter" in excludes
    assert "torch" in excludes
    assert "torch.utils.viz" in excludes
    assert "transformers" in excludes
    assert "glmocr.server" in excludes
    assert "glmocr.pipeline" in excludes


def test_spec_defines_macos_app_bundle():
    spec = Path("MarkItDown.spec").read_text(encoding="utf-8")

    assert 'if sys.platform == "darwin":' in spec
    assert "BUNDLE(" in spec
    assert 'name="MarkItDown.app"' in spec
    assert 'icon=os.path.abspath("markitdowngui/resources/markitdown-gui.icns")' in spec
    assert 'bundle_identifier="com.imadreamerboy.markitdown-gui"' in spec


def test_native_app_icon_assets_are_present():
    resources = Path("markitdowngui/resources")

    for filename in (
        "markitdown-gui.png",
        "markitdown-gui.ico",
        "markitdown-gui.icns",
    ):
        asset = resources / filename
        assert asset.is_file(), asset
        assert asset.stat().st_size > 0


def test_release_workflow_packages_signed_macos_app_bundle():
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    assert 'APP_PATH="dist/MarkItDown.app"' in workflow
    assert 'codesign --force --deep --timestamp=none --sign "$SIGN_IDENTITY" "$APP_PATH"' in workflow
    assert 'codesign --force --deep --timestamp --sign "$SIGN_IDENTITY" "$APP_PATH"' in workflow
    assert "ln -s /Applications dmg_root/Applications" in workflow
    assert "hdiutil create -volname \"MarkItDown\" -srcfolder dmg_root" in workflow


def test_release_workflow_smokes_packaged_app_before_packaging():
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    build_index = workflow.index("- name: Build executable")
    smoke_index = workflow.index("- name: Run packaged-app smoke test")
    package_index = workflow.index("- name: Package artifact")

    assert build_index < smoke_index < package_index
    assert "uv run python packaging/smoke_packaged_app.py" in workflow[smoke_index:package_index]


def test_release_workflow_builds_windows_setup_and_linux_appimage():
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    inno_script = Path("packaging/windows/MarkItDown.iss").read_text(encoding="utf-8")

    assert "choco install innosetup --no-progress -y" in workflow
    assert "packaging\\windows\\MarkItDown.iss" in workflow
    assert "AppId={{9F61B90E-8541-4E0A-A4D7-0C17622E20C2}" in inno_script
    assert "PrivilegesRequired=lowest" in inno_script
    assert r"DefaultDirName={localappdata}\Programs\MarkItDown" in inno_script
    assert "MarkItDown-Windows-Setup-{#AppVersion}" in inno_script
    assert "{userdesktop}" in inno_script
    assert "MarkItDown-Linux-${VERSION}.AppImage" in workflow
    assert "appimagetool-x86_64.AppImage" in workflow
    assert "Exec=AppRun" in workflow
    assert '"**/*.exe"' in workflow
    assert '"**/*.AppImage"' in workflow
    assert "artifacts/**/*.exe" in workflow
    assert "artifacts/**/*.AppImage" in workflow
