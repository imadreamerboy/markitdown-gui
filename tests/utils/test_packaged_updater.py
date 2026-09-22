import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from markitdowngui.utils import packaged_updater


VALID_SHA256 = "a" * 64


def test_build_packaged_update_plan_supports_packaged_windows_zip():
    plan = packaged_updater.build_packaged_update_plan(
        {
            "name": "MarkItDown-Windows-2.0.0.zip",
            "url": "https://example.com/app.zip",
            "sha256": VALID_SHA256,
        },
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
        {
            "name": "MarkItDown-macOS-2.0.0.dmg",
            "url": "https://example.com/app.dmg",
            "sha256": VALID_SHA256,
        },
        packaged=True,
        platform="darwin",
    )

    assert plan.supported is True
    assert plan.mode == "dmg"
    assert plan.label == "Download DMG"


@pytest.mark.parametrize(
    ("asset_name", "platform", "mode"),
    [
        ("MarkItDown-Windows-2.0.0.zip", "win32", "zip"),
        ("MarkItDown-Linux-2.0.0.zip", "linux", "zip"),
        ("MarkItDown-macOS-2.0.0.dmg", "darwin", "dmg"),
    ],
)
@pytest.mark.parametrize("sha256", [None, "", "abc123", "g" * 64, "a" * 65])
def test_build_packaged_update_plan_rejects_unverified_automatic_updates(
    asset_name,
    platform,
    mode,
    sha256,
):
    plan = packaged_updater.build_packaged_update_plan(
        {
            "name": asset_name,
            "url": f"https://example.com/{asset_name}",
            "sha256": sha256,
        },
        packaged=True,
        platform=platform,
    )

    assert plan.supported is False
    assert plan.mode == mode
    assert plan.label == "Download"
    assert "SHA256 checksum" in plan.reason


def test_build_packaged_update_plan_keeps_macos_source_builds_manual():
    plan = packaged_updater.build_packaged_update_plan(
        {"name": "MarkItDown-macOS-2.0.0.dmg", "url": "https://example.com/app.dmg"},
        packaged=False,
        platform="darwin",
    )

    assert plan.supported is False
    assert plan.mode == "source"
    assert plan.label == "Download"


@pytest.mark.parametrize(
    ("asset_name", "platform"),
    [
        ("MarkItDown-Windows-Setup-2.0.0.exe", "win32"),
        ("MarkItDown-Linux-2.0.0.AppImage", "linux"),
    ],
)
def test_build_packaged_update_plan_keeps_installer_assets_manual(
    asset_name,
    platform,
):
    plan = packaged_updater.build_packaged_update_plan(
        {"name": asset_name, "url": f"https://example.com/{asset_name}"},
        packaged=True,
        platform=platform,
    )

    assert plan.supported is False
    assert plan.mode == "manual"
    assert plan.label == "Download"


def test_verify_sha256_rejects_mismatched_download(tmp_path):
    archive = tmp_path / "app.zip"
    archive.write_bytes(b"not the expected archive")

    with pytest.raises(packaged_updater.PackagedUpdateError, match="checksum"):
        packaged_updater.verify_sha256(archive, "0" * 64)


@pytest.mark.parametrize(
    ("checksum", "message"),
    [
        (None, "missing a SHA256 checksum"),
        ("", "missing a SHA256 checksum"),
        ("abc123", "malformed"),
        ("g" * 64, "malformed"),
        ("a" * 65, "malformed"),
    ],
)
def test_verify_sha256_rejects_missing_or_malformed_checksum(
    tmp_path,
    checksum,
    message,
):
    archive = tmp_path / "app.zip"
    archive.write_bytes(b"archive")

    with pytest.raises(packaged_updater.PackagedUpdateError, match=message):
        packaged_updater.verify_sha256(archive, checksum)


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


def test_packaged_update_result_read_and_clear(tmp_path):
    result_path = tmp_path / "packaged-update-result.txt"
    result_path.write_text("Status: failed\nBackup: C:/App.backup\n", encoding="utf-8")

    assert packaged_updater.read_packaged_update_result(result_path) == (
        "Status: failed\nBackup: C:/App.backup"
    )

    packaged_updater.clear_packaged_update_result(result_path)

    assert packaged_updater.read_packaged_update_result(result_path) == ""


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
    result_path = tmp_path / "update-result.txt"
    launched: list[Path] = []
    monkeypatch.setattr(packaged_updater.sys, "platform", "win32")
    monkeypatch.setattr(packaged_updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        packaged_updater,
        "packaged_update_result_path",
        lambda: result_path,
    )
    monkeypatch.setattr(
        packaged_updater,
        "download_asset",
        lambda _url, target, **_kwargs: target.write_bytes(archive.read_bytes()),
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
    assert str(result_path) in script
    assert "Write-UpdateResult" in script
    assert "Backup: $backupDir" in script
    assert "$backupCreated = $false" in script
    assert "$backupCreated = $true" in script
    assert "$waitTimeoutSeconds = 90" in script
    assert "Remove-UpdateRuntime" in script
    assert "if ($backupCreated)" in script
    assert "if (Test-Path -LiteralPath $currentDir)" in script
    assert "$replacementProcess = Start-Process" in script
    assert "-PassThru" in script
    assert ".WaitForExit(2000)" in script
    assert "Write-UpdateResult \"success\"" in script
    assert script.index(".WaitForExit(2000)") < script.index(
        'Write-UpdateResult "success"'
    )
    assert "$failedReplacementRemoved = -not" in script
    assert "if (-not $failedReplacementRemoved)" in script
    assert "} elseif (Test-Path -LiteralPath $backupDir)" in script
    assert script.index("$failedReplacementRemoved = -not") < script.index(
        "Move-Item -LiteralPath $backupDir -Destination $currentDir"
    )


@pytest.mark.parametrize(
    ("checksum", "message"),
    [
        (None, "missing a SHA256 checksum"),
        ("abc123", "malformed"),
    ],
)
def test_install_packaged_update_rejects_unverified_asset_before_download(
    monkeypatch,
    checksum,
    message,
):
    downloaded = []
    monkeypatch.setattr(packaged_updater.sys, "platform", "win32")
    monkeypatch.setattr(packaged_updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        packaged_updater,
        "download_asset",
        lambda *_args, **_kwargs: downloaded.append(True),
    )

    with pytest.raises(packaged_updater.PackagedUpdateError, match=message):
        packaged_updater.install_packaged_update(
            {
                "name": "MarkItDown-Windows-2.0.0.zip",
                "url": "https://example.com/app.zip",
                "sha256": checksum,
            }
        )

    assert downloaded == []


def test_build_posix_replace_helper_writes_update_result(monkeypatch, tmp_path):
    monkeypatch.setattr(packaged_updater.sys, "platform", "linux")

    script = packaged_updater.build_replace_helper_script(
        current_dir=tmp_path / "MarkItDown",
        replacement_dir=tmp_path / "replacement",
        executable_name="MarkItDown",
        process_id=1234,
        result_path=tmp_path / "update-result.txt",
    )

    assert "write_update_result" in script
    assert "Status: %s\\n" in script
    assert str(tmp_path / "update-result.txt") in script
    assert "wait_timeout_seconds=90" in script
    assert "trap cleanup_update_runtime EXIT" in script
    assert "replacement_status=$?" in script
    assert "Replacement app exited during startup with code" in script
    assert script.index("kill -0") < script.index('write_update_result "success"')


@pytest.mark.skipif(os.name == "nt", reason="POSIX helper execution test")
def test_posix_replace_helper_times_out_before_replacing_and_cleans_runtime(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(packaged_updater.sys, "platform", "linux")

    current_dir = tmp_path / "current" / "MarkItDown"
    current_dir.mkdir(parents=True)
    (current_dir / "old.txt").write_text("old", encoding="utf-8")
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    replacement_dir = runtime_dir / "replacement"
    replacement_dir.mkdir()
    result_path = tmp_path / "update-result.txt"
    helper_path = runtime_dir / "apply-update.sh"
    helper_path.write_text(
        packaged_updater.build_replace_helper_script(
            current_dir=current_dir,
            replacement_dir=replacement_dir,
            executable_name="MarkItDown",
            process_id=0,
            result_path=result_path,
            cleanup_dir=runtime_dir,
            wait_timeout_seconds=1,
        ),
        encoding="utf-8",
    )
    helper_path.chmod(0o755)

    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
    helper_path.write_text(
        helper_path.read_text(encoding="utf-8").replace(
            "pid_to_wait=0",
            f"pid_to_wait={sleeper.pid}",
        ),
        encoding="utf-8",
    )
    helper_path.chmod(0o755)

    try:
        completed = subprocess.run(
            [str(helper_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    finally:
        sleeper.terminate()
        sleeper.wait(timeout=5)

    assert completed.returncode == 1
    assert current_dir.exists()
    assert (current_dir / "old.txt").read_text(encoding="utf-8") == "old"
    assert "Status: failed" in result_path.read_text(encoding="utf-8")
    assert "Timed out waiting" in result_path.read_text(encoding="utf-8")
    assert not runtime_dir.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX helper execution test")
def test_posix_replace_helper_rolls_back_when_replacement_exits_nonzero(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(packaged_updater.sys, "platform", "linux")

    current_dir = tmp_path / "current" / "MarkItDown"
    current_dir.mkdir(parents=True)
    (current_dir / "MarkItDown").write_text("old", encoding="utf-8")
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    replacement_dir = runtime_dir / "replacement"
    replacement_dir.mkdir()
    replacement_executable = replacement_dir / "MarkItDown"
    replacement_executable.write_text("#!/bin/sh\nexit 42\n", encoding="utf-8")
    replacement_executable.chmod(0o755)
    result_path = tmp_path / "update-result.txt"
    helper_path = runtime_dir / "apply-update.sh"

    exited_process = subprocess.Popen([sys.executable, "-c", "pass"])
    exited_process.wait(timeout=5)
    helper_path.write_text(
        packaged_updater.build_replace_helper_script(
            current_dir=current_dir,
            replacement_dir=replacement_dir,
            executable_name="MarkItDown",
            process_id=exited_process.pid,
            result_path=result_path,
            cleanup_dir=runtime_dir,
            wait_timeout_seconds=1,
        ),
        encoding="utf-8",
    )
    helper_path.chmod(0o755)

    completed = subprocess.run(
        [str(helper_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.returncode == 1
    assert (current_dir / "MarkItDown").read_text(encoding="utf-8") == "old"
    result = result_path.read_text(encoding="utf-8")
    assert "Status: failed" in result
    assert "exited during startup with code 42" in result
    assert "Previous version restored" in result
    assert not runtime_dir.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX helper execution test")
def test_posix_replace_helper_rolls_back_when_replacement_cannot_launch(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(packaged_updater.sys, "platform", "linux")

    current_dir = tmp_path / "current" / "MarkItDown"
    current_dir.mkdir(parents=True)
    (current_dir / "MarkItDown").write_text("old", encoding="utf-8")
    replacement_dir = tmp_path / "replacement"
    replacement_dir.mkdir()
    (replacement_dir / "MarkItDown").mkdir()
    result_path = tmp_path / "update-result.txt"
    helper_path = tmp_path / "apply-update.sh"

    exited_process = subprocess.Popen([sys.executable, "-c", "pass"])
    exited_process.wait(timeout=5)
    helper_path.write_text(
        packaged_updater.build_replace_helper_script(
            current_dir=current_dir,
            replacement_dir=replacement_dir,
            executable_name="MarkItDown",
            process_id=exited_process.pid,
            result_path=result_path,
            wait_timeout_seconds=1,
        ),
        encoding="utf-8",
    )
    helper_path.chmod(0o755)

    completed = subprocess.run(
        [str(helper_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.returncode == 1
    assert (current_dir / "MarkItDown").read_text(encoding="utf-8") == "old"
    result = result_path.read_text(encoding="utf-8")
    assert "Status: failed" in result
    assert "exited during startup" in result
    assert "Previous version restored" in result


@pytest.mark.skipif(os.name == "nt", reason="POSIX helper execution test")
def test_posix_replace_helper_keeps_healthy_replacement_and_removes_backup(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(packaged_updater.sys, "platform", "linux")

    current_dir = tmp_path / "current" / "MarkItDown"
    current_dir.mkdir(parents=True)
    (current_dir / "MarkItDown").write_text("old", encoding="utf-8")
    replacement_dir = tmp_path / "replacement"
    replacement_dir.mkdir()
    replacement_executable = replacement_dir / "MarkItDown"
    pid_path = tmp_path / "replacement.pid"
    replacement_contents = (
        f"#!{sys.executable}\n"
        "import os\n"
        "import signal\n"
        "from pathlib import Path\n"
        f"Path({str(pid_path)!r}).write_text(str(os.getpid()), encoding='utf-8')\n"
        "signal.pause()\n"
    )
    replacement_executable.write_text(replacement_contents, encoding="utf-8")
    replacement_executable.chmod(0o755)
    result_path = tmp_path / "update-result.txt"
    helper_path = tmp_path / "apply-update.sh"

    exited_process = subprocess.Popen([sys.executable, "-c", "pass"])
    exited_process.wait(timeout=5)
    helper_path.write_text(
        packaged_updater.build_replace_helper_script(
            current_dir=current_dir,
            replacement_dir=replacement_dir,
            executable_name="MarkItDown",
            process_id=exited_process.pid,
            result_path=result_path,
            wait_timeout_seconds=1,
        ),
        encoding="utf-8",
    )
    helper_path.chmod(0o755)

    completed = subprocess.run(
        [str(helper_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.returncode == 0
    assert pid_path.is_file()
    replacement_pid = int(pid_path.read_text(encoding="utf-8"))
    try:
        assert "Status: success" in result_path.read_text(encoding="utf-8")
        assert "startup check" in result_path.read_text(encoding="utf-8")
        assert (current_dir / "MarkItDown").read_text(encoding="utf-8") == replacement_contents
        assert not list(current_dir.parent.glob("MarkItDown.backup-*"))
    finally:
        os.kill(replacement_pid, 15)


@pytest.mark.skipif(os.name == "nt", reason="POSIX helper execution test")
def test_posix_replace_helper_restores_old_app_when_replacement_move_fails(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(packaged_updater.sys, "platform", "linux")

    current_dir = tmp_path / "current" / "MarkItDown"
    current_dir.mkdir(parents=True)
    (current_dir / "MarkItDown").write_text("old", encoding="utf-8")
    missing_replacement = tmp_path / "missing-replacement"
    result_path = tmp_path / "update-result.txt"
    helper_path = tmp_path / "apply-update.sh"

    exited_process = subprocess.Popen([sys.executable, "-c", "pass"])
    exited_process.wait(timeout=5)
    helper_path.write_text(
        packaged_updater.build_replace_helper_script(
            current_dir=current_dir,
            replacement_dir=missing_replacement,
            executable_name="MarkItDown",
            process_id=exited_process.pid,
            result_path=result_path,
            wait_timeout_seconds=1,
        ),
        encoding="utf-8",
    )
    helper_path.chmod(0o755)

    completed = subprocess.run(
        [str(helper_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.returncode == 1
    assert (current_dir / "MarkItDown").read_text(encoding="utf-8") == "old"
    result = result_path.read_text(encoding="utf-8")
    assert "Status: failed" in result
    assert "Could not move the replacement app into place" in result
    assert "Previous version restored" in result


_POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


@pytest.mark.skipif(_POWERSHELL is None, reason="PowerShell is not installed")
def test_windows_replace_helper_rolls_back_after_immediate_startup_exit(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(packaged_updater.sys, "platform", "win32")

    current_dir = tmp_path / "current" / "MarkItDown"
    current_dir.mkdir(parents=True)
    replacement_dir = tmp_path / "replacement"
    replacement_dir.mkdir()
    if os.name == "nt":
        executable_name = "MarkItDown.cmd"
        replacement_contents = "@echo off\r\nexit /b 42\r\n"
    else:
        executable_name = "MarkItDown.exe"
        replacement_contents = "#!/bin/sh\nexit 42\n"
    (current_dir / executable_name).write_text("old", encoding="utf-8")
    replacement_executable = replacement_dir / executable_name
    replacement_executable.write_text(replacement_contents, encoding="utf-8")
    replacement_executable.chmod(0o755)
    result_path = tmp_path / "update-result.txt"
    helper_path = tmp_path / "apply-update.ps1"

    exited_process = subprocess.Popen([sys.executable, "-c", "pass"])
    exited_process.wait(timeout=5)
    helper_path.write_text(
        packaged_updater.build_replace_helper_script(
            current_dir=current_dir,
            replacement_dir=replacement_dir,
            executable_name=executable_name,
            process_id=exited_process.pid,
            result_path=result_path,
            wait_timeout_seconds=1,
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            str(_POWERSHELL),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(helper_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode != 0
    assert (current_dir / executable_name).read_text(encoding="utf-8") == "old"
    result = result_path.read_text(encoding="utf-8")
    assert "Status: failed" in result
    assert "exited during startup with code 42" in result
    assert "previous version was restored" in result


def test_install_packaged_update_reports_progress(monkeypatch, tmp_path):
    app_dir = tmp_path / "current" / "MarkItDown"
    app_dir.mkdir(parents=True)
    executable = app_dir / "MarkItDown.exe"
    executable.write_text("old", encoding="utf-8")
    archive = tmp_path / "MarkItDown-Windows-2.0.0.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("MarkItDown/MarkItDown.exe", "new")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()

    progress: list[tuple[str, int]] = []
    monkeypatch.setattr(packaged_updater.sys, "platform", "win32")
    monkeypatch.setattr(packaged_updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        packaged_updater,
        "download_asset",
        lambda _url, target, **_kwargs: target.write_bytes(archive.read_bytes()),
    )
    monkeypatch.setattr(packaged_updater, "launch_replace_helper", lambda _helper: None)

    packaged_updater.install_packaged_update(
        {
            "name": archive.name,
            "url": "https://example.com/app.zip",
            "sha256": digest,
        },
        app_dir=app_dir,
        executable=str(executable),
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert progress == [
        ("Downloading update", 5),
        ("Verifying update", 72),
        ("Extracting update", 84),
        ("Preparing restart helper", 92),
        ("Starting restart helper", 98),
    ]


def test_install_packaged_update_can_prepare_without_starting_helper(
    monkeypatch, tmp_path
):
    app_dir = tmp_path / "current" / "MarkItDown"
    app_dir.mkdir(parents=True)
    executable = app_dir / "MarkItDown.exe"
    executable.write_text("old", encoding="utf-8")
    archive = tmp_path / "MarkItDown-Windows-2.0.0.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("MarkItDown/MarkItDown.exe", "new")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()

    progress: list[tuple[str, int]] = []
    launched: list[Path] = []
    monkeypatch.setattr(packaged_updater.sys, "platform", "win32")
    monkeypatch.setattr(packaged_updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        packaged_updater,
        "download_asset",
        lambda _url, target, **_kwargs: target.write_bytes(archive.read_bytes()),
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
        launch_helper=False,
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert helper.is_file()
    assert launched == []
    assert progress == [
        ("Downloading update", 5),
        ("Verifying update", 72),
        ("Extracting update", 84),
        ("Preparing restart helper", 92),
    ]

    packaged_updater.cleanup_prepared_update(helper)
    assert not helper.parent.exists()


def test_install_packaged_update_downloads_and_opens_macos_dmg(monkeypatch, tmp_path):
    dmg = tmp_path / "MarkItDown-macOS-2.0.0.dmg"
    dmg.write_bytes(b"disk image")
    digest = hashlib.sha256(dmg.read_bytes()).hexdigest()
    opened: list[Path] = []
    progress: list[tuple[str, int]] = []
    downloads_dir = tmp_path / "Downloads"
    monkeypatch.setattr(packaged_updater.sys, "platform", "darwin")
    monkeypatch.setattr(packaged_updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(packaged_updater, "default_downloads_dir", lambda: downloads_dir)

    def write_dmg(_url, target, **_kwargs):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(dmg.read_bytes())

    monkeypatch.setattr(
        packaged_updater,
        "download_asset",
        write_dmg,
    )
    monkeypatch.setattr(packaged_updater, "open_file", lambda path: opened.append(path))

    path = packaged_updater.install_packaged_update(
        {
            "name": dmg.name,
            "url": "https://example.com/app.dmg",
            "sha256": digest,
        },
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert path == downloads_dir / dmg.name
    assert path.read_bytes() == b"disk image"
    assert opened == [path]
    assert progress == [
        ("Downloading update", 5),
        ("Verifying update", 72),
        ("Opening DMG", 95),
        ("DMG opened", 100),
    ]


def test_download_and_open_dmg_uses_unique_filename(monkeypatch, tmp_path):
    existing = tmp_path / "MarkItDown.dmg"
    existing.write_bytes(b"old")
    opened: list[Path] = []
    monkeypatch.setattr(
        packaged_updater,
        "download_asset",
        lambda _url, target, **_kwargs: target.write_bytes(b"new"),
    )
    monkeypatch.setattr(packaged_updater, "open_file", lambda path: opened.append(path))

    path = packaged_updater.download_and_open_dmg(
        {
            "name": existing.name,
            "url": "https://example.com/app.dmg",
            "sha256": hashlib.sha256(b"new").hexdigest(),
        },
        downloads_dir=tmp_path,
    )

    assert path == tmp_path / "MarkItDown-1.dmg"
    assert existing.read_bytes() == b"old"
    assert path.read_bytes() == b"new"
    assert opened == [path]


@pytest.mark.parametrize(
    ("checksum", "message"),
    [
        (None, "missing a SHA256 checksum"),
        ("abc123", "malformed"),
    ],
)
def test_download_and_open_dmg_rejects_unverified_asset_before_download(
    monkeypatch,
    tmp_path,
    checksum,
    message,
):
    downloaded = []
    monkeypatch.setattr(
        packaged_updater,
        "download_asset",
        lambda *_args, **_kwargs: downloaded.append(True),
    )

    with pytest.raises(packaged_updater.PackagedUpdateError, match=message):
        packaged_updater.download_and_open_dmg(
            {
                "name": "MarkItDown-macOS-2.0.0.dmg",
                "url": "https://example.com/app.dmg",
                "sha256": checksum,
            },
            downloads_dir=tmp_path,
        )

    assert downloaded == []


def test_download_asset_reports_content_length_progress(monkeypatch, tmp_path):
    class FakeResponse:
        headers = {"content-length": "4"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"aa"
            yield b"bb"

    progress: list[tuple[str, int]] = []
    monkeypatch.setattr(
        packaged_updater.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    target = tmp_path / "app.zip"
    packaged_updater.download_asset(
        "https://example.com/app.zip",
        target,
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert target.read_bytes() == b"aabb"
    assert progress == [("Downloading update", 37), ("Downloading update", 70)]


def test_download_asset_ignores_invalid_content_length(monkeypatch, tmp_path):
    class FakeResponse:
        headers = {"content-length": "unknown"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"data"

    progress: list[tuple[str, int]] = []
    monkeypatch.setattr(
        packaged_updater.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    target = tmp_path / "app.zip"
    packaged_updater.download_asset(
        "https://example.com/app.zip",
        target,
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert target.read_bytes() == b"data"
    assert progress == []


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

    def write_bad_archive(_url, target, **_kwargs):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("not a zip", encoding="utf-8")

    monkeypatch.setattr(packaged_updater, "download_asset", write_bad_archive)

    with pytest.raises(packaged_updater.PackagedUpdateError):
        packaged_updater.install_packaged_update(
            {
                "name": "MarkItDown-Windows-2.0.0.zip",
                "url": "https://example.com/app.zip",
                "sha256": hashlib.sha256(b"not a zip").hexdigest(),
            },
            app_dir=app_dir,
            executable=str(executable),
        )

    assert not runtime_dir.exists()
