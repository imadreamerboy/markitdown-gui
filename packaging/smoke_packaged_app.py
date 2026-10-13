"""Check GUI startup and optional native backends in a packaged executable."""

from __future__ import annotations

import argparse
import json
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


def run_smoke(executable: Path, startup_timeout: float, qt_platform: str = "offscreen") -> int:
    if not executable.is_file():
        print(f"Packaged executable not found: {executable}", file=sys.stderr)
        return 1

    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = qt_platform
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


def run_backend_checks(executable: Path, report_path: Path) -> int:
    """Require a fresh functional receipt from the actual frozen executable."""
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.unlink(missing_ok=True)
    try:
        result = subprocess.run(
            [str(executable), "--check-package", "--report", str(report_path)],
            cwd=executable.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
        )
        receipt = json.loads(report_path.read_text(encoding="utf-8"))
        expected = {"anydoc", "pdf_inspector", "pdfium", "glmocr"}
        checks = receipt.get("checks", {})
        if (
            result.returncode != 0
            or receipt.get("schema_version") != 1
            or receipt.get("status") != "passed"
            or receipt.get("frozen") is not True
            or set(checks) != expected
            or any(check.get("status") != "passed" for check in checks.values())
        ):
            print(f"Packaged backend check failed (exit {result.returncode}): {report_path}",
                  file=sys.stderr)
            print(json.dumps(receipt, indent=2), file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            return 1
    except (OSError, ValueError, TypeError, AttributeError, subprocess.TimeoutExpired) as error:
        print(f"Could not verify packaged backends: {error}", file=sys.stderr)
        return 1

    print(f"Packaged native backends passed: {report_path}")
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
    parser.add_argument("--executable", type=Path, help="installed or extracted executable to check")
    parser.add_argument("--check-backends", action="store_true",
                        help="also require the frozen executable's native backend receipt")
    parser.add_argument("--report", type=Path,
                        help="backend JSON receipt path (default: package-check-reports/dist-backends.json)")
    parser.add_argument("--qt-platform", default="offscreen",
                        help="Qt platform for GUI startup (use xcb under Xvfb on Linux)")
    args = parser.parse_args()
    if args.startup_timeout <= 0:
        parser.error("--startup-timeout must be greater than zero")

    root = Path(__file__).resolve().parents[1]
    executable = (args.executable or packaged_executable(root)).resolve()
    startup = run_smoke(executable, args.startup_timeout, args.qt_platform)
    if not args.check_backends:
        return startup
    report = args.report or root / "package-check-reports" / "dist-backends.json"
    backends = run_backend_checks(executable, report)
    return max(startup, backends)


if __name__ == "__main__":
    raise SystemExit(main())
