from pathlib import Path
import shutil

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QWidget

from markitdowngui.core.conversion import (
    ConversionOptions,
    ConversionOutcome,
    convert_file_with_details,
)
from markitdowngui.core.markdown_assets import GeneratedAsset, build_asset_placeholder
from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui.home_interface import HomeInterface
from markitdowngui.utils.translations import get_translation

pytestmark = [pytest.mark.runtime_ui]


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
    manager.set_pdf_pipeline("pymupdf")
    parent = _RuntimeWindow()
    widget = HomeInterface(manager, parent=parent)
    placeholder = build_asset_placeholder("sha-preview")
    artifact = ConversionOutcome(
        markdown=f"# Report\n\n![Page 1 image 1]({placeholder})",
        assets=(
            GeneratedAsset(
                filename="page_001_img_001.png",
                temp_path=str(tmp_path / "page_001_img_001.png"),
                page_number=1,
                image_number=1,
                sha256="sha-preview",
                width=128,
                height=128,
                size_bytes=len(b"png-bytes"),
            ),
        ),
    )
    Path(artifact.assets[0].temp_path).write_bytes(b"png-bytes")

    markdown, preview_base_path = widget._build_preview_markdown("report.pdf", artifact)
    widget._set_markdown_preview(markdown, preview_base_path)

    try:
        assert preview_base_path is not None
        assert "assets/report_page_001_img_001.png" in markdown
        assert "## Extracted Images" not in markdown
        assert widget.markdown_raw.toPlainText().index("# Report") < widget.markdown_raw.toPlainText().index("assets/report_page_001_img_001.png")
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
    doc1_placeholder = build_asset_placeholder("sha-doc1")
    doc2_placeholder = build_asset_placeholder("sha-doc2")
    widget.conversionArtifacts = {
        "doc1.pdf": ConversionOutcome(
            markdown=f"# Doc 1\n\n![Page 1 image 1]({doc1_placeholder})",
            assets=(
                GeneratedAsset(
                    filename="page_001_img_001.png",
                    temp_path=str(tmp_path / "page_001_img_001.png"),
                    page_number=1,
                    image_number=1,
                    sha256="sha-doc1",
                    width=128,
                    height=128,
                    size_bytes=len(b"one"),
                ),
            ),
        ),
        "doc2.pdf": ConversionOutcome(
            markdown=f"# Doc 2\n\n![Page 1 image 2]({doc2_placeholder})",
            assets=(
                GeneratedAsset(
                    filename="page_001_img_002.png",
                    temp_path=str(tmp_path / "page_001_img_002.png"),
                    page_number=1,
                    image_number=2,
                    sha256="sha-doc2",
                    width=128,
                    height=128,
                    size_bytes=len(b"two"),
                ),
            ),
        ),
    }
    Path(widget.conversionArtifacts["doc1.pdf"].assets[0].temp_path).write_bytes(b"one")
    Path(widget.conversionArtifacts["doc2.pdf"].assets[0].temp_path).write_bytes(b"two")

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: str(tmp_path))
    widget.save_individual_outputs()

    try:
        doc1_md = (tmp_path / "doc1.md").read_text(encoding="utf-8")
        doc2_md = (tmp_path / "doc2.md").read_text(encoding="utf-8")
        assert "assets/doc1_page_001_img_001.png" in doc1_md
        assert "assets/doc2_page_001_img_002.png" in doc2_md
        assert "## Extracted Images" not in doc1_md
        assert "## Extracted Images" not in doc2_md
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
    doc1_placeholder = build_asset_placeholder("sha-doc1")
    doc2_placeholder = build_asset_placeholder("sha-doc2")
    widget.conversionArtifacts = {
        "doc1.pdf": ConversionOutcome(
            markdown=f"# Doc 1\n\n![Page 1 image 1]({doc1_placeholder})",
            assets=(
                GeneratedAsset(
                    filename="page_001_img_001.png",
                    temp_path=str(tmp_path / "page_001_img_001.png"),
                    page_number=1,
                    image_number=1,
                    sha256="sha-doc1",
                    width=128,
                    height=128,
                    size_bytes=len(b"one"),
                ),
            ),
        ),
        "doc2.pdf": ConversionOutcome(
            markdown=f"# Doc 2\n\n![Page 2 image 1]({doc2_placeholder})",
            assets=(
                GeneratedAsset(
                    filename="page_002_img_001.png",
                    temp_path=str(tmp_path / "page_002_img_001.png"),
                    page_number=2,
                    image_number=1,
                    sha256="sha-doc2",
                    width=128,
                    height=128,
                    size_bytes=len(b"two"),
                ),
            ),
        ),
    }
    Path(widget.conversionArtifacts["doc1.pdf"].assets[0].temp_path).write_bytes(b"one")
    Path(widget.conversionArtifacts["doc2.pdf"].assets[0].temp_path).write_bytes(b"two")

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
        assert "## Extracted Images" not in combined_md
        assert (tmp_path / "combined_assets" / "doc1" / "page_001_img_001.png").read_bytes() == b"one"
        assert (tmp_path / "combined_assets" / "doc2" / "page_002_img_001.png").read_bytes() == b"two"
    finally:
        widget.shutdown()
        widget.deleteLater()
        parent.deleteLater()


def test_home_interface_preview_uses_real_pymupdf_conversion_artifact(
    qapp,
    tmp_path,
    sample_pdf_factory,
):
    manager = _settings_manager(tmp_path)
    manager.set_pdf_pipeline("pymupdf")
    manager.set_preserve_pdf_images(True)
    manager.set_pdf_assets_layout("separate")
    parent = _RuntimeWindow()
    widget = HomeInterface(manager, parent=parent)
    pdf_path = sample_pdf_factory(tmp_path / "runtime-inline.pdf")

    outcome = convert_file_with_details(
        str(pdf_path),
        ConversionOptions(
            pdf_pipeline="pymupdf",
            preserve_pdf_images=True,
        ),
    )

    try:
        markdown, preview_base_path = widget._build_preview_markdown(
            str(pdf_path),
            outcome,
        )
        widget._set_markdown_preview(markdown, preview_base_path)

        assert preview_base_path is not None
        assert "Alpha paragraph" in markdown
        assert "Beta paragraph" in markdown
        assert "runtime-inline_assets/page_001_img_001.png" in markdown
        assert "## Extracted Images" not in markdown
        assert markdown.index("Alpha paragraph") < markdown.index(
            "runtime-inline_assets/page_001_img_001.png"
        ) < markdown.index("Beta paragraph")
    finally:
        temp_dirs = {str(Path(asset.temp_path).parent) for asset in outcome.assets}
        widget.shutdown()
        widget.deleteLater()
        parent.deleteLater()
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
