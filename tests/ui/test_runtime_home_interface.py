from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QWidget

from markitdowngui.core.conversion import ConversionOutcome
from markitdowngui.core.markdown_assets import GeneratedAsset
from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui.home_interface import HomeInterface
from markitdowngui.utils.translations import get_translation


def _settings_manager(tmp_path):
    test_settings_path = tmp_path / "test_settings.ini"
    test_settings = QSettings(str(test_settings_path), QSettings.Format.IniFormat)
    manager = SettingsManager()
    manager.settings = test_settings
    return manager


class _RuntimeWindow(QWidget):
    def translate(self, key: str) -> str:
        return get_translation("en", key)


def _asset(tmp_path, name: str, payload: bytes, *, page: int, image: int) -> GeneratedAsset:
    source_path = tmp_path / name
    source_path.write_bytes(payload)
    return GeneratedAsset(
        filename=name,
        temp_path=str(source_path),
        page_number=page,
        image_number=image,
        sha256=name,
        width=128,
        height=128,
        size_bytes=len(payload),
    )


def test_home_interface_preview_materializes_temp_assets(qapp, tmp_path):
    manager = _settings_manager(tmp_path)
    manager.set_pdf_assets_layout("single")
    parent = _RuntimeWindow()
    widget = HomeInterface(manager, parent=parent)
    artifact = ConversionOutcome(
        markdown="# Report",
        assets=(
            _asset(tmp_path, "page_001_img_001.png", b"png-bytes", page=1, image=1),
        ),
    )

    markdown, preview_base_path = widget._build_preview_markdown("report.pdf", artifact)

    try:
        assert preview_base_path is not None
        assert "assets/report_page_001_img_001.png" in markdown
        preview_asset = Path(preview_base_path).parent / "assets" / "report_page_001_img_001.png"
        assert preview_asset.read_bytes() == b"png-bytes"
    finally:
        widget.shutdown()
        widget.deleteLater()
        parent.deleteLater()


def test_home_interface_save_individual_outputs_single_assets_runtime(
    qapp,
    tmp_path,
    monkeypatch,
):
    manager = _settings_manager(tmp_path)
    manager.set_pdf_assets_layout("single")
    parent = _RuntimeWindow()
    widget = HomeInterface(manager, parent=parent)
    widget.conversionArtifacts = {
        "doc1.pdf": ConversionOutcome(
            markdown="# Doc 1",
            assets=(
                _asset(tmp_path, "page_001_img_001.png", b"one", page=1, image=1),
            ),
        ),
        "doc2.pdf": ConversionOutcome(
            markdown="# Doc 2",
            assets=(
                _asset(tmp_path, "page_001_img_002.png", b"two", page=1, image=2),
            ),
        ),
    }

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: str(tmp_path))
    widget.save_individual_outputs()

    try:
        doc1_md = (tmp_path / "doc1.md").read_text(encoding="utf-8")
        doc2_md = (tmp_path / "doc2.md").read_text(encoding="utf-8")
        assert "assets/doc1_page_001_img_001.png" in doc1_md
        assert "assets/doc2_page_001_img_002.png" in doc2_md
        assert (tmp_path / "assets" / "doc1_page_001_img_001.png").read_bytes() == b"one"
        assert (tmp_path / "assets" / "doc2_page_001_img_002.png").read_bytes() == b"two"
    finally:
        widget.shutdown()
        widget.deleteLater()
        parent.deleteLater()


def test_home_interface_save_combined_outputs_separate_assets_runtime(
    qapp,
    tmp_path,
    monkeypatch,
):
    manager = _settings_manager(tmp_path)
    manager.set_pdf_assets_layout("separate")
    parent = _RuntimeWindow()
    widget = HomeInterface(manager, parent=parent)
    widget.conversionArtifacts = {
        "doc1.pdf": ConversionOutcome(
            markdown="# Doc 1",
            assets=(
                _asset(tmp_path, "page_001_img_001.png", b"one", page=1, image=1),
            ),
        ),
        "doc2.pdf": ConversionOutcome(
            markdown="# Doc 2",
            assets=(
                _asset(tmp_path, "page_002_img_001.png", b"two", page=2, image=1),
            ),
        ),
    }

    combined_path = tmp_path / "combined.md"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (str(combined_path), "Markdown Files (*.md)"),
    )
    widget.save_combined_output()

    try:
        combined_md = combined_path.read_text(encoding="utf-8")
        assert "combined_assets/doc1/page_001_img_001.png" in combined_md
        assert "combined_assets/doc2/page_002_img_001.png" in combined_md
        assert (tmp_path / "combined_assets" / "doc1" / "page_001_img_001.png").read_bytes() == b"one"
        assert (tmp_path / "combined_assets" / "doc2" / "page_002_img_001.png").read_bytes() == b"two"
    finally:
        widget.shutdown()
        widget.deleteLater()
        parent.deleteLater()
