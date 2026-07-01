from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, QProcess, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication, QPalette, QTextDocument

from markitdowngui.core.conversion import (
    AZURE_OCR_API_KEY_ENV_VAR,
    DEFAULT_HTTP_OCR_API_KEY_ENV,
    DEFAULT_HTTP_OCR_TIMEOUT_SECONDS,
    DEFAULT_GLMOCR_OLLAMA_HOST,
    DEFAULT_GLMOCR_OLLAMA_MODEL,
    DEFAULT_GLMOCR_OLLAMA_PORT,
    DEFAULT_GLMOCR_SDK_SERVER_URL,
    GLMOCR_API_KEY_ENV_VAR,
    GLMOCR_MODE_OLLAMA,
    GLMOCR_MODE_SDK_SERVER,
    OCR_PROVIDER_AZURE_TESSERACT,
    OCR_PROVIDER_GLMOCR,
    OCR_PROVIDER_HTTP,
    OCR_PROVIDER_NONE,
    ZHIPU_API_KEY_ENV_VAR,
    ConversionOptions,
    ConversionWorker,
    get_ocr_provider_specs,
    test_ocr_provider_connection,
    validate_ocr_setup,
)
from markitdowngui.core.file_utils import FileManager
from markitdowngui.core.input_sources import (
    is_web_url,
    source_output_dir,
    source_output_stem,
)
from markitdowngui.core.markdown_assets import (
    MarkdownSaveInput,
    cleanup_temp_asset_root,
    create_temp_asset_root,
    prepare_combined_markdown_for_save,
    prepare_markdown_for_separate_save,
    rewrite_markdown_for_preview,
)
from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui_qml.models import QueueModel, ResultModel
from markitdowngui.utils.logger import AppLogger, build_diagnostic_report
from markitdowngui.utils.packaged_updater import (
    PackagedUpdateError,
    build_packaged_update_plan,
    clear_packaged_update_result,
    install_packaged_update,
    is_packaged_app,
    read_packaged_update_result,
)
from markitdowngui.utils.source_updater import (
    SOURCE_UPDATE_DIRTY,
    SOURCE_UPDATE_NOT_CHECKOUT,
    build_source_update_command,
    run_source_update,
)
from markitdowngui.utils.settings_profile import (
    export_settings_profile,
    import_settings_profile,
)
from markitdowngui.utils.support_bundle import (
    create_support_bundle,
    redact_diagnostic_text,
)
from markitdowngui.utils.translations import DEFAULT_LANG, get_translation
from markitdowngui.utils.update_checker import (
    ReleaseAsset,
    UpdateChecker,
    select_release_asset,
)


_PREVIEW_HEADING_RE = re.compile(r'<h([1-3]) style="([^"]*)"><span style="([^"]*)">')
_PREVIEW_HEADING_MARGINS = {
    "1": "10px",
    "2": "8px",
    "3": "6px",
}
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARKDOWN_DECORATION_RE = re.compile(r"[*_`>#]")
_SOURCE_UPDATE_COMPLETE_MESSAGE = "Source update complete. Restart the app."
_DEFAULT_HTTP_OCR_ENDPOINT = "http://127.0.0.1:8000/ocr"

class PackagedUpdateInstaller(QThread):
    progressChanged = Signal(str, int)
    installStarted = Signal()
    manualInstallOpened = Signal(str)
    installError = Signal(str)

    def __init__(self, asset: dict[str, object], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.asset = dict(asset)

    def run(self) -> None:
        try:
            plan = build_packaged_update_plan(self.asset)
            opened_path = install_packaged_update(
                self.asset,
                progress_callback=self.progressChanged.emit,
            )
        except PackagedUpdateError as exc:
            self.installError.emit(str(exc))
            return
        except Exception as exc:
            self.installError.emit(f"Update install failed: {exc}")
            return
        if plan.mode == "dmg":
            self.manualInstallOpened.emit(str(opened_path))
            return
        self.installStarted.emit()


class SourceUpdateInstaller(QThread):
    progressChanged = Signal(str, int)
    updateFinished = Signal()
    updateError = Signal(str)

    def run(self) -> None:
        try:
            result = run_source_update(progress_callback=self.progressChanged.emit)
        except Exception as exc:
            self.updateError.emit(f"Source update failed: {exc}")
            return
        if result == 0:
            self.updateFinished.emit()
            return
        if result == SOURCE_UPDATE_NOT_CHECKOUT:
            self.updateError.emit("No Git source checkout found for this installation.")
            return
        if result == SOURCE_UPDATE_DIRTY:
            self.updateError.emit(
                "Source checkout has local changes. Commit, stash, or discard them before updating."
            )
            return
        self.updateError.emit(f"Source update failed with exit code {result}.")


class AppController(QObject):
    statusChanged = Signal()
    progressChanged = Signal()
    convertingChanged = Signal()
    pausedChanged = Signal()
    queueChanged = Signal()
    resultsChanged = Signal()
    selectedResultChanged = Signal()
    previewModeChanged = Signal()
    settingsChanged = Signal()
    themeChanged = Signal()
    saveDefaultsChanged = Signal()
    updateNotificationChanged = Signal()
    updateInstallChanged = Signal()
    sourceUpdateChanged = Signal()
    diagnosticsChanged = Signal()
    toastRequested = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.settings = SettingsManager()
        self.file_manager = FileManager()
        self.queue_model = QueueModel()
        self.result_model = ResultModel()
        self.worker: ConversionWorker | None = None
        self._status = "Ready to convert"
        self._progress = 0
        self._converting = False
        self._paused = False
        self._selected_result_index = -1
        self._preview_mode = "rendered"
        self._temp_asset_root: str | None = None
        self._cancel_requested = False
        self._update_checker: UpdateChecker | None = None
        self._update_installer: PackagedUpdateInstaller | None = None
        self._update_check_manual = False
        self._available_update_version = ""
        self._available_release_url = ""
        self._available_release_notes = ""
        self._available_release_assets: list[dict[str, object]] = []
        self._preferred_release_asset: dict[str, object] = {}
        self._update_install_running = False
        self._update_install_progress = 0
        self._update_install_status = ""
        self._last_packaged_update_result = ""
        self._source_update_runner: SourceUpdateInstaller | None = None
        self._source_update_running = False
        self._source_update_progress = 0
        self._source_update_status = ""

    @Property(QObject, constant=True)
    def queueModel(self) -> QueueModel:
        return self.queue_model

    @Property(QObject, constant=True)
    def resultModel(self) -> ResultModel:
        return self.result_model

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status

    @Property(int, notify=progressChanged)
    def progress(self) -> int:
        return self._progress

    @Property(bool, notify=convertingChanged)
    def converting(self) -> bool:
        return self._converting

    @Property(bool, notify=pausedChanged)
    def paused(self) -> bool:
        return self._paused

    @Property(bool, notify=queueChanged)
    def hasQueue(self) -> bool:
        return bool(self.queue_model.sources())

    @Property(int, notify=queueChanged)
    def queueCount(self) -> int:
        return self.queue_model.rowCount()

    @Property(bool, notify=resultsChanged)
    def hasResults(self) -> bool:
        return self.result_model.rowCount() > 0

    @Property(bool, notify=resultsChanged)
    def hasSuccessfulResults(self) -> bool:
        return bool(self._successful_result_items())

    @Property(bool, notify=resultsChanged)
    def hasFailedResults(self) -> bool:
        return bool(self._failed_result_items())

    @Property(int, notify=resultsChanged)
    def failedResultCount(self) -> int:
        return len(self._failed_result_items())

    @Property(int, notify=selectedResultChanged)
    def selectedResultIndex(self) -> int:
        return self._selected_result_index

    @Property(str, notify=selectedResultChanged)
    def selectedMarkdown(self) -> str:
        item = self.result_model.item_at(self._selected_result_index)
        return item.outcome.markdown if item else ""

    @Property(bool, notify=selectedResultChanged)
    def selectedResultFailed(self) -> bool:
        item = self.result_model.item_at(self._selected_result_index)
        return bool(item and item.failed)

    @Property(str, notify=selectedResultChanged)
    def selectedPreviewHtml(self) -> str:
        item = self.result_model.item_at(self._selected_result_index)
        if not item:
            return ""
        markdown = rewrite_markdown_for_preview(
            item.outcome.markdown,
            item.outcome.assets,
        )
        doc = QTextDocument()
        doc.setMarkdown(markdown)
        html = self._compact_preview_html(doc.toHtml())
        return f"<style>{self._preview_css()}</style>{html}"

    @Property(str, notify=previewModeChanged)
    def previewMode(self) -> str:
        return self._preview_mode

    @Property(str, notify=settingsChanged)
    def themeMode(self) -> str:
        return self.settings.get_theme_mode()

    @Property(bool, notify=themeChanged)
    def darkMode(self) -> bool:
        mode = self.settings.get_theme_mode()
        if mode == "dark":
            return True
        if mode == "light":
            return False
        app = QGuiApplication.instance()
        if app is None:
            return False
        window_color = app.palette().color(QPalette.ColorRole.Window)
        return window_color.lightness() < 128

    @Property(str, notify=settingsChanged)
    def outputFolder(self) -> str:
        return self.settings.get_default_output_folder()

    @Property(str, notify=saveDefaultsChanged)
    def outputFolderUrl(self) -> str:
        return self._folder_url(self.settings.get_default_output_folder())

    @Property(str, notify=saveDefaultsChanged)
    def suggestedCombinedOutputUrl(self) -> str:
        output_dir = self.settings.get_default_output_folder()
        if not output_dir:
            return ""

        items = self._successful_result_items()
        if not items:
            return ""
        stem = source_output_stem(items[0].source) if len(items) == 1 else "converted"
        output_path = Path(output_dir) / f"{stem}{self.settings.get_default_output_format()}"
        return QUrl.fromLocalFile(str(output_path)).toString()

    @Property(str, notify=saveDefaultsChanged)
    def suggestedSeparateOutputFolderUrl(self) -> str:
        return self._folder_url(self._dialog_output_dir())

    @Property(bool, notify=saveDefaultsChanged)
    def canSaveSeparateWithoutDialog(self) -> bool:
        return self._can_save_separate_without_dialog()

    @Property(bool, notify=settingsChanged)
    def saveCombined(self) -> bool:
        return self.settings.get_save_mode()

    @Property(bool, notify=settingsChanged)
    def saveToSourceFolder(self) -> bool:
        return self.settings.get_save_to_source_folder()

    @Property(int, notify=settingsChanged)
    def batchSize(self) -> int:
        return self.settings.get_batch_size()

    @Property(bool, notify=settingsChanged)
    def ocrEnabled(self) -> bool:
        return self.settings.get_ocr_enabled()

    @Property(bool, notify=settingsChanged)
    def preservePdfImages(self) -> bool:
        return self.settings.get_preserve_pdf_images()

    @Property(bool, notify=settingsChanged)
    def preserveDocxImages(self) -> bool:
        return self.settings.get_preserve_docx_images()

    @Property(str, notify=settingsChanged)
    def ocrProvider(self) -> str:
        return self.settings.get_ocr_provider()

    @Property(bool, notify=settingsChanged)
    def ocrFallbackEnabled(self) -> bool:
        return self.settings.get_ocr_fallback_enabled()

    @Property(str, notify=settingsChanged)
    def ocrFallbackProvider(self) -> str:
        return self.settings.get_ocr_fallback_provider()

    @Property(str, notify=settingsChanged)
    def glmocrMode(self) -> str:
        return self.settings.get_glmocr_mode()

    @Property(str, notify=settingsChanged)
    def glmocrOllamaHost(self) -> str:
        return self.settings.get_glmocr_ollama_host()

    @Property(int, notify=settingsChanged)
    def glmocrOllamaPort(self) -> int:
        return self.settings.get_glmocr_ollama_port()

    @Property(str, notify=settingsChanged)
    def glmocrOllamaModel(self) -> str:
        return self.settings.get_glmocr_ollama_model()

    @Property(str, notify=settingsChanged)
    def glmocrSdkServerUrl(self) -> str:
        return self.settings.get_glmocr_sdk_server_url()

    @Property(str, notify=settingsChanged)
    def httpOcrEndpoint(self) -> str:
        return self.settings.get_http_ocr_endpoint()

    @Property(str, notify=settingsChanged)
    def httpOcrModel(self) -> str:
        return self.settings.get_http_ocr_model()

    @Property(str, notify=settingsChanged)
    def httpOcrApiKeyEnv(self) -> str:
        return self.settings.get_http_ocr_api_key_env()

    @Property(int, notify=settingsChanged)
    def httpOcrTimeoutSeconds(self) -> int:
        return self.settings.get_http_ocr_timeout_seconds()

    @Property("QVariant", constant=True)
    def ocrProviderOptions(self) -> list[dict[str, object]]:
        return [
            {
                "id": spec.provider_id,
                "label": spec.label,
                "detail": spec.detail,
                "capabilities": list(spec.capabilities),
                "settingsGroup": spec.settings_group,
                "fallbackAllowed": spec.fallback_allowed,
            }
            for spec in get_ocr_provider_specs()
        ]

    @Property("QVariant", constant=True)
    def ocrPresetActions(self) -> list[dict[str, str]]:
        return [
            {
                "id": "glmocr_ollama",
                "label": "GLM-OCR Ollama",
                "detail": "Use local Ollama at 127.0.0.1:11434 with glm-ocr:latest.",
            },
            {
                "id": "glmocr_sdk_server",
                "label": "GLM-OCR SDK server",
                "detail": "Use the local /glmocr/parse SDK server endpoint.",
            },
            {
                "id": "http_local",
                "label": "HTTP OCR local",
                "detail": "Use a local multipart OCR endpoint at 127.0.0.1:8000.",
            },
        ]

    @Property("QVariant", notify=settingsChanged)
    def ocrSetupActions(self) -> list[dict[str, str]]:
        return self._build_ocr_setup_actions()

    @Property(str, notify=settingsChanged)
    def docintelEndpoint(self) -> str:
        return self.settings.get_docintel_endpoint()

    @Property(str, notify=settingsChanged)
    def ocrLanguages(self) -> str:
        return self.settings.get_ocr_languages()

    @Property(str, notify=settingsChanged)
    def tesseractPath(self) -> str:
        return self.settings.get_tesseract_path()

    @Property(bool, notify=updateNotificationChanged)
    def hasUpdateNotification(self) -> bool:
        return bool(self._available_update_version)

    @Property(str, notify=updateNotificationChanged)
    def availableUpdateVersion(self) -> str:
        return self._available_update_version

    @Property(str, notify=updateNotificationChanged)
    def availableReleaseUrl(self) -> str:
        return self._available_release_url

    @Property(str, notify=updateNotificationChanged)
    def availableReleaseNotes(self) -> str:
        return self._available_release_notes

    @Property("QVariant", notify=updateNotificationChanged)
    def availableReleaseAssets(self) -> list[dict[str, object]]:
        return self._available_release_assets

    @Property("QVariant", notify=updateNotificationChanged)
    def preferredReleaseAsset(self) -> dict[str, object]:
        return self._preferred_release_asset

    @Property("QVariant", notify=updateNotificationChanged)
    def preferredReleaseAssetPreflightItems(self) -> list[dict[str, str]]:
        return self._build_preferred_release_asset_preflight_items()

    @Property(bool, notify=updateNotificationChanged)
    def canInstallPreferredUpdate(self) -> bool:
        return bool(
            self._preferred_release_asset.get("installSupported")
            and not self._update_install_running
        )

    @Property(bool, notify=updateInstallChanged)
    def updateInstallRunning(self) -> bool:
        return self._update_install_running

    @Property(int, notify=updateInstallChanged)
    def updateInstallProgress(self) -> int:
        return self._update_install_progress

    @Property(str, notify=updateInstallChanged)
    def updateInstallStatus(self) -> str:
        return self._update_install_status

    @Property(bool, notify=updateInstallChanged)
    def hasLastPackagedUpdateResult(self) -> bool:
        return bool(self._last_packaged_update_result)

    @Property(str, notify=updateInstallChanged)
    def lastPackagedUpdateResult(self) -> str:
        return self._last_packaged_update_result

    @Property(bool, notify=updateInstallChanged)
    def hasLastPackagedUpdateBackupPath(self) -> bool:
        return bool(self.lastPackagedUpdateBackupPath)

    @Property(str, notify=updateInstallChanged)
    def lastPackagedUpdateBackupPath(self) -> str:
        return self._packaged_update_result_field("Backup")

    @Property("QVariant", notify=diagnosticsChanged)
    def diagnosticReadinessItems(self) -> list[dict[str, str]]:
        return self._build_diagnostic_readiness_items()

    @Property(str, constant=True)
    def sourceUpdateCommand(self) -> str:
        return build_source_update_command()

    @Property(bool, notify=sourceUpdateChanged)
    def canRunSourceUpdate(self) -> bool:
        return bool(
            self.sourceUpdateCommand
            and not self._source_update_running
            and not self._source_update_needs_restart()
            and not self._update_install_running
        )

    @Property(bool, notify=sourceUpdateChanged)
    def sourceUpdateNeedsRestart(self) -> bool:
        return self._source_update_needs_restart()

    @Property(bool, notify=sourceUpdateChanged)
    def sourceUpdateRunning(self) -> bool:
        return self._source_update_running

    @Property(int, notify=sourceUpdateChanged)
    def sourceUpdateProgress(self) -> int:
        return self._source_update_progress

    @Property(str, notify=sourceUpdateChanged)
    def sourceUpdateStatus(self) -> str:
        return self._source_update_status

    @Slot("QVariant")
    def addFiles(self, values: Any) -> None:
        if self._queue_change_locked():
            return
        sources = [path for path in self._paths_from_variant(values) if path]
        added = self.queue_model.add_sources(sources)
        if added:
            self._clear_results_after_queue_change()
            self._set_status(f"Added {added} input{'s' if added != 1 else ''}")
            self.queueChanged.emit()

    @Slot(str)
    def addUrl(self, value: str) -> None:
        url = value.strip()
        if not is_web_url(url):
            self.toastRequested.emit("error", "Enter a valid http:// or https:// URL.")
            return
        self.addFiles([url])

    @Slot(int)
    def removeQueued(self, row: int) -> None:
        if self._queue_change_locked():
            return
        sources_before = self.queue_model.sources()
        self.queue_model.remove(row)
        if self.queue_model.sources() != sources_before:
            self._clear_results_after_queue_change()
        self.queueChanged.emit()

    @Slot()
    def clearQueue(self) -> None:
        if self._queue_change_locked():
            return
        self.queue_model.clear()
        self._clear_results_after_queue_change()
        self.queueChanged.emit()
        self._set_status("Queue cleared")

    @Slot()
    def clearResults(self) -> None:
        self.result_model.clear()
        self._selected_result_index = -1
        self._progress = 0
        self._cleanup_temp_assets()
        self.resultsChanged.emit()
        self.selectedResultChanged.emit()
        self.progressChanged.emit()
        self.saveDefaultsChanged.emit()

    @Slot()
    def retryFailedResults(self) -> None:
        if self._queue_change_locked():
            return
        failed_sources = [item.source for item in self._failed_result_items()]
        if not failed_sources:
            self.toastRequested.emit("error", "No failed conversions to retry.")
            return

        self.queue_model.clear()
        added = self.queue_model.add_sources(failed_sources)
        self.clearResults()
        self.queueChanged.emit()
        self._set_status(
            f"Queued {added} failed input{'s' if added != 1 else ''} for retry"
        )
        self.toastRequested.emit(
            "success",
            f"Queued {added} failed input{'s' if added != 1 else ''} for retry.",
        )

    @Slot()
    def convert(self) -> None:
        if self._converting:
            return
        sources = self.queue_model.sources()
        if not sources:
            self.toastRequested.emit("error", "Add files or a website URL first.")
            return

        self.clearResults()
        self._cancel_requested = False
        self.worker = ConversionWorker(
            files=sources,
            batch_size=self.settings.get_batch_size(),
            options=self._build_conversion_options(),
        )
        self.worker.progress.connect(self._handle_progress)
        self.worker.finished.connect(self._handle_finished)
        self.worker.error.connect(lambda message: self.toastRequested.emit("error", message))
        self.worker.start()
        self._converting = True
        self._paused = False
        self._progress = 0
        self._set_status("Starting conversion")
        self.convertingChanged.emit()
        self.pausedChanged.emit()
        self.progressChanged.emit()

    @Slot()
    def togglePause(self) -> None:
        if not self.worker or not self._converting:
            return
        self._paused = not self._paused
        self.worker.is_paused = self._paused
        self._set_status("Paused" if self._paused else "Converting")
        self.pausedChanged.emit()

    @Slot()
    def cancel(self) -> None:
        if not self.worker or not self._converting:
            return
        self._cancel_requested = True
        self.worker.is_cancelled = True
        self.worker.is_paused = False
        if self._paused:
            self._paused = False
            self.pausedChanged.emit()
        self._set_status("Cancelling")

    @Slot(int)
    def selectResult(self, row: int) -> None:
        if self.result_model.item_at(row) is None:
            return
        self._selected_result_index = row
        self.selectedResultChanged.emit()

    @Slot(str)
    def setPreviewMode(self, mode: str) -> None:
        normalized = mode if mode in {"rendered", "raw"} else "rendered"
        if normalized == self._preview_mode:
            return
        self._preview_mode = normalized
        self.previewModeChanged.emit()

    @Slot()
    def copySelectedMarkdown(self) -> None:
        text = self.selectedMarkdown.strip()
        if not text:
            self.toastRequested.emit("error", "No Markdown selected.")
            return
        QGuiApplication.clipboard().setText(text)
        self.toastRequested.emit("success", "Copied Markdown to clipboard.")

    @Slot()
    def notifyNoOutputToSave(self) -> None:
        self.toastRequested.emit("error", "No output to save.")

    @Slot()
    def notifyNoSuccessfulOutputToSave(self) -> None:
        self.toastRequested.emit("error", "No successful output to save.")

    @Slot("QVariant")
    def saveCombinedOutput(self, file_url: Any) -> None:
        output_path = self._path_from_url(file_url)
        if not output_path:
            return
        if not output_path.lower().endswith(".md"):
            output_path = f"{output_path}.md"

        all_items = self.result_model.items()
        if not all_items:
            self.toastRequested.emit("error", "No output to save.")
            return
        items = self._successful_result_items(all_items)
        if not items:
            self.notifyNoSuccessfulOutputToSave()
            return

        documents = [
            MarkdownSaveInput(
                source=item.source,
                markdown=item.outcome.markdown,
                assets=item.outcome.assets,
            )
            for item in items
        ]
        try:
            output = prepare_combined_markdown_for_save(
                documents,
                output_path,
                source_heading_template="## {source}",
            )
            self.file_manager.save_markdown_file(output_path, output)
            self.settings.set_recent_outputs(
                self.file_manager.update_recent_list(
                    output_path,
                    self.settings.get_recent_outputs(),
                )
            )
            self.toastRequested.emit("success", f"Saved {Path(output_path).name}.")
        except Exception as exc:
            AppLogger.error(f"Failed saving combined output: {exc}")
            self.toastRequested.emit("error", f"Save failed: {exc}")

    @Slot("QVariant")
    def saveSeparateOutputs(self, folder_url: Any) -> None:
        fallback_dir = self._path_from_url(folder_url)
        all_items = self.result_model.items()
        if not all_items:
            self.toastRequested.emit("error", "No output to save.")
            return
        items = self._successful_result_items(all_items)
        if not items:
            self.notifyNoSuccessfulOutputToSave()
            return

        if not fallback_dir and not self._can_save_separate_without_dialog(items):
            self.toastRequested.emit("error", "Choose an output folder before saving.")
            return

        if fallback_dir:
            Path(fallback_dir).mkdir(parents=True, exist_ok=True)

        saved_paths: list[str] = []
        for item in items:
            output_dir = self._separate_output_dir(fallback_dir, item.source)
            if not output_dir:
                AppLogger.error(f"No output folder available for {item.source}")
                continue
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            output_path = self._unique_output_path(output_dir, item.source)
            try:
                markdown = prepare_markdown_for_separate_save(
                    item.outcome.markdown,
                    item.outcome.assets,
                    output_path,
                )
                self.file_manager.save_markdown_file(output_path, markdown)
                saved_paths.append(output_path)
            except Exception as exc:
                AppLogger.error(f"Failed saving {output_path}: {exc}")

        if saved_paths:
            self.toastRequested.emit("success", f"Saved {len(saved_paths)} files.")
        else:
            self.toastRequested.emit("error", "No files were saved.")

    @Slot("QVariant")
    def setOutputFolderFromUrl(self, folder_url: Any) -> None:
        output_dir = self._path_from_url(folder_url)
        if output_dir:
            self.setOutputFolder(output_dir)

    @Slot(str)
    def setOutputFolder(self, folder: str) -> None:
        self.settings.set_default_output_folder(folder)
        self.settingsChanged.emit()
        self.saveDefaultsChanged.emit()

    @Slot(str)
    def setThemeMode(self, mode: str) -> None:
        self.settings.set_theme_mode(mode)
        self.settingsChanged.emit()
        self.themeChanged.emit()
        if self._selected_result_index >= 0:
            self.selectedResultChanged.emit()

    @Slot(bool)
    def setSaveCombined(self, enabled: bool) -> None:
        self.settings.set_save_mode(enabled)
        self.settingsChanged.emit()

    @Slot(bool)
    def setSaveToSourceFolder(self, enabled: bool) -> None:
        self.settings.set_save_to_source_folder(enabled)
        self.settingsChanged.emit()
        self.saveDefaultsChanged.emit()

    @Slot(int)
    def setBatchSize(self, value: int) -> None:
        self.settings.set_batch_size(value)
        self.settingsChanged.emit()

    @Slot(bool)
    def setOcrEnabled(self, enabled: bool) -> None:
        self.settings.set_ocr_enabled(enabled)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(bool)
    def setPreservePdfImages(self, enabled: bool) -> None:
        self.settings.set_preserve_pdf_images(enabled)
        self.settingsChanged.emit()

    @Slot(bool)
    def setPreserveDocxImages(self, enabled: bool) -> None:
        self.settings.set_preserve_docx_images(enabled)
        self.settingsChanged.emit()

    @Slot(str)
    def setOcrProvider(self, provider: str) -> None:
        self.settings.set_ocr_provider(provider)
        ocr_provider = self.settings.get_ocr_provider()
        fallback_provider = self.settings.get_ocr_fallback_provider()
        if (
            ocr_provider == OCR_PROVIDER_AZURE_TESSERACT
            or fallback_provider == ocr_provider
        ):
            self.settings.set_ocr_fallback_provider(OCR_PROVIDER_NONE)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(bool)
    def setOcrFallbackEnabled(self, enabled: bool) -> None:
        self.settings.set_ocr_fallback_enabled(enabled)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setOcrFallbackProvider(self, provider: str) -> None:
        self.settings.set_ocr_fallback_provider(provider)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setGlmocrMode(self, mode: str) -> None:
        self.settings.set_glmocr_mode(mode)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setGlmocrOllamaHost(self, value: str) -> None:
        self.settings.set_glmocr_ollama_host(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(int)
    def setGlmocrOllamaPort(self, value: int) -> None:
        self.settings.set_glmocr_ollama_port(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setGlmocrOllamaModel(self, value: str) -> None:
        self.settings.set_glmocr_ollama_model(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setGlmocrSdkServerUrl(self, value: str) -> None:
        self.settings.set_glmocr_sdk_server_url(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setHttpOcrEndpoint(self, value: str) -> None:
        self.settings.set_http_ocr_endpoint(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setHttpOcrModel(self, value: str) -> None:
        self.settings.set_http_ocr_model(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setHttpOcrApiKeyEnv(self, value: str) -> None:
        self.settings.set_http_ocr_api_key_env(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(int)
    def setHttpOcrTimeoutSeconds(self, value: int) -> None:
        self.settings.set_http_ocr_timeout_seconds(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setDocintelEndpoint(self, value: str) -> None:
        self.settings.set_docintel_endpoint(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setOcrLanguages(self, value: str) -> None:
        self.settings.set_ocr_languages(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def setTesseractPath(self, value: str) -> None:
        self.settings.set_tesseract_path(value)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot(str)
    def applyOcrPreset(self, preset_id: str) -> None:
        if preset_id == "glmocr_ollama":
            self.settings.set_ocr_enabled(True)
            self.settings.set_ocr_provider(OCR_PROVIDER_GLMOCR)
            self.settings.set_ocr_fallback_provider(OCR_PROVIDER_NONE)
            self.settings.set_glmocr_mode(GLMOCR_MODE_OLLAMA)
            self.settings.set_glmocr_ollama_host(DEFAULT_GLMOCR_OLLAMA_HOST)
            self.settings.set_glmocr_ollama_port(DEFAULT_GLMOCR_OLLAMA_PORT)
            self.settings.set_glmocr_ollama_model(DEFAULT_GLMOCR_OLLAMA_MODEL)
            message = "GLM-OCR Ollama preset applied. Run Test connection next."
        elif preset_id == "glmocr_sdk_server":
            self.settings.set_ocr_enabled(True)
            self.settings.set_ocr_provider(OCR_PROVIDER_GLMOCR)
            self.settings.set_ocr_fallback_provider(OCR_PROVIDER_NONE)
            self.settings.set_glmocr_mode(GLMOCR_MODE_SDK_SERVER)
            self.settings.set_glmocr_sdk_server_url(DEFAULT_GLMOCR_SDK_SERVER_URL)
            message = "GLM-OCR SDK server preset applied. Run Test connection next."
        elif preset_id == "http_local":
            self.settings.set_ocr_enabled(True)
            self.settings.set_ocr_provider(OCR_PROVIDER_HTTP)
            self.settings.set_ocr_fallback_provider(OCR_PROVIDER_NONE)
            self.settings.set_http_ocr_endpoint(_DEFAULT_HTTP_OCR_ENDPOINT)
            self.settings.set_http_ocr_model("")
            self.settings.set_http_ocr_api_key_env(DEFAULT_HTTP_OCR_API_KEY_ENV)
            self.settings.set_http_ocr_timeout_seconds(DEFAULT_HTTP_OCR_TIMEOUT_SECONDS)
            message = "HTTP OCR local preset applied. Run Test connection next."
        else:
            self.toastRequested.emit("error", "Unknown OCR preset.")
            return

        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()
        self.toastRequested.emit("success", message)

    @Slot()
    def validateOcrSetup(self) -> None:
        result = validate_ocr_setup(self._build_ocr_validation_options())
        self.toastRequested.emit("success" if result.ok else "error", result.message)

    @Slot()
    def testOcrConnection(self) -> None:
        try:
            message = test_ocr_provider_connection(self._build_ocr_validation_options())
        except Exception as exc:
            self.toastRequested.emit("error", str(exc))
            return
        self.toastRequested.emit("success", message)

    @Slot(str, str, str)
    def runOcrSetupAction(self, action: str, value: str, label: str) -> None:
        if action == "open":
            self.openExternalUrl(value)
            return
        if action == "copy":
            QGuiApplication.clipboard().setText(value)
            self.toastRequested.emit("success", f"{label} copied.")
            return
        self.toastRequested.emit("error", "Unknown OCR setup action.")

    @Slot()
    def startAutomaticUpdateCheck(self) -> None:
        if self.settings.get_update_notifications_enabled():
            self._start_update_check(manual=False)

    @Slot()
    def checkForUpdates(self) -> None:
        self._start_update_check(manual=True)

    @Slot()
    def checkLastPackagedUpdateResult(self) -> None:
        result = read_packaged_update_result()
        if not result:
            return

        self._last_packaged_update_result = result
        clear_packaged_update_result()
        self.updateInstallChanged.emit()
        self.diagnosticsChanged.emit()

        if "Status: failed" in result:
            self.toastRequested.emit(
                "error",
                "Previous update failed and rollback details are in Diagnostics.",
            )
        else:
            self.toastRequested.emit("success", "Previous update completed.")

    @Slot()
    def clearLastPackagedUpdateResult(self) -> None:
        if not self._last_packaged_update_result:
            return
        self._last_packaged_update_result = ""
        self.updateInstallChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot()
    def openLastPackagedUpdateBackup(self) -> None:
        backup_path = self.lastPackagedUpdateBackupPath
        if not backup_path:
            self.toastRequested.emit("error", "No update backup path was recorded.")
            return
        backup_dir = Path(backup_path).expanduser()
        if not backup_dir.exists():
            self.toastRequested.emit("error", "Backup folder no longer exists.")
            return
        self.openExternalUrl(QUrl.fromLocalFile(str(backup_dir)).toString())

    @Slot()
    def dismissUpdateNotification(self) -> None:
        if not self._available_update_version:
            return
        self._available_update_version = ""
        self._available_release_url = ""
        self._available_release_notes = ""
        self._available_release_assets = []
        self._preferred_release_asset = {}
        self.updateNotificationChanged.emit()
        self.diagnosticsChanged.emit()

    @Slot()
    def disableUpdateNotifications(self) -> None:
        self.settings.set_update_notifications_enabled(False)
        self.settingsChanged.emit()
        self.diagnosticsChanged.emit()
        self.dismissUpdateNotification()
        self.toastRequested.emit("success", "Update notifications disabled.")

    @Slot()
    def openReleases(self) -> None:
        self.openExternalUrl(
            self._available_release_url
            or "https://github.com/imadreamerboy/markitdown-gui/releases"
        )
        self.dismissUpdateNotification()

    @Slot(str)
    def openReleaseAsset(self, url: str) -> None:
        if not url:
            self.openReleases()
            return
        self.openExternalUrl(url)
        self.dismissUpdateNotification()

    @Slot()
    def installPreferredUpdate(self) -> None:
        if self._update_install_running:
            self.toastRequested.emit("success", "Update install already running.")
            return
        if self._converting:
            self.toastRequested.emit(
                "error",
                "Wait for conversion to finish before installing an update.",
            )
            return
        if not self._preferred_release_asset:
            self.openReleases()
            return
        if not self._preferred_release_asset.get("installSupported"):
            reason = str(self._preferred_release_asset.get("installReason") or "")
            if reason:
                self.toastRequested.emit("error", reason)
            self.openReleaseAsset(str(self._preferred_release_asset.get("url") or ""))
            return
        self._update_install_running = True
        self._update_install_progress = 0
        self._update_install_status = "Preparing update"
        self.updateInstallChanged.emit()
        self.updateNotificationChanged.emit()
        self.sourceUpdateChanged.emit()
        self.diagnosticsChanged.emit()

        self._update_installer = self._create_update_installer(
            dict(self._preferred_release_asset)
        )
        self._update_installer.progressChanged.connect(self._on_update_install_progress)
        self._update_installer.installError.connect(self._on_update_install_error)
        self._update_installer.manualInstallOpened.connect(
            self._on_manual_update_install_opened
        )
        self._update_installer.installStarted.connect(self._on_update_install_started)
        self._update_installer.finished.connect(self._clear_update_installer)
        self._update_installer.start()

    @Slot()
    def copySourceUpdateCommand(self) -> None:
        command = self.sourceUpdateCommand
        if not command:
            self.toastRequested.emit(
                "error",
                "No Git source checkout found for this installation.",
            )
            return
        QGuiApplication.clipboard().setText(command)
        self.toastRequested.emit("success", "Source update command copied.")

    @Slot()
    def runSourceUpdate(self) -> None:
        if self._source_update_running:
            self.toastRequested.emit("success", "Source update already running.")
            return
        if self._source_update_needs_restart():
            self.toastRequested.emit("success", "Restart the app to finish updating.")
            return
        if self._update_install_running:
            self.toastRequested.emit(
                "error",
                "Wait for packaged update install to finish before updating source.",
            )
            return
        if self._converting:
            self.toastRequested.emit(
                "error",
                "Wait for conversion to finish before updating the source checkout.",
            )
            return
        if not self.sourceUpdateCommand:
            self.toastRequested.emit(
                "error",
                "No Git source checkout found for this installation.",
            )
            return

        self._source_update_running = True
        self._source_update_progress = 0
        self._source_update_status = "Preparing source update"
        self.sourceUpdateChanged.emit()
        self.diagnosticsChanged.emit()

        self._source_update_runner = self._create_source_update_runner()
        self._source_update_runner.progressChanged.connect(self._on_source_update_progress)
        self._source_update_runner.updateError.connect(self._on_source_update_error)
        self._source_update_runner.updateFinished.connect(self._on_source_update_finished)
        self._source_update_runner.finished.connect(self._clear_source_update_runner)
        self._source_update_runner.start()

    @Slot()
    def restartApp(self) -> None:
        if self._converting:
            self.toastRequested.emit(
                "error",
                "Wait for conversion to finish before restarting.",
            )
            return
        if self._update_install_running or self._source_update_running:
            self.toastRequested.emit(
                "error",
                "Wait for the current update to finish before restarting.",
            )
            return
        if not self._start_restart_process():
            self.toastRequested.emit("error", "Could not restart the app.")
            return
        self.toastRequested.emit("success", "Restarting app.")
        QGuiApplication.quit()

    @Slot()
    def openLogFolder(self) -> None:
        log_dir = AppLogger.log_dir()
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        self.openExternalUrl(QUrl.fromLocalFile(log_dir).toString())

    @Slot()
    def copyDiagnostics(self) -> None:
        diagnostic_text = "\n\n".join(
            part
            for part in (
                build_diagnostic_report(),
                self._build_diagnostic_readiness_text(),
            )
            if part.strip()
        )
        QGuiApplication.clipboard().setText(redact_diagnostic_text(diagnostic_text))
        self.toastRequested.emit("success", "Diagnostics copied.")

    @Slot()
    def exportSupportBundle(self) -> None:
        try:
            bundle_path = create_support_bundle(self.settings)
        except Exception as exc:
            AppLogger.error(f"Failed creating support bundle: {exc}")
            self.toastRequested.emit("error", f"Support bundle failed: {exc}")
            return
        self.toastRequested.emit("success", f"Created {bundle_path.name}.")
        self.openExternalUrl(QUrl.fromLocalFile(str(bundle_path.parent)).toString())

    @Slot(str)
    def exportSettingsProfile(self, file_url: str) -> None:
        profile_path = self._path_from_url(file_url)
        if not profile_path:
            return
        if not profile_path.lower().endswith(".json"):
            profile_path = f"{profile_path}.json"
        try:
            exported_path = export_settings_profile(self.settings, profile_path)
        except Exception as exc:
            AppLogger.error(f"Failed exporting settings profile: {exc}")
            self.toastRequested.emit("error", f"Settings export failed: {exc}")
            return
        self.toastRequested.emit("success", f"Exported {exported_path.name}.")

    @Slot(str)
    def importSettingsProfile(self, file_url: str) -> None:
        profile_path = self._path_from_url(file_url)
        if not profile_path:
            return
        try:
            import_settings_profile(self.settings, profile_path)
        except Exception as exc:
            AppLogger.error(f"Failed importing settings profile: {exc}")
            self.toastRequested.emit("error", f"Settings import failed: {exc}")
            return
        self.settingsChanged.emit()
        self.themeChanged.emit()
        self.saveDefaultsChanged.emit()
        self.diagnosticsChanged.emit()
        self.toastRequested.emit("success", "Settings profile imported.")

    @Slot(str)
    def openExternalUrl(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    @Slot(result=bool)
    def shutdown(self) -> bool:
        if self.worker and self.worker.isRunning():
            self._cancel_requested = True
            self.worker.is_cancelled = True
            self.worker.is_paused = False
            if self._paused:
                self._paused = False
                self.pausedChanged.emit()
            self._set_status("Cancelling")
            if not self.worker.wait(1500):
                self.toastRequested.emit(
                    "error",
                    "Conversion is still stopping. Close again after it finishes.",
                )
                return False
        self._cleanup_temp_assets()
        if self._update_checker and self._update_checker.isRunning():
            self._update_checker.wait(2000)
        if self._update_installer and self._update_installer.isRunning():
            if self._update_install_running:
                self.toastRequested.emit(
                    "error",
                    "Update install is still preparing. Close after it finishes.",
                )
                return False
            self._update_installer.wait(2000)
        if self._source_update_runner and self._source_update_runner.isRunning():
            if self._source_update_running:
                self.toastRequested.emit(
                    "error",
                    "Source update is still running. Close after it finishes.",
                )
                return False
            self._source_update_runner.wait(2000)
        return True

    def _start_update_check(self, manual: bool) -> None:
        if self._update_checker and self._update_checker.isRunning():
            if manual:
                self.toastRequested.emit("success", "Update check already running.")
            return

        self._update_check_manual = manual
        self._update_checker = self._create_update_checker()
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.update_error.connect(self._on_update_error)
        self._update_checker.no_update_available.connect(self._on_no_update)
        self._update_checker.finished.connect(self._clear_update_checker)
        self._update_checker.start()

    def _create_update_checker(self) -> UpdateChecker:
        return UpdateChecker(self)

    def _create_update_installer(
        self,
        asset: dict[str, object],
    ) -> PackagedUpdateInstaller:
        return PackagedUpdateInstaller(asset, self)

    def _create_source_update_runner(self) -> SourceUpdateInstaller:
        return SourceUpdateInstaller(self)

    def _start_restart_process(self) -> bool:
        return QProcess.startDetached(sys.executable, list(sys.argv))

    def _on_update_install_progress(self, status: str, progress: int) -> None:
        self._update_install_status = status
        self._update_install_progress = max(0, min(100, int(progress)))
        self.updateInstallChanged.emit()
        self.diagnosticsChanged.emit()

    def _on_update_install_error(self, message: str) -> None:
        self._update_install_running = False
        self._update_install_status = message
        self._update_install_progress = 0
        self.updateInstallChanged.emit()
        self.updateNotificationChanged.emit()
        self.sourceUpdateChanged.emit()
        self.diagnosticsChanged.emit()
        self.toastRequested.emit("error", message)

    def _on_update_install_started(self) -> None:
        self._update_install_running = False
        self._update_install_status = "Restarting app"
        self._update_install_progress = 100
        self.updateInstallChanged.emit()
        self.updateNotificationChanged.emit()
        self.sourceUpdateChanged.emit()
        self.diagnosticsChanged.emit()
        self.toastRequested.emit("success", "Update installer started. Closing app.")
        self.dismissUpdateNotification()
        QGuiApplication.quit()

    def _on_manual_update_install_opened(self, path: str) -> None:
        self._update_install_running = False
        self._update_install_status = (
            "DMG downloaded and opened. Drag MarkItDown to Applications."
        )
        self._update_install_progress = 100
        self.updateInstallChanged.emit()
        self.updateNotificationChanged.emit()
        self.sourceUpdateChanged.emit()
        self.diagnosticsChanged.emit()
        self.toastRequested.emit(
            "success",
            f"DMG opened from {path}. Drag MarkItDown to Applications.",
        )

    def _clear_update_installer(self) -> None:
        if self._update_install_running:
            self._update_install_running = False
            self.updateInstallChanged.emit()
            self.updateNotificationChanged.emit()
            self.sourceUpdateChanged.emit()
            self.diagnosticsChanged.emit()
        self._update_installer = None

    def _build_diagnostic_readiness_items(self) -> list[dict[str, str]]:
        ocr_result = validate_ocr_setup(self._build_ocr_validation_options())
        if not self.settings.get_ocr_enabled():
            ocr_status = "Off"
            ocr_severity = "muted"
        elif ocr_result.ok:
            ocr_status = "Ready"
            ocr_severity = "ok"
        else:
            ocr_status = "Needs setup"
            ocr_severity = "warn"

        if self._update_install_running:
            packaged_status = "Installing"
            packaged_detail = self._update_install_status or "Preparing update."
            packaged_severity = "warn"
        elif self._last_packaged_update_result:
            packaged_status = "Last result"
            packaged_detail = self._last_packaged_update_result.splitlines()[0]
            packaged_severity = (
                "warn"
                if "Status: failed" in self._last_packaged_update_result
                else "ok"
            )
        elif is_packaged_app():
            packaged_status = "Ready"
            packaged_detail = "Packaged install helper is available for supported release assets."
            packaged_severity = "ok"
        else:
            packaged_status = "Source build"
            packaged_detail = "Packaged install helper runs only in frozen builds."
            packaged_severity = "muted"

        if self._source_update_running:
            source_status = "Running"
            source_detail = self._source_update_status or "Source update is running."
            source_severity = "warn"
        elif self.sourceUpdateCommand:
            source_status = "Available"
            source_detail = "Git checkout can pull and reinstall from Help."
            source_severity = "ok"
        else:
            source_status = "Unavailable"
            source_detail = "No Git checkout detected for source updates."
            source_severity = "muted"

        if self.hasUpdateNotification:
            update_status = "Update available"
            update_detail = f"Latest detected release: {self._available_update_version}."
            update_severity = "warn"
        elif self.settings.get_update_notifications_enabled():
            update_status = "Auto-check on"
            update_detail = "The app checks GitHub releases after startup."
            update_severity = "ok"
        else:
            update_status = "Auto-check off"
            update_detail = "Update notifications are disabled."
            update_severity = "muted"

        return [
            {
                "label": "OCR",
                "status": ocr_status,
                "detail": ocr_result.message,
                "severity": ocr_severity,
            },
            {
                "label": "Packaged updates",
                "status": packaged_status,
                "detail": packaged_detail,
                "severity": packaged_severity,
            },
            {
                "label": "Source updates",
                "status": source_status,
                "detail": source_detail,
                "severity": source_severity,
            },
            {
                "label": "Update checks",
                "status": update_status,
                "detail": update_detail,
                "severity": update_severity,
            },
            {
                "label": "Logs",
                "status": "Ready",
                "detail": f"Log directory: {AppLogger.log_dir()}",
                "severity": "ok",
            },
        ]

    def _build_diagnostic_readiness_text(self) -> str:
        lines = ["Readiness"]
        for item in self._build_diagnostic_readiness_items():
            lines.append(f"- {item['label']}: {item['status']} - {item['detail']}")
        if self._last_packaged_update_result:
            lines.extend(["", "Last packaged update", self._last_packaged_update_result])
        return "\n".join(lines)

    def _packaged_update_result_field(self, name: str) -> str:
        prefix = f"{name}:"
        for line in self._last_packaged_update_result.splitlines():
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
        return ""

    def _build_ocr_setup_actions(self) -> list[dict[str, str]]:
        provider = self.settings.get_ocr_provider()
        if provider == OCR_PROVIDER_GLMOCR:
            return [
                {
                    "label": "Open GLM-OCR docs",
                    "detail": "Model options, API mode, Ollama, and SDK server setup.",
                    "action": "open",
                    "value": "https://github.com/zai-org/GLM-OCR",
                },
                {
                    "label": "Copy API key hint",
                    "detail": "Use this for Official API mode.",
                    "action": "copy",
                    "value": f"{ZHIPU_API_KEY_ENV_VAR}=<key> or {GLMOCR_API_KEY_ENV_VAR}=<key>",
                },
                {
                    "label": "Copy SDK server URL",
                    "detail": "Use this when running the GLM-OCR SDK server locally.",
                    "action": "copy",
                    "value": self.settings.get_glmocr_sdk_server_url(),
                },
            ]
        if provider == OCR_PROVIDER_HTTP:
            return [
                {
                    "label": "Copy endpoint contract",
                    "detail": "The server receives multipart `file` plus optional `model`.",
                    "action": "copy",
                    "value": "POST multipart/form-data: file=<document>, model=<optional>",
                },
                {
                    "label": "Copy curl template",
                    "detail": "Smoke-test the configured endpoint outside the app.",
                    "action": "copy",
                    "value": self._http_ocr_curl_template(),
                },
                {
                    "label": "Copy API key env",
                    "detail": "Only needed when the endpoint expects bearer auth.",
                    "action": "copy",
                    "value": self.settings.get_http_ocr_api_key_env()
                    or DEFAULT_HTTP_OCR_API_KEY_ENV,
                },
            ]
        return [
            {
                "label": "Open Azure OCR docs",
                "detail": "Document Intelligence resource and endpoint setup.",
                "action": "open",
                "value": "https://learn.microsoft.com/azure/ai-services/document-intelligence/",
            },
            {
                "label": "Open Tesseract docs",
                "detail": "Install the local fallback executable and language packs.",
                "action": "open",
                "value": "https://github.com/tesseract-ocr/tesseract",
            },
            {
                "label": "Copy API key env",
                "detail": "Set this before using Azure OCR.",
                "action": "copy",
                "value": f"{AZURE_OCR_API_KEY_ENV_VAR}=<key>",
            },
        ]

    def _http_ocr_curl_template(self) -> str:
        endpoint = self.settings.get_http_ocr_endpoint() or _DEFAULT_HTTP_OCR_ENDPOINT
        parts = ["curl", "-X", "POST", "-F", '"file=@sample.pdf"']
        model = self.settings.get_http_ocr_model()
        if model:
            parts.extend(["-F", f'"model={model}"'])
        api_key_env = self.settings.get_http_ocr_api_key_env() or DEFAULT_HTTP_OCR_API_KEY_ENV
        parts.extend(["-H", f'"Authorization: Bearer ${api_key_env}"', f'"{endpoint}"'])
        return " ".join(parts)

    def _build_preferred_release_asset_preflight_items(self) -> list[dict[str, str]]:
        asset = self._preferred_release_asset
        if not asset:
            return []

        size = self._format_release_asset_size(asset.get("size"))
        checksum = "SHA256 available" if asset.get("sha256") else "No SHA256 metadata"
        mode = str(asset.get("installMode") or "").strip()
        supported = bool(asset.get("installSupported"))
        reason = str(asset.get("installReason") or "").strip()
        if supported and mode == "dmg":
            action = "Download and open DMG"
            restart = "Install from the mounted DMG, then reopen the app."
        elif supported:
            action = "In-app install"
            restart = "Closes, replaces the app folder, then restarts."
        elif mode == "dmg":
            action = "Open DMG"
            restart = "Install from the mounted DMG, then reopen the app."
        else:
            action = str(asset.get("installLabel") or "Download")
            restart = reason or "Open the release asset manually."

        items = [
            {
                "label": "Selected asset",
                "value": str(asset.get("name") or "Unknown asset"),
            },
            {
                "label": "Platform",
                "value": str(asset.get("platform") or "Not specified"),
            },
            {"label": "Size", "value": size},
            {"label": "Checksum", "value": checksum},
            {"label": "Action", "value": action},
            {"label": "Restart", "value": restart},
        ]
        if reason and supported:
            items.append({"label": "Note", "value": reason})
        return items

    @staticmethod
    def _format_release_asset_size(value: object) -> str:
        try:
            size = int(value or 0)
        except (TypeError, ValueError):
            size = 0
        if size <= 0:
            return "Unknown"
        units = ("B", "KB", "MB", "GB")
        amount = float(size)
        unit_index = 0
        while amount >= 1024 and unit_index < len(units) - 1:
            amount /= 1024
            unit_index += 1
        if unit_index == 0:
            return f"{int(amount)} {units[unit_index]}"
        return f"{amount:.1f} {units[unit_index]}"

    def _build_ocr_validation_options(self) -> ConversionOptions:
        return ConversionOptions(
            ocr_enabled=self.settings.get_ocr_enabled(),
            ocr_provider=self.settings.get_ocr_provider(),
            ocr_fallback_enabled=self.settings.get_ocr_fallback_enabled(),
            ocr_fallback_provider=self.settings.get_ocr_fallback_provider(),
            docintel_endpoint=self.settings.get_docintel_endpoint(),
            ocr_languages=self.settings.get_ocr_languages(),
            tesseract_path=self.settings.get_tesseract_path(),
            glmocr_mode=self.settings.get_glmocr_mode(),
            glmocr_ollama_host=self.settings.get_glmocr_ollama_host(),
            glmocr_ollama_port=self.settings.get_glmocr_ollama_port(),
            glmocr_ollama_model=self.settings.get_glmocr_ollama_model(),
            glmocr_sdk_server_url=self.settings.get_glmocr_sdk_server_url(),
            http_ocr_endpoint=self.settings.get_http_ocr_endpoint(),
            http_ocr_model=self.settings.get_http_ocr_model(),
            http_ocr_api_key_env=self.settings.get_http_ocr_api_key_env(),
            http_ocr_timeout_seconds=self.settings.get_http_ocr_timeout_seconds(),
        )

    def _on_source_update_progress(self, status: str, progress: int) -> None:
        self._source_update_status = status
        self._source_update_progress = max(0, min(100, int(progress)))
        self.sourceUpdateChanged.emit()
        self.diagnosticsChanged.emit()

    def _on_source_update_error(self, message: str) -> None:
        self._source_update_running = False
        self._source_update_status = message
        self._source_update_progress = 0
        self.sourceUpdateChanged.emit()
        self.diagnosticsChanged.emit()
        self.toastRequested.emit("error", message)

    def _on_source_update_finished(self) -> None:
        self._source_update_running = False
        self._source_update_status = _SOURCE_UPDATE_COMPLETE_MESSAGE
        self._source_update_progress = 100
        self.sourceUpdateChanged.emit()
        self.diagnosticsChanged.emit()
        self.toastRequested.emit("success", _SOURCE_UPDATE_COMPLETE_MESSAGE)

    def _clear_source_update_runner(self) -> None:
        if self._source_update_running:
            self._source_update_running = False
            self.sourceUpdateChanged.emit()
            self.diagnosticsChanged.emit()
        self._source_update_runner = None

    def _source_update_needs_restart(self) -> bool:
        return (
            not self._source_update_running
            and self._source_update_progress == 100
            and self._source_update_status == _SOURCE_UPDATE_COMPLETE_MESSAGE
        )

    @staticmethod
    def _release_asset_to_dict(asset: ReleaseAsset) -> dict[str, object]:
        value = {
            "name": asset.name,
            "url": asset.browser_download_url,
            "size": asset.size,
            "platform": asset.platform,
            "sha256": asset.sha256,
        }
        plan = build_packaged_update_plan(value)
        value.update(
            {
                "installSupported": plan.supported,
                "installMode": plan.mode,
                "installLabel": plan.label,
                "installReason": plan.reason,
            }
        )
        return value

    def _on_update_available(self, version: str) -> None:
        self._available_update_version = version
        release = getattr(self._update_checker, "latest_release", None)
        preferred_asset = select_release_asset(release)
        self._available_release_url = getattr(release, "html_url", "") if release else ""
        self._available_release_notes = self._release_notes_excerpt(
            getattr(release, "body", "") if release else ""
        )
        self._available_release_assets = [
            self._release_asset_to_dict(asset)
            for asset in (getattr(release, "assets", ()) if release else ())
        ]
        self._preferred_release_asset = (
            self._release_asset_to_dict(preferred_asset)
            if preferred_asset
            else {}
        )
        self.updateNotificationChanged.emit()
        self.diagnosticsChanged.emit()
        if self._update_check_manual:
            self.toastRequested.emit("success", f"Update {version} is available.")

    @staticmethod
    def _release_notes_excerpt(body: str, *, max_chars: int = 360) -> str:
        lines: list[str] = []
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = line.lstrip("-*0123456789. ")
            line = _MARKDOWN_LINK_RE.sub(r"\1", line)
            line = _MARKDOWN_DECORATION_RE.sub("", line).strip()
            if line:
                lines.append(line)
            if len(lines) >= 4:
                break

        excerpt = " ".join(lines)
        if len(excerpt) <= max_chars:
            return excerpt
        return excerpt[: max(0, max_chars - 3)].rstrip() + "..."

    def _on_update_error(self, message: str) -> None:
        if self._update_check_manual:
            self.toastRequested.emit("error", message)
        else:
            AppLogger.error(f"Update check failed: {message}")

    def _on_no_update(self) -> None:
        if self._update_check_manual:
            self.toastRequested.emit("success", "You are using the latest version.")
        else:
            AppLogger.info("No updates available")
        self.diagnosticsChanged.emit()

    def _clear_update_checker(self) -> None:
        self._update_checker = None

    def _build_conversion_options(self) -> ConversionOptions:
        artifacts_dir = ""
        preserve_pdf_images = self.settings.get_preserve_pdf_images()
        preserve_docx_images = self.settings.get_preserve_docx_images()
        if preserve_pdf_images or preserve_docx_images:
            self._cleanup_temp_assets()
            self._temp_asset_root = str(create_temp_asset_root())
            artifacts_dir = self._temp_asset_root

        return ConversionOptions(
            ocr_enabled=self.settings.get_ocr_enabled(),
            preserve_pdf_images=preserve_pdf_images,
            preserve_docx_images=preserve_docx_images,
            ocr_provider=self.settings.get_ocr_provider(),
            ocr_fallback_enabled=self.settings.get_ocr_fallback_enabled(),
            ocr_fallback_provider=self.settings.get_ocr_fallback_provider(),
            docintel_endpoint=self.settings.get_docintel_endpoint(),
            ocr_languages=self.settings.get_ocr_languages(),
            tesseract_path=self.settings.get_tesseract_path(),
            pdf_artifacts_dir=artifacts_dir,
            docx_artifacts_dir=artifacts_dir,
            glmocr_mode=self.settings.get_glmocr_mode(),
            glmocr_ollama_host=self.settings.get_glmocr_ollama_host(),
            glmocr_ollama_port=self.settings.get_glmocr_ollama_port(),
            glmocr_ollama_model=self.settings.get_glmocr_ollama_model(),
            glmocr_sdk_server_url=self.settings.get_glmocr_sdk_server_url(),
            http_ocr_endpoint=self.settings.get_http_ocr_endpoint(),
            http_ocr_model=self.settings.get_http_ocr_model(),
            http_ocr_api_key_env=self.settings.get_http_ocr_api_key_env(),
            http_ocr_timeout_seconds=self.settings.get_http_ocr_timeout_seconds(),
        )

    def _handle_progress(self, progress: int, current_source: str) -> None:
        self._progress = progress
        self._set_status(f"Converting {Path(current_source).name or current_source}")
        self.progressChanged.emit()

    def _handle_finished(self, results: dict) -> None:
        worker = self.worker
        was_cancelled = self._cancel_requested or bool(worker and worker.is_cancelled)
        failed = set(worker.failed_files) if worker else set()
        self.result_model.set_results(results, failed)
        self._selected_result_index = 0 if results else -1
        self._converting = False
        self._paused = False
        self._progress = self._progress if was_cancelled else 100 if results else 0
        if was_cancelled:
            self._set_status(
                f"Cancelled after {len(results)} input{'s' if len(results) != 1 else ''}"
                if results
                else "Cancelled"
            )
        elif failed:
            failed_count = len(failed)
            converted_count = max(0, len(results) - failed_count)
            self._set_status(
                f"{converted_count} converted, {failed_count} failed"
                if converted_count
                else f"{failed_count} failed"
            )
        else:
            self._set_status(f"Converted {len(results)} input{'s' if len(results) != 1 else ''}")
        self.worker = None
        self._cancel_requested = False
        self.resultsChanged.emit()
        self.selectedResultChanged.emit()
        self.convertingChanged.emit()
        self.pausedChanged.emit()
        self.progressChanged.emit()
        self.saveDefaultsChanged.emit()
        if was_cancelled:
            self.toastRequested.emit("success", "Conversion cancelled.")
        elif failed:
            failed_count = len(failed)
            self.toastRequested.emit(
                "error",
                "1 conversion failed."
                if failed_count == 1
                else f"{failed_count} conversions failed.",
            )
        else:
            self.toastRequested.emit("success", "Conversion complete.")

    def _set_status(self, value: str) -> None:
        if value == self._status:
            return
        self._status = value
        self.statusChanged.emit()

    def _queue_change_locked(self) -> bool:
        if not self._converting:
            return False
        self.toastRequested.emit(
            "error",
            "Wait for conversion to finish before changing the queue.",
        )
        return True

    def _clear_results_after_queue_change(self) -> None:
        if self.result_model.rowCount() == 0:
            return
        self.clearResults()

    def _cleanup_temp_assets(self) -> None:
        cleanup_temp_asset_root(self._temp_asset_root)
        self._temp_asset_root = None

    def _paths_from_variant(self, values: Any) -> list[str]:
        if values is None:
            return []
        if isinstance(values, (str, QUrl)):
            values = [values]
        return [self._path_from_url(value) for value in values]

    def _path_from_url(self, value: Any) -> str:
        if isinstance(value, QUrl):
            if value.isLocalFile():
                return value.toLocalFile()
            return value.toString()
        text = str(value or "").strip()
        if not text:
            return ""
        url = QUrl(text)
        if url.isValid() and url.isLocalFile():
            return url.toLocalFile()
        if text.startswith("file:///"):
            return QUrl(text).toLocalFile()
        return text

    def _unique_output_path(self, output_dir: str, source: str) -> str:
        output_ext = self.settings.get_default_output_format()
        path = Path(output_dir) / f"{source_output_stem(source)}{output_ext}"
        counter = 1
        while path.exists():
            path = Path(output_dir) / f"{source_output_stem(source)}_{counter}{output_ext}"
            counter += 1
        return str(path)

    def _separate_output_dir(self, fallback_dir: str, source: str) -> str:
        if self.settings.get_save_to_source_folder():
            source_dir = source_output_dir(source)
            if source_dir and self._is_writable_output_dir(source_dir):
                return source_dir
        return fallback_dir

    def _can_save_separate_without_dialog(self, items: list[Any] | None = None) -> bool:
        if not self.settings.get_save_to_source_folder():
            return False

        items = (
            self._successful_result_items()
            if items is None
            else self._successful_result_items(items)
        )
        if not items:
            return False

        return all(self._separate_output_dir("", item.source) for item in items)

    def _dialog_output_dir(self) -> str:
        output_dir = self.settings.get_default_output_folder()
        if output_dir:
            return output_dir

        items = self._successful_result_items()
        if not items:
            return ""
        return self._separate_output_dir("", items[0].source)

    def _successful_result_items(self, items: list[Any] | None = None) -> list[Any]:
        result_items = self.result_model.items() if items is None else items
        return [item for item in result_items if not item.failed]

    def _failed_result_items(self, items: list[Any] | None = None) -> list[Any]:
        result_items = self.result_model.items() if items is None else items
        return [item for item in result_items if item.failed]

    @staticmethod
    def _folder_url(folder: str) -> str:
        return QUrl.fromLocalFile(folder).toString() if folder else ""

    @staticmethod
    def _is_writable_output_dir(output_dir: str) -> bool:
        if not output_dir or not os.path.isdir(output_dir):
            return False
        probe_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                dir=output_dir,
                prefix=".markitdown-gui-",
                suffix=".tmp",
                delete=False,
            ) as probe:
                probe_path = probe.name
            return True
        except OSError:
            return False
        finally:
            if probe_path:
                try:
                    os.unlink(probe_path)
                except OSError:
                    pass

    def _preview_css(self) -> str:
        if self.darkMode:
            return (
                "body{background:#2b313c;color:#eceff4;font-family:Segoe UI,Arial,sans-serif;"
                "font-size:14px;line-height:1.68;margin:0;} "
                "h1{font-size:18px;line-height:1.28;margin:0 0 14px;font-weight:700;color:#f4f7fb;} "
                "h2{font-size:15px;line-height:1.36;margin:18px 0 8px;font-weight:700;color:#eceff4;} "
                "h3{font-size:14px;margin:18px 0 8px;color:#eceff4;} p{margin:0 0 14px;} "
                "a{color:#88c0d0;} strong{color:#f4f7fb;} "
                "code{background:#3b4252;border-radius:5px;padding:2px 5px;font-family:Cascadia Mono,Consolas,monospace;"
                "font-size:13px;color:#eceff4;} pre{background:#3b4252;border:1px solid #566176;border-radius:8px;"
                "padding:12px 14px;margin:14px 0;color:#eceff4;} "
                "table{border-collapse:collapse;margin:12px 0 16px;font-size:13px;} "
                "th{background:#3b4252;color:#f4f7fb;font-weight:700;} "
                "td,th{border:1px solid #657083;padding:7px 10px;} "
                "blockquote{border-left:3px solid #88c0d0;background:#303744;margin:14px 0;padding:10px 14px;"
                "border-radius:6px;color:#d8dee9;} ul,ol{margin:0 0 14px 22px;} hr{border:0;border-top:1px solid #4c566a;}"
            )
        return (
            "body{background:#fffef7;color:#073642;font-family:Segoe UI,Arial,sans-serif;"
            "font-size:14px;line-height:1.68;margin:0;} "
            "h1{font-size:18px;line-height:1.28;margin:0 0 14px;font-weight:700;color:#073642;} "
            "h2{font-size:15px;line-height:1.36;margin:18px 0 8px;font-weight:700;color:#073642;} "
            "h3{font-size:14px;margin:18px 0 8px;color:#073642;} p{margin:0 0 14px;} "
            "a{color:#687700;} strong{color:#073642;} "
            "code{background:#eee8d5;border-radius:5px;padding:2px 5px;font-family:Cascadia Mono,Consolas,monospace;"
            "font-size:13px;color:#073642;} pre{background:#eee8d5;border:1px solid #d6ccb2;border-radius:8px;"
            "padding:12px 14px;margin:14px 0;color:#073642;} "
            "table{border-collapse:collapse;margin:12px 0 16px;font-size:13px;} "
            "th{background:#eee8d5;color:#073642;font-weight:700;} "
            "td,th{border:1px solid #cfc4a8;padding:7px 10px;} "
            "blockquote{border-left:3px solid #687700;background:#f6efd8;margin:14px 0;padding:10px 14px;"
            "border-radius:6px;color:#586e75;} ul,ol{margin:0 0 14px 22px;} hr{border:0;border-top:1px solid #d6ccb2;}"
        )

    @staticmethod
    def _compact_preview_html(html: str) -> str:
        # Qt RichText applies built-in heading scale even when the span font is restyled.
        html = (
            html.replace("font-size:xx-large;", "font-size:18px;")
            .replace("font-size:x-large;", "font-size:15px;")
            .replace("font-size:large;", "font-size:14px;")
        )
        html = _PREVIEW_HEADING_RE.sub(AppController._preview_heading_to_paragraph, html)
        return (
            html.replace("</h1>", "</p>")
            .replace("</h2>", "</p>")
            .replace("</h3>", "</p>")
        )

    @staticmethod
    def _preview_heading_to_paragraph(match: re.Match[str]) -> str:
        level, style, span_style = match.groups()
        margin = _PREVIEW_HEADING_MARGINS[level]
        style = style.replace("margin-bottom:0px;", f"margin-bottom:{margin};")
        return f'<p style="{style}"><span style="{span_style}">'

    def translate(self, key: str) -> str:
        lang = self.settings.get_current_language() or DEFAULT_LANG
        return get_translation(lang, key)

