from dataclasses import dataclass
import os
import stat

import pytest

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


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory modes are not available")
def test_prepare_markdown_for_separate_save_uses_normal_directory_permissions(
    tmp_path,
):
    asset_path = tmp_path / "temp-assets" / "page-1.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"png")
    output_path = tmp_path / "report.md"
    current_umask = os.umask(0)
    os.umask(current_umask)

    prepare_markdown_for_separate_save(
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

    asset_root_mode = stat.S_IMODE((tmp_path / "report_assets").stat().st_mode)
    assert asset_root_mode == 0o777 & ~current_umask


def test_prepare_markdown_for_separate_save_refuses_to_replace_unowned_assets(
    tmp_path,
):
    asset_path = tmp_path / "temp-assets" / "page-1.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"new-png")
    output_path = tmp_path / "report.md"
    unowned_asset_root = tmp_path / "report_assets"
    unowned_asset_root.mkdir()
    sentinel_path = unowned_asset_root / "user-file.txt"
    sentinel_path.write_text("keep me", encoding="utf-8")
    (unowned_asset_root / ".markitdowngui-assets.json").write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError, match="unowned asset directory"):
        prepare_markdown_for_separate_save(
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

    assert sentinel_path.read_text(encoding="utf-8") == "keep me"
    assert not (unowned_asset_root / "page-1.png").exists()


def test_prepare_markdown_for_separate_save_keeps_unowned_assets_when_no_assets(
    tmp_path,
):
    output_path = tmp_path / "report.md"
    unowned_asset_root = tmp_path / "report_assets"
    unowned_asset_root.mkdir()
    sentinel_path = unowned_asset_root / "user-file.txt"
    sentinel_path.write_text("keep me", encoding="utf-8")

    markdown = prepare_markdown_for_separate_save("# Report", [], output_path)

    assert markdown == "# Report"
    assert sentinel_path.read_text(encoding="utf-8") == "keep me"


def test_prepare_markdown_for_separate_save_replaces_only_app_owned_assets(tmp_path):
    first_asset = tmp_path / "temp-assets" / "page-1.png"
    second_asset = tmp_path / "temp-assets" / "page-2.png"
    first_asset.parent.mkdir(parents=True)
    first_asset.write_bytes(b"first")
    second_asset.write_bytes(b"second")
    output_path = tmp_path / "report.md"

    prepare_markdown_for_separate_save(
        "![page](C:/temp/run/report/page-1.png)",
        [
            _FakeAsset(
                filename="page-1.png",
                source_path=str(first_asset),
                preview_markdown_path="C:/temp/run/report/page-1.png",
            )
        ],
        output_path,
    )
    markdown = prepare_markdown_for_separate_save(
        "![page](C:/temp/run/report/page-2.png)",
        [
            _FakeAsset(
                filename="page-2.png",
                source_path=str(second_asset),
                preview_markdown_path="C:/temp/run/report/page-2.png",
            )
        ],
        output_path,
    )

    asset_root = tmp_path / "report_assets"
    assert "report_assets/page-2.png" in markdown
    assert not (asset_root / "page-1.png").exists()
    assert (asset_root / "page-2.png").read_bytes() == b"second"
    assert not list(tmp_path.glob(".report_assets.*.backup"))


def test_prepare_markdown_for_separate_save_reserves_the_ownership_marker_name(
    tmp_path,
):
    asset_path = tmp_path / "temp-assets" / ".markitdowngui-assets.json"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"asset")
    output_path = tmp_path / "report.md"

    markdown = prepare_markdown_for_separate_save(
        "[asset](C:/temp/run/report/manifest.json)",
        [
            _FakeAsset(
                filename=".markitdowngui-assets.json",
                source_path=str(asset_path),
                preview_markdown_path="C:/temp/run/report/manifest.json",
            )
        ],
        output_path,
    )

    asset_root = tmp_path / "report_assets"
    assert "report_assets/.markitdowngui-assets_1.json" in markdown
    assert (asset_root / ".markitdowngui-assets_1.json").read_bytes() == b"asset"
    assert (asset_root / ".markitdowngui-assets.json").is_file()


def test_prepare_markdown_for_separate_save_keeps_previous_owned_assets_on_copy_error(
    tmp_path,
):
    first_asset = tmp_path / "temp-assets" / "page-1.png"
    first_asset.parent.mkdir(parents=True)
    first_asset.write_bytes(b"first")
    output_path = tmp_path / "report.md"

    prepare_markdown_for_separate_save(
        "![page](C:/temp/run/report/page-1.png)",
        [
            _FakeAsset(
                filename="page-1.png",
                source_path=str(first_asset),
                preview_markdown_path="C:/temp/run/report/page-1.png",
            )
        ],
        output_path,
    )

    missing_asset = tmp_path / "temp-assets" / "missing.png"
    with pytest.raises(FileNotFoundError, match="Missing asset file"):
        prepare_markdown_for_separate_save(
            "![page](C:/temp/run/report/missing.png)",
            [
                _FakeAsset(
                    filename="missing.png",
                    source_path=str(missing_asset),
                    preview_markdown_path="C:/temp/run/report/missing.png",
                )
            ],
            output_path,
        )

    assert (tmp_path / "report_assets" / "page-1.png").read_bytes() == b"first"
    assert not list(tmp_path.glob(".report_assets.*.staging"))


def test_prepare_markdown_for_separate_save_removes_only_owned_assets_when_empty(
    tmp_path,
):
    asset_path = tmp_path / "temp-assets" / "page-1.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"first")
    output_path = tmp_path / "report.md"

    prepare_markdown_for_separate_save(
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

    markdown = prepare_markdown_for_separate_save("# Report", [], output_path)

    assert markdown == "# Report"
    assert not (tmp_path / "report_assets").exists()


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


def test_prepare_combined_markdown_for_save_refuses_to_replace_unowned_assets(
    tmp_path,
):
    asset_path = tmp_path / "temp-assets" / "page-1.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"new-png")
    output_path = tmp_path / "combined.md"
    unowned_asset_root = tmp_path / "combined_assets"
    unowned_asset_root.mkdir()
    sentinel_path = unowned_asset_root / "user-file.txt"
    sentinel_path.write_text("keep me", encoding="utf-8")

    with pytest.raises(FileExistsError, match="unowned asset directory"):
        prepare_combined_markdown_for_save(
            [
                MarkdownSaveInput(
                    source="C:/docs/report.pdf",
                    markdown="![page](C:/temp/run/report/page-1.png)",
                    assets=[
                        _FakeAsset(
                            filename="page-1.png",
                            source_path=str(asset_path),
                            preview_markdown_path="C:/temp/run/report/page-1.png",
                        )
                    ],
                )
            ],
            output_path,
            source_heading_template="Source: {source}",
        )

    assert sentinel_path.read_text(encoding="utf-8") == "keep me"


def test_temp_asset_root_creation_and_cleanup():
    asset_root = create_temp_asset_root()

    assert asset_root.is_dir()

    cleanup_temp_asset_root(asset_root)

    assert not asset_root.exists()
