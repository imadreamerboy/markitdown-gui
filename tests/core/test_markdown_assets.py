from pathlib import Path

from markitdowngui.core.markdown_assets import (
    ASSET_LAYOUT_SEPARATE,
    ASSET_LAYOUT_SINGLE,
    GeneratedAsset,
    materialize_assets_and_rewrite_markdown,
)


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


def test_materialize_assets_and_rewrite_markdown_separate_individual(tmp_path):
    output_md = tmp_path / "report.md"
    asset = _asset(tmp_path, "page_001_img_001.png", b"png-bytes", page=1, image=1)

    markdown = materialize_assets_and_rewrite_markdown(
        "report.pdf",
        "# Report",
        (asset,),
        output_md,
        ASSET_LAYOUT_SEPARATE,
    )

    assert "![Page 1 image 1](report_assets/page_001_img_001.png)" in markdown
    assert (tmp_path / "report_assets" / "page_001_img_001.png").read_bytes() == b"png-bytes"


def test_materialize_assets_and_rewrite_markdown_single_individual(tmp_path):
    output_md = tmp_path / "report.md"
    asset = _asset(tmp_path, "page_001_img_001.png", b"png-bytes", page=1, image=1)

    markdown = materialize_assets_and_rewrite_markdown(
        "report.pdf",
        "# Report",
        (asset,),
        output_md,
        ASSET_LAYOUT_SINGLE,
    )

    assert "![Page 1 image 1](assets/report_page_001_img_001.png)" in markdown
    assert (tmp_path / "assets" / "report_page_001_img_001.png").read_bytes() == b"png-bytes"


def test_materialize_assets_and_rewrite_markdown_combined_separate(tmp_path):
    output_md = tmp_path / "combined.md"
    asset = _asset(tmp_path, "page_001_img_001.png", b"png-bytes", page=1, image=1)

    markdown = materialize_assets_and_rewrite_markdown(
        "report.pdf",
        "# Report",
        (asset,),
        output_md,
        ASSET_LAYOUT_SEPARATE,
        combined=True,
        used_relative_paths=set(),
    )

    assert "![Page 1 image 1](combined_assets/report/page_001_img_001.png)" in markdown
    assert (tmp_path / "combined_assets" / "report" / "page_001_img_001.png").read_bytes() == b"png-bytes"


def test_materialize_assets_and_rewrite_markdown_combined_single(tmp_path):
    output_md = tmp_path / "combined.md"
    asset = _asset(tmp_path, "page_001_img_001.png", b"png-bytes", page=1, image=1)

    markdown = materialize_assets_and_rewrite_markdown(
        "report.pdf",
        "# Report",
        (asset,),
        output_md,
        ASSET_LAYOUT_SINGLE,
        combined=True,
        used_relative_paths=set(),
    )

    assert "![Page 1 image 1](combined_assets/report_page_001_img_001.png)" in markdown
    assert (tmp_path / "combined_assets" / "report_page_001_img_001.png").read_bytes() == b"png-bytes"
