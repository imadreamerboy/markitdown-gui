import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QSettings

from markitdowngui.core.settings import SettingsManager
from markitdowngui.utils import support_bundle


def _settings(tmp_path):
    manager = SettingsManager()
    manager.settings = QSettings(
        str(tmp_path / "settings.ini"),
        QSettings.Format.IniFormat,
    )
    return manager


def test_sanitized_settings_snapshot_excludes_raw_paths(tmp_path):
    settings = _settings(tmp_path)
    settings.set_default_output_folder(str(tmp_path / "exports"))
    settings.set_recent_files([str(tmp_path / "private.pdf")])
    settings.set_recent_outputs([str(tmp_path / "private.md")])
    settings.set_http_ocr_endpoint("https://ocr.example/private")
    settings.set_docintel_endpoint("https://azure.example/private")
    settings.set_tesseract_path(str(tmp_path / "tesseract.exe"))

    snapshot = support_bundle.build_sanitized_settings_snapshot(settings)
    encoded = json.dumps(snapshot)

    assert snapshot["output"]["defaultOutputFolderConfigured"] is True
    assert snapshot["output"]["recentFilesCount"] == 1
    assert snapshot["output"]["recentOutputsCount"] == 1
    assert snapshot["ocr"]["httpEndpointConfigured"] is True
    assert snapshot["ocr"]["docintelEndpointConfigured"] is True
    assert str(tmp_path) not in encoded
    assert "private.pdf" not in encoded
    assert "ocr.example" not in encoded


def test_redact_diagnostic_text_removes_home_and_secret_values():
    text = (
        f"Executable: {Path.home() / 'app' / 'MarkItDown.exe'}\n"
        "token: token-value\n"
        "Authorization: Bearer secret-token"
    )

    redacted = support_bundle.redact_diagnostic_text(text)

    assert str(Path.home()) not in redacted
    assert "Executable: ~/app/MarkItDown.exe" in redacted
    assert "token: [redacted]" in redacted
    assert "Authorization: Bearer [redacted]" in redacted


def test_create_support_bundle_writes_redacted_zip(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "markitdown_20260629.log").write_text(
        "before\napi_key=secret-value\nAuthorization: Bearer token-value\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        support_bundle,
        "build_diagnostic_report",
        lambda: f"Diagnostics\nLog directory: {Path.home() / '.markitdown'}\n",
    )

    bundle = support_bundle.create_support_bundle(
        settings,
        output_dir=tmp_path / "bundles",
        log_dir=log_dir,
        now=datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
    )

    assert bundle.name == "markitdown-support-20260629-120000.zip"
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        assert {
            "diagnostics.txt",
            "settings.json",
            "manifest.json",
            "logs/markitdown_20260629.log",
        } <= names
        diagnostics = archive.read("diagnostics.txt").decode("utf-8")
        log_text = archive.read("logs/markitdown_20260629.log").decode("utf-8")
        settings_payload = json.loads(archive.read("settings.json"))

    assert str(Path.home()) not in diagnostics
    assert "secret-value" not in log_text
    assert "token-value" not in log_text
    assert "api_key=[redacted]" in log_text
    assert "Authorization: Bearer [redacted]" in log_text
    assert settings_payload["updates"]["notificationsEnabled"] is True
