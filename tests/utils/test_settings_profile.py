import json
from datetime import datetime, timezone

import pytest
from PySide6.QtCore import QSettings

from markitdowngui.core.settings import SettingsManager
from markitdowngui.utils import settings_profile


def _settings(tmp_path, name="settings.ini"):
    manager = SettingsManager()
    manager.settings = QSettings(
        str(tmp_path / name),
        QSettings.Format.IniFormat,
    )
    manager.settings.clear()
    return manager


def test_settings_profile_exports_portable_settings_without_recent_paths(tmp_path):
    settings = _settings(tmp_path)
    settings.set_theme_mode("dark")
    settings.set_default_output_folder(str(tmp_path / "private-exports"))
    settings.set_recent_files([str(tmp_path / "private.pdf")])
    settings.set_recent_outputs([str(tmp_path / "private.md")])
    settings.set_ocr_enabled(True)
    settings.set_ocr_provider("http")
    settings.set_http_ocr_endpoint("http://localhost:8000/ocr")
    settings.set_http_ocr_model("surya")
    settings.set_update_notifications_enabled(False)

    profile = settings_profile.build_settings_profile(
        settings,
        now=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )

    assert profile["schema"] == 1
    assert profile["generatedAt"] == "2026-01-02T03:04:05+00:00"
    assert profile["settings"]["appearance"]["themeMode"] == "dark"
    assert profile["settings"]["ocr"]["provider"] == "http"
    assert profile["settings"]["ocr"]["httpEndpoint"] == "http://localhost:8000/ocr"
    assert profile["settings"]["updates"]["notificationsEnabled"] is False

    text = json.dumps(profile)
    assert "private.pdf" not in text
    assert "private.md" not in text
    assert "private-exports" not in text


def test_settings_profile_import_applies_safe_settings(tmp_path):
    settings = _settings(tmp_path)
    profile = {
        "schema": 1,
        "settings": {
            "appearance": {"themeMode": "system", "language": "de"},
            "output": {
                "defaultFormat": ".txt",
                "saveToSourceFolder": True,
                "combinedSaveMode": False,
            },
            "conversion": {
                "batchSize": 8,
                "preservePdfImages": True,
                "preserveDocxImages": True,
            },
            "ocr": {
                "enabled": True,
                "provider": "glmocr",
                "fallbackProvider": "http",
                "glmocrMode": "ollama",
                "glmocrOllamaHost": "localhost",
                "glmocrOllamaPort": 12434,
                "glmocrOllamaModel": "glm-ocr:latest",
                "glmocrSdkServerUrl": "http://localhost:5002/glmocr/parse",
                "httpEndpoint": "http://localhost:8000/ocr",
                "httpModel": "surya",
                "httpApiKeyEnv": "CUSTOM_OCR_KEY",
                "httpTimeoutSeconds": 45,
                "docintelEndpoint": "https://example.cognitiveservices.azure.com/",
                "ocrLanguages": "eng+deu",
            },
            "updates": {"notificationsEnabled": False},
        },
    }

    settings_profile.apply_settings_profile(settings, profile)

    assert settings.get_theme_mode() == "system"
    assert settings.get_current_language() == "de"
    assert settings.get_default_output_format() == ".txt"
    assert settings.get_save_to_source_folder() is True
    assert settings.get_save_mode() is False
    assert settings.get_batch_size() == 8
    assert settings.get_preserve_pdf_images() is True
    assert settings.get_preserve_docx_images() is True
    assert settings.get_ocr_enabled() is True
    assert settings.get_ocr_provider() == "glmocr"
    assert settings.get_ocr_fallback_provider() == "http"
    assert settings.get_glmocr_mode() == "ollama"
    assert settings.get_http_ocr_endpoint() == "http://localhost:8000/ocr"
    assert settings.get_http_ocr_model() == "surya"
    assert settings.get_http_ocr_api_key_env() == "CUSTOM_OCR_KEY"
    assert settings.get_http_ocr_timeout_seconds() == 45
    assert settings.get_update_notifications_enabled() is False


def test_settings_profile_rejects_unsupported_schema(tmp_path):
    settings = _settings(tmp_path)

    with pytest.raises(ValueError, match="Unsupported settings profile schema"):
        settings_profile.apply_settings_profile(settings, {"schema": 999, "settings": {}})


def test_settings_profile_import_parses_string_booleans(tmp_path):
    settings = _settings(tmp_path)

    settings_profile.apply_settings_profile(
        settings,
        {
            "schema": 1,
            "settings": {
                "output": {
                    "saveToSourceFolder": "false",
                    "combinedSaveMode": "false",
                },
                "conversion": {
                    "preservePdfImages": "true",
                    "preserveDocxImages": "false",
                },
                "ocr": {"enabled": "true"},
                "updates": {"notificationsEnabled": "false"},
            },
        },
    )

    assert settings.get_save_to_source_folder() is False
    assert settings.get_save_mode() is False
    assert settings.get_preserve_pdf_images() is True
    assert settings.get_preserve_docx_images() is False
    assert settings.get_ocr_enabled() is True
    assert settings.get_update_notifications_enabled() is False


def test_settings_profile_round_trips_file(tmp_path):
    source = _settings(tmp_path, "source.ini")
    target = _settings(tmp_path, "target.ini")
    source.set_ocr_enabled(True)
    source.set_ocr_provider("http")
    source.set_http_ocr_endpoint("http://localhost:8000/ocr")

    path = settings_profile.export_settings_profile(source, tmp_path / "profile.json")
    settings_profile.import_settings_profile(target, path)

    assert path.is_file()
    assert target.get_ocr_enabled() is True
    assert target.get_ocr_provider() == "http"
    assert target.get_http_ocr_endpoint() == "http://localhost:8000/ocr"
