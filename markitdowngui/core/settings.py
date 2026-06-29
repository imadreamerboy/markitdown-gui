from PySide6.QtCore import QSettings
from typing import cast, List


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
DEFAULT_HTTP_OCR_API_KEY_ENV = "OCR_HTTP_API_KEY"
DEFAULT_HTTP_OCR_TIMEOUT_SECONDS = 300


def normalize_ocr_provider(value: str, default: str = OCR_PROVIDER_AZURE_TESSERACT) -> str:
    """Normalise saved and legacy OCR provider identifiers."""
    normalized = (value or '').strip().lower()
    return OCR_PROVIDER_ALIASES.get(normalized, default)


class SettingsManager:
    """Manages application settings and preferences."""
    
    def __init__(self):
        self.settings = QSettings('MarkItDown', 'GUI')
        
    def get_theme_mode(self) -> str:
        """Get theme mode preference: 'light', 'dark', or 'system'."""
        theme_mode = str(self.settings.value('themeMode', '', type=str)).strip().lower()
        if theme_mode in {'light', 'dark', 'system'}:
            return theme_mode
        # Backward compatibility for older boolean darkMode settings
        legacy_dark_mode = bool(self.settings.value('darkMode', False, type=bool))
        return 'dark' if legacy_dark_mode else 'light'

    def set_theme_mode(self, mode: str) -> None:
        """Set theme mode preference."""
        normalized = (mode or '').strip().lower()
        if normalized not in {'light', 'dark', 'system'}:
            normalized = 'light'
        self.settings.setValue('themeMode', normalized)

    def get_dark_mode(self) -> bool:
        """Backward compatible dark mode getter."""
        return self.get_theme_mode() == 'dark'

    def set_dark_mode(self, enabled: bool) -> None:
        """Backward compatible dark mode setter."""
        self.set_theme_mode('dark' if enabled else 'light')

    def get_format_settings(self) -> dict:
        """Get markdown format settings."""
        return {
            'headerStyle': self.settings.value('headerStyle', "ATX (#)"),
            'tableStyle': self.settings.value('tableStyle', "Simple"),
        }
        
    def save_format_settings(self, settings: dict) -> None:
        """Save markdown format settings."""
        for key, value in settings.items():
            self.settings.setValue(key, value)
    def get_recent_files(self) -> List[str]:
        """Get list of recently opened files."""
        return cast(List[str], self.settings.value('recentFiles', [], type=list))
        
    def set_recent_files(self, files: list) -> None:
        """Save list of recently opened files."""
        self.settings.setValue('recentFiles', files)
        
    
    def get_recent_outputs(self) -> List[str]:
        """Get list of recent output locations."""
        return cast(List[str], self.settings.value('recentOutputs', [], type=list))
    def set_recent_outputs(self, paths: list) -> None:
        """Save list of recent output locations."""
        self.settings.setValue('recentOutputs', paths)
        
    def get_current_language(self) -> str:
        """Get current language code."""
        return str(self.settings.value('currentLanguage', 'en', type=str))

    def set_current_language(self, lang_code: str) -> None:
        """Set current language code."""
        self.settings.setValue('currentLanguage', lang_code)
        
    def get_save_mode(self) -> bool:
        """Get save mode preference (True for combined, False for individual)."""
        # Ensure returned value is a bool for type checking
        return cast(bool, self.settings.value('combinedSaveMode', True, type=bool))
        
    def set_save_mode(self, combined: bool) -> None:
        """Set save mode preference."""
        self.settings.setValue('combinedSaveMode', combined)

    def get_default_output_format(self) -> str:
        """Get default output format extension."""
        fmt = str(self.settings.value('defaultOutputFormat', '.md', type=str))
        return fmt if fmt.startswith('.') else f'.{fmt}'

    def set_default_output_format(self, output_format: str) -> None:
        """Set default output format extension."""
        fmt = (output_format or '.md').strip()
        if not fmt.startswith('.'):
            fmt = f'.{fmt}'
        self.settings.setValue('defaultOutputFormat', fmt)

    def get_default_output_folder(self) -> str:
        """Get default output folder path."""
        return str(self.settings.value('defaultOutputFolder', '', type=str))

    def set_default_output_folder(self, folder_path: str) -> None:
        """Set default output folder path."""
        self.settings.setValue('defaultOutputFolder', folder_path or '')

    def get_save_to_source_folder(self) -> bool:
        """Get whether file outputs should default to the source folder."""
        return bool(self.settings.value('saveToSourceFolder', False, type=bool))

    def set_save_to_source_folder(self, enabled: bool) -> None:
        """Set whether file outputs should default to the source folder."""
        self.settings.setValue('saveToSourceFolder', enabled)

    def get_batch_size(self) -> int:
        """Get default conversion batch size."""
        return int(self.settings.value('batchSize', 3, type=int))

    def set_batch_size(self, batch_size: int) -> None:
        """Set default conversion batch size."""
        size = max(1, min(10, int(batch_size)))
        self.settings.setValue('batchSize', size)

    def get_ocr_enabled(self) -> bool:
        """Get whether OCR is enabled."""
        return bool(self.settings.value('ocrEnabled', False, type=bool))

    def set_ocr_enabled(self, enabled: bool) -> None:
        """Set whether OCR is enabled."""
        self.settings.setValue('ocrEnabled', enabled)

    def get_preserve_pdf_images(self) -> bool:
        """Get whether PDF image preservation is enabled by default."""
        return bool(self.settings.value('preservePdfImages', False, type=bool))

    def set_preserve_pdf_images(self, enabled: bool) -> None:
        """Set whether PDF image preservation is enabled by default."""
        self.settings.setValue('preservePdfImages', enabled)

    def get_preserve_docx_images(self) -> bool:
        """Get whether DOCX image preservation is enabled by default."""
        return bool(self.settings.value('preserveDocxImages', False, type=bool))

    def set_preserve_docx_images(self, enabled: bool) -> None:
        """Set whether DOCX image preservation is enabled by default."""
        self.settings.setValue('preserveDocxImages', enabled)

    def get_ocr_provider(self) -> str:
        """Get the configured OCR provider."""
        value = str(
            self.settings.value('ocrProvider', OCR_PROVIDER_AZURE_TESSERACT, type=str)
        )
        return normalize_ocr_provider(value)

    def set_ocr_provider(self, provider: str) -> None:
        """Set the OCR provider."""
        normalized = normalize_ocr_provider(provider)
        self.settings.setValue('ocrProvider', normalized)

    def get_ocr_fallback_provider(self) -> str:
        """Get the optional OCR fallback provider."""
        value = str(self.settings.value('ocrFallbackProvider', '', type=str))
        normalized = (value or '').strip().lower()
        if normalized in OCR_FALLBACK_PROVIDERS:
            return normalized

        if bool(self.settings.value('ocrFallbackEnabled', True, type=bool)):
            return OCR_PROVIDER_AZURE_TESSERACT
        return OCR_PROVIDER_NONE

    def set_ocr_fallback_provider(self, provider: str) -> None:
        """Set the optional OCR fallback provider."""
        normalized = (provider or '').strip().lower()
        if normalized != OCR_PROVIDER_NONE:
            normalized = normalize_ocr_provider(normalized)
        if normalized not in OCR_FALLBACK_PROVIDERS:
            normalized = OCR_PROVIDER_AZURE_TESSERACT
        self.settings.setValue('ocrFallbackProvider', normalized)
        self.settings.setValue('ocrFallbackEnabled', normalized != OCR_PROVIDER_NONE)

    def get_ocr_fallback_enabled(self) -> bool:
        """Get whether a secondary OCR provider is configured."""
        return self.get_ocr_fallback_provider() != OCR_PROVIDER_NONE

    def set_ocr_fallback_enabled(self, enabled: bool) -> None:
        """Set whether Azure/Tesseract is used as OCR fallback."""
        self.set_ocr_fallback_provider(
            OCR_PROVIDER_AZURE_TESSERACT if enabled else OCR_PROVIDER_NONE
        )

    def get_glmocr_mode(self) -> str:
        """Get the configured GLM-OCR mode."""
        value = str(
            self.settings.value('glmocrMode', GLMOCR_MODE_MAAS, type=str)
        ).strip().lower()
        if value == GLMOCR_MODE_SERVER:
            return GLMOCR_MODE_SDK_SERVER
        if value in {
            GLMOCR_MODE_MAAS,
            GLMOCR_MODE_OLLAMA,
            GLMOCR_MODE_SDK_SERVER,
        }:
            return value
        return GLMOCR_MODE_MAAS

    def set_glmocr_mode(self, mode: str) -> None:
        """Set the GLM-OCR mode."""
        normalized = (mode or '').strip().lower()
        if normalized == GLMOCR_MODE_SERVER:
            normalized = GLMOCR_MODE_SDK_SERVER
        if normalized not in {
            GLMOCR_MODE_MAAS,
            GLMOCR_MODE_OLLAMA,
            GLMOCR_MODE_SDK_SERVER,
        }:
            normalized = GLMOCR_MODE_MAAS
        self.settings.setValue('glmocrMode', normalized)

    def get_glmocr_ollama_host(self) -> str:
        """Get the configured Ollama host."""
        value = str(
            self.settings.value(
                'glmocrOllamaHost',
                DEFAULT_GLMOCR_OLLAMA_HOST,
                type=str,
            )
        ).strip()
        return value or DEFAULT_GLMOCR_OLLAMA_HOST

    def set_glmocr_ollama_host(self, host: str) -> None:
        """Set the Ollama host."""
        normalized = (host or '').strip() or DEFAULT_GLMOCR_OLLAMA_HOST
        self.settings.setValue('glmocrOllamaHost', normalized)

    def get_glmocr_ollama_port(self) -> int:
        """Get the configured Ollama port."""
        port = int(
            self.settings.value(
                'glmocrOllamaPort',
                DEFAULT_GLMOCR_OLLAMA_PORT,
                type=int,
            )
        )
        return port if 1 <= port <= 65535 else DEFAULT_GLMOCR_OLLAMA_PORT

    def set_glmocr_ollama_port(self, port: int) -> None:
        """Set the Ollama port."""
        normalized = max(1, min(65535, int(port)))
        self.settings.setValue('glmocrOllamaPort', normalized)

    def get_glmocr_ollama_model(self) -> str:
        """Get the configured Ollama model name."""
        value = str(
            self.settings.value(
                'glmocrOllamaModel',
                DEFAULT_GLMOCR_OLLAMA_MODEL,
                type=str,
            )
        ).strip()
        return value or DEFAULT_GLMOCR_OLLAMA_MODEL

    def set_glmocr_ollama_model(self, model: str) -> None:
        """Set the Ollama model name."""
        normalized = (model or '').strip() or DEFAULT_GLMOCR_OLLAMA_MODEL
        self.settings.setValue('glmocrOllamaModel', normalized)

    def get_glmocr_sdk_server_url(self) -> str:
        """Get the configured GLM-OCR SDK server parse endpoint."""
        value = str(
            self.settings.value(
                'glmocrSdkServerUrl',
                '',
                type=str,
            )
        ).strip()
        if not value:
            value = str(
                self.settings.value(
                    'glmocrServerUrl',
                    DEFAULT_GLMOCR_SDK_SERVER_URL,
                    type=str,
                )
            ).strip()
        return value or DEFAULT_GLMOCR_SDK_SERVER_URL

    def set_glmocr_sdk_server_url(self, url: str) -> None:
        """Set the GLM-OCR SDK server parse endpoint."""
        normalized = (url or '').strip() or DEFAULT_GLMOCR_SDK_SERVER_URL
        self.settings.setValue('glmocrSdkServerUrl', normalized)

    def get_http_ocr_endpoint(self) -> str:
        """Get the generic HTTP OCR endpoint."""
        return str(self.settings.value('httpOcrEndpoint', '', type=str)).strip()

    def set_http_ocr_endpoint(self, endpoint: str) -> None:
        """Set the generic HTTP OCR endpoint."""
        self.settings.setValue('httpOcrEndpoint', (endpoint or '').strip())

    def get_http_ocr_model(self) -> str:
        """Get the optional generic HTTP OCR model name."""
        return str(self.settings.value('httpOcrModel', '', type=str)).strip()

    def set_http_ocr_model(self, model: str) -> None:
        """Set the optional generic HTTP OCR model name."""
        self.settings.setValue('httpOcrModel', (model or '').strip())

    def get_http_ocr_api_key_env(self) -> str:
        """Get the environment variable used for generic HTTP OCR auth."""
        value = str(
            self.settings.value(
                'httpOcrApiKeyEnv',
                DEFAULT_HTTP_OCR_API_KEY_ENV,
                type=str,
            )
        ).strip()
        return value or DEFAULT_HTTP_OCR_API_KEY_ENV

    def set_http_ocr_api_key_env(self, env_var: str) -> None:
        """Set the environment variable used for generic HTTP OCR auth."""
        normalized = (env_var or '').strip() or DEFAULT_HTTP_OCR_API_KEY_ENV
        self.settings.setValue('httpOcrApiKeyEnv', normalized)

    def get_http_ocr_timeout_seconds(self) -> int:
        """Get the generic HTTP OCR request timeout."""
        timeout = int(
            self.settings.value(
                'httpOcrTimeoutSeconds',
                DEFAULT_HTTP_OCR_TIMEOUT_SECONDS,
                type=int,
            )
        )
        return max(1, min(3600, timeout))

    def set_http_ocr_timeout_seconds(self, timeout_seconds: int) -> None:
        """Set the generic HTTP OCR request timeout."""
        normalized = max(1, min(3600, int(timeout_seconds)))
        self.settings.setValue('httpOcrTimeoutSeconds', normalized)

    def get_docintel_endpoint(self) -> str:
        """Get the configured Azure Document Intelligence endpoint."""
        return str(self.settings.value('docintelEndpoint', '', type=str)).strip()

    def set_docintel_endpoint(self, endpoint: str) -> None:
        """Set the Azure Document Intelligence endpoint."""
        self.settings.setValue('docintelEndpoint', (endpoint or '').strip())

    def get_ocr_languages(self) -> str:
        """Get configured Tesseract language codes."""
        return str(self.settings.value('ocrLanguages', '', type=str)).strip()

    def set_ocr_languages(self, languages: str) -> None:
        """Set Tesseract language codes such as 'eng' or 'eng+deu'."""
        self.settings.setValue('ocrLanguages', (languages or '').strip())

    def get_tesseract_path(self) -> str:
        """Get the optional Tesseract executable path."""
        return str(self.settings.value('tesseractPath', '', type=str)).strip()

    def set_tesseract_path(self, path: str) -> None:
        """Set the optional Tesseract executable path."""
        self.settings.setValue('tesseractPath', (path or '').strip())
        
    def get_update_notifications_enabled(self) -> bool:
        """Get whether update notifications are enabled."""
        return bool(self.settings.value('updateNotifications', True, type=bool))
        
    def set_update_notifications_enabled(self, enabled: bool) -> None:
        """Set whether update notifications are enabled."""
        self.settings.setValue('updateNotifications', enabled)

    def get_window_geometry(self) -> bytes | None:
        """Get stored window geometry."""
        return cast(bytes | None, self.settings.value('windowGeometry', None))

    def set_window_geometry(self, geometry: bytes) -> None:
        """Save window geometry."""
        self.settings.setValue('windowGeometry', geometry)

    def get_window_state(self) -> bytes | None:
        """Get stored window state (e.g., maximized, minimized)."""
        return cast(bytes | None, self.settings.value('windowState', None))

    def set_window_state(self, state: bytes) -> None:
        """Save window state."""
        self.settings.setValue('windowState', state)

    def get_splitter_state(self) -> bytes | None:
        """Get stored splitter state."""
        return cast(bytes | None, self.settings.value('splitterState', None))

    def set_splitter_state(self, state: bytes) -> None:
        """Save splitter state."""
        self.settings.setValue('splitterState', state)
