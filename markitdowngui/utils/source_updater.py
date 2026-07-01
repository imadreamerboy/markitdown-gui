from __future__ import annotations

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
    root = source_root or find_source_root()
    if root is None:
        return ""

    root_arg = quote_command_arg(str(root))
    git_command = f"git -C {root_arg} pull --ff-only"

    uv_path = uv_executable if uv_executable is not None else shutil.which("uv")
    python_path = python_executable or sys.executable
    if uv_path:
        python_arg = quote_command_arg(python_path)
        install_command = (
            f"{quote_command_arg(uv_path)} pip install --python {python_arg} -e {root_arg}"
        )
    else:
        install_command = (
            f"{quote_command_arg(python_path)} -m pip install -e {root_arg}"
        )

    return f"{git_command} && {install_command}"


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
) -> int:
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

        _emit_progress(progress_callback, "Pulling latest source", 15)
        subprocess.run(["git", "-C", str(root), "pull", "--ff-only"], check=True)

        _emit_progress(progress_callback, "Reinstalling app", 70)
        uv_path = shutil.which("uv")
        if uv_path:
            subprocess.run(
                [
                    uv_path,
                    "pip",
                    "install",
                    "--python",
                    sys.executable,
                    "-e",
                    str(root),
                ],
                check=True,
            )
        else:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", str(root)],
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
    return run_source_update()


if __name__ == "__main__":
    raise SystemExit(main())
