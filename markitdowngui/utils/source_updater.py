from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
import shutil
import shlex
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ProgressCallback = Callable[[str, int], None]
SOURCE_UPDATE_OK = 0
SOURCE_UPDATE_FAILED = 1
SOURCE_UPDATE_NOT_CHECKOUT = 2
SOURCE_UPDATE_DIRTY = 3


def _emit_progress(callback: ProgressCallback | None, status: str, progress: int) -> None:
    if callback is not None:
        callback(status, max(0, min(100, progress)))


def find_source_root(start: Path | None = None) -> Path | None:
    """Find the project checkout that can be updated in place."""
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for path in (current, *current.parents):
        if (path / ".git").exists() and (path / "pyproject.toml").is_file():
            return path
    return None


def quote_command_arg(value: str) -> str:
    if sys.platform == "win32":
        escaped = value.replace('"', r'\"')
        return f'"{escaped}"'
    return shlex.quote(value)


def build_source_update_command(
    source_root: Path | None = None,
    *,
    python_executable: str | None = None,
    uv_executable: str | None = None,
) -> str:
    """Update source and install the exported runtime pins in the active environment."""
    root = source_root or find_source_root()
    if root is None:
        return ""

    uv_path = uv_executable if uv_executable is not None else shutil.which("uv")
    command = [
        python_executable or sys.executable,
        "-m",
        "markitdowngui.utils.source_updater",
        "--source-root",
        str(root),
        "--uv-executable",
        uv_path or "",
    ]
    return " ".join(quote_command_arg(argument) for argument in command)


def _installed_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _migrate_legacy_qt(requirements: Path, uv_path: str | None) -> None:
    """Remove former full-Qt packages before installing the Essentials-only runtime."""
    pins = requirements.read_text(encoding="utf-8").lower().splitlines()
    essentials_pin = next(
        (line.partition("==")[2].split(";", 1)[0].strip()
         for line in pins if line.startswith("pyside6-essentials==")),
        None,
    )
    if essentials_pin is None:
        return
    if any(line.startswith("pyside6==") for line in pins):
        return

    legacy = [
        name
        for name in ("PySide6", "PySide6-Addons")
        if (installed := _installed_version(name)) is not None
        and installed != essentials_pin
    ]
    if not legacy:
        return
    # Older distributions share namespace files with Essentials. Remove Essentials
    # too so even an already-upgraded environment gets those files reinstalled.
    if _installed_version("PySide6-Essentials") is not None:
        legacy.append("PySide6-Essentials")
    print("Replacing former Qt distributions: " + ", ".join(legacy))
    if uv_path:
        command = [uv_path, "pip", "uninstall", "--python", sys.executable, *legacy]
    else:
        command = [sys.executable, "-m", "pip", "uninstall", "--yes", *legacy]
    subprocess.run(command, check=True)


def source_checkout_has_local_changes(source_root: Path) -> bool:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(source_root),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def run_source_update(
    source_root: Path | None = None,
    *,
    progress_callback: ProgressCallback | None = None,
    uv_executable: str | None = None,
) -> int:
    """Refresh the checkout and exact runtime pins without pruning unrelated packages."""
    root = source_root or find_source_root()
    if root is None:
        print("No Git source checkout found for this installation.", file=sys.stderr)
        return SOURCE_UPDATE_NOT_CHECKOUT

    try:
        _emit_progress(progress_callback, "Checking source checkout", 5)
        if source_checkout_has_local_changes(root):
            print(
                "Source checkout has local changes. Commit, stash, or discard them before updating.",
                file=sys.stderr,
            )
            return SOURCE_UPDATE_DIRTY

        requirements = root / "requirements.txt"
        if not requirements.is_file():
            print(
                f"Source update requires the exported runtime dependencies: {requirements}",
                file=sys.stderr,
            )
            return SOURCE_UPDATE_FAILED

        _emit_progress(progress_callback, "Pulling latest source", 15)
        subprocess.run(["git", "-C", str(root), "pull", "--ff-only"], check=True)

        _emit_progress(progress_callback, "Reinstalling app", 70)
        uv_path = uv_executable if uv_executable is not None else shutil.which("uv")
        _migrate_legacy_qt(requirements, uv_path)
        if uv_path:
            subprocess.run(
                [
                    uv_path,
                    "pip",
                    "install",
                    "--python",
                    sys.executable,
                    "--no-deps",
                    "-r",
                    str(requirements),
                    "-e",
                    str(root),
                ],
                check=True,
            )
        else:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "-r",
                    str(requirements),
                    "-e",
                    str(root),
                ],
                check=True,
            )
    except subprocess.CalledProcessError as exc:
        command = " ".join(str(part) for part in exc.cmd)
        print(f"Source update failed while running: {command}", file=sys.stderr)
        return exc.returncode or SOURCE_UPDATE_FAILED

    _emit_progress(progress_callback, "Source update complete", 100)
    print("Source update complete. Restart MarkItDown GUI.")
    return SOURCE_UPDATE_OK


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update this source checkout and its runtime dependencies."
    )
    parser.add_argument("--source-root", type=Path)
    parser.add_argument(
        "--uv-executable", help="uv executable; an empty value selects python -m pip"
    )
    args = parser.parse_args()
    return run_source_update(args.source_root, uv_executable=args.uv_executable)


if __name__ == "__main__":
    raise SystemExit(main())
