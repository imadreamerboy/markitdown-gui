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
)
OPTIONAL_HIDDENIMPORTS = (
    "azure.ai.documentintelligence",
    "azure.ai.documentintelligence.aio",
    "azure.identity",
    "docling_core.types.doc",
    "docling_core.types.doc.base",
    "docling_core.types.doc.document",
    "docling_core.types.doc.labels",
    "docling_parse.pdf_parser",
    "glmocr",
    "glmocr.api",
    "glmocr.config",
    "glmocr.maas_client",
    "glmocr.parser_result",
    "glmocr.parser_result.base",
    "glmocr.parser_result.pipeline_result",
    "glmocr.utils",
    "glmocr.utils.logging",
    "markitdown_pdf_images",
    "markitdown_pdf_images.converter",
    "markitdown_pdf_images.export",
    "markitdown_pdf_images.models",
    "markitdown_pdf_images.ocr",
    "markitdown_pdf_images.pipeline",
    "markitdown_pdf_images.vector",
    "pypdfium2",
    "pypdfium2_raw",
    "pytesseract",
)
BASE_DATAS = (
    ("markitdowngui/qml", "markitdowngui/qml"),
    ("markitdowngui/resources/icons", "markitdowngui/resources/icons"),
    ("markitdowngui/resources/markitdown-gui.ico", "markitdowngui/resources"),
    ("markitdowngui/resources/markitdown-gui.png", "markitdowngui/resources"),
    ("markitdowngui/resources/moon.svg", "markitdowngui/resources"),
    ("markitdowngui/resources/sun.svg", "markitdowngui/resources"),
    ("LICENSE", "."),
)
OPTIONAL_DATA_PACKAGES = (
    "docling_parse",
    "magika",
    "pypdfium2",
    "pypdfium2_raw",
)
BASE_EXCLUDES = (
    "tkinter",
    "_tkinter",
    "pytest",
    "_pytest",
    "pygments",
)
OPTIONAL_EXCLUDES = (
    "accelerate",
    "glmocr.cli",
    "glmocr.dataloader",
    "glmocr.layout",
    "glmocr.ocr_client",
    "glmocr.pipeline",
    "glmocr.postprocess",
    "glmocr.server",
    "glmocr.tests",
    "huggingface_hub",
    "sentencepiece",
    "tensorboard",
    "torch",
    "torch.utils.tensorboard",
    "torch.utils.viz",
    "torchvision",
    "transformers",
    "tree_sitter",
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

    hiddenimports.extend(OPTIONAL_HIDDENIMPORTS)

    return _dedupe(hiddenimports)


def build_excludes() -> list[str]:
    return list(_dedupe(list(BASE_EXCLUDES) + list(OPTIONAL_EXCLUDES)))


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
