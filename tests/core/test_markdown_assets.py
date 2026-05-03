from dataclasses import dataclass

from markitdowngui.core.markdown_assets import (
    MarkdownSaveInput,
    cleanup_temp_asset_root,
    create_temp_asset_root,
    prepare_combined_markdown_for_save,
    prepare_markdown_for_separate_save,
    rewrite_markdown_for_preview,
)


@dataclass(frozen=True)
class _FakeAsset:
    filename: str
    source_path: str | None
    preview_markdown_path: str


def test_rewrite_markdown_for_preview_uses_file_urls(tmp_path):
    asset_path = tmp_path / "assets" / "page-1.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"png")

    markdown = rewrite_markdown_for_preview(
        "![page](C:/temp/run/report/page-1.png)",
        [
            _FakeAsset(
                filename="page-1.png",
                source_path=str(asset_path),
                preview_markdown_path="C:/temp/run/report/page-1.png",
            )
        ],
    )

    assert asset_path.resolve().as_uri() in markdown


def test_prepare_markdown_for_separate_save_copies_assets_and_rewrites_paths(tmp_path):
    asset_path = tmp_path / "temp-assets" / "report" / "page-1.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"png")
    output_path = tmp_path / "report.md"

    markdown = prepare_markdown_for_separate_save(
        "![page](C:/temp/run/report/page-1.png)",
        [
            _FakeAsset(
                filename="page-1.png",
                source_path=str(asset_path),
                preview_markdown_path="C:/temp/run/report/page-1.png",
            )
        ],
        output_path,
    )

    assert "report_assets/page-1.png" in markdown
    assert "C:/temp/run/report/page-1.png" not in markdown
    assert (tmp_path / "report_assets" / "page-1.png").is_file()


def test_prepare_combined_markdown_for_save_scopes_documents_and_avoids_collisions(
    tmp_path,
):
    first_asset = tmp_path / "temp-assets" / "report-a" / "page-1.png"
    second_asset = tmp_path / "temp-assets" / "report-b" / "page-1.png"
    first_asset.parent.mkdir(parents=True)
    second_asset.parent.mkdir(parents=True)
    first_asset.write_bytes(b"a")
    second_asset.write_bytes(b"b")
    output_path = tmp_path / "combined.md"

    markdown = prepare_combined_markdown_for_save(
        [
            MarkdownSaveInput(
                source="C:/docs/report.pdf",
                markdown="![first](C:/temp/run/report-a/page-1.png)",
                assets=[
                    _FakeAsset(
                        filename="page-1.png",
                        source_path=str(first_asset),
                        preview_markdown_path="C:/temp/run/report-a/page-1.png",
                    )
                ],
            ),
            MarkdownSaveInput(
                source="D:/docs/report.pdf",
                markdown="![second](C:/temp/run/report-b/page-1.png)",
                assets=[
                    _FakeAsset(
                        filename="page-1.png",
                        source_path=str(second_asset),
                        preview_markdown_path="C:/temp/run/report-b/page-1.png",
                    )
                ],
            ),
        ],
        output_path,
        source_heading_template="Source: {source}",
    )

    assert "combined_assets/001_report/page-1.png" in markdown
    assert "combined_assets/002_report/page-1.png" in markdown
    assert "C:/temp/run/report-a/page-1.png" not in markdown
    assert "C:/temp/run/report-b/page-1.png" not in markdown
    assert (tmp_path / "combined_assets" / "001_report" / "page-1.png").is_file()
    assert (tmp_path / "combined_assets" / "002_report" / "page-1.png").is_file()


def test_temp_asset_root_creation_and_cleanup():
    asset_root = create_temp_asset_root()

    assert asset_root.is_dir()

    cleanup_temp_asset_root(asset_root)

    assert not asset_root.exists()
