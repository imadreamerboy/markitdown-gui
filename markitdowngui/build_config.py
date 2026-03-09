from __future__ import annotations

from collections.abc import Callable

BASE_HIDDENIMPORTS = (
    "packaging.version",
    "requests",
    "charset_normalizer",
    "charset_normalizer.md",
    "charset_normalizer.md__mypyc",
)
MANDATORY_HIDDENIMPORT_PACKAGES = (
    "markitdown",
    "charset_normalizer",
)
OPTIONAL_HIDDENIMPORT_PACKAGES = (
    "azure.ai.documentintelligence",
    "azure.identity",
    "pypdfium2",
    "pypdfium2_raw",
    "pytesseract",
)
BASE_DATAS = (
    ("markitdowngui/resources/markitdown-gui.ico", "markitdowngui/resources"),
    ("markitdowngui/resources/moon.svg", "markitdowngui/resources"),
    ("markitdowngui/resources/sun.svg", "markitdowngui/resources"),
    ("LICENSE", "."),
)
OPTIONAL_DATA_PACKAGES = (
    "magika",
    "pypdfium2",
    "pypdfium2_raw",
)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def build_hiddenimports(
    collect_submodules: Callable[[str], list[str]],
    *,
    warn: Callable[[str], None] | None = None,
) -> list[str]:
    hiddenimports = list(BASE_HIDDENIMPORTS)

    for package in MANDATORY_HIDDENIMPORT_PACKAGES:
        hiddenimports.extend(collect_submodules(package))

    for package in OPTIONAL_HIDDENIMPORT_PACKAGES:
        try:
            hiddenimports.extend(collect_submodules(package))
        except Exception as exc:
            if warn is not None:
                warn(
                    f"Warning: Could not collect hidden imports for {package}: {exc}"
                )

    return _dedupe(hiddenimports)


def build_datas(
    collect_data_files: Callable[[str], list[tuple[str, str]]],
    *,
    warn: Callable[[str], None] | None = None,
) -> list[tuple[str, str]]:
    datas = list(BASE_DATAS)

    for package in OPTIONAL_DATA_PACKAGES:
        try:
            datas.extend(collect_data_files(package))
        except Exception as exc:
            if warn is not None:
                warn(f"Warning: Could not collect data files for {package}: {exc}")

    return datas
