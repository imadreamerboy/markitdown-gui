from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from markitdowngui.core.settings import SettingsManager
from markitdowngui.utils.logger import AppLogger, build_diagnostic_report


MAX_LOG_BYTES = 256 * 1024
MAX_LOG_FILES = 3


_SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password)(\s*[:=]\s*)([^\s,;]+)"
    ),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+"),
)


def create_support_bundle(
    settings: SettingsManager | None = None,
    *,
    output_dir: Path | str | None = None,
    log_dir: Path | str | None = None,
    now: datetime | None = None,
) -> Path:
    """Create a zip with diagnostics, sanitised settings, and recent log tails."""
    settings = settings or SettingsManager()
    generated_at = now or datetime.now(timezone.utc)
    output_root = Path(output_dir) if output_dir is not None else Path(AppLogger.log_dir())
    output_root.mkdir(parents=True, exist_ok=True)
    bundle_path = output_root / (
        f"markitdown-support-{generated_at.strftime('%Y%m%d-%H%M%S')}.zip"
    )

    logs = _collect_log_tails(Path(log_dir) if log_dir is not None else Path(AppLogger.log_dir()))
    manifest = {
        "schema": 1,
        "generatedAt": generated_at.isoformat(),
        "contents": [
            "diagnostics.txt",
            "settings.json",
            "manifest.json",
            *[f"logs/{name}" for name in logs],
        ],
        "notes": [
            "Settings are sanitised and exclude recent file/output paths.",
            f"Logs are redacted and capped at {MAX_LOG_BYTES} bytes each.",
        ],
    }

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.txt", redact_diagnostic_text(build_diagnostic_report()))
        archive.writestr(
            "settings.json",
            json.dumps(build_sanitized_settings_snapshot(settings), indent=2) + "\n",
        )
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for name, text in logs.items():
            archive.writestr(f"logs/{name}", text)

    return bundle_path


def build_sanitized_settings_snapshot(settings: SettingsManager) -> dict[str, Any]:
    """Return support-useful settings without raw file paths or secrets."""
    tesseract_path = settings.get_tesseract_path()
    return {
        "appearance": {
            "themeMode": settings.get_theme_mode(),
            "language": settings.get_current_language(),
        },
        "output": {
            "defaultFormat": settings.get_default_output_format(),
            "defaultOutputFolderConfigured": bool(settings.get_default_output_folder()),
            "saveToSourceFolder": settings.get_save_to_source_folder(),
            "combinedSaveMode": settings.get_save_mode(),
            "recentFilesCount": len(settings.get_recent_files()),
            "recentOutputsCount": len(settings.get_recent_outputs()),
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
            "glmocrOllamaHostConfigured": bool(settings.get_glmocr_ollama_host()),
            "glmocrOllamaPort": settings.get_glmocr_ollama_port(),
            "glmocrOllamaModelConfigured": bool(settings.get_glmocr_ollama_model()),
            "glmocrSdkServerUrlConfigured": bool(settings.get_glmocr_sdk_server_url()),
            "httpEndpointConfigured": bool(settings.get_http_ocr_endpoint()),
            "httpModelConfigured": bool(settings.get_http_ocr_model()),
            "httpApiKeyEnv": settings.get_http_ocr_api_key_env(),
            "httpTimeoutSeconds": settings.get_http_ocr_timeout_seconds(),
            "docintelEndpointConfigured": bool(settings.get_docintel_endpoint()),
            "ocrLanguagesConfigured": bool(settings.get_ocr_languages()),
            "tesseractPathConfigured": bool(tesseract_path),
            "tesseractPathExists": bool(tesseract_path and Path(tesseract_path).exists()),
        },
        "updates": {
            "notificationsEnabled": settings.get_update_notifications_enabled(),
        },
    }


def _collect_log_tails(log_dir: Path) -> dict[str, str]:
    if not log_dir.is_dir():
        return {}

    logs: dict[str, str] = {}
    candidates = sorted(
        (path for path in log_dir.glob("*.log") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:MAX_LOG_FILES]

    for path in candidates:
        try:
            raw = _tail_bytes(path, MAX_LOG_BYTES).decode("utf-8", errors="replace")
        except OSError:
            continue
        logs[path.name] = redact_diagnostic_text(raw)
    return logs


def _tail_bytes(path: Path, limit: int) -> bytes:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > limit:
            handle.seek(-limit, 2)
        return handle.read(limit)


def redact_diagnostic_text(text: str) -> str:
    redacted = text.replace(str(Path.home()), "~")
    redacted = redacted.replace(Path.home().as_posix(), "~")
    redacted = re.sub(
        r"~[^\s]*",
        lambda match: match.group(0).replace("\\", "/"),
        redacted,
    )
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(_redact_secret_match, redacted)
    return redacted


def _redact_secret_match(match: re.Match[str]) -> str:
    if match.re.pattern.startswith("(?i)\\bbearer"):
        return "Bearer [redacted]"
    return f"{match.group(1)}{match.group(2)}[redacted]"
