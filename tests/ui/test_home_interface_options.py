from PySide6.QtCore import QSettings

from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui.home_interface import build_conversion_options_from_settings


def test_build_conversion_options_from_settings(tmp_path):
    test_settings_path = tmp_path / "test_settings.ini"
    test_settings = QSettings(str(test_settings_path), QSettings.Format.IniFormat)

    manager = SettingsManager()
    manager.settings = test_settings
    manager.set_ocr_enabled(True)
    manager.set_docintel_endpoint("https://example.cognitiveservices.azure.com/")
    manager.set_ocr_languages("eng")
    manager.set_tesseract_path("/usr/bin/tesseract")
    manager.set_preserve_pdf_images(True)
    manager.set_pdf_assets_layout("single")
    manager.set_pdf_pipeline("pymupdf")

    options = build_conversion_options_from_settings(manager)

    assert options.ocr_enabled is True
    assert options.docintel_endpoint == "https://example.cognitiveservices.azure.com/"
    assert options.ocr_languages == "eng"
    assert options.tesseract_path == "/usr/bin/tesseract"
    assert options.preserve_pdf_images is True
    assert options.pdf_assets_layout == "single"
    assert options.pdf_pipeline == "pymupdf"
