from __future__ import annotations

from dataclasses import dataclass, field
from itertools import islice
import base64
import mimetypes
import os
import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests

from PySide6.QtCore import QThread, Signal

from markitdowngui.core.input_sources import is_web_url

IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tiff", ".webp"}
DOCINTEL_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tiff"}
DOCX_EXTENSION = ".docx"
PDF_EXTENSION = ".pdf"
DOCX_IMAGE_EXTENSIONS_BY_CONTENT_TYPE = {
    "image/bmp": ".bmp",
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
    "image/x-emf": ".emf",
    "image/x-wmf": ".wmf",
}
PDF_RENDER_SCALE = 3.0
LOCAL_OCR_TIMEOUT_SECONDS = 60
DEFUDDLE_REQUEST_TIMEOUT_SECONDS = 30
DEFUDDLE_API_BASE_URL = "https://defuddle.md/"
AZURE_OCR_API_KEY_ENV_VAR = "AZURE_OCR_API_KEY"
CONVERSION_ERROR_PREFIX = "Error converting "
BACKEND_AZURE = "azure"
BACKEND_DEFUDDLE = "defuddle"
BACKEND_GLMOCR = "glmocr"
BACKEND_HTTP_OCR = "http-ocr"
BACKEND_LOCAL = "local"
BACKEND_NATIVE = "native"
BACKEND_DOCX_IMAGES = "docx-images"
BACKEND_PDF_IMAGES = "pdf-images"
OCR_PROVIDER_AZURE_TESSERACT = "azure_tesseract"
OCR_PROVIDER_GLMOCR = "glmocr"
OCR_PROVIDER_HTTP = "http"
OCR_PROVIDER_LEGACY = "legacy"
OCR_PROVIDER_NONE = "none"
OCR_PROVIDER_ALIASES = {
    "azure": OCR_PROVIDER_AZURE_TESSERACT,
    "azure_tesseract": OCR_PROVIDER_AZURE_TESSERACT,
    "custom_http": OCR_PROVIDER_HTTP,
    "legacy": OCR_PROVIDER_AZURE_TESSERACT,
    "local": OCR_PROVIDER_AZURE_TESSERACT,
    "tesseract": OCR_PROVIDER_AZURE_TESSERACT,
    "glmocr": OCR_PROVIDER_GLMOCR,
    "http": OCR_PROVIDER_HTTP,
    "http_ocr": OCR_PROVIDER_HTTP,
}
OCR_PROVIDERS = {OCR_PROVIDER_AZURE_TESSERACT, OCR_PROVIDER_GLMOCR, OCR_PROVIDER_HTTP}
OCR_FALLBACK_PROVIDERS = {
    OCR_PROVIDER_NONE,
    OCR_PROVIDER_AZURE_TESSERACT,
    OCR_PROVIDER_HTTP,
}
GLMOCR_MODE_MAAS = "maas"
GLMOCR_MODE_OLLAMA = "ollama"
GLMOCR_MODE_SDK_SERVER = "sdk_server"
GLMOCR_MODE_SERVER = "server"
DEFAULT_GLMOCR_SDK_SERVER_URL = "http://127.0.0.1:5002/glmocr/parse"
DEFAULT_GLMOCR_OLLAMA_HOST = "127.0.0.1"
DEFAULT_GLMOCR_OLLAMA_PORT = 11434
DEFAULT_GLMOCR_OLLAMA_MODEL = "glm-ocr:latest"
GLMOCR_OLLAMA_API_PATH = "/api/generate"
GLMOCR_OLLAMA_TIMEOUT_SECONDS = 300
GLMOCR_OLLAMA_MAX_TOKENS = 16384
GLMOCR_OLLAMA_PROMPT = (
    "Recognize the text in the image and output in Markdown format. "
    "Preserve the original layout, including headings, paragraphs, tables, and formulas. "
    "Do not fabricate content that does not exist in the image."
)
GLMOCR_SDK_SERVER_API_KEY = "markitdown-gui-sdk-server"
ZHIPU_API_KEY_ENV_VAR = "ZHIPU_API_KEY"
GLMOCR_API_KEY_ENV_VAR = "GLMOCR_API_KEY"
DEFAULT_HTTP_OCR_API_KEY_ENV = "OCR_HTTP_API_KEY"
DEFAULT_HTTP_OCR_TIMEOUT_SECONDS = 300
OCR_CONNECTION_TEST_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class OcrProviderSpec:
    provider_id: str
    label: str
    detail: str
    capabilities: tuple[str, ...]
    settings_group: str
    fallback_allowed: bool = True


@dataclass(frozen=True)
class OcrSetupValidation:
    ok: bool
    message: str
    issues: tuple[str, ...] = ()
    checked_providers: tuple[str, ...] = ()


OCR_PROVIDER_SPECS = {
    OCR_PROVIDER_AZURE_TESSERACT: OcrProviderSpec(
        provider_id=OCR_PROVIDER_AZURE_TESSERACT,
        label="Azure + Tesseract",
        detail="Azure Document Intelligence first, then local Tesseract.",
        capabilities=("PDF", "images", "cloud optional", "local fallback"),
        settings_group="azure_tesseract",
        fallback_allowed=True,
    ),
    OCR_PROVIDER_GLMOCR: OcrProviderSpec(
        provider_id=OCR_PROVIDER_GLMOCR,
        label="GLM-OCR",
        detail="Official API, Ollama, or SDK server for multimodal OCR.",
        capabilities=("PDF", "images", "API", "Ollama", "server"),
        settings_group="glmocr",
        fallback_allowed=False,
    ),
    OCR_PROVIDER_HTTP: OcrProviderSpec(
        provider_id=OCR_PROVIDER_HTTP,
        label="HTTP OCR",
        detail="Generic self-hosted endpoint using multipart file upload.",
        capabilities=("PDF", "images", "server", "model field"),
        settings_group="http",
        fallback_allowed=True,
    ),
}


@dataclass(frozen=True)
class ConversionOptions:
    """User-controlled conversion behavior."""

    ocr_enabled: bool = False
    preserve_pdf_images: bool = False
    preserve_docx_images: bool = False
    ocr_provider: str = OCR_PROVIDER_AZURE_TESSERACT
    ocr_fallback_enabled: bool = True
    ocr_fallback_provider: str = OCR_PROVIDER_AZURE_TESSERACT
    docintel_endpoint: str = ""
    ocr_languages: str = ""
    tesseract_path: str = ""
    pdf_artifacts_dir: str = ""
    docx_artifacts_dir: str = ""
    glmocr_mode: str = GLMOCR_MODE_MAAS
    glmocr_ollama_host: str = DEFAULT_GLMOCR_OLLAMA_HOST
    glmocr_ollama_port: int = DEFAULT_GLMOCR_OLLAMA_PORT
    glmocr_ollama_model: str = DEFAULT_GLMOCR_OLLAMA_MODEL
    glmocr_sdk_server_url: str = DEFAULT_GLMOCR_SDK_SERVER_URL
    http_ocr_endpoint: str = ""
    http_ocr_model: str = ""
    http_ocr_api_key_env: str = DEFAULT_HTTP_OCR_API_KEY_ENV
    http_ocr_timeout_seconds: int = DEFAULT_HTTP_OCR_TIMEOUT_SECONDS

    @property
    def normalized_ocr_provider(self) -> str:
        return _normalize_ocr_provider(self.ocr_provider)

    @property
    def normalized_ocr_fallback_provider(self) -> str:
        if not self.ocr_fallback_enabled:
            return OCR_PROVIDER_NONE

        provider = self.ocr_fallback_provider.strip().lower()
        if provider == OCR_PROVIDER_NONE:
            return OCR_PROVIDER_NONE

        normalized = _normalize_ocr_provider(provider)
        if normalized in OCR_FALLBACK_PROVIDERS:
            return normalized
        return OCR_PROVIDER_AZURE_TESSERACT

    @property
    def normalized_preserve_pdf_images(self) -> bool:
        return bool(self.preserve_pdf_images)

    @property
    def normalized_preserve_docx_images(self) -> bool:
        return bool(self.preserve_docx_images)

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
    def normalized_pdf_artifacts_dir(self) -> str:
        return self.pdf_artifacts_dir.strip()

    @property
    def normalized_docx_artifacts_dir(self) -> str:
        return self.docx_artifacts_dir.strip()

    @property
    def normalized_glmocr_mode(self) -> str:
        mode = self.glmocr_mode.strip().lower()
        if mode == GLMOCR_MODE_SERVER:
            return GLMOCR_MODE_SDK_SERVER
        if mode in {
            GLMOCR_MODE_MAAS,
            GLMOCR_MODE_OLLAMA,
            GLMOCR_MODE_SDK_SERVER,
        }:
            return mode
        return GLMOCR_MODE_MAAS

    @property
    def normalized_glmocr_ollama_host(self) -> str:
        return self.glmocr_ollama_host.strip() or DEFAULT_GLMOCR_OLLAMA_HOST

    @property
    def normalized_glmocr_ollama_port(self) -> int:
        if 1 <= int(self.glmocr_ollama_port) <= 65535:
            return int(self.glmocr_ollama_port)
        return DEFAULT_GLMOCR_OLLAMA_PORT

    @property
    def normalized_glmocr_ollama_model(self) -> str:
        return self.glmocr_ollama_model.strip() or DEFAULT_GLMOCR_OLLAMA_MODEL

    @property
    def normalized_glmocr_sdk_server_url(self) -> str:
        return self.glmocr_sdk_server_url.strip() or DEFAULT_GLMOCR_SDK_SERVER_URL

    @property
    def normalized_http_ocr_endpoint(self) -> str:
        return self.http_ocr_endpoint.strip()

    @property
    def normalized_http_ocr_model(self) -> str:
        return self.http_ocr_model.strip()

    @property
    def normalized_http_ocr_api_key_env(self) -> str:
        return self.http_ocr_api_key_env.strip() or DEFAULT_HTTP_OCR_API_KEY_ENV

    @property
    def normalized_http_ocr_timeout_seconds(self) -> int:
        return max(1, min(3600, int(self.http_ocr_timeout_seconds)))


@dataclass(frozen=True)
class ConversionAsset:
    filename: str
    source_path: str | None
    preview_markdown_path: str
    page_number: int | None
    kind: str
    ocr_text: str | None = None


@dataclass(frozen=True)
class ConversionOutcome:
    markdown: str
    backend: str = BACKEND_NATIVE
    assets: list[ConversionAsset] = field(default_factory=list)


def format_conversion_error(file_path: str, error: Exception) -> str:
    return f"{CONVERSION_ERROR_PREFIX}{file_path}: {error}"


def _summarize_error(error: Exception) -> str:
    message = str(error).strip()
    return message or type(error).__name__


def _normalize_ocr_provider(
    provider: str,
    default: str = OCR_PROVIDER_AZURE_TESSERACT,
) -> str:
    normalized = (provider or "").strip().lower()
    return OCR_PROVIDER_ALIASES.get(normalized, default)


def get_ocr_provider_specs() -> tuple[OcrProviderSpec, ...]:
    """Return UI-safe OCR provider metadata in display order."""
    return (
        OCR_PROVIDER_SPECS[OCR_PROVIDER_AZURE_TESSERACT],
        OCR_PROVIDER_SPECS[OCR_PROVIDER_GLMOCR],
        OCR_PROVIDER_SPECS[OCR_PROVIDER_HTTP],
    )


def validate_ocr_setup(options: ConversionOptions) -> OcrSetupValidation:
    """Validate OCR settings without running an OCR job."""
    if not options.ocr_enabled:
        return OcrSetupValidation(
            ok=False,
            message="OCR is disabled.",
            issues=("Enable OCR before validating provider settings.",),
        )

    providers = [options.normalized_ocr_provider]
    fallback = options.normalized_ocr_fallback_provider
    if fallback != OCR_PROVIDER_NONE and fallback not in providers:
        providers.append(fallback)

    issues: list[str] = []
    for provider in providers:
        issues.extend(_ocr_provider_setup_issues(provider, options))

    if issues:
        return OcrSetupValidation(
            ok=False,
            message=issues[0],
            issues=tuple(issues),
            checked_providers=tuple(providers),
        )

    labels = ", ".join(_ocr_provider_label(provider) for provider in providers)
    return OcrSetupValidation(
        ok=True,
        message=f"OCR settings look ready for {labels}.",
        checked_providers=tuple(providers),
    )


def _ocr_provider_setup_issues(
    provider: str,
    options: ConversionOptions,
) -> list[str]:
    if provider == OCR_PROVIDER_AZURE_TESSERACT:
        return _azure_tesseract_setup_issues(options)
    if provider == OCR_PROVIDER_GLMOCR:
        return _glmocr_setup_issues(options)
    if provider == OCR_PROVIDER_HTTP:
        return _http_ocr_setup_issues(options)
    return [f"Unknown OCR provider: {provider}."]


def _azure_tesseract_setup_issues(options: ConversionOptions) -> list[str]:
    issues: list[str] = []
    tesseract_path = options.normalized_tesseract_path
    if tesseract_path and not Path(tesseract_path).exists():
        issues.append(f"Tesseract executable was not found: {tesseract_path}")

    has_azure_endpoint = bool(options.normalized_docintel_endpoint)
    has_tesseract = bool(tesseract_path and Path(tesseract_path).exists()) or bool(
        shutil.which("tesseract")
    )
    if not has_azure_endpoint and not has_tesseract:
        issues.append(
            "Azure + Tesseract needs an Azure endpoint or a usable Tesseract executable."
        )
    return issues


def _glmocr_setup_issues(options: ConversionOptions) -> list[str]:
    if options.normalized_glmocr_mode == GLMOCR_MODE_MAAS and not _glmocr_api_key_available():
        return ["GLM-OCR Official API requires ZHIPU_API_KEY or GLMOCR_API_KEY."]
    if options.normalized_glmocr_mode == GLMOCR_MODE_OLLAMA and not options.normalized_glmocr_ollama_model:
        return ["GLM-OCR Ollama requires a model name."]
    if options.normalized_glmocr_mode == GLMOCR_MODE_SDK_SERVER and not options.normalized_glmocr_sdk_server_url:
        return ["GLM-OCR SDK Server requires an endpoint URL."]
    return []


def _http_ocr_setup_issues(options: ConversionOptions) -> list[str]:
    if not options.normalized_http_ocr_endpoint:
        return ["HTTP OCR requires an endpoint URL."]
    return []


def _ocr_provider_label(provider: str) -> str:
    spec = OCR_PROVIDER_SPECS.get(provider)
    return spec.label if spec else provider


def _raise_provider_failure(
    file_label: str,
    *,
    provider: str,
    provider_error: Exception,
    fallback_provider: str = OCR_PROVIDER_NONE,
    fallback_error: Exception | None = None,
) -> str:
    provider_label = _ocr_provider_label(provider)
    if fallback_error is not None:
        fallback_label = _ocr_provider_label(fallback_provider)
        raise RuntimeError(
            f"{provider_label} failed for the {file_label} ({_summarize_error(provider_error)}), "
            f"and {fallback_label} fallback also failed ({_summarize_error(fallback_error)})."
        ) from provider_error

    raise RuntimeError(
        f"{provider_label} failed for the {file_label}: {_summarize_error(provider_error)}"
    ) from provider_error


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


def _raise_glmocr_failure(
    file_label: str,
    *,
    glm_error: Exception,
    fallback_error: Exception | None = None,
) -> str:
    if fallback_error is not None:
        raise RuntimeError(
            f"GLM-OCR failed for the {file_label} ({_summarize_error(glm_error)}), "
            f"and fallback OCR also failed ({_summarize_error(fallback_error)})."
        ) from glm_error

    raise RuntimeError(
        f"GLM-OCR failed for the {file_label}: {_summarize_error(glm_error)}"
    ) from glm_error


def _glmocr_api_key_available() -> bool:
    return bool(
        os.getenv(ZHIPU_API_KEY_ENV_VAR, "").strip()
        or os.getenv(GLMOCR_API_KEY_ENV_VAR, "").strip()
    )


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


def test_ocr_provider_connection(options: ConversionOptions) -> str:
    """Run a lightweight provider-specific connectivity check."""
    if not options.ocr_enabled:
        raise RuntimeError("Enable OCR before testing provider connectivity.")

    provider = options.normalized_ocr_provider
    if provider == OCR_PROVIDER_AZURE_TESSERACT:
        auth_method = test_azure_ocr_connection(options)
        return f"Azure OCR connection succeeded with {auth_method} auth."
    if provider == OCR_PROVIDER_HTTP:
        return test_http_ocr_connection(options)
    if provider == OCR_PROVIDER_GLMOCR:
        mode = options.normalized_glmocr_mode
        if mode == GLMOCR_MODE_OLLAMA:
            return test_glmocr_ollama_connection(options)
        if mode == GLMOCR_MODE_SDK_SERVER:
            return _test_http_endpoint_reachable(
                options.normalized_glmocr_sdk_server_url,
                label="GLM-OCR SDK server",
            )
        if not _glmocr_api_key_available():
            raise RuntimeError(
                "Set ZHIPU_API_KEY or GLMOCR_API_KEY before testing GLM-OCR Official API."
            )
        return "GLM-OCR Official API key is configured."
    raise RuntimeError(f"Unsupported OCR provider: {provider}")


def test_http_ocr_connection(options: ConversionOptions) -> str:
    endpoint = options.normalized_http_ocr_endpoint
    if not endpoint:
        raise RuntimeError("Set an HTTP OCR endpoint before testing connectivity.")
    return _test_http_endpoint_reachable(
        endpoint,
        label="HTTP OCR endpoint",
        timeout=min(
            OCR_CONNECTION_TEST_TIMEOUT_SECONDS,
            options.normalized_http_ocr_timeout_seconds,
        ),
    )


def test_glmocr_ollama_connection(options: ConversionOptions) -> str:
    tags_url = _build_glmocr_ollama_tags_url(options)
    try:
        response = requests.get(tags_url, timeout=OCR_CONNECTION_TEST_TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        raise RuntimeError("GLM-OCR Ollama test timed out.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"GLM-OCR Ollama test could not reach {tags_url}: {exc}") from exc

    if not response.ok:
        message = response.text.strip()
        raise RuntimeError(
            message or f"GLM-OCR Ollama test failed with status {response.status_code}."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("GLM-OCR Ollama returned an invalid /api/tags response.") from exc

    model = options.normalized_glmocr_ollama_model
    names = {
        str(item.get("name") or item.get("model") or "").strip()
        for item in payload.get("models", [])
        if isinstance(item, dict)
    }
    if model not in names:
        raise RuntimeError(f"Ollama is reachable, but model `{model}` is not installed.")
    return f"GLM-OCR Ollama is reachable and `{model}` is installed."


def _test_http_endpoint_reachable(
    endpoint: str,
    *,
    label: str,
    timeout: int = OCR_CONNECTION_TEST_TIMEOUT_SECONDS,
) -> str:
    if not endpoint:
        raise RuntimeError(f"Set a {label} URL before testing connectivity.")
    try:
        response = requests.options(endpoint, timeout=timeout)
    except requests.Timeout as exc:
        raise RuntimeError(f"{label} test timed out.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"{label} test could not reach {endpoint}: {exc}") from exc

    if response.status_code == 404:
        raise RuntimeError(f"{label} responded with 404. Check the configured URL.")
    if response.status_code >= 500:
        raise RuntimeError(f"{label} responded with status {response.status_code}.")
    return f"{label} is reachable."


def convert_file_with_details(
    file_path: str,
    options: ConversionOptions | None = None,
) -> ConversionOutcome:
    """Convert a single file to Markdown text and report which backend produced it."""
    effective_options = options or ConversionOptions()

    if is_web_url(file_path):
        return ConversionOutcome(
            markdown=_convert_url_with_defuddle(file_path),
            backend=BACKEND_DEFUDDLE,
        )

    extension = Path(file_path).suffix.lower()

    if extension == PDF_EXTENSION and effective_options.normalized_preserve_pdf_images:
        return _convert_pdf_with_preserved_images(file_path, effective_options)

    if extension == DOCX_EXTENSION and effective_options.normalized_preserve_docx_images:
        return _convert_docx_with_preserved_images(file_path, effective_options)

    if not effective_options.ocr_enabled:
        return ConversionOutcome(
            markdown=_convert_with_markitdown(file_path, effective_options),
            backend=BACKEND_NATIVE,
        )

    if extension in IMAGE_EXTENSIONS:
        return _convert_image_with_ocr(file_path, effective_options, extension)

    if extension == PDF_EXTENSION:
        return _convert_pdf_with_ocr(file_path, effective_options)

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
    provider = options.normalized_ocr_provider
    try:
        return _convert_image_with_ocr_provider(
            file_path,
            options,
            extension,
            provider,
        )
    except Exception as exc:
        fallback_provider = options.normalized_ocr_fallback_provider
        if fallback_provider in {OCR_PROVIDER_NONE, provider}:
            if provider == OCR_PROVIDER_AZURE_TESSERACT:
                raise
            return _raise_provider_failure(
                "image",
                provider=provider,
                provider_error=exc,
            )

        try:
            return _convert_image_with_ocr_provider(
                file_path,
                options,
                extension,
                fallback_provider,
            )
        except Exception as fallback_error:
            return _raise_provider_failure(
                "image",
                provider=provider,
                provider_error=exc,
                fallback_provider=fallback_provider,
                fallback_error=fallback_error,
            )


def _convert_image_with_ocr_provider(
    file_path: str,
    options: ConversionOptions,
    extension: str,
    provider: str,
) -> ConversionOutcome:
    if provider == OCR_PROVIDER_GLMOCR:
        return _convert_image_with_glmocr(file_path, options, extension)
    if provider == OCR_PROVIDER_AZURE_TESSERACT:
        return _convert_image_with_azure_tesseract_ocr(file_path, options, extension)
    if provider == OCR_PROVIDER_HTTP:
        return _convert_image_with_http_ocr(file_path, options)
    raise RuntimeError(f"Unsupported OCR provider: {provider}")


def _convert_image_with_glmocr(
    file_path: str,
    options: ConversionOptions,
    extension: str,
) -> ConversionOutcome:
    markdown = _convert_with_glmocr(file_path, options)
    if markdown.strip():
        return ConversionOutcome(markdown=markdown, backend=BACKEND_GLMOCR)
    raise RuntimeError("GLM-OCR did not extract any text from the image.")


def _convert_image_with_azure_tesseract_ocr(
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


def _convert_pdf_with_ocr(
    file_path: str,
    options: ConversionOptions,
) -> ConversionOutcome:
    provider = options.normalized_ocr_provider
    try:
        return _convert_pdf_with_ocr_provider(
            file_path,
            options,
            provider,
        )
    except Exception as exc:
        fallback_provider = options.normalized_ocr_fallback_provider
        if fallback_provider in {OCR_PROVIDER_NONE, provider}:
            if provider == OCR_PROVIDER_AZURE_TESSERACT:
                raise
            return _raise_provider_failure(
                "PDF",
                provider=provider,
                provider_error=exc,
            )

        try:
            return _convert_pdf_with_ocr_provider(file_path, options, fallback_provider)
        except Exception as fallback_error:
            return _raise_provider_failure(
                "PDF",
                provider=provider,
                provider_error=exc,
                fallback_provider=fallback_provider,
                fallback_error=fallback_error,
            )


def _convert_pdf_with_ocr_provider(
    file_path: str,
    options: ConversionOptions,
    provider: str,
) -> ConversionOutcome:
    if provider == OCR_PROVIDER_GLMOCR:
        return _convert_pdf_with_glmocr(file_path, options)
    if provider == OCR_PROVIDER_AZURE_TESSERACT:
        return _convert_pdf_with_azure_tesseract_ocr(file_path, options)
    if provider == OCR_PROVIDER_HTTP:
        return _convert_pdf_with_http_ocr(file_path, options)
    raise RuntimeError(f"Unsupported OCR provider: {provider}")


def _convert_pdf_with_preserved_images(
    file_path: str,
    options: ConversionOptions,
) -> ConversionOutcome:
    artifacts_dir = options.normalized_pdf_artifacts_dir
    if not artifacts_dir:
        raise RuntimeError(
            "Preserve PDF images requires a writable temporary asset directory."
        )

    try:
        from markitdown_pdf_images import convert_pdf
    except ImportError as exc:
        raise RuntimeError(
            "Preserve PDF images requires the `markitdown-pdf-images` package to be installed."
        ) from exc

    plugin_ocr_enabled = (
        options.ocr_enabled
        and options.normalized_ocr_provider == OCR_PROVIDER_AZURE_TESSERACT
    )
    result = convert_pdf(
        file_path,
        preserve_images=True,
        image_mode="external",
        artifacts_dir=artifacts_dir,
        path_mode="absolute",
        ocr_enabled=plugin_ocr_enabled,
        tesseract_path=options.normalized_tesseract_path or None,
        ocr_languages=options.normalized_ocr_languages,
    )
    markdown = result.markdown

    if options.ocr_enabled and not plugin_ocr_enabled:
        ocr_outcome = _convert_pdf_with_ocr(file_path, options)
        markdown = _merge_preserved_pdf_markdown_with_provider_ocr(
            markdown,
            ocr_outcome.markdown,
        )

    return ConversionOutcome(
        markdown=markdown,
        backend=BACKEND_PDF_IMAGES,
        assets=_map_pdf_assets(getattr(result, "assets", [])),
    )


def _merge_preserved_pdf_markdown_with_provider_ocr(
    preserved_markdown: str,
    ocr_markdown: str,
) -> str:
    preserved = preserved_markdown.strip()
    ocr_text = ocr_markdown.strip()
    if not ocr_text:
        return preserved
    if not preserved:
        return ocr_text
    if ocr_text in preserved:
        return preserved
    return f"{preserved}\n\n{ocr_text}"


def _convert_docx_with_preserved_images(
    file_path: str,
    options: ConversionOptions,
) -> ConversionOutcome:
    artifacts_dir = options.normalized_docx_artifacts_dir
    if not artifacts_dir:
        raise RuntimeError(
            "Preserve DOCX images requires a writable temporary asset directory."
        )

    try:
        import mammoth
        from markdownify import markdownify
        from markitdown.converter_utils.docx.pre_process import pre_process_docx
    except ImportError as exc:
        raise RuntimeError(
            "Preserve DOCX images requires MarkItDown's DOCX dependencies to be installed."
        ) from exc

    artifact_root = Path(artifacts_dir)
    artifact_root.mkdir(parents=True, exist_ok=True)
    document_asset_dir = Path(
        tempfile.mkdtemp(prefix="docx-images-", dir=artifact_root)
    ).resolve()
    assets: list[ConversionAsset] = []
    image_count = 0

    def convert_image(image) -> dict[str, str]:
        nonlocal image_count
        image_count += 1

        with image.open() as image_file:
            image_bytes = image_file.read()
        if not image_bytes:
            return {}

        extension = _docx_image_extension(getattr(image, "content_type", ""))
        filename = f"image-{image_count:03d}{extension}"
        image_path = (document_asset_dir / filename).resolve()
        image_path.write_bytes(image_bytes)

        markdown_path = image_path.as_posix()
        assets.append(
            ConversionAsset(
                filename=filename,
                source_path=str(image_path),
                preview_markdown_path=markdown_path,
                page_number=None,
                kind="docx-image",
            )
        )
        return {"src": markdown_path}

    with Path(file_path).open("rb") as file_stream:
        preprocessed_stream = pre_process_docx(file_stream)
        result = mammoth.convert_to_html(
            preprocessed_stream,
            convert_image=mammoth.images.img_element(convert_image),
            ignore_empty_paragraphs=False,
        )

    html_content = _extract_images_from_single_cell_tables(result.value)
    markdown = markdownify(html_content)

    return ConversionOutcome(
        markdown=markdown,
        backend=BACKEND_DOCX_IMAGES,
        assets=assets,
    )


def _docx_image_extension(content_type: str) -> str:
    normalized = content_type.split(";", 1)[0].strip().lower()
    return DOCX_IMAGE_EXTENSIONS_BY_CONTENT_TYPE.get(normalized, ".bin")


def _extract_images_from_single_cell_tables(html_content: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")
    changed = False

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) != 1:
            continue

        cells = rows[0].find_all(["td", "th"])
        if len(cells) != 1:
            continue

        cell = cells[0]
        images = cell.find_all("img")
        if not images or cell.get_text(strip=True):
            continue

        paragraph = soup.new_tag("p")
        for image in images:
            paragraph.append(image.extract())
        table.replace_with(paragraph)
        changed = True

    return str(soup) if changed else html_content


def _convert_pdf_with_glmocr(
    file_path: str,
    options: ConversionOptions,
) -> ConversionOutcome:
    markdown = _convert_with_glmocr(file_path, options)
    if markdown.strip():
        return ConversionOutcome(markdown=markdown, backend=BACKEND_GLMOCR)
    raise RuntimeError("GLM-OCR did not extract any text from the PDF.")


def _convert_pdf_with_azure_tesseract_ocr(
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


def _convert_with_glmocr(
    file_path: str,
    options: ConversionOptions,
) -> str:
    normalized_mode = options.normalized_glmocr_mode

    if normalized_mode == GLMOCR_MODE_OLLAMA:
        return _convert_with_glmocr_ollama(file_path, options)

    try:
        from glmocr.api import GlmOcr
    except ImportError as exc:
        raise RuntimeError(
            "GLM-OCR requires the `glmocr` package to be installed."
        ) from exc

    kwargs: dict[str, object] = {"model": "glm-ocr"}

    if normalized_mode == GLMOCR_MODE_MAAS:
        kwargs["mode"] = GLMOCR_MODE_MAAS
        if not _glmocr_api_key_available():
            raise RuntimeError(
                "GLM-OCR MaaS requires ZHIPU_API_KEY or GLMOCR_API_KEY to be set."
            )
    elif normalized_mode == GLMOCR_MODE_SDK_SERVER:
        kwargs["mode"] = GLMOCR_MODE_MAAS
        kwargs["api_url"] = options.normalized_glmocr_sdk_server_url
        kwargs["api_key"] = GLMOCR_SDK_SERVER_API_KEY

    with GlmOcr(**kwargs) as parser:
        result = parser.parse(file_path)

    markdown = getattr(result, "markdown_result", "")
    return str(markdown or "").strip()


def _convert_with_glmocr_ollama(
    file_path: str,
    options: ConversionOptions,
) -> str:
    page_markdowns: list[str] = []

    for image in _iter_glmocr_ollama_images(file_path):
        try:
            markdown = _call_glmocr_ollama(image, options)
            if markdown.strip():
                page_markdowns.append(markdown.strip())
        finally:
            if hasattr(image, "close"):
                image.close()

    return "\n\n".join(page_markdowns).strip()


def _convert_image_with_http_ocr(
    file_path: str,
    options: ConversionOptions,
) -> ConversionOutcome:
    markdown = _convert_with_http_ocr(file_path, options)
    if markdown.strip():
        return ConversionOutcome(markdown=markdown, backend=BACKEND_HTTP_OCR)
    raise RuntimeError("HTTP OCR did not extract any text from the image.")


def _convert_pdf_with_http_ocr(
    file_path: str,
    options: ConversionOptions,
) -> ConversionOutcome:
    markdown = _convert_with_http_ocr(file_path, options)
    if markdown.strip():
        return ConversionOutcome(markdown=markdown, backend=BACKEND_HTTP_OCR)
    raise RuntimeError("HTTP OCR did not extract any text from the PDF.")


def _convert_with_http_ocr(file_path: str, options: ConversionOptions) -> str:
    endpoint = options.normalized_http_ocr_endpoint
    if not endpoint:
        raise RuntimeError("Set an HTTP OCR endpoint in Settings first.")

    path = Path(file_path)
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data: dict[str, str] = {}
    if options.normalized_http_ocr_model:
        data["model"] = options.normalized_http_ocr_model

    headers: dict[str, str] = {}
    api_key_env = options.normalized_http_ocr_api_key_env
    api_key = os.getenv(api_key_env, "").strip() if api_key_env else ""
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with path.open("rb") as file_obj:
            response = requests.post(
                endpoint,
                data=data,
                files={"file": (path.name, file_obj, content_type)},
                headers=headers,
                timeout=options.normalized_http_ocr_timeout_seconds,
            )
    except requests.Timeout as exc:
        raise RuntimeError("HTTP OCR request timed out.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"HTTP OCR request failed: {exc}") from exc

    if not response.ok:
        message = response.text.strip()
        raise RuntimeError(
            message or f"HTTP OCR request failed with status {response.status_code}."
        )

    return _extract_http_ocr_response_text(response)


def _extract_http_ocr_response_text(response: requests.Response) -> str:
    content_type = response.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        return response.text.strip()

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("HTTP OCR returned an invalid JSON response.") from exc

    extracted = _find_text_in_http_ocr_payload(payload)
    if extracted is None:
        raise RuntimeError(
            "HTTP OCR JSON response did not include markdown, text, result, content, or output."
        )
    return extracted.strip()


def _find_text_in_http_ocr_payload(payload: object) -> str | None:
    if isinstance(payload, str):
        return payload if payload.strip() else None
    if isinstance(payload, dict):
        for key in ("markdown", "text", "result", "content", "output"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, (dict, list)):
                nested = _find_text_in_http_ocr_payload(value)
                if nested is not None:
                    return nested
        return None
    if isinstance(payload, list):
        parts = [
            value
            for value in (_find_text_in_http_ocr_payload(item) for item in payload)
            if value
        ]
        return "\n\n".join(parts) if parts else None
    return None


def _iter_glmocr_ollama_images(file_path: str):
    extension = Path(file_path).suffix.lower()

    if extension == PDF_EXTENSION:
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError(
                "GLM-OCR Ollama PDF conversion requires pypdfium2 to be installed."
            ) from exc

        pdf = pdfium.PdfDocument(file_path)
        try:
            for page_index in range(len(pdf)):
                page = pdf[page_index]
                bitmap = None
                try:
                    bitmap = page.render(scale=PDF_RENDER_SCALE)
                    yield bitmap.to_pil().convert("RGB")
                finally:
                    if bitmap is not None and hasattr(bitmap, "close"):
                        bitmap.close()
                    if hasattr(page, "close"):
                        page.close()
        finally:
            if hasattr(pdf, "close"):
                pdf.close()
        return

    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "GLM-OCR Ollama image conversion requires Pillow to be installed."
        ) from exc

    with Image.open(file_path) as image:
        yield ImageOps.exif_transpose(image).convert("RGB")


def _call_glmocr_ollama(image, options: ConversionOptions) -> str:
    request_url = _build_glmocr_ollama_url(options)
    payload = {
        "model": options.normalized_glmocr_ollama_model,
        "prompt": GLMOCR_OLLAMA_PROMPT,
        "images": [_encode_image_for_ollama(image)],
        "stream": False,
        "options": {
            "num_predict": GLMOCR_OLLAMA_MAX_TOKENS,
            "temperature": 0.01,
            "top_p": 0.00001,
            "top_k": 1,
            "repeat_penalty": 1.1,
        },
    }

    try:
        response = requests.post(
            request_url,
            json=payload,
            timeout=GLMOCR_OLLAMA_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise RuntimeError("GLM-OCR Ollama request timed out.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(
            f"GLM-OCR Ollama request failed to reach Ollama at {request_url}: {exc}"
        ) from exc

    if not response.ok:
        message = response.text.strip()
        raise RuntimeError(
            message
            or f"GLM-OCR Ollama request failed with status {response.status_code}."
        )

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("GLM-OCR Ollama returned an invalid JSON response.") from exc

    if result.get("error"):
        raise RuntimeError(f"GLM-OCR Ollama error: {result['error']}")

    markdown = result.get("response")
    if markdown is None:
        raise RuntimeError("GLM-OCR Ollama response did not include output text.")

    return str(markdown)


def _build_glmocr_ollama_url(options: ConversionOptions) -> str:
    host = options.normalized_glmocr_ollama_host.rstrip("/")
    if "://" in host:
        base_url = host
    elif ":" in host and not host.startswith("["):
        base_url = f"http://{host}"
    else:
        base_url = f"http://{host}:{options.normalized_glmocr_ollama_port}"
    return f"{base_url}{GLMOCR_OLLAMA_API_PATH}"


def _build_glmocr_ollama_tags_url(options: ConversionOptions) -> str:
    request_url = _build_glmocr_ollama_url(options)
    if request_url.endswith(GLMOCR_OLLAMA_API_PATH):
        return request_url[: -len(GLMOCR_OLLAMA_API_PATH)] + "/api/tags"
    return request_url.rstrip("/") + "/api/tags"


def _encode_image_for_ollama(image) -> str:
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _map_pdf_assets(assets: list[object]) -> list[ConversionAsset]:
    mapped_assets: list[ConversionAsset] = []
    for asset in assets:
        source_path = getattr(asset, "path", None)
        mapped_assets.append(
            ConversionAsset(
                filename=str(getattr(asset, "filename", "")),
                source_path=str(Path(source_path).resolve()) if source_path else None,
                preview_markdown_path=str(getattr(asset, "markdown_path", "")),
                page_number=getattr(asset, "page_number", None),
                kind=str(getattr(asset, "kind", "")),
                ocr_text=getattr(asset, "ocr_text", None),
            )
        )
    return mapped_assets


def _convert_url_with_defuddle(url: str) -> str:
    request_url = _build_defuddle_request_url(url)

    try:
        response = requests.get(
            request_url,
            timeout=DEFUDDLE_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise RuntimeError(
            "Website conversion timed out while waiting for the Defuddle service."
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Website conversion failed to reach the Defuddle service: {exc}"
        ) from exc

    if response.status_code == 429:
        raise RuntimeError(
            "Defuddle rate limit reached. The free tier allows up to 1,000 requests per month per IP."
        )

    if not response.ok:
        message = response.text.strip()
        raise RuntimeError(message or "Defuddle failed to convert the URL.")

    return response.text.strip()


def _build_defuddle_request_url(url: str) -> str:
    encoded_url = quote(url.strip(), safe="")
    return f"{DEFUDDLE_API_BASE_URL}{encoded_url}"


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
                        break
                    self.msleep(100)
                if self.is_cancelled:
                    break

                try:
                    outcome = convert_file_with_details(file_path, self.options)
                    results[file_path] = outcome
                    self.processing_backends[file_path] = outcome.backend
                except Exception as exc:
                    self.failed_files.add(file_path)
                    results[file_path] = ConversionOutcome(
                        markdown=format_conversion_error(file_path, exc)
                    )

                progress = int((i + j + 1) / len(self.files) * 100)
                self.progress.emit(progress, file_path)
            if self.is_cancelled:
                break

        self.finished.emit(results)
