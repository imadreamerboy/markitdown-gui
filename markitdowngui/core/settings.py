from PySide6.QtCore import QSettings
from typing import cast, List

class SettingsManager:
    """Manages application settings and preferences."""
    
    def __init__(self):
        self.settings = QSettings('MarkItDown', 'GUI')
        
    def get_dark_mode(self) -> bool:
        """Get dark mode preference."""
        return bool(self.settings.value('darkMode', False, type=bool))
        
    def set_dark_mode(self, enabled: bool) -> None:
        """Set dark mode preference."""
        self.settings.setValue('darkMode', enabled)
        
    def get_format_settings(self) -> dict:
        """Get markdown format settings."""
        return {
            'headerStyle': self.settings.value('headerStyle', "ATX (#)"),
            'tableStyle': self.settings.value('tableStyle', "Simple"),
            'autoSave': self.settings.value('autoSave', False, type=bool),
            'autoSaveInterval': self.settings.value('autoSaveInterval', 5, type=int)
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
        
    def get_update_notifications_enabled(self) -> bool:
        """Get whether update notifications are enabled."""
        return bool(self.settings.value('updateNotifications', True, type=bool))
        
    def set_update_notifications_enabled(self, enabled: bool) -> None:
        """Set whether update notifications are enabled."""
        self.settings.setValue('updateNotifications', enabled)