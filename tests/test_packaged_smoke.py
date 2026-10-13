import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest


spec = importlib.util.spec_from_file_location("packaged_smoke", Path("packaging/smoke_packaged_app.py"))
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def receipt():
    return {"schema_version": 1, "status": "passed", "frozen": True,
            "checks": {name: {"status": "passed"} for name in ("anydoc", "pdf_inspector", "pdfium", "glmocr")}}


@pytest.mark.parametrize("failure", [None, "exit", "status", "frozen", "missing", "backend"])
def test_backend_harness_requires_frozen_complete_success(tmp_path, monkeypatch, failure):
    report_path = tmp_path / "receipt.json"
    command = []

    def run(args, **kwargs):
        command.extend(args)
        result = receipt()
        if failure == "status":
            result["status"] = "failed"
        if failure == "frozen":
            result["frozen"] = False
        if failure == "missing":
            result["checks"].pop("anydoc")
        if failure == "backend":
            result["checks"]["glmocr"]["status"] = "failed"
        report_path.write_text(json.dumps(result))
        return subprocess.CompletedProcess(args, 1 if failure == "exit" else 0, "", "")

    monkeypatch.setattr(smoke.subprocess, "run", run)

    assert smoke.run_backend_checks(tmp_path / "MarkItDown.exe", report_path) == (0 if failure is None else 1)
    assert command[1:] == ["--check-package", "--report", str(report_path)]


def test_missing_receipt_cannot_reuse_stale_success(tmp_path, monkeypatch):
    report_path = tmp_path / "receipt.json"
    report_path.write_text(json.dumps(receipt()))
    monkeypatch.setattr(smoke.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))

    assert smoke.run_backend_checks(tmp_path / "MarkItDown", report_path) == 1
    assert not report_path.exists()


def test_backend_timeout_is_failure(tmp_path, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 60)

    monkeypatch.setattr(smoke.subprocess, "run", timeout)

    assert smoke.run_backend_checks(tmp_path / "MarkItDown", tmp_path / "r.json") == 1


def test_gui_smoke_uses_requested_qt_platform(tmp_path, monkeypatch):
    executable = tmp_path / "MarkItDown"
    executable.touch()
    process = Mock()
    process.communicate.return_value = ("", "")
    start = Mock(return_value=process)
    monkeypatch.setattr(smoke.subprocess, "Popen", start)
    clock = iter([0, 2])
    monkeypatch.setattr(smoke.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(smoke, "_terminate", lambda _process: None)

    assert smoke.run_smoke(executable, 1, "xcb") == 0
    assert start.call_args.kwargs["env"]["QT_QPA_PLATFORM"] == "xcb"


def test_harness_checks_both_gui_and_backends_with_explicit_paths(tmp_path, monkeypatch):
    executable = tmp_path / "installed" / "MarkItDown.exe"
    report_path = tmp_path / "installed-backends.json"
    monkeypatch.setattr(sys, "argv", ["smoke", "--executable", str(executable),
                                     "--check-backends", "--report", str(report_path),
                                     "--qt-platform", "xcb"])
    gui = Mock(return_value=1)
    backends = Mock(return_value=0)
    monkeypatch.setattr(smoke, "run_smoke", gui)
    monkeypatch.setattr(smoke, "run_backend_checks", backends)

    assert smoke.main() == 1
    gui.assert_called_once_with(executable, 3.0, "xcb")
    backends.assert_called_once_with(executable, report_path)
