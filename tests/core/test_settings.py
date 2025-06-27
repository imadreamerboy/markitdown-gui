import pytest
from PySide6.QtCore import QSettings
from markitdowngui.core.settings import SettingsManager

@pytest.fixture
def settings_manager(tmp_path):
    """
    Fixture to create a SettingsManager instance that uses a temporary,
    test-specific QSettings object that writes to a temp file.
    """
    test_settings_path = tmp_path / "test_settings.ini"
    test_settings = QSettings(str(test_settings_path), QSettings.Format.IniFormat)

    manager = SettingsManager()
    # Overwrite the default settings object with our test-specific one
    manager.settings = test_settings
    
    yield manager
    
    manager.settings.clear()

def test_dark_mode(settings_manager):
    """Test getting and setting the dark mode preference."""
    assert not settings_manager.get_dark_mode()  # Default is False
    settings_manager.set_dark_mode(True)
    assert settings_manager.get_dark_mode()

def test_format_settings(settings_manager):
    """Test getting and saving format settings."""
    default_settings = settings_manager.get_format_settings()
    assert not default_settings['autoSave']
    assert default_settings['headerStyle'] == "ATX (#)"

    new_settings = {
        'headerStyle': 'Setext',
        'tableStyle': 'Grid',
        'autoSave': True,
        'autoSaveInterval': 15
    }
    settings_manager.save_format_settings(new_settings)
    
    saved_settings = settings_manager.get_format_settings()
    assert saved_settings['autoSave']
    assert saved_settings['headerStyle'] == 'Setext'
    assert saved_settings['autoSaveInterval'] == 15

def test_recent_files(settings_manager):
    """Test getting and setting the recent files list."""
    assert settings_manager.get_recent_files() == []
    
    files = ["/path/a", "/path/b"]
    settings_manager.set_recent_files(files)
    assert settings_manager.get_recent_files() == files

def test_recent_outputs(settings_manager):
    """Test getting and setting recent output paths."""
    assert settings_manager.get_recent_outputs() == []

    outputs = ["/output/a", "/output/b"]
    settings_manager.set_recent_outputs(outputs)
    assert settings_manager.get_recent_outputs() == outputs

def test_language_settings(settings_manager):
    """Test getting and setting the application language."""
    assert settings_manager.get_current_language() == 'en'  # Default is 'en'
    
    settings_manager.set_current_language('de')
    assert settings_manager.get_current_language() == 'de'

def test_save_mode(settings_manager):
    """Test getting and setting the save mode."""
    assert settings_manager.get_save_mode()  # Default is True
    
    settings_manager.set_save_mode(False)
    assert not settings_manager.get_save_mode() 