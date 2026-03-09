from markitdowngui import build_config


def test_build_hiddenimports_includes_charset_normalizer_mypyc_runtime():
    calls = []

    def fake_collect(package: str) -> list[str]:
        calls.append(package)
        return {
            "markitdown": ["markitdown._markdown"],
            "charset_normalizer": ["charset_normalizer.api"],
            "azure.ai.documentintelligence": ["azure.ai.documentintelligence._client"],
            "azure.identity": [],
            "pypdfium2": [],
            "pypdfium2_raw": [],
            "pytesseract": [],
        }[package]

    hiddenimports = build_config.build_hiddenimports(fake_collect)

    assert "charset_normalizer" in hiddenimports
    assert "charset_normalizer.md" in hiddenimports
    assert "charset_normalizer.md__mypyc" in hiddenimports
    assert "markitdown._markdown" in hiddenimports
    assert calls[:2] == ["markitdown", "charset_normalizer"]


def test_build_hiddenimports_warns_and_keeps_required_modules_when_optional_collection_fails():
    warnings = []

    def fake_collect(package: str) -> list[str]:
        if package == "markitdown":
            return []
        if package == "charset_normalizer":
            return []
        if package == "pytesseract":
            raise RuntimeError("missing optional package")
        return []

    hiddenimports = build_config.build_hiddenimports(
        fake_collect,
        warn=warnings.append,
    )

    assert "charset_normalizer.md__mypyc" in hiddenimports
    assert warnings == [
        "Warning: Could not collect hidden imports for pytesseract: missing optional package"
    ]


def test_build_datas_keeps_base_files_and_warns_for_missing_optional_packages():
    warnings = []

    def fake_collect(package: str) -> list[tuple[str, str]]:
        if package == "magika":
            return [("magika/model.onnx", "magika")]
        if package == "pypdfium2":
            raise RuntimeError("missing pdf runtime")
        if package == "pypdfium2_raw":
            return [("pdfium.dll", "pypdfium2_raw")]
        raise AssertionError(f"Unexpected package: {package}")

    datas = build_config.build_datas(fake_collect, warn=warnings.append)

    assert ("LICENSE", ".") in datas
    assert ("magika/model.onnx", "magika") in datas
    assert ("pdfium.dll", "pypdfium2_raw") in datas
    assert warnings == [
        "Warning: Could not collect data files for pypdfium2: missing pdf runtime"
    ]
