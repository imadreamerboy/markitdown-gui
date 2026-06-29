from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
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


def is_packaged_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def current_app_dir(executable: str | None = None) -> Path:
    return Path(executable or sys.executable).resolve().parent


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
    if platform_name == "darwin" and suffix == ".dmg":
        return PackagedUpdatePlan(
            False,
            "dmg",
            "Open DMG",
            "macOS DMG updates are installed outside the running app.",
        )
    if not frozen:
        return PackagedUpdatePlan(
            False,
            "source",
            "Download",
            "Packaged install is available only in packaged builds.",
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
) -> Path:
    plan = build_packaged_update_plan(asset)
    if not plan.supported:
        raise PackagedUpdateError(plan.reason or "Automatic install is not supported.")

    name = str(asset.get("name") or "").strip()
    url = str(asset.get("url") or asset.get("browser_download_url") or "").strip()
    sha256 = str(asset.get("sha256") or "").strip().lower()
    if not name or not url:
        raise PackagedUpdateError("Release asset is missing a name or download URL.")

    runtime_dir = Path(tempfile.mkdtemp(prefix="markitdown-update-"))
    archive_path = runtime_dir / name
    extract_dir = runtime_dir / "extract"
    staging_dir = runtime_dir / "replacement"
    target_dir = app_dir or current_app_dir(executable)
    target_executable = Path(executable or sys.executable).resolve()
    helper_path = runtime_dir / _helper_script_name()

    try:
        download_asset(url, archive_path)
        verify_sha256(archive_path, sha256)
        replacement_root = extract_zip_to_staging(archive_path, extract_dir, staging_dir)
        replacement_executable = replacement_root / target_executable.name
        if not replacement_executable.exists():
            raise PackagedUpdateError(
                f"Update archive does not contain {target_executable.name}."
            )

        script = build_replace_helper_script(
            current_dir=target_dir,
            replacement_dir=replacement_root,
            executable_name=target_executable.name,
            process_id=process_id or os.getpid(),
        )
        helper_path.write_text(script, encoding="utf-8")
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            helper_path.chmod(0o755)
        launch_replace_helper(helper_path)
    except Exception:
        shutil.rmtree(runtime_dir, ignore_errors=True)
        raise
    return helper_path


def download_asset(url: str, target: Path, *, timeout: int = 60) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
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
) -> str:
    backup_dir = current_dir.with_name(
        f"{current_dir.name}.backup-{int(time.time())}"
    )
    if sys.platform.startswith("win32") or sys.platform == "cygwin":
        return _build_windows_helper(
            current_dir=current_dir,
            replacement_dir=replacement_dir,
            backup_dir=backup_dir,
            executable_name=executable_name,
            process_id=process_id,
        )
    return _build_posix_helper(
        current_dir=current_dir,
        replacement_dir=replacement_dir,
        backup_dir=backup_dir,
        executable_name=executable_name,
        process_id=process_id,
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
) -> str:
    return f"""$ErrorActionPreference = "Stop"
$pidToWait = {process_id}
$currentDir = '{_ps(current_dir)}'
$replacementDir = '{_ps(replacement_dir)}'
$backupDir = '{_ps(backup_dir)}'
$executableName = '{_ps(executable_name)}'

try {{
    Wait-Process -Id $pidToWait -Timeout 90 -ErrorAction SilentlyContinue
}} catch {{}}

if (Test-Path -LiteralPath $backupDir) {{
    Remove-Item -LiteralPath $backupDir -Recurse -Force
}}

Move-Item -LiteralPath $currentDir -Destination $backupDir -Force
try {{
    Move-Item -LiteralPath $replacementDir -Destination $currentDir -Force
    Start-Process -FilePath (Join-Path $currentDir $executableName)
    Start-Sleep -Seconds 2
    Remove-Item -LiteralPath $backupDir -Recurse -Force -ErrorAction SilentlyContinue
}} catch {{
    if (Test-Path -LiteralPath $currentDir) {{
        Remove-Item -LiteralPath $currentDir -Recurse -Force -ErrorAction SilentlyContinue
    }}
    if (Test-Path -LiteralPath $backupDir) {{
        Move-Item -LiteralPath $backupDir -Destination $currentDir -Force
    }}
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
) -> str:
    executable_path = current_dir / executable_name
    return f"""#!/bin/sh
set -eu
pid_to_wait={process_id}
current_dir={_sh(current_dir)}
replacement_dir={_sh(replacement_dir)}
backup_dir={_sh(backup_dir)}
executable_path={_sh(executable_path)}

while kill -0 "$pid_to_wait" 2>/dev/null; do
    sleep 1
done

rm -rf "$backup_dir"
mv "$current_dir" "$backup_dir"
if mv "$replacement_dir" "$current_dir"; then
    chmod +x "$executable_path" 2>/dev/null || true
    nohup "$executable_path" >/dev/null 2>&1 &
    sleep 2
    rm -rf "$backup_dir"
else
    rm -rf "$current_dir"
    mv "$backup_dir" "$current_dir"
    exit 1
fi
"""
