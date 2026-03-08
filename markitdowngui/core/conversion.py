from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal

IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tiff", ".webp"}
DOCINTEL_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tiff"}
PDF_EXTENSION = ".pdf"
PDF_RENDER_SCALE = 3.0
LOCAL_OCR_TIMEOUT_SECONDS = 60
AZURE_OCR_API_KEY_ENV_VAR = "AZURE_OCR_API_KEY"
AZURE_DOCINTEL_INFO_API_VERSION = "2024-11-30"
CONVERSION_ERROR_PREFIX = "Error converting "
BACKEND_AZURE = "azure"
BACKEND_LOCAL = "local"
BACKEND_NATIVE = "native"


@dataclass(frozen=True)
class ConversionOptions:
    """User-controlled conversion behavior."""

    ocr_enabled: bool = False
    docintel_endpoint: str = ""
    ocr_languages: str = ""
    tesseract_path: str = ""

    @property
    def normalized_docintel_endpoint(self) -> str:
        return self.docintel_endpoint.strip()

    @property
    def normalized_ocr_languages(self) -> str:
        return self.ocr_languages.strip()

    @property
    def normalized_tesseract_path(self) -> str:
        return self.tesseract_path.strip()


@dataclass(frozen=True)
class ConversionOutcome:
    markdown: str
    backend: str = BACKEND_NATIVE


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


def _build_docintel_info_url(endpoint: str) -> str:
    parts = urlsplit(endpoint.strip())
    if not parts.scheme or not parts.netloc:
        raise RuntimeError("Enter a valid Azure Document Intelligence endpoint.")

    base_path = parts.path.rstrip("/")
    info_path = f"{base_path}/info" if base_path else "/info"
    query = urlencode({"api-version": AZURE_DOCINTEL_INFO_API_VERSION})
    return urlunsplit((parts.scheme, parts.netloc, info_path, query, ""))


def _extract_docintel_http_error_message(error: HTTPError) -> str:
    try:
        payload = error.read().decode("utf-8", errors="replace")
    except Exception:
        payload = ""

    if payload:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return payload.strip()

        inner = data.get("error") if isinstance(data, dict) else None
        if isinstance(inner, dict):
            for key in ("message", "code"):
                value = inner.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

    return f"HTTP {error.code}"


def test_azure_ocr_connection(options: ConversionOptions) -> str:
    endpoint = options.normalized_docintel_endpoint
    if not endpoint:
        raise RuntimeError("Set an Azure Document Intelligence endpoint first.")

    api_key = os.getenv(AZURE_OCR_API_KEY_ENV_VAR, "").strip()
    if not api_key:
        raise RuntimeError(
            "Set AZURE_OCR_API_KEY before using Test Azure OCR. This check validates API-key authentication only."
        )

    request = Request(
        _build_docintel_info_url(endpoint),
        headers={
            "Accept": "application/json",
            "Ocp-Apim-Subscription-Key": api_key,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            if getattr(response, "status", 200) != 200:
                raise RuntimeError(f"Azure OCR test failed with HTTP {response.status}.")
    except HTTPError as exc:
        raise RuntimeError(
            f"Azure OCR test failed: {_extract_docintel_http_error_message(exc)}"
        ) from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(f"Azure OCR test failed: {reason}") from exc

    return "api_key"


def convert_file_with_details(
    file_path: str,
    options: ConversionOptions | None = None,
) -> ConversionOutcome:
    """Convert a single file to Markdown text and report which backend produced it."""
    effective_options = options or ConversionOptions()
    extension = Path(file_path).suffix.lower()

    if not effective_options.ocr_enabled:
        return ConversionOutcome(
            markdown=_convert_with_markitdown(file_path, effective_options),
            backend=BACKEND_NATIVE,
        )

    if extension in IMAGE_EXTENSIONS:
        return _convert_image_with_ocr(file_path, effective_options, extension)

    if extension == PDF_EXTENSION:
        return _convert_pdf_with_ocr_fallback(file_path, effective_options)

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
            return ConversionOutcome(markdown=markdown, backend=BACKEND_NATIVE)
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
                return ConversionOutcome(markdown=markdown, backend=BACKEND_AZURE)
        except Exception as exc:
            docintel_error = exc

    local_error: Exception | None = None
    try:
        markdown = _convert_pdf_with_local_ocr(file_path, options)
        if markdown.strip():
            return ConversionOutcome(markdown=markdown, backend=BACKEND_LOCAL)
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
    # Delay heavy imports until conversion is requested.
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
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise RuntimeError(
            "Local PDF OCR requires pypdfium2 to be installed."
        ) from exc

    page_texts: list[str] = []
    pdf = pdfium.PdfDocument(file_path)
    try:
        for page_index in range(len(pdf)):
            page = pdf[page_index]
            bitmap = None
            try:
                bitmap = page.render(scale=PDF_RENDER_SCALE)
                page_text = _run_tesseract_ocr(bitmap.to_pil(), options)
                if page_text.strip():
                    page_texts.append(page_text.strip())
            finally:
                if bitmap is not None and hasattr(bitmap, "close"):
                    bitmap.close()
                if hasattr(page, "close"):
                    page.close()
    finally:
        if hasattr(pdf, "close"):
            pdf.close()

    return "\n\n".join(page_texts).strip()


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
        results: dict[str, str] = {}
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
                    results[file_path] = outcome.markdown
                    self.processing_backends[file_path] = outcome.backend
                except Exception as exc:
                    self.failed_files.add(file_path)
                    results[file_path] = format_conversion_error(file_path, exc)

                progress = int((i + j + 1) / len(self.files) * 100)
                self.progress.emit(progress, file_path)

        self.finished.emit(results)
