import pytest
from PySide6.QtCore import QSettings

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

