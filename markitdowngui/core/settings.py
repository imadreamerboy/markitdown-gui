from PySide6.QtCore import QSettings

class SettingsManager:
    """Manages application settings and preferences."""
    
    def __init__(self):
        self.settings = QSettings('MarkItDown', 'GUI')
        
    def get_dark_mode(self) -> bool:
        """Get dark mode preference."""
        return self.settings.value('darkMode', False, type=bool)
        
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
            
    def get_recent_files(self) -> list:
        """Get list of recently opened files."""
        return self.settings.value('recentFiles', [], type=list)
        
    def set_recent_files(self, files: list) -> None:
        """Save list of recently opened files."""
        self.settings.setValue('recentFiles', files)
        
    def get_recent_outputs(self) -> list:
        """Get list of recent output locations."""
        return self.settings.value('recentOutputs', [], type=list)
        
    def set_recent_outputs(self, paths: list) -> None:
        """Save list of recent output locations."""
        self.settings.setValue('recentOutputs', paths)
        
    def get_save_mode(self) -> bool:
        """Get save mode preference (True for combined, False for individual)."""
        return self.settings.value('combinedSaveMode', True, type=bool)
        
    def set_save_mode(self, combined: bool) -> None:
        """Set save mode preference."""
        self.settings.setValue('combinedSaveMode', combined)