import importlib
import json
import subprocess
import sys
import types

import pytest

from markitdowngui import package_check


def test_real_native_package_checks_write_receipt_and_clean_fixture(tmp_path, monkeypatch):
    temporary_directory = package_check.tempfile.TemporaryDirectory
    monkeypatch.setattr(package_check.tempfile, "TemporaryDirectory",
                        lambda **kwargs: temporary_directory(dir=tmp_path, **kwargs))
    report_path = tmp_path / "receipt.json"

    assert package_check.run_package_checks(report_path) == 0

    report = json.loads(report_path.read_text())
    assert report["schema_version"] == 1
    assert report["status"] == "passed"
    assert report["phase"] == "complete"
    assert report["elapsed_seconds"] >= report["fixture_seconds"] >= 0
    assert set(report["checks"]) == set(package_check.BACKENDS)
    assert all(check["status"] == "passed" for check in report["checks"].values())
    assert all(check["duration_seconds"] >= 0 for check in report["checks"].values())
    assert report["checks"]["glmocr"]["pdf_payload_verified"] is True
    assert report["checks"]["glmocr"]["localhost_requests"] == 1
    assert list(tmp_path.iterdir()) == [report_path]


def test_failure_receipt_has_traceback_without_console(tmp_path, monkeypatch):
    temporary_directory = package_check.tempfile.TemporaryDirectory
    monkeypatch.setattr(package_check.tempfile, "TemporaryDirectory",
                        lambda **kwargs: temporary_directory(dir=tmp_path, **kwargs))
    monkeypatch.setattr(package_check.sys, "stderr", None)

    def fail(_path):
        progress = json.loads((tmp_path / "receipt.json").read_text())
        assert progress["status"] == "running"
        assert progress["phase"] == "pdf_inspector"
        assert progress["checks"]["anydoc"]["status"] == "passed"
        raise RuntimeError("native inspector unavailable")

    monkeypatch.setattr(package_check, "_check_pdf_inspector", fail)
    report_path = tmp_path / "receipt.json"

    assert package_check.run_package_checks(report_path) == 1

    report = json.loads(report_path.read_text())
    assert report["status"] == "failed"
    assert report["phase"] == "pdf_inspector"
    assert report["checks"]["anydoc"]["status"] == "passed"
    assert report["checks"]["pdf_inspector"]["status"] == "failed"
    assert "RuntimeError: native inspector unavailable" in report["traceback"]
    assert "glmocr" not in report["checks"]
    assert list(tmp_path.iterdir()) == [report_path]


def test_real_checks_with_no_standard_streams(tmp_path):
    report_path = tmp_path / "windowed.json"
    stack_path = tmp_path / "windowed-stacks.log"
    # Match the frozen backend harness's bounded budget. Keep a file-backed
    # stack dump so a slow native import remains diagnosable without a console.
    program = """
import faulthandler
from pathlib import Path
import sys

with open(sys.argv[2], "w", encoding="utf-8") as trace:
    faulthandler.enable(file=trace)
    faulthandler.dump_traceback_later(25, repeat=True, file=trace)
    sys.stdout = None
    sys.stderr = None
    try:
        from markitdowngui.package_check import run_package_checks
        result = run_package_checks(Path(sys.argv[1]))
    finally:
        faulthandler.cancel_dump_traceback_later()
        faulthandler.disable()
sys.exit(result)
"""
    try:
        process = subprocess.run(
            [sys.executable, "-c", program, str(report_path), str(stack_path)],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except subprocess.TimeoutExpired:
        diagnostics = [f"{path.name}:\n{path.read_text()[-20000:]}"
                       for path in (report_path, stack_path) if path.is_file()]
        pytest.fail("Package checks exceeded 60s.\n" + "\n".join(diagnostics), pytrace=False)

    assert process.returncode == 0, (
        process.stderr, report_path.read_text() if report_path.is_file() else "No receipt",
        stack_path.read_text(),
    )
    assert json.loads(report_path.read_text())["status"] == "passed"


def test_unwritable_report_returns_nonzero_without_console(tmp_path, monkeypatch):
    parent = tmp_path / "file"
    parent.write_text("not a directory")
    monkeypatch.setattr(package_check.sys, "stderr", None)
    monkeypatch.setattr(package_check, "_create_pdf", lambda _path: None)
    for name in package_check.BACKENDS:
        monkeypatch.setattr(package_check, f"_check_{name}", lambda _path: {})

    assert package_check.run_package_checks(parent / "receipt.json") == 1


def test_package_cli_dispatches_without_importing_gui(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "markitdowngui.ui_qml.app", None)
    entrypoint = importlib.import_module("markitdowngui.main")
    monkeypatch.setattr(sys, "argv", ["MarkItDown", "--check-package", "--report", str(tmp_path / "r.json")])
    paths = []
    monkeypatch.setattr(package_check, "run_package_checks", lambda path: paths.append(path) or 1)

    with pytest.raises(SystemExit) as exit_info:
        entrypoint.main()

    assert exit_info.value.code == 1
    assert paths == [tmp_path / "r.json"]


def test_gui_entrypoint_keeps_gui_dispatch(monkeypatch):
    entrypoint = importlib.import_module("markitdowngui.main")
    monkeypatch.setitem(sys.modules, "markitdowngui.ui_qml.app", types.SimpleNamespace(main=lambda: 7))
    monkeypatch.setattr(sys, "argv", ["MarkItDown"])

    with pytest.raises(SystemExit) as exit_info:
        entrypoint.main()

    assert exit_info.value.code == 7


def test_package_cli_requires_explicit_report(monkeypatch):
    entrypoint = importlib.import_module("markitdowngui.main")
    monkeypatch.setitem(sys.modules, "markitdowngui.ui_qml.app", None)
    monkeypatch.setattr(sys, "argv", ["MarkItDown", "--check-package"])

    with pytest.raises(SystemExit) as exit_info:
        entrypoint.main()

    assert exit_info.value.code == 2
