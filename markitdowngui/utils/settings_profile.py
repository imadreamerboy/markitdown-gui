from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from markitdowngui.core.settings import SettingsManager


PROFILE_SCHEMA = 1


def build_settings_profile(
    settings: SettingsManager,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = now or datetime.now(timezone.utc)
    return {
        "schema": PROFILE_SCHEMA,
        "app": "markitdown-gui",
        "generatedAt": generated_at.isoformat(),
        "notes": [
            "Portable profile excludes recent files, recent outputs, window state, and default output folders.",
            "Secrets are not stored by the app; this profile includes environment variable names, not secret values.",
        ],
        "settings": {
            "appearance": {
                "themeMode": settings.get_theme_mode(),
                "language": settings.get_current_language(),
            },
            "output": {
                "defaultFormat": settings.get_default_output_format(),
                "saveToSourceFolder": settings.get_save_to_source_folder(),
                "combinedSaveMode": settings.get_save_mode(),
            },
            "conversion": {
                "batchSize": settings.get_batch_size(),
                "preservePdfImages": settings.get_preserve_pdf_images(),
                "preserveDocxImages": settings.get_preserve_docx_images(),
            },
            "ocr": {
                "enabled": settings.get_ocr_enabled(),
                "provider": settings.get_ocr_provider(),
                "fallbackProvider": settings.get_ocr_fallback_provider(),
                "glmocrMode": settings.get_glmocr_mode(),
                "glmocrOllamaHost": settings.get_glmocr_ollama_host(),
                "glmocrOllamaPort": settings.get_glmocr_ollama_port(),
                "glmocrOllamaModel": settings.get_glmocr_ollama_model(),
                "glmocrSdkServerUrl": settings.get_glmocr_sdk_server_url(),
                "httpEndpoint": settings.get_http_ocr_endpoint(),
                "httpModel": settings.get_http_ocr_model(),
                "httpApiKeyEnv": settings.get_http_ocr_api_key_env(),
                "httpTimeoutSeconds": settings.get_http_ocr_timeout_seconds(),
                "docintelEndpoint": settings.get_docintel_endpoint(),
                "ocrLanguages": settings.get_ocr_languages(),
            },
            "updates": {
                "notificationsEnabled": settings.get_update_notifications_enabled(),
            },
        },
    }


def export_settings_profile(
    settings: SettingsManager,
    path: Path | str,
    *,
    now: datetime | None = None,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_settings_profile(settings, now=now), indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def import_settings_profile(settings: SettingsManager, path: Path | str) -> None:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    apply_settings_profile(settings, payload)


def apply_settings_profile(settings: SettingsManager, payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Settings profile must be a JSON object.")
    if int(payload.get("schema") or 0) != PROFILE_SCHEMA:
        raise ValueError("Unsupported settings profile schema.")

    values = payload.get("settings")
    if not isinstance(values, dict):
        raise ValueError("Settings profile is missing settings.")

    appearance = _section(values, "appearance")
    output = _section(values, "output")
    conversion = _section(values, "conversion")
    ocr = _section(values, "ocr")
    updates = _section(values, "updates")

    if "themeMode" in appearance:
        settings.set_theme_mode(str(appearance["themeMode"]))
    if "language" in appearance:
        settings.set_current_language(str(appearance["language"]))

    if "defaultFormat" in output:
        settings.set_default_output_format(str(output["defaultFormat"]))
    if "saveToSourceFolder" in output:
        settings.set_save_to_source_folder(_bool_value(output["saveToSourceFolder"]))
    if "combinedSaveMode" in output:
        settings.set_save_mode(_bool_value(output["combinedSaveMode"]))

    if "batchSize" in conversion:
        settings.set_batch_size(_int_value(conversion["batchSize"]))
    if "preservePdfImages" in conversion:
        settings.set_preserve_pdf_images(_bool_value(conversion["preservePdfImages"]))
    if "preserveDocxImages" in conversion:
        settings.set_preserve_docx_images(_bool_value(conversion["preserveDocxImages"]))

    if "enabled" in ocr:
        settings.set_ocr_enabled(_bool_value(ocr["enabled"]))
    if "provider" in ocr:
        settings.set_ocr_provider(str(ocr["provider"]))
    if "fallbackProvider" in ocr:
        settings.set_ocr_fallback_provider(str(ocr["fallbackProvider"]))
    if "glmocrMode" in ocr:
        settings.set_glmocr_mode(str(ocr["glmocrMode"]))
    if "glmocrOllamaHost" in ocr:
        settings.set_glmocr_ollama_host(str(ocr["glmocrOllamaHost"]))
    if "glmocrOllamaPort" in ocr:
        settings.set_glmocr_ollama_port(_int_value(ocr["glmocrOllamaPort"]))
    if "glmocrOllamaModel" in ocr:
        settings.set_glmocr_ollama_model(str(ocr["glmocrOllamaModel"]))
    if "glmocrSdkServerUrl" in ocr:
        settings.set_glmocr_sdk_server_url(str(ocr["glmocrSdkServerUrl"]))
    if "httpEndpoint" in ocr:
        settings.set_http_ocr_endpoint(str(ocr["httpEndpoint"]))
    if "httpModel" in ocr:
        settings.set_http_ocr_model(str(ocr["httpModel"]))
    if "httpApiKeyEnv" in ocr:
        settings.set_http_ocr_api_key_env(str(ocr["httpApiKeyEnv"]))
    if "httpTimeoutSeconds" in ocr:
        settings.set_http_ocr_timeout_seconds(_int_value(ocr["httpTimeoutSeconds"]))
    if "docintelEndpoint" in ocr:
        settings.set_docintel_endpoint(str(ocr["docintelEndpoint"]))
    if "ocrLanguages" in ocr:
        settings.set_ocr_languages(str(ocr["ocrLanguages"]))

    if "notificationsEnabled" in updates:
        settings.set_update_notifications_enabled(_bool_value(updates["notificationsEnabled"]))


def _section(values: dict[str, Any], key: str) -> dict[str, Any]:
    section = values.get(key)
    return section if isinstance(section, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
