from PySide6.QtCore import QSettings

from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui.settings_interface import SettingsInterface
from markitdowngui.utils.translations import get_translation


def _settings_manager(tmp_path):
    test_settings_path = tmp_path / "test_settings.ini"
    test_settings = QSettings(str(test_settings_path), QSettings.Format.IniFormat)
    manager = SettingsManager()
    manager.settings = test_settings
    return manager


def test_settings_interface_persists_pdf_image_controls(qapp, tmp_path):
    manager = _settings_manager(tmp_path)
    widget = SettingsInterface(
        manager,
        lambda key: get_translation("en", key),
    )

    widget.pdf_pipeline_combo.setCurrentIndex(
        widget.pdf_pipeline_combo.findData("pymupdf")
    )
    widget.preserve_pdf_images_check.setChecked(True)
    widget.pdf_assets_layout_combo.setCurrentIndex(
        widget.pdf_assets_layout_combo.findData("single")
    )

    assert manager.get_pdf_pipeline() == "pymupdf"
    assert manager.get_preserve_pdf_images() is True
    assert manager.get_pdf_assets_layout() == "single"

    widget.deleteLater()


def test_settings_interface_restores_pdf_controls_from_persisted_settings(qapp, tmp_path):
    manager = _settings_manager(tmp_path)
    manager.set_pdf_pipeline("pymupdf")
    manager.set_preserve_pdf_images(True)
    manager.set_pdf_assets_layout("single")

    widget = SettingsInterface(
        manager,
        lambda key: get_translation("en", key),
    )

    try:
        assert widget.pdf_pipeline_combo.currentData() == "pymupdf"
        assert widget.preserve_pdf_images_check.isChecked() is True
        assert widget.pdf_assets_layout_combo.currentData() == "single"
    finally:
        widget.deleteLater()
