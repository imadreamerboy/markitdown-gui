"""Launch the platform artifact briefly to catch Qt/QML packaging failures."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time


def packaged_executable(repository_root: Path) -> Path:
    """Return the executable that the release workflow is going to package."""

    dist = repository_root / "dist"
    if sys.platform == "darwin":
        return dist / "MarkItDown.app" / "Contents" / "MacOS" / "MarkItDown"
    if os.name == "nt":
        return dist / "MarkItDown" / "MarkItDown.exe"
    return dist / "MarkItDown" / "MarkItDown"


def _terminate(process: subprocess.Popen[str]) -> None:
    """Stop a healthy GUI process and make a best effort to reap it."""

    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_smoke(executable: Path, startup_timeout: float) -> int:
    if not executable.is_file():
        print(f"Packaged executable not found: {executable}", file=sys.stderr)
        return 1

    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    try:
        process = subprocess.Popen(
            [str(executable)],
            cwd=executable.parent,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as error:
        print(f"Could not launch packaged executable {executable}: {error}", file=sys.stderr)
        return 1

    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            stdout, stderr = process.communicate()
            print(
                f"Packaged app exited during startup with code {return_code}: {executable}",
                file=sys.stderr,
            )
            if stdout:
                print("stdout:", file=sys.stderr)
                print(stdout, file=sys.stderr, end="")
            if stderr:
                print("stderr:", file=sys.stderr)
                print(stderr, file=sys.stderr, end="")
            return 1
        time.sleep(0.05)

    _terminate(process)
    stdout, stderr = process.communicate()
    if stdout or stderr:
        print("Packaged app startup output:")
        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, file=sys.stderr, end="")
    print(f"Packaged app survived {startup_timeout:.1f}s startup smoke: {executable}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch the platform-specific MarkItDown release artifact briefly."
    )
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=3.0,
        help="seconds the artifact must remain alive (default: 3)",
    )
    args = parser.parse_args()
    if args.startup_timeout <= 0:
        parser.error("--startup-timeout must be greater than zero")

    return run_smoke(packaged_executable(Path(__file__).resolve().parents[1]), args.startup_timeout)


if __name__ == "__main__":
    raise SystemExit(main())
