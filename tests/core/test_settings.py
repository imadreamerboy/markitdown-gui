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

def test_theme_mode(settings_manager):
    """Test setting and retrieving explicit theme mode."""
    assert settings_manager.get_theme_mode() in {"light", "dark", "system"}
    settings_manager.set_theme_mode("system")
    assert settings_manager.get_theme_mode() == "system"
    settings_manager.set_theme_mode("dark")
    assert settings_manager.get_theme_mode() == "dark"
    settings_manager.set_theme_mode("invalid")
    assert settings_manager.get_theme_mode() == "light"

def test_format_settings(settings_manager):
    """Test getting and saving format settings."""
    default_settings = settings_manager.get_format_settings()
    assert default_settings['headerStyle'] == "ATX (#)"

    new_settings = {
        'headerStyle': 'Setext',
        'tableStyle': 'Grid',
    }
    settings_manager.save_format_settings(new_settings)
    
    saved_settings = settings_manager.get_format_settings()
    assert saved_settings['headerStyle'] == 'Setext'
    assert saved_settings['tableStyle'] == 'Grid'

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

def test_output_defaults(settings_manager, tmp_path):
    """Test output format and default folder settings."""
    assert settings_manager.get_default_output_format() == ".md"
    settings_manager.set_default_output_format("txt")
    assert settings_manager.get_default_output_format() == ".txt"

    assert settings_manager.get_default_output_folder() == ""
    settings_manager.set_default_output_folder(str(tmp_path))
    assert settings_manager.get_default_output_folder() == str(tmp_path)

def test_batch_size(settings_manager):
    """Test batch size bounds and persistence."""
    assert settings_manager.get_batch_size() == 3
    settings_manager.set_batch_size(7)
    assert settings_manager.get_batch_size() == 7
    settings_manager.set_batch_size(0)
    assert settings_manager.get_batch_size() == 1
    settings_manager.set_batch_size(99)
    assert settings_manager.get_batch_size() == 10

def test_ocr_settings(settings_manager):
    """Test OCR-related settings and persistence."""
    assert not settings_manager.get_ocr_enabled()
    settings_manager.set_ocr_enabled(True)
    assert settings_manager.get_ocr_enabled()

    assert settings_manager.get_docintel_endpoint() == ""
    settings_manager.set_docintel_endpoint(" https://example.cognitiveservices.azure.com/ ")
    assert settings_manager.get_docintel_endpoint() == "https://example.cognitiveservices.azure.com/"

    assert settings_manager.get_ocr_languages() == ""
    settings_manager.set_ocr_languages(" eng+deu ")
    assert settings_manager.get_ocr_languages() == "eng+deu"

    assert settings_manager.get_tesseract_path() == ""
    settings_manager.set_tesseract_path(" /usr/bin/tesseract ")
    assert settings_manager.get_tesseract_path() == "/usr/bin/tesseract"
