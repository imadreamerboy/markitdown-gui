import hashlib
import zipfile
from pathlib import Path

import pytest

from markitdowngui.utils import packaged_updater


def test_build_packaged_update_plan_supports_packaged_windows_zip():
    plan = packaged_updater.build_packaged_update_plan(
        {"name": "MarkItDown-Windows-2.0.0.zip", "url": "https://example.com/app.zip"},
        packaged=True,
        platform="win32",
    )

    assert plan.supported is True
    assert plan.mode == "zip"
    assert plan.label == "Install update"


def test_build_packaged_update_plan_keeps_source_builds_manual():
    plan = packaged_updater.build_packaged_update_plan(
        {"name": "MarkItDown-Windows-2.0.0.zip", "url": "https://example.com/app.zip"},
        packaged=False,
        platform="win32",
    )

    assert plan.supported is False
    assert plan.mode == "source"
    assert plan.label == "Download"


def test_build_packaged_update_plan_opens_macos_dmg_manually():
    plan = packaged_updater.build_packaged_update_plan(
        {"name": "MarkItDown-macOS-2.0.0.dmg", "url": "https://example.com/app.dmg"},
        packaged=True,
        platform="darwin",
    )

    assert plan.supported is False
    assert plan.mode == "dmg"
    assert plan.label == "Open DMG"


def test_verify_sha256_rejects_mismatched_download(tmp_path):
    archive = tmp_path / "app.zip"
    archive.write_bytes(b"not the expected archive")

    with pytest.raises(packaged_updater.PackagedUpdateError, match="checksum"):
        packaged_updater.verify_sha256(archive, "0" * 64)


def test_extract_zip_to_staging_returns_single_app_root(tmp_path):
    archive = tmp_path / "app.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("MarkItDown/MarkItDown.exe", "binary")
        zf.writestr("MarkItDown/_internal/runtime.txt", "runtime")

    root = packaged_updater.extract_zip_to_staging(
        archive,
        tmp_path / "extract",
        tmp_path / "replacement",
    )

    assert root.name == "MarkItDown"
    assert (root / "MarkItDown.exe").is_file()


def test_extract_zip_to_staging_rejects_path_traversal(tmp_path):
    archive = tmp_path / "app.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", "bad")

    with pytest.raises(packaged_updater.PackagedUpdateError, match="unsafe path"):
        packaged_updater.extract_zip_to_staging(
            archive,
            tmp_path / "extract",
            tmp_path / "replacement",
        )


def test_install_packaged_update_prepares_helper_without_replacing_app(
    monkeypatch,
    tmp_path,
):
    app_dir = tmp_path / "current" / "MarkItDown"
    app_dir.mkdir(parents=True)
    executable = app_dir / "MarkItDown.exe"
    executable.write_text("old", encoding="utf-8")
    archive = tmp_path / "MarkItDown-Windows-2.0.0.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("MarkItDown/MarkItDown.exe", "new")

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    launched: list[Path] = []
    monkeypatch.setattr(packaged_updater.sys, "platform", "win32")
    monkeypatch.setattr(packaged_updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        packaged_updater,
        "download_asset",
        lambda _url, target: target.write_bytes(archive.read_bytes()),
    )
    monkeypatch.setattr(
        packaged_updater,
        "launch_replace_helper",
        lambda helper_path: launched.append(helper_path),
    )

    helper = packaged_updater.install_packaged_update(
        {
            "name": archive.name,
            "url": "https://example.com/app.zip",
            "sha256": digest,
        },
        app_dir=app_dir,
        executable=str(executable),
        process_id=1234,
    )

    assert launched == [helper]
    script = helper.read_text(encoding="utf-8")
    assert str(app_dir) in script
    assert "MarkItDown.exe" in script


def test_install_packaged_update_cleans_temp_dir_on_prepare_failure(
    monkeypatch,
    tmp_path,
):
    app_dir = tmp_path / "current" / "MarkItDown"
    app_dir.mkdir(parents=True)
    executable = app_dir / "MarkItDown.exe"
    executable.write_text("old", encoding="utf-8")
    runtime_dir = tmp_path / "runtime"
    monkeypatch.setattr(packaged_updater.sys, "platform", "win32")
    monkeypatch.setattr(packaged_updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        packaged_updater.tempfile,
        "mkdtemp",
        lambda prefix: str(runtime_dir),
    )

    def write_bad_archive(_url, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("not a zip", encoding="utf-8")

    monkeypatch.setattr(packaged_updater, "download_asset", write_bad_archive)

    with pytest.raises(packaged_updater.PackagedUpdateError):
        packaged_updater.install_packaged_update(
            {
                "name": "MarkItDown-Windows-2.0.0.zip",
                "url": "https://example.com/app.zip",
            },
            app_dir=app_dir,
            executable=str(executable),
        )

    assert not runtime_dir.exists()
