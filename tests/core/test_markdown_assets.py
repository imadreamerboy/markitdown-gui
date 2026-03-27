from pathlib import Path

from markitdowngui.core.markdown_assets import (
    ASSET_LAYOUT_SEPARATE,
    ASSET_LAYOUT_SINGLE,
    GeneratedAsset,
    build_asset_placeholder,
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


def test_materialize_assets_and_rewrite_markdown_rewrites_inline_placeholders(tmp_path):
    output_md = tmp_path / "report.md"
    asset = GeneratedAsset(
        filename="page_001_img_001.png",
        temp_path=str(tmp_path / "page_001_img_001.png"),
        page_number=1,
        image_number=1,
        sha256="abc123",
        width=128,
        height=128,
        size_bytes=len(b"png-bytes"),
    )
    Path(asset.temp_path).write_bytes(b"png-bytes")
    placeholder = build_asset_placeholder(asset.sha256)
    markdown = materialize_assets_and_rewrite_markdown(
        "report.pdf",
        f"# Report\n\n![Page 1 image 1]({placeholder})",
        (asset,),
        output_md,
        ASSET_LAYOUT_SEPARATE,
    )

    assert "![Page 1 image 1](report_assets/page_001_img_001.png)" in markdown
    assert "## Extracted Images" not in markdown
    assert (tmp_path / "report_assets" / "page_001_img_001.png").read_bytes() == b"png-bytes"


def test_materialize_assets_and_rewrite_markdown_rewrites_multiple_inline_placeholders(tmp_path):
    output_md = tmp_path / "report.md"
    asset_one = GeneratedAsset(
        filename="page_001_img_001.png",
        temp_path=str(tmp_path / "page_001_img_001.png"),
        page_number=1,
        image_number=1,
        sha256="abc123",
        width=128,
        height=128,
        size_bytes=len(b"one"),
    )
    asset_two = GeneratedAsset(
        filename="page_001_img_002.png",
        temp_path=str(tmp_path / "page_001_img_002.png"),
        page_number=1,
        image_number=2,
        sha256="def456",
        width=128,
        height=128,
        size_bytes=len(b"two"),
    )
    Path(asset_one.temp_path).write_bytes(b"one")
    Path(asset_two.temp_path).write_bytes(b"two")
    placeholder_one = build_asset_placeholder(asset_one.sha256)
    placeholder_two = build_asset_placeholder(asset_two.sha256)

    markdown = materialize_assets_and_rewrite_markdown(
        "report.pdf",
        (
            f"# Report\n\n![Page 1 image 1]({placeholder_one})"
            f"\n\nText between\n\n![Page 1 image 2]({placeholder_two})"
        ),
        (asset_one, asset_two),
        output_md,
        ASSET_LAYOUT_SEPARATE,
    )

    assert "![Page 1 image 1](report_assets/page_001_img_001.png)" in markdown
    assert "![Page 1 image 2](report_assets/page_001_img_002.png)" in markdown
    assert "Text between" in markdown
    assert "## Extracted Images" not in markdown


def test_materialize_assets_and_rewrite_markdown_keeps_append_for_unreferenced_assets(tmp_path):
    output_md = tmp_path / "report.md"
    asset = GeneratedAsset(
        filename="page_001_img_001.png",
        temp_path=str(tmp_path / "page_001_img_001.png"),
        page_number=1,
        image_number=1,
        sha256="abc123",
        width=128,
        height=128,
        size_bytes=len(b"png-bytes"),
    )
    Path(asset.temp_path).write_bytes(b"png-bytes")

    markdown = materialize_assets_and_rewrite_markdown(
        "report.pdf",
        "# Report",
        (asset,),
        output_md,
        ASSET_LAYOUT_SEPARATE,
    )

    assert "## Extracted Images" in markdown
    assert "![Page 1 image 1](report_assets/page_001_img_001.png)" in markdown


def test_materialize_assets_and_rewrite_markdown_appends_only_unreferenced_assets(tmp_path):
    output_md = tmp_path / "report.md"
    inline_asset = GeneratedAsset(
        filename="page_001_img_001.png",
        temp_path=str(tmp_path / "page_001_img_001.png"),
        page_number=1,
        image_number=1,
        sha256="abc123",
        width=128,
        height=128,
        size_bytes=len(b"one"),
    )
    extra_asset = GeneratedAsset(
        filename="page_001_img_002.png",
        temp_path=str(tmp_path / "page_001_img_002.png"),
        page_number=1,
        image_number=2,
        sha256="def456",
        width=128,
        height=128,
        size_bytes=len(b"two"),
    )
    Path(inline_asset.temp_path).write_bytes(b"one")
    Path(extra_asset.temp_path).write_bytes(b"two")
    inline_placeholder = build_asset_placeholder(inline_asset.sha256)

    markdown = materialize_assets_and_rewrite_markdown(
        "report.pdf",
        f"# Report\n\n![Page 1 image 1]({inline_placeholder})",
        (inline_asset, extra_asset),
        output_md,
        ASSET_LAYOUT_SEPARATE,
    )

    assert "![Page 1 image 1](report_assets/page_001_img_001.png)" in markdown
    assert "## Extracted Images" in markdown
    assert "![Page 1 image 2](report_assets/page_001_img_002.png)" in markdown


def test_materialize_assets_and_rewrite_markdown_combined_single_rewrites_inline_placeholders_with_collisions(
    tmp_path,
):
    output_md = tmp_path / "combined.md"
    used_relative_paths: set[str] = set()
    asset_one = GeneratedAsset(
        filename="page_001_img_001.png",
        temp_path=str(tmp_path / "doc1_page_001_img_001.png"),
        page_number=1,
        image_number=1,
        sha256="same-sha-doc1",
        width=128,
        height=128,
        size_bytes=len(b"one"),
    )
    asset_two = GeneratedAsset(
        filename="page_001_img_001.png",
        temp_path=str(tmp_path / "doc2_page_001_img_001.png"),
        page_number=1,
        image_number=1,
        sha256="same-sha-doc2",
        width=128,
        height=128,
        size_bytes=len(b"two"),
    )
    Path(asset_one.temp_path).write_bytes(b"one")
    Path(asset_two.temp_path).write_bytes(b"two")

    doc1_markdown = materialize_assets_and_rewrite_markdown(
        "doc.pdf",
        f"![Page 1 image 1]({build_asset_placeholder(asset_one.sha256)})",
        (asset_one,),
        output_md,
        ASSET_LAYOUT_SINGLE,
        combined=True,
        used_relative_paths=used_relative_paths,
    )
    doc2_markdown = materialize_assets_and_rewrite_markdown(
        "doc.pdf",
        f"![Page 1 image 1]({build_asset_placeholder(asset_two.sha256)})",
        (asset_two,),
        output_md,
        ASSET_LAYOUT_SINGLE,
        combined=True,
        used_relative_paths=used_relative_paths,
    )

    assert "combined_assets/doc_page_001_img_001.png" in doc1_markdown
    assert "combined_assets/doc_page_001_img_001" in doc2_markdown
    assert doc1_markdown != doc2_markdown
    saved_assets = sorted((tmp_path / "combined_assets").glob("doc_page_001_img_001*"))
    assert len(saved_assets) == 2
    assert saved_assets[0].read_bytes() == b"one"
    assert saved_assets[1].read_bytes() == b"two"
