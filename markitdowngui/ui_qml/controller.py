from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication, QPalette, QTextDocument

from markitdowngui.core.conversion import ConversionOptions, ConversionWorker
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
from markitdowngui.utils.logger import AppLogger
from markitdowngui.utils.translations import DEFAULT_LANG, get_translation
from markitdowngui.utils.update_checker import UpdateChecker


_PREVIEW_HEADING_RE = re.compile(r'<h([1-3]) style="([^"]*)"><span style="([^"]*)">')
_PREVIEW_HEADING_MARGINS = {
    "1": "10px",
    "2": "8px",
    "3": "6px",
}


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
        self._update_check_manual = False
        self._available_update_version = ""

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
        self.settingsChanged.emit()

    @Slot(bool)
    def setOcrFallbackEnabled(self, enabled: bool) -> None:
        self.settings.set_ocr_fallback_enabled(enabled)
        self.settingsChanged.emit()

    @Slot(str)
    def setGlmocrMode(self, mode: str) -> None:
        self.settings.set_glmocr_mode(mode)
        self.settingsChanged.emit()

    @Slot(str)
    def setGlmocrOllamaHost(self, value: str) -> None:
        self.settings.set_glmocr_ollama_host(value)
        self.settingsChanged.emit()

    @Slot(int)
    def setGlmocrOllamaPort(self, value: int) -> None:
        self.settings.set_glmocr_ollama_port(value)
        self.settingsChanged.emit()

    @Slot(str)
    def setGlmocrOllamaModel(self, value: str) -> None:
        self.settings.set_glmocr_ollama_model(value)
        self.settingsChanged.emit()

    @Slot(str)
    def setGlmocrSdkServerUrl(self, value: str) -> None:
        self.settings.set_glmocr_sdk_server_url(value)
        self.settingsChanged.emit()

    @Slot(str)
    def setDocintelEndpoint(self, value: str) -> None:
        self.settings.set_docintel_endpoint(value)
        self.settingsChanged.emit()

    @Slot(str)
    def setOcrLanguages(self, value: str) -> None:
        self.settings.set_ocr_languages(value)
        self.settingsChanged.emit()

    @Slot(str)
    def setTesseractPath(self, value: str) -> None:
        self.settings.set_tesseract_path(value)
        self.settingsChanged.emit()

    @Slot()
    def startAutomaticUpdateCheck(self) -> None:
        if self.settings.get_update_notifications_enabled():
            self._start_update_check(manual=False)

    @Slot()
    def checkForUpdates(self) -> None:
        self._start_update_check(manual=True)

    @Slot()
    def dismissUpdateNotification(self) -> None:
        if not self._available_update_version:
            return
        self._available_update_version = ""
        self.updateNotificationChanged.emit()

    @Slot()
    def disableUpdateNotifications(self) -> None:
        self.settings.set_update_notifications_enabled(False)
        self.settingsChanged.emit()
        self.dismissUpdateNotification()
        self.toastRequested.emit("success", "Update notifications disabled.")

    @Slot()
    def openReleases(self) -> None:
        self.openExternalUrl("https://github.com/imadreamerboy/markitdown-gui/releases")
        self.dismissUpdateNotification()

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

    def _on_update_available(self, version: str) -> None:
        self._available_update_version = version
        self.updateNotificationChanged.emit()
        if self._update_check_manual:
            self.toastRequested.emit("success", f"Update {version} is available.")

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

