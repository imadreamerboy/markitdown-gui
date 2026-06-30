from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass(frozen=True)
class PackagedUpdatePlan:
    supported: bool
    mode: str
    label: str
    reason: str = ""


class PackagedUpdateError(RuntimeError):
    """Raised when a packaged update cannot be prepared or started."""


ProgressCallback = Callable[[str, int], None]
PACKAGED_UPDATE_RESULT_FILE = "packaged-update-result.txt"
MAX_UPDATE_RESULT_CHARS = 4000


def _emit_progress(callback: ProgressCallback | None, status: str, progress: int) -> None:
    if callback is not None:
        callback(status, max(0, min(100, progress)))


def is_packaged_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def current_app_dir(executable: str | None = None) -> Path:
    return Path(executable or sys.executable).resolve().parent


def packaged_update_result_path(log_dir: Path | str | None = None) -> Path:
    root = Path(log_dir) if log_dir is not None else Path.home() / ".markitdown"
    return root / PACKAGED_UPDATE_RESULT_FILE


def read_packaged_update_result(path: Path | str | None = None) -> str:
    result_path = Path(path) if path is not None else packaged_update_result_path()
    try:
        text = result_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return text[:MAX_UPDATE_RESULT_CHARS]


def clear_packaged_update_result(path: Path | str | None = None) -> None:
    result_path = Path(path) if path is not None else packaged_update_result_path()
    try:
        result_path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def build_packaged_update_plan(
    asset: dict[str, object],
    *,
    packaged: bool | None = None,
    platform: str | None = None,
) -> PackagedUpdatePlan:
    name = str(asset.get("name") or "").strip()
    url = str(asset.get("url") or asset.get("browser_download_url") or "").strip()
    suffix = Path(name.lower()).suffix
    platform_name = (platform or sys.platform).lower()
    frozen = is_packaged_app() if packaged is None else packaged

    if not url:
        return PackagedUpdatePlan(False, "none", "Releases", "No release asset URL.")
    if not frozen:
        return PackagedUpdatePlan(
            False,
            "source",
            "Download",
            "Packaged install is available only in packaged builds.",
        )
    if platform_name == "darwin" and suffix == ".dmg":
        return PackagedUpdatePlan(
            True,
            "dmg",
            "Download DMG",
            "The app will download, verify, and open the DMG for manual installation.",
        )
    if platform_name.startswith(("win32", "cygwin")) and suffix == ".zip":
        return PackagedUpdatePlan(True, "zip", "Install update")
    if platform_name.startswith("linux") and suffix == ".zip":
        return PackagedUpdatePlan(True, "zip", "Install update")
    return PackagedUpdatePlan(
        False,
        "manual",
        "Download",
        f"Automatic install is not available for {name or 'this asset'}.",
    )


def install_packaged_update(
    asset: dict[str, object],
    *,
    app_dir: Path | None = None,
    executable: str | None = None,
    process_id: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> Path:
    plan = build_packaged_update_plan(asset)
    if not plan.supported:
        raise PackagedUpdateError(plan.reason or "Automatic install is not supported.")

    name = str(asset.get("name") or "").strip()
    url = str(asset.get("url") or asset.get("browser_download_url") or "").strip()
    sha256 = str(asset.get("sha256") or "").strip().lower()
    if not name or not url:
        raise PackagedUpdateError("Release asset is missing a name or download URL.")

    if plan.mode == "dmg":
        _emit_progress(progress_callback, "Downloading update", 5)
        return download_and_open_dmg(
            asset,
            progress_callback=progress_callback,
        )

    runtime_dir = Path(tempfile.mkdtemp(prefix="markitdown-update-"))
    archive_path = runtime_dir / name
    extract_dir = runtime_dir / "extract"
    staging_dir = runtime_dir / "replacement"
    target_dir = app_dir or current_app_dir(executable)
    target_executable = Path(executable or sys.executable).resolve()
    helper_path = runtime_dir / _helper_script_name()
    result_path = packaged_update_result_path()

    try:
        _emit_progress(progress_callback, "Downloading update", 5)
        download_asset(url, archive_path, progress_callback=progress_callback)
        _emit_progress(progress_callback, "Verifying update", 72)
        verify_sha256(archive_path, sha256)
        _emit_progress(progress_callback, "Extracting update", 84)
        replacement_root = extract_zip_to_staging(archive_path, extract_dir, staging_dir)
        replacement_executable = replacement_root / target_executable.name
        if not replacement_executable.exists():
            raise PackagedUpdateError(
                f"Update archive does not contain {target_executable.name}."
            )

        _emit_progress(progress_callback, "Preparing restart helper", 92)
        script = build_replace_helper_script(
            current_dir=target_dir,
            replacement_dir=replacement_root,
            executable_name=target_executable.name,
            process_id=process_id or os.getpid(),
            result_path=result_path,
        )
        helper_path.write_text(script, encoding="utf-8")
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            helper_path.chmod(0o755)
        _emit_progress(progress_callback, "Starting restart helper", 98)
        launch_replace_helper(helper_path)
    except Exception:
        shutil.rmtree(runtime_dir, ignore_errors=True)
        raise
    return helper_path


def download_and_open_dmg(
    asset: dict[str, object],
    *,
    downloads_dir: Path | None = None,
    progress_callback: ProgressCallback | None = None,
) -> Path:
    name = str(asset.get("name") or "").strip()
    url = str(asset.get("url") or asset.get("browser_download_url") or "").strip()
    sha256 = str(asset.get("sha256") or "").strip().lower()
    if not name or not url:
        raise PackagedUpdateError("Release asset is missing a name or download URL.")
    if Path(name.lower()).suffix != ".dmg":
        raise PackagedUpdateError("macOS manual install requires a DMG asset.")

    target = unique_download_path(
        (downloads_dir or default_downloads_dir()) / Path(name).name
    )
    try:
        download_asset(url, target, progress_callback=progress_callback)
        _emit_progress(progress_callback, "Verifying update", 72)
        verify_sha256(target, sha256)
        _emit_progress(progress_callback, "Opening DMG", 95)
        open_file(target)
    except Exception:
        try:
            target.unlink()
        except OSError:
            pass
        raise
    _emit_progress(progress_callback, "DMG opened", 100)
    return target


def default_downloads_dir() -> Path:
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        return downloads
    return Path(tempfile.gettempdir())


def unique_download_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 100):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}-{int(time.time())}{suffix}")


def download_asset(
    url: str,
    target: Path,
    *,
    timeout: int = 60,
    progress_callback: ProgressCallback | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            try:
                total = int(response.headers.get("content-length") or 0)
            except (TypeError, ValueError):
                total = 0
            downloaded = 0
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            progress = 5 + int((downloaded / total) * 65)
                            _emit_progress(
                                progress_callback,
                                "Downloading update",
                                progress,
                            )
    except requests.exceptions.RequestException as exc:
        raise PackagedUpdateError(f"Download failed: {exc}") from exc


def verify_sha256(path: Path, expected: str) -> None:
    if not expected:
        return
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if digest.lower() != expected.lower():
        raise PackagedUpdateError("Downloaded update checksum does not match.")


def extract_zip_to_staging(archive_path: Path, extract_dir: Path, staging_dir: Path) -> Path:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            _extract_zip_safely(archive, extract_dir)
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackagedUpdateError(f"Could not extract update archive: {exc}") from exc

    candidates = [path for path in extract_dir.iterdir() if path.name != "__MACOSX"]
    if len(candidates) == 1 and candidates[0].is_dir():
        replacement_root = candidates[0]
    else:
        staging_dir.mkdir(parents=True, exist_ok=True)
        for candidate in candidates:
            shutil.move(str(candidate), staging_dir / candidate.name)
        replacement_root = staging_dir

    if not any(replacement_root.iterdir()):
        raise PackagedUpdateError("Update archive is empty.")
    return replacement_root


def _extract_zip_safely(archive: zipfile.ZipFile, extract_dir: Path) -> None:
    extract_root = extract_dir.resolve()
    extract_root.mkdir(parents=True, exist_ok=True)
    for member in archive.infolist():
        target = (extract_root / member.filename).resolve()
        if target != extract_root and extract_root not in target.parents:
            raise PackagedUpdateError("Update archive contains an unsafe path.")
        archive.extract(member, extract_root)


def build_replace_helper_script(
    *,
    current_dir: Path,
    replacement_dir: Path,
    executable_name: str,
    process_id: int,
    result_path: Path | None = None,
) -> str:
    backup_dir = current_dir.with_name(
        f"{current_dir.name}.backup-{int(time.time())}"
    )
    result_path = result_path or packaged_update_result_path()
    if sys.platform.startswith("win32") or sys.platform == "cygwin":
        return _build_windows_helper(
            current_dir=current_dir,
            replacement_dir=replacement_dir,
            backup_dir=backup_dir,
            executable_name=executable_name,
            process_id=process_id,
            result_path=result_path,
        )
    return _build_posix_helper(
        current_dir=current_dir,
        replacement_dir=replacement_dir,
        backup_dir=backup_dir,
        executable_name=executable_name,
        process_id=process_id,
        result_path=result_path,
    )


def launch_replace_helper(helper_path: Path) -> None:
    if sys.platform.startswith("win32") or sys.platform == "cygwin":
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(helper_path),
            ],
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return
    subprocess.Popen([str(helper_path)], close_fds=True, start_new_session=True)


def open_file(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)], close_fds=True, start_new_session=True)
        return
    if sys.platform.startswith("win32") or sys.platform == "cygwin":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    subprocess.Popen(["xdg-open", str(path)], close_fds=True, start_new_session=True)


def _helper_script_name() -> str:
    if sys.platform.startswith("win32") or sys.platform == "cygwin":
        return "apply-update.ps1"
    return "apply-update.sh"


def _ps(value: Path | str) -> str:
    return str(value).replace("'", "''")


def _sh(value: Path | str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def _build_windows_helper(
    *,
    current_dir: Path,
    replacement_dir: Path,
    backup_dir: Path,
    executable_name: str,
    process_id: int,
    result_path: Path,
) -> str:
    return f"""$ErrorActionPreference = "Stop"
$pidToWait = {process_id}
$currentDir = '{_ps(current_dir)}'
$replacementDir = '{_ps(replacement_dir)}'
$backupDir = '{_ps(backup_dir)}'
$executableName = '{_ps(executable_name)}'
$resultPath = '{_ps(result_path)}'
$backupCreated = $false

function Write-UpdateResult([string]$status, [string]$message) {{
    try {{
        $resultDir = Split-Path -Parent $resultPath
        if ($resultDir) {{
            New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
        }}
        @"
Status: $status
Message: $message
Current app: $currentDir
Backup: $backupDir
Replacement: $replacementDir
Executable: $executableName
Time: $(Get-Date -Format o)
"@ | Set-Content -LiteralPath $resultPath -Encoding UTF8
    }} catch {{}}
}}

try {{
    Wait-Process -Id $pidToWait -Timeout 90 -ErrorAction SilentlyContinue
}} catch {{}}

try {{
    if (Test-Path -LiteralPath $backupDir) {{
        Remove-Item -LiteralPath $backupDir -Recurse -Force
    }}

    Move-Item -LiteralPath $currentDir -Destination $backupDir -Force
    $backupCreated = $true
    Move-Item -LiteralPath $replacementDir -Destination $currentDir -Force
    Write-UpdateResult "success" "Update installed and app restarted."
    Start-Process -FilePath (Join-Path $currentDir $executableName)
    Start-Sleep -Seconds 2
    Remove-Item -LiteralPath $backupDir -Recurse -Force -ErrorAction SilentlyContinue
}} catch {{
    if ($backupCreated -and (Test-Path -LiteralPath $currentDir)) {{
        Remove-Item -LiteralPath $currentDir -Recurse -Force -ErrorAction SilentlyContinue
    }}
    if ($backupCreated -and (Test-Path -LiteralPath $backupDir)) {{
        Move-Item -LiteralPath $backupDir -Destination $currentDir -Force
    }}
    Write-UpdateResult "failed" "Update failed and rollback was attempted: $($_.Exception.Message)"
    throw
}}
"""


def _build_posix_helper(
    *,
    current_dir: Path,
    replacement_dir: Path,
    backup_dir: Path,
    executable_name: str,
    process_id: int,
    result_path: Path,
) -> str:
    executable_path = current_dir / executable_name
    return f"""#!/bin/sh
set -eu
pid_to_wait={process_id}
current_dir={_sh(current_dir)}
replacement_dir={_sh(replacement_dir)}
backup_dir={_sh(backup_dir)}
executable_path={_sh(executable_path)}
result_path={_sh(result_path)}

write_update_result() {{
    status=$1
    message=$2
    result_dir=$(dirname "$result_path")
    mkdir -p "$result_dir" 2>/dev/null || true
    {{
        printf 'Status: %s\\n' "$status"
        printf 'Message: %s\\n' "$message"
        printf 'Current app: %s\\n' "$current_dir"
        printf 'Backup: %s\\n' "$backup_dir"
        printf 'Replacement: %s\\n' "$replacement_dir"
        printf 'Executable: %s\\n' "$executable_path"
        printf 'Time: %s\\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    }} > "$result_path" 2>/dev/null || true
}}

while kill -0 "$pid_to_wait" 2>/dev/null; do
    sleep 1
done

rm -rf "$backup_dir"
if ! mv "$current_dir" "$backup_dir"; then
    write_update_result "failed" "Could not move the current app to the backup path."
    exit 1
fi

if mv "$replacement_dir" "$current_dir"; then
    chmod +x "$executable_path" 2>/dev/null || true
    write_update_result "success" "Update installed and app restarted."
    nohup "$executable_path" >/dev/null 2>&1 &
    sleep 2
    rm -rf "$backup_dir"
else
    rm -rf "$current_dir"
    mv "$backup_dir" "$current_dir"
    write_update_result "failed" "Update failed and rollback was attempted."
    exit 1
fi
"""
