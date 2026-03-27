from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from markitdowngui.core.markdown_assets import (
    ASSET_LAYOUT_SEPARATE,
    GeneratedAsset,
    normalize_assets_layout,
)
from markitdowngui.core.pdf_pipeline import (
    PDF_PIPELINE_MARKITDOWN,
    PDF_PIPELINE_PYMUPDF,
    convert_pdf_with_local_ocr as convert_pdf_with_local_ocr_pymupdf,
    extract_pdf_image_assets as extract_pdf_image_assets_pymupdf,
    extract_pdf_markdown,
    extract_pdf_markdown_with_inline_assets,
    normalize_pdf_pipeline,
)
from markitdowngui.utils.logger import AppLogger

IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tiff", ".webp"}
DOCINTEL_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tiff"}
PDF_EXTENSION = ".pdf"
PDF_RENDER_SCALE = 3.0
LOCAL_OCR_TIMEOUT_SECONDS = 60
AZURE_OCR_API_KEY_ENV_VAR = "AZURE_OCR_API_KEY"
CONVERSION_ERROR_PREFIX = "Error converting "
BACKEND_AZURE = "azure"
BACKEND_LOCAL = "local"
BACKEND_NATIVE = "native"
PDF_IMAGE_MIN_WIDTH = 64
PDF_IMAGE_MIN_HEIGHT = 64
PDF_IMAGE_MIN_BYTES = 2048


@dataclass(frozen=True)
class ConversionOptions:
    """User-controlled conversion behavior."""

    ocr_enabled: bool = False
    docintel_endpoint: str = ""
    ocr_languages: str = ""
    tesseract_path: str = ""
    preserve_pdf_images: bool = False
    pdf_assets_layout: str = ASSET_LAYOUT_SEPARATE
    pdf_pipeline: str = PDF_PIPELINE_MARKITDOWN

    @property
    def normalized_docintel_endpoint(self) -> str:
        return self.docintel_endpoint.strip()

    @property
    def normalized_ocr_languages(self) -> str:
        return self.ocr_languages.strip()

    @property
    def normalized_tesseract_path(self) -> str:
        return self.tesseract_path.strip()

    @property
    def normalized_pdf_assets_layout(self) -> str:
        return normalize_assets_layout(self.pdf_assets_layout)

    @property
    def normalized_pdf_pipeline(self) -> str:
        return normalize_pdf_pipeline(self.pdf_pipeline)


@dataclass(frozen=True)
class ConversionOutcome:
    markdown: str
    backend: str = BACKEND_NATIVE
    assets: tuple[GeneratedAsset, ...] = ()


def format_conversion_error(file_path: str, error: Exception) -> str:
    return f"{CONVERSION_ERROR_PREFIX}{file_path}: {error}"


def _summarize_error(error: Exception) -> str:
    message = str(error).strip()
    return message or type(error).__name__


def _raise_ocr_failure(
    file_label: str,
    *,
    native_error: Exception | None = None,
    docintel_attempted: bool = False,
    docintel_error: Exception | None = None,
    local_error: Exception | None = None,
) -> str:
    if docintel_error is not None and local_error is not None:
        raise RuntimeError(
            f"Azure OCR failed for the {file_label} ({_summarize_error(docintel_error)}), "
            f"and local OCR fallback also failed ({_summarize_error(local_error)})."
        ) from docintel_error

    if docintel_error is not None:
        raise RuntimeError(
            f"Azure OCR failed for the {file_label}: {_summarize_error(docintel_error)}"
        ) from docintel_error

    if docintel_attempted and local_error is not None:
        raise RuntimeError(
            f"Azure OCR did not extract text from the {file_label}, and local OCR fallback also failed "
            f"({_summarize_error(local_error)})."
        ) from local_error

    if native_error is not None and local_error is not None:
        raise RuntimeError(
            f"Native extraction failed for the {file_label} ({_summarize_error(native_error)}), "
            f"and local OCR fallback also failed ({_summarize_error(local_error)})."
        ) from native_error

    if native_error is not None:
        raise RuntimeError(
            f"Native extraction failed for the {file_label}: {_summarize_error(native_error)}"
        ) from native_error

    if local_error is not None:
        raise RuntimeError(
            f"Local OCR failed for the {file_label}: {_summarize_error(local_error)}"
        ) from local_error

    raise RuntimeError(f"OCR did not extract any text from the {file_label}.")


def _build_docintel_credential() -> tuple[object, str]:
    api_key = os.getenv(AZURE_OCR_API_KEY_ENV_VAR, "").strip()
    if api_key:
        from azure.core.credentials import AzureKeyCredential

        return AzureKeyCredential(api_key), "api_key"

    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential(), "azure_identity"


def test_azure_ocr_connection(options: ConversionOptions) -> str:
    endpoint = options.normalized_docintel_endpoint
    if not endpoint:
        raise RuntimeError("Set an Azure Document Intelligence endpoint first.")

    api_key = os.getenv(AZURE_OCR_API_KEY_ENV_VAR, "").strip()
    if not api_key:
        raise RuntimeError(
            "Set AZURE_OCR_API_KEY before using Test Azure OCR. This check validates API-key authentication only."
        )

    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.ai.documentintelligence import DocumentIntelligenceAdministrationClient
    except ImportError as exc:
        raise RuntimeError(
            "Azure OCR testing requires azure-ai-documentintelligence to be installed."
        ) from exc

    client = DocumentIntelligenceAdministrationClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key),
    )
    try:
        list(islice(client.list_models(), 1))
    finally:
        if hasattr(client, "close"):
            client.close()

    return "api_key"


def convert_file_with_details(
    file_path: str,
    options: ConversionOptions | None = None,
) -> ConversionOutcome:
    """Convert a single file to Markdown text and report which backend produced it."""
    effective_options = options or ConversionOptions()
    extension = Path(file_path).suffix.lower()

    if extension == PDF_EXTENSION:
        if effective_options.normalized_pdf_pipeline == PDF_PIPELINE_PYMUPDF:
            return _convert_pdf_with_pymupdf_pipeline(file_path, effective_options)
        if not effective_options.ocr_enabled:
            markdown = _convert_with_markitdown(file_path, effective_options)
            return ConversionOutcome(
                markdown=markdown,
                backend=BACKEND_NATIVE,
                assets=_maybe_extract_pdf_image_assets(file_path, effective_options),
            )
        return _convert_pdf_with_ocr_fallback(file_path, effective_options)

    if not effective_options.ocr_enabled:
        return ConversionOutcome(
            markdown=_convert_with_markitdown(file_path, effective_options),
            backend=BACKEND_NATIVE,
        )

    if extension in IMAGE_EXTENSIONS:
        return _convert_image_with_ocr(file_path, effective_options, extension)

    return ConversionOutcome(
        markdown=_convert_with_markitdown(file_path, effective_options),
        backend=BACKEND_NATIVE,
    )


def convert_file(file_path: str, options: ConversionOptions | None = None) -> str:
    """Convert a single file to Markdown text."""
    return convert_file_with_details(file_path, options).markdown


def _convert_image_with_ocr(
    file_path: str,
    options: ConversionOptions,
    extension: str,
) -> ConversionOutcome:
    docintel_error: Exception | None = None
    docintel_attempted = False

    if (
        options.normalized_docintel_endpoint
        and extension in DOCINTEL_IMAGE_EXTENSIONS
    ):
        docintel_attempted = True
        try:
            markdown = _convert_with_markitdown(
                file_path,
                options,
                use_docintel=True,
            )
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_AZURE)
        except Exception as exc:
            docintel_error = exc

    local_error: Exception | None = None
    try:
        markdown = _convert_image_with_local_ocr(file_path, options)
        if markdown.strip():
            return ConversionOutcome(markdown=markdown, backend=BACKEND_LOCAL)
    except Exception as exc:
        local_error = exc

    return _raise_ocr_failure(
        "image",
        docintel_attempted=docintel_attempted,
        docintel_error=docintel_error,
        local_error=local_error,
    )


def _convert_pdf_with_ocr_fallback(
    file_path: str,
    options: ConversionOptions,
) -> ConversionOutcome:
    native_error: Exception | None = None
    try:
        markdown = _convert_with_markitdown(file_path, options)
        if markdown.strip():
            return ConversionOutcome(
                markdown=markdown,
                backend=BACKEND_NATIVE,
                assets=_maybe_extract_pdf_image_assets(file_path, options),
            )
    except Exception as exc:
        native_error = exc

    docintel_error: Exception | None = None
    docintel_attempted = False
    if options.normalized_docintel_endpoint:
        docintel_attempted = True
        try:
            markdown = _convert_with_markitdown(
                file_path,
                options,
                use_docintel=True,
            )
            if markdown.strip():
                return ConversionOutcome(
                    markdown=markdown,
                    backend=BACKEND_AZURE,
                    assets=_maybe_extract_pdf_image_assets(file_path, options),
                )
        except Exception as exc:
            docintel_error = exc

    local_error: Exception | None = None
    try:
        markdown = _convert_pdf_with_local_ocr(file_path, options)
        if markdown.strip():
            return ConversionOutcome(
                markdown=markdown,
                backend=BACKEND_LOCAL,
                assets=_maybe_extract_pdf_image_assets(file_path, options),
            )
    except Exception as exc:
        local_error = exc

    return _raise_ocr_failure(
        "PDF",
        native_error=native_error,
        docintel_attempted=docintel_attempted,
        docintel_error=docintel_error,
        local_error=local_error,
    )


def _convert_pdf_with_pymupdf_pipeline(
    file_path: str,
    options: ConversionOptions,
) -> ConversionOutcome:
    if not options.ocr_enabled:
        if options.preserve_pdf_images:
            markdown, assets = extract_pdf_markdown_with_inline_assets(
                file_path,
                min_width=PDF_IMAGE_MIN_WIDTH,
                min_height=PDF_IMAGE_MIN_HEIGHT,
                min_bytes=PDF_IMAGE_MIN_BYTES,
                logger=AppLogger,
            )
            return ConversionOutcome(
                markdown=markdown,
                backend=BACKEND_NATIVE,
                assets=assets,
            )
        return ConversionOutcome(
            markdown=extract_pdf_markdown(file_path),
            backend=BACKEND_NATIVE,
        )

    native_error: Exception | None = None
    try:
        if options.preserve_pdf_images:
            markdown, assets = extract_pdf_markdown_with_inline_assets(
                file_path,
                min_width=PDF_IMAGE_MIN_WIDTH,
                min_height=PDF_IMAGE_MIN_HEIGHT,
                min_bytes=PDF_IMAGE_MIN_BYTES,
                logger=AppLogger,
            )
            if markdown.strip():
                return ConversionOutcome(
                    markdown=markdown,
                    backend=BACKEND_NATIVE,
                    assets=assets,
                )
        else:
            markdown = extract_pdf_markdown(file_path)
            if markdown.strip():
                return ConversionOutcome(
                    markdown=markdown,
                    backend=BACKEND_NATIVE,
                )
    except Exception as exc:
        native_error = exc

    docintel_error: Exception | None = None
    docintel_attempted = False
    if options.normalized_docintel_endpoint:
        docintel_attempted = True
        try:
            markdown = _convert_with_markitdown(
                file_path,
                options,
                use_docintel=True,
            )
            if markdown.strip():
                return ConversionOutcome(
                    markdown=markdown,
                    backend=BACKEND_AZURE,
                    assets=_maybe_extract_pdf_image_assets(file_path, options),
                )
        except Exception as exc:
            docintel_error = exc

    local_error: Exception | None = None
    try:
        markdown = _convert_pdf_with_local_ocr(file_path, options)
        if markdown.strip():
            return ConversionOutcome(
                markdown=markdown,
                backend=BACKEND_LOCAL,
                assets=_maybe_extract_pdf_image_assets(file_path, options),
            )
    except Exception as exc:
        local_error = exc

    return _raise_ocr_failure(
        "PDF",
        native_error=native_error,
        docintel_attempted=docintel_attempted,
        docintel_error=docintel_error,
        local_error=local_error,
    )


def _convert_with_markitdown(
    file_path: str,
    options: ConversionOptions,
    *,
    use_docintel: bool = False,
) -> str:
    from markitdown import MarkItDown

    kwargs: dict[str, object] = {}
    if use_docintel and options.normalized_docintel_endpoint:
        kwargs["docintel_endpoint"] = options.normalized_docintel_endpoint
        kwargs["docintel_credential"], _auth_method = _build_docintel_credential()

    md = MarkItDown(**kwargs)
    result = md.convert(file_path)
    return result.text_content or ""


def _convert_image_with_local_ocr(file_path: str, options: ConversionOptions) -> str:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("Local OCR requires Pillow to be installed.") from exc

    with Image.open(file_path) as image:
        prepared = ImageOps.exif_transpose(image).convert("RGB")
        return _run_tesseract_ocr(prepared, options)


def _convert_pdf_with_local_ocr(file_path: str, options: ConversionOptions) -> str:
    return convert_pdf_with_local_ocr_pymupdf(
        file_path,
        render_scale=PDF_RENDER_SCALE,
        run_ocr=lambda image: _run_tesseract_ocr(image, options),
    )


def _run_tesseract_ocr(image, options: ConversionOptions) -> str:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("Local OCR requires pytesseract to be installed.") from exc

    if options.normalized_tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = options.normalized_tesseract_path
    else:
        pytesseract.pytesseract.tesseract_cmd = "tesseract"

    kwargs: dict[str, object] = {"timeout": LOCAL_OCR_TIMEOUT_SECONDS}
    if options.normalized_ocr_languages:
        kwargs["lang"] = options.normalized_ocr_languages

    try:
        return str(pytesseract.image_to_string(image, **kwargs)).strip()
    except Exception as exc:
        raise RuntimeError(
            "Local OCR failed. Install Tesseract or set its path in Settings."
        ) from exc


def _safe_extract_pdf_image_assets(
    file_path: str,
    options: ConversionOptions,
) -> tuple[GeneratedAsset, ...]:
    try:
        return _extract_pdf_image_assets(file_path)
    except Exception as exc:
        AppLogger.warning(
            f"PDF image extraction failed for {file_path}: {_summarize_error(exc)}"
        )
        return ()


def _maybe_extract_pdf_image_assets(
    file_path: str,
    options: ConversionOptions,
) -> tuple[GeneratedAsset, ...]:
    if not options.preserve_pdf_images:
        return ()
    return _safe_extract_pdf_image_assets(file_path, options)


def _extract_pdf_image_assets(file_path: str) -> tuple[GeneratedAsset, ...]:
    """Extract embedded PDF images for markdown export."""
    return extract_pdf_image_assets_pymupdf(
        file_path,
        min_width=PDF_IMAGE_MIN_WIDTH,
        min_height=PDF_IMAGE_MIN_HEIGHT,
        min_bytes=PDF_IMAGE_MIN_BYTES,
        logger=AppLogger,
    )


class ConversionWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        files: list[str],
        batch_size: int,
        options: ConversionOptions | None = None,
    ):
        super().__init__()
        self.files = files
        self.batch_size = batch_size
        self.options = options or ConversionOptions()
        self.failed_files: set[str] = set()
        self.processing_backends: dict[str, str] = {}
        self.is_paused = False
        self.is_cancelled = False

    def run(self) -> None:
        results: dict[str, ConversionOutcome] = {}
        self.failed_files = set()
        self.processing_backends = {}

        for i in range(0, len(self.files), self.batch_size):
            if self.is_cancelled:
                break

            batch = self.files[i : i + self.batch_size]
            for j, file_path in enumerate(batch):
                while self.is_paused:
                    if self.is_cancelled:
                        return
                    self.msleep(100)

                try:
                    outcome = convert_file_with_details(file_path, self.options)
                    results[file_path] = outcome
                    self.processing_backends[file_path] = outcome.backend
                except Exception as exc:
                    self.failed_files.add(file_path)
                    results[file_path] = ConversionOutcome(
                        markdown=format_conversion_error(file_path, exc),
                        backend=BACKEND_NATIVE,
                    )

                progress = int((i + j + 1) / len(self.files) * 100)
                self.progress.emit(progress, file_path)

        self.finished.emit(results)
