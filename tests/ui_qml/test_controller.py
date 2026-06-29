from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QSettings, QUrl

from markitdowngui.core.conversion import ConversionOutcome
from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui_qml.controller import AppController


class _FakeSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self._callbacks):
            callback(*args)


class _FakeUpdateChecker:
    def __init__(self, action: tuple[str, str | None]):
        self.action = action
        self.update_available = _FakeSignal()
        self.update_error = _FakeSignal()
        self.no_update_available = _FakeSignal()
        self.finished = _FakeSignal()
        self.started = False
        self.waited = False

    def start(self):
        self.started = True
        kind, value = self.action
        if kind == "available":
            self.update_available.emit(value or "")
        elif kind == "error":
            self.update_error.emit(value or "")
        elif kind == "none":
            self.no_update_available.emit()
        self.finished.emit()

    def isRunning(self):
        return self.started and not self.waited

    def wait(self, _timeout):
        self.waited = True
        return True


@pytest.fixture
def controller(tmp_path):
    controller = AppController()
    settings = SettingsManager()
    settings.settings = QSettings(
        str(tmp_path / "settings.ini"),
        QSettings.Format.IniFormat,
    )
    controller.settings = settings
    return controller


def test_controller_add_url_rejects_invalid_url(controller):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))

    controller.addUrl("not a url")

    assert controller.queue_model.rowCount() == 0
    assert messages == [("error", "Enter a valid http:// or https:// URL.")]


def test_controller_add_url_queues_valid_url(controller):
    controller.addUrl("https://example.com/article")

    assert controller.queue_model.sources() == ["https://example.com/article"]
    assert controller.hasQueue is True
    assert controller.queueCount == 1


def test_controller_auto_update_check_respects_disabled_setting(controller, monkeypatch):
    controller.settings.set_update_notifications_enabled(False)
    monkeypatch.setattr(
        controller,
        "_create_update_checker",
        lambda: pytest.fail("update checker should not start"),
    )

    controller.startAutomaticUpdateCheck()

    assert controller.hasUpdateNotification is False


def test_controller_auto_update_check_exposes_available_release(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    changes: list[None] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller.updateNotificationChanged.connect(lambda: changes.append(None))
    monkeypatch.setattr(
        controller,
        "_create_update_checker",
        lambda: _FakeUpdateChecker(("available", "v1.2.0")),
    )

    controller.startAutomaticUpdateCheck()

    assert controller.hasUpdateNotification is True
    assert controller.availableUpdateVersion == "v1.2.0"
    assert changes == [None]
    assert messages == []


def test_controller_manual_update_check_reports_no_update(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        controller,
        "_create_update_checker",
        lambda: _FakeUpdateChecker(("none", None)),
    )

    controller.checkForUpdates()

    assert messages == [("success", "You are using the latest version.")]


def test_controller_manual_update_check_reports_error(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        controller,
        "_create_update_checker",
        lambda: _FakeUpdateChecker(("error", "Network unavailable")),
    )

    controller.checkForUpdates()

    assert messages == [("error", "Network unavailable")]


def test_controller_dismisses_update_notification(controller, monkeypatch):
    monkeypatch.setattr(
        controller,
        "_create_update_checker",
        lambda: _FakeUpdateChecker(("available", "v1.2.0")),
    )
    controller.startAutomaticUpdateCheck()

    controller.dismissUpdateNotification()

    assert controller.hasUpdateNotification is False
    assert controller.availableUpdateVersion == ""


def test_controller_disables_update_notifications_from_banner(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        controller,
        "_create_update_checker",
        lambda: _FakeUpdateChecker(("available", "v1.2.0")),
    )
    controller.startAutomaticUpdateCheck()

    controller.disableUpdateNotifications()

    assert controller.settings.get_update_notifications_enabled() is False
    assert controller.hasUpdateNotification is False
    assert controller.availableUpdateVersion == ""
    assert messages == [("success", "Update notifications disabled.")]


def test_controller_locks_queue_mutations_while_converting(controller, tmp_path):
    source_a = str(tmp_path / "a.pdf")
    source_b = str(tmp_path / "b.pdf")
    source_c = str(tmp_path / "c.pdf")
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller.addFiles([source_a, source_b])
    controller._converting = True

    controller.addFiles([source_c])
    controller.removeQueued(0)
    controller.clearQueue()

    assert controller.queue_model.sources() == [source_a, source_b]
    assert messages[-3:] == [
        ("error", "Wait for conversion to finish before changing the queue."),
        ("error", "Wait for conversion to finish before changing the queue."),
        ("error", "Wait for conversion to finish before changing the queue."),
    ]


def test_controller_add_files_invalidates_stale_results(controller, tmp_path):
    source_a = str(tmp_path / "a.pdf")
    source_b = str(tmp_path / "b.pdf")
    controller.addFiles([source_a])
    controller.result_model.set_results(
        {source_a: ConversionOutcome("# Converted", backend="native")}
    )
    controller.selectResult(0)

    controller.addFiles([source_b])

    assert controller.result_model.rowCount() == 0
    assert controller.selectedResultIndex == -1
    assert controller.queue_model.sources() == [source_a, source_b]


def test_controller_remove_queued_invalidates_stale_results(controller, tmp_path):
    source_a = str(tmp_path / "a.pdf")
    source_b = str(tmp_path / "b.pdf")
    controller.addFiles([source_a, source_b])
    controller.result_model.set_results(
        {source_a: ConversionOutcome("# Converted", backend="native")}
    )
    controller.selectResult(0)

    controller.removeQueued(0)

    assert controller.result_model.rowCount() == 0
    assert controller.selectedResultIndex == -1
    assert controller.queue_model.sources() == [source_b]


def test_controller_clear_queue_invalidates_stale_results(controller, tmp_path):
    source = str(tmp_path / "a.pdf")
    controller.addFiles([source])
    controller.result_model.set_results(
        {source: ConversionOutcome("# Converted", backend="native")}
    )
    controller.selectResult(0)

    controller.clearQueue()

    assert controller.result_model.rowCount() == 0
    assert controller.selectedResultIndex == -1
    assert controller.queue_model.sources() == []


def test_controller_clear_empty_queue_invalidates_stale_results(controller):
    controller.result_model.set_results(
        {"C:/tmp/a.pdf": ConversionOutcome("# Converted", backend="native")}
    )
    controller.selectResult(0)

    controller.clearQueue()

    assert controller.result_model.rowCount() == 0
    assert controller.selectedResultIndex == -1
    assert controller.queue_model.sources() == []


def test_controller_notifies_before_save_dialog_when_no_output(controller):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))

    controller.notifyNoOutputToSave()

    assert messages == [("error", "No output to save.")]


def test_controller_separate_save_prefers_source_folder_for_local_files(
    controller,
    tmp_path,
):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / "report.pdf"
    source_file.write_text("input", encoding="utf-8")
    fallback_dir = tmp_path / "chosen"

    controller.settings.set_save_to_source_folder(True)
    controller.result_model.set_results(
        {
            str(source_file): ConversionOutcome("# Local\n\nBody", backend="native"),
            "https://example.com/docs/page": ConversionOutcome(
                "# Web\n\nBody",
                backend="defuddle",
            ),
        }
    )

    controller.saveSeparateOutputs(str(fallback_dir))

    assert (source_dir / "report.md").read_text(encoding="utf-8") == "# Local\n\nBody"
    assert (fallback_dir / "example.com-page.md").read_text(
        encoding="utf-8"
    ) == "# Web\n\nBody"


def test_controller_separate_save_can_skip_dialog_for_local_source_folders(
    controller,
    tmp_path,
):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / "report.pdf"
    source_file.write_text("input", encoding="utf-8")

    controller.settings.set_save_to_source_folder(True)
    controller.result_model.set_results(
        {str(source_file): ConversionOutcome("# Local\n\nBody", backend="native")}
    )

    assert controller.canSaveSeparateWithoutDialog is True

    controller.saveSeparateOutputs("")

    assert (source_dir / "report.md").read_text(encoding="utf-8") == "# Local\n\nBody"


def test_controller_separate_save_requires_fallback_for_web_sources(
    controller,
):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller.settings.set_save_to_source_folder(True)
    controller.result_model.set_results(
        {"https://example.com/docs": ConversionOutcome("# Web\n\nBody", backend="defuddle")}
    )

    assert controller.canSaveSeparateWithoutDialog is False

    controller.saveSeparateOutputs("")

    assert messages == [("error", "Choose an output folder before saving.")]


def test_controller_save_combined_skips_failed_results(controller, tmp_path):
    output_path = tmp_path / "combined.md"
    controller.result_model.set_results(
        {
            "C:/tmp/ok.pdf": ConversionOutcome("# Converted\n\nBody", backend="native"),
            "C:/tmp/broken.pdf": ConversionOutcome(
                "Error converting broken.pdf",
                backend="native",
            ),
        },
        {"C:/tmp/broken.pdf"},
    )

    assert controller.hasSuccessfulResults is True

    controller.saveCombinedOutput(str(output_path))

    saved = output_path.read_text(encoding="utf-8")
    assert "# Converted" in saved
    assert "Error converting broken.pdf" not in saved
    assert "C:/tmp/broken.pdf" not in saved


def test_controller_save_separate_skips_failed_results(controller, tmp_path):
    output_dir = tmp_path / "exports"
    controller.result_model.set_results(
        {
            "C:/tmp/ok.pdf": ConversionOutcome("# Converted\n\nBody", backend="native"),
            "C:/tmp/broken.pdf": ConversionOutcome(
                "Error converting broken.pdf",
                backend="native",
            ),
        },
        {"C:/tmp/broken.pdf"},
    )

    controller.saveSeparateOutputs(str(output_dir))

    saved_files = sorted(path.name for path in output_dir.glob("*.md"))
    assert saved_files == ["ok.md"]
    assert (output_dir / "ok.md").read_text(encoding="utf-8") == "# Converted\n\nBody"


def test_controller_save_all_failed_results_reports_no_success(controller, tmp_path):
    output_path = tmp_path / "combined.md"
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller.result_model.set_results(
        {
            "C:/tmp/broken.pdf": ConversionOutcome(
                "Error converting broken.pdf",
                backend="native",
            )
        },
        {"C:/tmp/broken.pdf"},
    )

    assert controller.hasSuccessfulResults is False
    assert controller.suggestedCombinedOutputUrl == ""

    controller.saveCombinedOutput(str(output_path))

    assert not output_path.exists()
    assert messages == [("error", "No successful output to save.")]


def test_controller_finished_status_reports_mixed_failures(controller):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller.worker = SimpleNamespace(
        is_cancelled=False,
        failed_files={"C:/tmp/broken.pdf"},
    )
    controller._converting = True

    controller._handle_finished(
        {
            "C:/tmp/ok.pdf": ConversionOutcome("# Converted", backend="native"),
            "C:/tmp/broken.pdf": ConversionOutcome("Conversion failed", backend="native"),
        }
    )

    assert controller.statusText == "1 converted, 1 failed"
    assert controller.hasSuccessfulResults is True
    assert messages == [("error", "1 conversion failed.")]


def test_controller_finished_status_reports_all_failed(controller):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller.worker = SimpleNamespace(
        is_cancelled=False,
        failed_files={"C:/tmp/broken.pdf"},
    )
    controller._converting = True

    controller._handle_finished(
        {"C:/tmp/broken.pdf": ConversionOutcome("Conversion failed", backend="native")}
    )

    assert controller.statusText == "1 failed"
    assert controller.hasSuccessfulResults is False
    assert messages == [("error", "1 conversion failed.")]


def test_controller_separate_save_falls_back_when_source_folder_is_not_writable(
    controller,
    monkeypatch,
    tmp_path,
):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / "report.pdf"
    fallback_dir = tmp_path / "chosen"
    fallback_dir.mkdir()

    controller.settings.set_save_to_source_folder(True)
    monkeypatch.setattr(
        AppController,
        "_is_writable_output_dir",
        staticmethod(lambda output_dir: output_dir == str(fallback_dir)),
    )

    output_dir = controller._separate_output_dir(str(fallback_dir), str(source_file))

    assert output_dir == str(fallback_dir)


def test_controller_suggests_output_paths_from_settings(controller, tmp_path):
    output_dir = tmp_path / "exports"
    source_file = tmp_path / "quarterly report.pdf"
    controller.settings.set_default_output_folder(str(output_dir))
    controller.result_model.set_results(
        {str(source_file): ConversionOutcome("# Local\n\nBody", backend="native")}
    )

    assert Path(QUrl(controller.outputFolderUrl).toLocalFile()) == output_dir
    assert Path(QUrl(controller.suggestedSeparateOutputFolderUrl).toLocalFile()) == output_dir
    assert Path(QUrl(controller.suggestedCombinedOutputUrl).toLocalFile()) == (
        output_dir / "quarterly report.md"
    )


def test_controller_cancel_unpauses_worker(controller):
    worker = SimpleNamespace(is_paused=True, is_cancelled=False)
    controller.worker = worker
    controller._converting = True
    controller._paused = True
    changes: list[None] = []
    controller.pausedChanged.connect(lambda: changes.append(None))

    controller.cancel()

    assert worker.is_cancelled is True
    assert worker.is_paused is False
    assert controller.paused is False
    assert controller.statusText == "Cancelling"
    assert changes == [None]


def test_controller_shutdown_rejects_close_until_worker_stops(controller):
    worker = SimpleNamespace(
        is_paused=True,
        is_cancelled=False,
        isRunning=lambda: True,
        wait=lambda timeout: False,
    )
    controller.worker = worker
    controller._converting = True
    controller._paused = True
    messages: list[tuple[str, str]] = []
    pause_changes: list[None] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller.pausedChanged.connect(lambda: pause_changes.append(None))

    accepted = controller.shutdown()

    assert accepted is False
    assert worker.is_cancelled is True
    assert worker.is_paused is False
    assert controller.paused is False
    assert controller.statusText == "Cancelling"
    assert pause_changes == [None]
    assert messages == [
        ("error", "Conversion is still stopping. Close again after it finishes.")
    ]


def test_controller_shutdown_cleans_up_after_worker_stops(controller, monkeypatch):
    worker = SimpleNamespace(
        is_cancelled=False,
        is_paused=False,
        isRunning=lambda: True,
        wait=lambda timeout: True,
    )
    controller.worker = worker
    controller._temp_asset_root = "C:/tmp/markitdown-assets"
    cleaned: list[str | None] = []
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.cleanup_temp_asset_root",
        lambda path: cleaned.append(path),
    )

    accepted = controller.shutdown()

    assert accepted is True
    assert worker.is_cancelled is True
    assert cleaned == ["C:/tmp/markitdown-assets"]
    assert controller._temp_asset_root is None


def test_controller_theme_change_refreshes_selected_preview(controller):
    controller.result_model.set_results(
        {"C:/tmp/report.pdf": ConversionOutcome("# Title", backend="native")}
    )
    controller.selectResult(0)
    changes: list[None] = []
    controller.selectedResultChanged.connect(lambda: changes.append(None))

    controller.setThemeMode("dark")

    assert changes == [None]
    assert "background:#2b313c" in controller.selectedPreviewHtml


def test_controller_light_preview_uses_olive_accents(controller):
    controller.setThemeMode("light")
    controller.result_model.set_results(
        {
            "C:/tmp/report.pdf": ConversionOutcome(
                "# Title\n\n[Release notes](https://example.com)\n\n> Check OCR.",
                backend="native",
            )
        }
    )
    controller.selectResult(0)

    html = controller.selectedPreviewHtml

    assert "a{color:#687700;}" in html
    assert "blockquote{border-left:3px solid #687700;" in html
    assert "#268bd2" not in html
    assert "#2aa198" not in html


def test_controller_preview_compacts_qt_heading_sizes(controller):
    controller.result_model.set_results(
        {
            "C:/tmp/report.pdf": ConversionOutcome(
                "# Title\n\n## Section\n\n### Detail",
                backend="native",
            )
        }
    )
    controller.selectResult(0)

    html = controller.selectedPreviewHtml

    assert "font-size:xx-large;" not in html
    assert "font-size:x-large;" not in html
    assert "font-size:large;" not in html
    assert "font-size:18px;" in html
    assert "font-size:15px;" in html
    assert "font-size:14px;" in html
    assert "<h1" not in html
    assert "<h2" not in html
    assert "<h3" not in html


def test_controller_exposes_selected_failed_result(controller):
    controller.result_model.set_results(
        {
            "C:/tmp/ok.pdf": ConversionOutcome("# Title", backend="native"),
            "C:/tmp/broken.pdf": ConversionOutcome("Conversion failed", backend="native"),
        },
        {"C:/tmp/broken.pdf"},
    )

    controller.selectResult(0)
    assert controller.selectedResultFailed is False

    controller.selectResult(1)
    assert controller.selectedResultFailed is True

