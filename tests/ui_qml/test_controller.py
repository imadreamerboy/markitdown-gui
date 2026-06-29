from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QSettings, QUrl

from markitdowngui.core.conversion import ConversionOutcome
from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui_qml.controller import AppController


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

