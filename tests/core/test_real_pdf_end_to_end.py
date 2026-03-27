import shutil
from pathlib import Path

import pytest

from markitdowngui.core.conversion import (
    BACKEND_NATIVE,
    ConversionOptions,
    convert_file_with_details,
)
from markitdowngui.core.markdown_assets import (
    ASSET_LAYOUT_SEPARATE,
    build_asset_placeholder,
    materialize_assets_and_rewrite_markdown,
)


def _cleanup_asset_temp_dirs(temp_paths: list[str]) -> None:
    temp_dirs = {str(Path(temp_path).parent) for temp_path in temp_paths}
    for temp_dir in temp_dirs:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_pymupdf_pipeline_real_pdf_preserves_inline_image_order_and_page_fallback(
    tmp_path,
    sample_pdf_factory,
):
    pdf_path = sample_pdf_factory(tmp_path / "inline-layout.pdf")

    outcome = convert_file_with_details(
        str(pdf_path),
        ConversionOptions(
            pdf_pipeline="pymupdf",
            preserve_pdf_images=True,
        ),
    )

    temp_paths = [asset.temp_path for asset in outcome.assets]
    try:
        assert outcome.backend == BACKEND_NATIVE
        assert len(outcome.assets) == 3

        assets_by_position = {
            (asset.page_number, asset.image_number): asset for asset in outcome.assets
        }
        first_placeholder = build_asset_placeholder(
            assets_by_position[(1, 1)].sha256
        )
        second_placeholder = build_asset_placeholder(
            assets_by_position[(1, 2)].sha256
        )
        trailing_placeholder = build_asset_placeholder(
            assets_by_position[(2, 1)].sha256
        )

        assert outcome.markdown.index("Alpha paragraph") < outcome.markdown.index(
            first_placeholder
        ) < outcome.markdown.index("Beta paragraph")
        assert outcome.markdown.index("Beta paragraph") < outcome.markdown.index(
            second_placeholder
        ) < outcome.markdown.index("Gamma paragraph")
        assert outcome.markdown.index("Gamma paragraph") < outcome.markdown.index(
            trailing_placeholder
        )

        output_path = tmp_path / "inline-output.md"
        rewritten = materialize_assets_and_rewrite_markdown(
            str(pdf_path),
            outcome.markdown,
            outcome.assets,
            output_path,
            ASSET_LAYOUT_SEPARATE,
        )
        output_path.write_text(rewritten, encoding="utf-8")

        assert "__PDF_ASSET_" not in rewritten
        assert "## Extracted Images" not in rewritten
        asset_dir = tmp_path / "inline-output_assets"
        assert (asset_dir / assets_by_position[(1, 1)].filename).exists()
        assert (asset_dir / assets_by_position[(1, 2)].filename).exists()
        assert (asset_dir / assets_by_position[(2, 1)].filename).exists()
    finally:
        _cleanup_asset_temp_dirs(temp_paths)


def test_pymupdf_pipeline_real_pdf_without_preserve_keeps_plain_markdown(
    tmp_path,
    sample_pdf_factory,
):
    pdf_path = sample_pdf_factory(tmp_path / "plain-layout.pdf")

    outcome = convert_file_with_details(
        str(pdf_path),
        ConversionOptions(pdf_pipeline="pymupdf"),
    )

    assert outcome.backend == BACKEND_NATIVE
    assert outcome.assets == ()
    assert "Alpha paragraph" in outcome.markdown
    assert "Beta paragraph" in outcome.markdown
    assert "Gamma paragraph" in outcome.markdown
    assert "__PDF_ASSET_" not in outcome.markdown
    assert "## Extracted Images" not in outcome.markdown


def test_markitdown_pipeline_real_pdf_appends_extracted_images_section(
    tmp_path,
    sample_pdf_factory,
):
    pytest.importorskip("markitdown")
    pdf_path = sample_pdf_factory(tmp_path / "legacy-layout.pdf")

    outcome = convert_file_with_details(
        str(pdf_path),
        ConversionOptions(
            pdf_pipeline="markitdown",
            preserve_pdf_images=True,
        ),
    )

    temp_paths = [asset.temp_path for asset in outcome.assets]
    try:
        assert outcome.backend == BACKEND_NATIVE
        assert "Alpha paragraph" in outcome.markdown
        assert len(outcome.assets) == 3

        output_path = tmp_path / "legacy-output.md"
        rewritten = materialize_assets_and_rewrite_markdown(
            str(pdf_path),
            outcome.markdown,
            outcome.assets,
            output_path,
            ASSET_LAYOUT_SEPARATE,
        )
        output_path.write_text(rewritten, encoding="utf-8")

        assert "## Extracted Images" in rewritten
        assert rewritten.index("Alpha paragraph") < rewritten.index(
            "## Extracted Images"
        )
        legacy_assets_dir = tmp_path / "legacy-output_assets"
        assert (legacy_assets_dir / "page_001_img_001.png").exists()
        assert (legacy_assets_dir / "page_001_img_002.png").exists()
        assert (legacy_assets_dir / "page_002_img_001.png").exists()
    finally:
        _cleanup_asset_temp_dirs(temp_paths)
