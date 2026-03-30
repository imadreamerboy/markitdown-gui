from PySide6.QtCore import QSettings
from typing import cast, List


OCR_PROVIDER_LEGACY = "legacy"
OCR_PROVIDER_GLMOCR = "glmocr"
GLMOCR_MODE_MAAS = "maas"
GLMOCR_MODE_SELFHOSTED = "selfhosted"


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

    def get_batch_size(self) -> int:
        """Get default conversion batch size."""
        return int(self.settings.value('batchSize', 3, type=int))

    def set_batch_size(self, batch_size: int) -> None:
        """Set default conversion batch size."""
        size = max(1, min(10, int(batch_size)))
        self.settings.setValue('batchSize', size)

    def get_ocr_enabled(self) -> bool:
        """Get whether OCR fallback is enabled."""
        return bool(self.settings.value('ocrEnabled', False, type=bool))

    def set_ocr_enabled(self, enabled: bool) -> None:
        """Set whether OCR fallback is enabled."""
        self.settings.setValue('ocrEnabled', enabled)

    def get_ocr_provider(self) -> str:
        """Get the configured OCR provider."""
        value = str(
            self.settings.value('ocrProvider', OCR_PROVIDER_LEGACY, type=str)
        ).strip().lower()
        if value in {OCR_PROVIDER_LEGACY, OCR_PROVIDER_GLMOCR}:
            return value
        return OCR_PROVIDER_LEGACY

    def set_ocr_provider(self, provider: str) -> None:
        """Set the OCR provider."""
        normalized = (provider or '').strip().lower()
        if normalized not in {OCR_PROVIDER_LEGACY, OCR_PROVIDER_GLMOCR}:
            normalized = OCR_PROVIDER_LEGACY
        self.settings.setValue('ocrProvider', normalized)

    def get_ocr_fallback_enabled(self) -> bool:
        """Get whether GLM-OCR falls back to the legacy OCR stack."""
        return bool(self.settings.value('ocrFallbackEnabled', True, type=bool))

    def set_ocr_fallback_enabled(self, enabled: bool) -> None:
        """Set whether GLM-OCR falls back to the legacy OCR stack."""
        self.settings.setValue('ocrFallbackEnabled', enabled)

    def get_glmocr_mode(self) -> str:
        """Get the configured GLM-OCR mode."""
        value = str(
            self.settings.value('glmocrMode', GLMOCR_MODE_MAAS, type=str)
        ).strip().lower()
        if value in {GLMOCR_MODE_MAAS, GLMOCR_MODE_SELFHOSTED}:
            return value
        return GLMOCR_MODE_MAAS

    def set_glmocr_mode(self, mode: str) -> None:
        """Set the GLM-OCR mode."""
        normalized = (mode or '').strip().lower()
        if normalized not in {GLMOCR_MODE_MAAS, GLMOCR_MODE_SELFHOSTED}:
            normalized = GLMOCR_MODE_MAAS
        self.settings.setValue('glmocrMode', normalized)

    def get_glmocr_api_host(self) -> str:
        """Get the configured GLM-OCR self-hosted API host."""
        value = str(self.settings.value('glmocrApiHost', '127.0.0.1', type=str)).strip()
        return value or '127.0.0.1'

    def set_glmocr_api_host(self, host: str) -> None:
        """Set the GLM-OCR self-hosted API host."""
        normalized = (host or '').strip() or '127.0.0.1'
        self.settings.setValue('glmocrApiHost', normalized)

    def get_glmocr_api_port(self) -> int:
        """Get the configured GLM-OCR self-hosted API port."""
        port = int(self.settings.value('glmocrApiPort', 8080, type=int))
        return port if 1 <= port <= 65535 else 8080

    def set_glmocr_api_port(self, port: int) -> None:
        """Set the GLM-OCR self-hosted API port."""
        normalized = max(1, min(65535, int(port)))
        self.settings.setValue('glmocrApiPort', normalized)

    def get_glmocr_model(self) -> str:
        """Get the configured GLM-OCR model name."""
        value = str(self.settings.value('glmocrModel', 'glm-ocr', type=str)).strip()
        return value or 'glm-ocr'

    def set_glmocr_model(self, model: str) -> None:
        """Set the GLM-OCR model name."""
        normalized = (model or '').strip() or 'glm-ocr'
        self.settings.setValue('glmocrModel', normalized)

    def get_glmocr_config_path(self) -> str:
        """Get the optional GLM-OCR config path override."""
        return str(self.settings.value('glmocrConfigPath', '', type=str)).strip()

    def set_glmocr_config_path(self, path: str) -> None:
        """Set the optional GLM-OCR config path override."""
        self.settings.setValue('glmocrConfigPath', (path or '').strip())

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
