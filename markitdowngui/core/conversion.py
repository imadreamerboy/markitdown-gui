from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tiff", ".webp"}
DOCINTEL_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tiff"}
PDF_EXTENSION = ".pdf"
PDF_RENDER_SCALE = 3.0
LOCAL_OCR_TIMEOUT_SECONDS = 60


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


def convert_file(file_path: str, options: ConversionOptions | None = None) -> str:
    """Convert a single file to Markdown text."""
    effective_options = options or ConversionOptions()
    extension = Path(file_path).suffix.lower()

    if not effective_options.ocr_enabled:
        return _convert_with_markitdown(file_path, effective_options)

    if extension in IMAGE_EXTENSIONS:
        return _convert_image_with_ocr(file_path, effective_options, extension)

    if extension == PDF_EXTENSION:
        return _convert_pdf_with_ocr_fallback(file_path, effective_options)

    return _convert_with_markitdown(file_path, effective_options)


def _convert_image_with_ocr(
    file_path: str,
    options: ConversionOptions,
    extension: str,
) -> str:
    docintel_error: Exception | None = None

    if (
        options.normalized_docintel_endpoint
        and extension in DOCINTEL_IMAGE_EXTENSIONS
    ):
        try:
            markdown = _convert_with_markitdown(
                file_path,
                options,
                use_docintel=True,
            )
            if markdown.strip():
                return markdown
        except Exception as exc:
            docintel_error = exc

    markdown = _convert_image_with_local_ocr(file_path, options)
    if markdown.strip():
        return markdown

    if docintel_error is not None:
        raise RuntimeError(
            "OCR did not extract text from the image after Azure and local fallback."
        ) from docintel_error

    raise RuntimeError("OCR did not extract any text from the image.")


def _convert_pdf_with_ocr_fallback(file_path: str, options: ConversionOptions) -> str:
    markdown = _convert_with_markitdown(file_path, options)
    if markdown.strip():
        return markdown

    docintel_error: Exception | None = None
    if options.normalized_docintel_endpoint:
        try:
            markdown = _convert_with_markitdown(
                file_path,
                options,
                use_docintel=True,
            )
            if markdown.strip():
                return markdown
        except Exception as exc:
            docintel_error = exc

    markdown = _convert_pdf_with_local_ocr(file_path, options)
    if markdown.strip():
        return markdown

    if docintel_error is not None:
        raise RuntimeError(
            "OCR did not extract text from the PDF after Azure and local fallback."
        ) from docintel_error

    raise RuntimeError("OCR did not extract any text from the PDF.")


def _convert_with_markitdown(
    file_path: str,
    options: ConversionOptions,
    *,
    use_docintel: bool = False,
) -> str:
    # Delay heavy imports until conversion is requested.
    from markitdown import MarkItDown

    kwargs: dict[str, str] = {}
    if use_docintel and options.normalized_docintel_endpoint:
        kwargs["docintel_endpoint"] = options.normalized_docintel_endpoint

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
        self.is_paused = False
        self.is_cancelled = False

    def run(self) -> None:
        results: dict[str, str] = {}

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
                    results[file_path] = convert_file(file_path, self.options)
                except Exception as exc:
                    results[file_path] = f"Error converting {file_path}: {exc}"

                progress = int((i + j + 1) / len(self.files) * 100)
                self.progress.emit(progress, file_path)

        self.finished.emit(results)
