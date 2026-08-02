from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QSettings, QUrl

from markitdowngui.core.conversion import ConversionAsset, ConversionOutcome
from markitdowngui.core.markdown_assets import (
    prepare_markdown_for_separate_save,
    prepare_markdown_for_separate_save_transaction,
)
from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui_qml.controller import (
    AppController,
    PackagedUpdateInstaller,
    SourceUpdateInstaller,
)
from markitdowngui.utils.packaged_updater import PackagedUpdatePlan
from markitdowngui.utils.source_updater import SOURCE_UPDATE_DIRTY
from markitdowngui.utils.update_checker import ReleaseAsset, ReleaseInfo


class _FakeSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self._callbacks):
            callback(*args)


class _FakeUpdateChecker:
    def __init__(
        self,
        action: tuple[str, str | None],
        release: ReleaseInfo | None = None,
    ):
        self.action = action
        self.latest_release = release
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


class _FakeUpdateInstaller:
    def __init__(self, action: str = "success"):
        self.action = action
        self.progressChanged = _FakeSignal()
        self.installStarted = _FakeSignal()
        self.manualInstallOpened = _FakeSignal()
        self.installError = _FakeSignal()
        self.finished = _FakeSignal()
        self.started = False
        self.waited = False

    def start(self):
        self.started = True
        self.progressChanged.emit("Downloading update", 25)
        if self.action == "error":
            self.installError.emit("Download failed")
        elif self.action == "manual":
            self.progressChanged.emit("DMG opened", 100)
            self.manualInstallOpened.emit("C:/Users/test/Downloads/MarkItDown.dmg")
        else:
            self.progressChanged.emit("Starting restart helper", 98)
            self.installStarted.emit()
        self.finished.emit()

    def isRunning(self):
        return self.started and not self.waited

    def wait(self, _timeout):
        self.waited = True
        return True


class _FakeSourceUpdateRunner:
    def __init__(self, action: str = "success"):
        self.action = action
        self.progressChanged = _FakeSignal()
        self.updateFinished = _FakeSignal()
        self.updateError = _FakeSignal()
        self.finished = _FakeSignal()
        self.started = False
        self.waited = False

    def start(self):
        self.started = True
        self.progressChanged.emit("Pulling latest source", 15)
        if self.action == "error":
            self.updateError.emit("Source update failed with exit code 1.")
        else:
            self.progressChanged.emit("Source update complete", 100)
            self.updateFinished.emit()
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


def _complete_results(
    controller: AppController,
    results: dict[str, ConversionOutcome],
    failed_sources: set[str] | None = None,
) -> None:
    controller.worker = SimpleNamespace(
        is_cancelled=False,
        failed_files=failed_sources or set(),
    )
    controller._converting = True
    controller._handle_finished(results)


def test_controller_add_url_rejects_invalid_url(controller):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))

    controller.addUrl("not a url")

    assert controller.queue_model.rowCount() == 0
    assert messages == [("error", "Enter a valid http:// or https:// URL.")]


def test_controller_add_url_queues_valid_url(controller):
    assert controller.addUrl("https://example.com/article") is True

    assert controller.queue_model.sources() == ["https://example.com/article"]
    assert controller.hasQueue is True
    assert controller.queueCount == 1


def test_controller_add_url_waits_for_discard_confirmation(controller, tmp_path):
    source = str(tmp_path / "existing.pdf")
    url = "https://example.com/article"
    controller.addFiles([source])
    _complete_results(
        controller,
        {source: ConversionOutcome("# Existing", backend="native")},
    )
    requests: list[str] = []
    queued_urls: list[str] = []
    controller.discardResultsRequested.connect(requests.append)
    controller.urlQueued.connect(queued_urls.append)

    assert controller.addUrl(url) is False
    assert requests == ["add inputs to the queue"]
    assert queued_urls == []

    controller.cancelPendingResultDiscard()

    assert controller.queue_model.sources() == [source]
    assert queued_urls == []

    assert controller.addUrl(url) is False
    controller.discardPendingResults()

    assert controller.queue_model.sources() == [source, url]
    assert queued_urls == [url]


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


def test_controller_exposes_release_assets_for_packaged_updates(controller, monkeypatch):
    release = ReleaseInfo(
        tag_name="v1.2.0",
        html_url="https://github.com/example/releases/tag/v1.2.0",
        body="## Changes\n\n- Faster updater\n- [Fixes](https://example.com) for OCR",
        assets=(
            ReleaseAsset(
                name="MarkItDown-Linux.zip",
                browser_download_url="https://example.com/linux.zip",
                size=41,
                platform="Linux",
            ),
            ReleaseAsset(
                name="MarkItDown-Windows.zip",
                browser_download_url="https://example.com/windows.zip",
                size=42,
                platform="Windows",
                sha256="abc123",
            ),
        ),
    )
    opened: list[str] = []
    monkeypatch.setattr(
        controller,
        "_create_update_checker",
        lambda: _FakeUpdateChecker(("available", "v1.2.0"), release),
    )
    monkeypatch.setattr(controller, "openExternalUrl", lambda url: opened.append(url))

    controller.startAutomaticUpdateCheck()

    assert controller.availableReleaseUrl == release.html_url
    assert controller.availableReleaseNotes == "Changes Faster updater Fixes for OCR"
    assert controller.availableReleaseAssets == [
        {
            "name": "MarkItDown-Linux.zip",
            "url": "https://example.com/linux.zip",
            "size": 41,
            "platform": "Linux",
            "sha256": "",
            "installSupported": False,
            "installMode": "source",
            "installLabel": "Download",
            "installReason": "Packaged install is available only in packaged builds.",
        },
        {
            "name": "MarkItDown-Windows.zip",
            "url": "https://example.com/windows.zip",
            "size": 42,
            "platform": "Windows",
            "sha256": "abc123",
            "installSupported": False,
            "installMode": "source",
            "installLabel": "Download",
            "installReason": "Packaged install is available only in packaged builds.",
        }
    ]
    if controller.preferredReleaseAsset:
        assert controller.preferredReleaseAsset["url"] in {
            "https://example.com/linux.zip",
            "https://example.com/windows.zip",
        }
        assert controller.preferredReleaseAssetPreflightItems

    controller.openReleaseAsset("https://example.com/windows.zip")

    assert opened == ["https://example.com/windows.zip"]
    assert controller.hasUpdateNotification is False
    assert controller.availableReleaseNotes == ""


def test_controller_exposes_preflight_for_supported_packaged_update(controller):
    controller._preferred_release_asset = {
        "name": "MarkItDown-Windows.zip",
        "url": "https://example.com/windows.zip",
        "size": 42 * 1024 * 1024,
        "platform": "Windows",
        "sha256": "abc123",
        "installSupported": True,
        "installMode": "zip",
        "installLabel": "Install update",
        "installReason": "",
    }

    rows = {
        item["label"]: item["value"]
        for item in controller.preferredReleaseAssetPreflightItems
    }

    assert rows == {
        "Selected asset": "MarkItDown-Windows.zip",
        "Platform": "Windows",
        "Size": "42.0 MB",
        "Checksum": "SHA256 available",
        "Action": "In-app install",
        "Restart": "Closes, replaces the app folder, then restarts.",
    }


def test_controller_exposes_preflight_for_manual_release_asset(controller):
    controller._preferred_release_asset = {
        "name": "MarkItDown-macOS.dmg",
        "url": "https://example.com/macos.dmg",
        "size": 0,
        "platform": "macOS",
        "sha256": "",
        "installSupported": False,
        "installMode": "dmg",
        "installLabel": "Open DMG",
        "installReason": "macOS DMG updates are installed outside the running app.",
    }

    rows = {
        item["label"]: item["value"]
        for item in controller.preferredReleaseAssetPreflightItems
    }

    assert rows["Size"] == "Unknown"
    assert rows["Checksum"] == "No SHA256 metadata"
    assert rows["Action"] == "Open DMG"
    assert rows["Restart"] == "Install from the mounted DMG, then reopen the app."


def test_controller_exposes_preflight_for_supported_dmg_update(controller):
    controller._preferred_release_asset = {
        "name": "MarkItDown-macOS.dmg",
        "url": "https://example.com/macos.dmg",
        "size": 12 * 1024 * 1024,
        "platform": "macOS",
        "sha256": "abc123",
        "installSupported": True,
        "installMode": "dmg",
        "installLabel": "Download DMG",
        "installReason": "The app will download, verify, and open the DMG.",
    }

    rows = {
        item["label"]: item["value"]
        for item in controller.preferredReleaseAssetPreflightItems
    }

    assert rows["Action"] == "Download and open DMG"
    assert rows["Restart"] == "Install from the mounted DMG, then reopen the app."


def test_controller_release_notes_excerpt_cleans_markdown_and_caps_length():
    body = "\n".join(
        [
            "## Release notes",
            "- **Installer** now shows progress",
            "- [OCR fix](https://example.com) for setup validation",
            "- " + ("Long detail " * 80),
        ]
    )

    excerpt = AppController._release_notes_excerpt(body, max_chars=80)

    assert "Installer now shows progress" in excerpt
    assert "OCR fix" in excerpt
    assert "[" not in excerpt
    assert "**" not in excerpt
    assert excerpt.endswith("...")
    assert len(excerpt) <= 80


def test_controller_installs_supported_preferred_update(controller, monkeypatch):
    release = ReleaseInfo(
        tag_name="v1.2.0",
        html_url="https://github.com/example/releases/tag/v1.2.0",
        assets=(
            ReleaseAsset(
                name="MarkItDown-Windows.zip",
                browser_download_url="https://example.com/windows.zip",
                platform="Windows",
            ),
        ),
    )
    messages: list[tuple[str, str]] = []
    created: list[dict[str, object]] = []
    quit_called: list[None] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_packaged_update_plan",
        lambda _asset: PackagedUpdatePlan(True, "zip", "Install update"),
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.quit",
        lambda: quit_called.append(None),
    )
    monkeypatch.setattr(
        controller,
        "_create_update_installer",
        lambda asset: created.append(asset) or _FakeUpdateInstaller(),
    )
    monkeypatch.setattr(
        controller,
        "_create_update_checker",
        lambda: _FakeUpdateChecker(("available", "v1.2.0"), release),
    )

    controller.startAutomaticUpdateCheck()
    assert controller.canInstallPreferredUpdate is True

    controller.installPreferredUpdate()

    assert created and created[0]["url"] == "https://example.com/windows.zip"
    assert controller.updateInstallRunning is False
    assert controller.updateInstallProgress == 100
    assert controller.updateInstallStatus == "Restarting app"
    assert quit_called == [None]
    assert messages == [("success", "Update installer started. Closing app.")]
    assert controller.hasUpdateNotification is False


def test_controller_confirms_before_starting_update_with_unsaved_results(
    controller, monkeypatch, tmp_path
):
    source = str(tmp_path / "result.pdf")
    _complete_results(
        controller,
        {source: ConversionOutcome("# Converted", backend="native")},
    )
    asset = {
        "url": "https://example.com/windows.zip",
        "installSupported": True,
        "installMode": "zip",
    }
    controller._preferred_release_asset = asset
    requests: list[str] = []
    created: list[dict[str, object]] = []
    quit_calls: list[None] = []
    controller.discardResultsRequested.connect(requests.append)
    monkeypatch.setattr(
        controller,
        "_create_update_installer",
        lambda asset: created.append(asset) or _FakeUpdateInstaller(),
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.quit",
        lambda: quit_calls.append(None),
    )

    controller.installPreferredUpdate()

    assert requests == ["install the update and close the application"]
    assert created == []
    assert quit_calls == []

    controller.discardPendingResults()

    assert controller.hasResults is False
    assert created == [asset]
    assert quit_calls == [None]


def test_packaged_update_installer_emits_progress_and_success(monkeypatch):
    progress: list[tuple[str, int]] = []
    started: list[None] = []
    opened: list[str] = []
    errors: list[str] = []

    def fake_install(_asset, progress_callback):
        progress_callback("Downloading update", 25)
        progress_callback("Starting restart helper", 98)

    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.install_packaged_update",
        fake_install,
    )
    installer = PackagedUpdateInstaller({"url": "https://example.com/windows.zip"})
    installer.progressChanged.connect(lambda status, value: progress.append((status, value)))
    installer.installStarted.connect(lambda: started.append(None))
    installer.manualInstallOpened.connect(lambda path: opened.append(path))
    installer.installError.connect(lambda message: errors.append(message))

    installer.run()

    assert progress == [("Downloading update", 25), ("Starting restart helper", 98)]
    assert started == [None]
    assert opened == []
    assert errors == []


def test_packaged_update_installer_emits_manual_open_for_dmg(monkeypatch):
    progress: list[tuple[str, int]] = []
    started: list[None] = []
    opened: list[str] = []
    errors: list[str] = []

    def fake_install(_asset, progress_callback):
        progress_callback("DMG opened", 100)
        return "/Users/test/Downloads/MarkItDown.dmg"

    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_packaged_update_plan",
        lambda _asset: PackagedUpdatePlan(True, "dmg", "Download DMG"),
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.install_packaged_update",
        fake_install,
    )
    installer = PackagedUpdateInstaller(
        {"name": "MarkItDown.dmg", "url": "https://example.com/macos.dmg"}
    )
    installer.progressChanged.connect(lambda status, value: progress.append((status, value)))
    installer.installStarted.connect(lambda: started.append(None))
    installer.manualInstallOpened.connect(lambda path: opened.append(path))
    installer.installError.connect(lambda message: errors.append(message))

    installer.run()

    assert progress == [("DMG opened", 100)]
    assert started == []
    assert opened == ["/Users/test/Downloads/MarkItDown.dmg"]
    assert errors == []


def test_controller_reports_manual_dmg_open_without_quitting(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    quit_called: list[None] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller._preferred_release_asset = {
        "name": "MarkItDown.dmg",
        "url": "https://example.com/macos.dmg",
        "installSupported": True,
        "installMode": "dmg",
    }
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.quit",
        lambda: quit_called.append(None),
    )
    monkeypatch.setattr(
        controller,
        "_create_update_installer",
        lambda _asset: _FakeUpdateInstaller("manual"),
    )

    controller.installPreferredUpdate()

    assert controller.updateInstallRunning is False
    assert controller.updateInstallProgress == 100
    assert controller.updateInstallStatus == (
        "DMG downloaded and opened. Drag MarkItDown to Applications."
    )
    assert quit_called == []
    assert messages == [
        (
            "success",
            "DMG opened from C:/Users/test/Downloads/MarkItDown.dmg. "
            "Drag MarkItDown to Applications.",
        )
    ]


def test_controller_keeps_unsaved_results_when_opening_manual_dmg(
    controller, monkeypatch, tmp_path
):
    source = str(tmp_path / "result.pdf")
    _complete_results(
        controller,
        {source: ConversionOutcome("# Converted", backend="native")},
    )
    asset = {
        "name": "MarkItDown.dmg",
        "url": "https://example.com/macos.dmg",
        "installSupported": True,
        "installMode": "dmg",
    }
    controller._preferred_release_asset = asset
    requests: list[str] = []
    created: list[dict[str, object]] = []
    controller.discardResultsRequested.connect(requests.append)
    monkeypatch.setattr(
        controller,
        "_create_update_installer",
        lambda installed_asset: created.append(installed_asset)
        or _FakeUpdateInstaller("manual"),
    )

    controller.installPreferredUpdate()

    assert requests == []
    assert created == [asset]
    assert controller.hasResults is True


def test_controller_blocks_update_install_while_converting(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    created: list[dict[str, object]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller._preferred_release_asset = {
        "url": "https://example.com/windows.zip",
        "installSupported": True,
    }
    controller._converting = True
    monkeypatch.setattr(
        controller,
        "_create_update_installer",
        lambda asset: created.append(asset) or _FakeUpdateInstaller(),
    )

    controller.installPreferredUpdate()

    assert created == []
    assert messages == [
        ("error", "Wait for conversion to finish before installing an update.")
    ]


def test_controller_reports_packaged_update_install_error(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller._preferred_release_asset = {
        "url": "https://example.com/windows.zip",
        "installSupported": True,
    }
    monkeypatch.setattr(
        controller,
        "_create_update_installer",
        lambda asset: _FakeUpdateInstaller("error"),
    )

    controller.installPreferredUpdate()

    assert controller.updateInstallRunning is False
    assert controller.updateInstallProgress == 0
    assert controller.updateInstallStatus == "Download failed"
    assert messages == [("error", "Download failed")]


def test_controller_loads_last_packaged_update_result(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    cleared: list[None] = []
    result = (
        "Status: failed\n"
        "Message: Update failed and rollback was attempted.\n"
        "Backup: C:/Apps/MarkItDown.backup"
    )
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.read_packaged_update_result",
        lambda: result,
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.clear_packaged_update_result",
        lambda: cleared.append(None),
    )

    controller.checkLastPackagedUpdateResult()

    assert controller.hasLastPackagedUpdateResult is True
    assert controller.lastPackagedUpdateResult == result
    assert controller.hasLastPackagedUpdateBackupPath is True
    assert controller.lastPackagedUpdateBackupPath == "C:/Apps/MarkItDown.backup"
    assert cleared == [None]
    assert messages == [
        (
            "error",
            "Previous update failed and rollback details are in Diagnostics.",
        )
    ]


def test_controller_clears_last_packaged_update_result(controller):
    controller._last_packaged_update_result = "Status: success"

    controller.clearLastPackagedUpdateResult()

    assert controller.hasLastPackagedUpdateResult is False
    assert controller.lastPackagedUpdateResult == ""
    assert controller.hasLastPackagedUpdateBackupPath is False
    assert controller.lastPackagedUpdateBackupPath == ""


def test_controller_opens_last_packaged_update_backup(controller, tmp_path, monkeypatch):
    opened: list[str] = []
    backup_dir = tmp_path / "MarkItDown.backup"
    backup_dir.mkdir()
    controller._last_packaged_update_result = (
        "Status: failed\n"
        "Message: Update failed and rollback was attempted.\n"
        f"Backup: {backup_dir}"
    )
    monkeypatch.setattr(controller, "openExternalUrl", lambda url: opened.append(url))

    controller.openLastPackagedUpdateBackup()

    assert opened and opened[0].startswith("file:")


def test_controller_reports_missing_last_packaged_update_backup(
    controller, tmp_path
):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller._last_packaged_update_result = (
        "Status: failed\n"
        f"Backup: {tmp_path / 'missing-backup'}"
    )

    controller.openLastPackagedUpdateBackup()

    assert messages == [("error", "Backup folder no longer exists.")]


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


def test_controller_exposes_ocr_fallback_provider(controller):
    controller.setOcrFallbackProvider("none")
    assert controller.ocrFallbackProvider == "none"
    assert controller.ocrFallbackEnabled is False

    controller.setOcrFallbackProvider("legacy")
    assert controller.ocrFallbackProvider == "azure_tesseract"
    assert controller.ocrFallbackEnabled is True


def test_controller_clears_same_provider_ocr_fallback(controller):
    controller.setOcrProvider("glmocr")
    controller.setOcrFallbackProvider("http")

    controller.setOcrProvider("http")

    assert controller.ocrProvider == "http"
    assert controller.ocrFallbackProvider == "none"
    assert controller.ocrFallbackEnabled is False


def test_controller_clears_ocr_fallback_for_azure_primary(controller):
    controller.setOcrProvider("glmocr")
    controller.setOcrFallbackProvider("http")

    controller.setOcrProvider("azure_tesseract")

    assert controller.ocrProvider == "azure_tesseract"
    assert controller.ocrFallbackProvider == "none"
    assert controller.ocrFallbackEnabled is False


def test_controller_preserves_different_ocr_fallback(controller):
    controller.setOcrFallbackProvider("azure_tesseract")

    controller.setOcrProvider("http")

    assert controller.ocrProvider == "http"
    assert controller.ocrFallbackProvider == "azure_tesseract"
    assert controller.ocrFallbackEnabled is True


def test_controller_exposes_ocr_provider_options_and_http_settings(controller):
    provider_ids = [option["id"] for option in controller.ocrProviderOptions]

    assert provider_ids == ["azure_tesseract", "glmocr", "http"]

    controller.setHttpOcrEndpoint(" http://localhost:8000/ocr ")
    controller.setHttpOcrModel(" surya ")
    controller.setHttpOcrApiKeyEnv(" CUSTOM_OCR_KEY ")
    controller.setHttpOcrTimeoutSeconds(45)

    assert controller.httpOcrEndpoint == "http://localhost:8000/ocr"
    assert controller.httpOcrModel == "surya"
    assert controller.httpOcrApiKeyEnv == "CUSTOM_OCR_KEY"
    assert controller.httpOcrTimeoutSeconds == 45


def test_controller_exposes_provider_specific_ocr_setup_actions(controller):
    azure_actions = {item["label"]: item for item in controller.ocrSetupActions}
    assert azure_actions["Open Azure OCR docs"]["action"] == "open"
    assert azure_actions["Copy API key env"]["value"] == "AZURE_OCR_API_KEY=<key>"

    controller.setOcrProvider("glmocr")
    glm_actions = {item["label"]: item for item in controller.ocrSetupActions}
    assert glm_actions["Open GLM-OCR docs"]["value"] == "https://github.com/zai-org/GLM-OCR"
    assert glm_actions["Copy API key hint"]["value"] == (
        "ZHIPU_API_KEY=<key> or GLMOCR_API_KEY=<key>"
    )
    assert glm_actions["Copy SDK server URL"]["value"] == "http://127.0.0.1:5002/glmocr/parse"

    controller.setOcrProvider("http")
    controller.setHttpOcrEndpoint("http://localhost:8000/ocr")
    controller.setHttpOcrModel("surya")
    controller.setHttpOcrApiKeyEnv("CUSTOM_OCR_KEY")
    http_actions = {item["label"]: item for item in controller.ocrSetupActions}
    assert http_actions["Copy endpoint contract"]["value"] == (
        "POST multipart/form-data: file=<document>, model=<optional>"
    )
    assert http_actions["Copy API key env"]["value"] == "CUSTOM_OCR_KEY"
    assert http_actions["Copy curl template"]["value"] == (
        'curl -X POST -F "file=@sample.pdf" -F "model=surya" '
        '-H "Authorization: Bearer $CUSTOM_OCR_KEY" "http://localhost:8000/ocr"'
    )


def test_controller_applies_ocr_ollama_preset(controller):
    messages: list[tuple[str, str]] = []
    signals: list[str] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller.settingsChanged.connect(lambda: signals.append("settings"))
    controller.diagnosticsChanged.connect(lambda: signals.append("diagnostics"))

    controller.setOcrEnabled(False)
    signals.clear()
    controller.applyOcrPreset("glmocr_ollama")

    assert controller.ocrEnabled is True
    assert controller.ocrProvider == "glmocr"
    assert controller.ocrFallbackProvider == "none"
    assert controller.glmocrMode == "ollama"
    assert controller.glmocrOllamaHost == "127.0.0.1"
    assert controller.glmocrOllamaPort == 11434
    assert controller.glmocrOllamaModel == "glm-ocr:latest"
    assert signals == ["settings", "diagnostics"]
    assert messages[-1] == (
        "success",
        "GLM-OCR Ollama preset applied. Run Test connection next.",
    )


def test_controller_applies_ocr_sdk_server_preset(controller):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))

    controller.applyOcrPreset("glmocr_sdk_server")

    assert controller.ocrEnabled is True
    assert controller.ocrProvider == "glmocr"
    assert controller.ocrFallbackProvider == "none"
    assert controller.glmocrMode == "sdk_server"
    assert controller.glmocrSdkServerUrl == "http://127.0.0.1:5002/glmocr/parse"
    assert messages[-1] == (
        "success",
        "GLM-OCR SDK server preset applied. Run Test connection next.",
    )


def test_controller_applies_http_local_ocr_preset(controller):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller.setHttpOcrEndpoint("https://example.com/old")
    controller.setHttpOcrModel("old-model")
    controller.setHttpOcrApiKeyEnv("OLD_KEY")
    controller.setHttpOcrTimeoutSeconds(5)

    controller.applyOcrPreset("http_local")

    assert controller.ocrEnabled is True
    assert controller.ocrProvider == "http"
    assert controller.ocrFallbackProvider == "none"
    assert controller.httpOcrEndpoint == "http://127.0.0.1:8000/ocr"
    assert controller.httpOcrModel == ""
    assert controller.httpOcrApiKeyEnv == "OCR_HTTP_API_KEY"
    assert controller.httpOcrTimeoutSeconds == 300
    assert messages[-1] == (
        "success",
        "HTTP OCR local preset applied. Run Test connection next.",
    )


def test_controller_reports_unknown_ocr_preset(controller):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))

    controller.applyOcrPreset("unknown")

    assert messages == [("error", "Unknown OCR preset.")]


def test_controller_runs_ocr_setup_actions(controller, monkeypatch):
    opened: list[str] = []
    copied: list[str] = []
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    monkeypatch.setattr(controller, "openExternalUrl", lambda url: opened.append(url))
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.clipboard",
        lambda: SimpleNamespace(setText=lambda value: copied.append(value)),
    )

    controller.runOcrSetupAction("open", "https://example.com/docs", "Open docs")
    controller.runOcrSetupAction("copy", "AZURE_OCR_API_KEY=<key>", "Copy API key env")

    assert opened == ["https://example.com/docs"]
    assert copied == ["AZURE_OCR_API_KEY=<key>"]
    assert messages == [("success", "Copy API key env copied.")]


def test_controller_validates_ocr_setup(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.validate_ocr_setup",
        lambda _options: SimpleNamespace(ok=True, message="OCR settings look ready."),
    )

    controller.validateOcrSetup()

    assert messages == [("success", "OCR settings look ready.")]


def test_controller_reports_ocr_validation_error(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.validate_ocr_setup",
        lambda _options: SimpleNamespace(ok=False, message="HTTP OCR requires an endpoint URL."),
    )

    controller.validateOcrSetup()

    assert messages == [("error", "HTTP OCR requires an endpoint URL.")]


def test_controller_preflights_ocr_before_starting_a_conversion(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller.addFiles(["C:/tmp/scan.pdf"])
    controller.setOcrEnabled(True)
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.validate_ocr_setup",
        lambda _options: SimpleNamespace(
            ok=False,
            message="HTTP OCR requires an endpoint URL.",
        ),
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.ConversionWorker",
        lambda **_kwargs: pytest.fail("worker should not start after failed preflight"),
    )

    controller.convert()

    assert controller.converting is False
    assert controller.statusText == "OCR setup needs attention"
    assert messages == [("error", "HTTP OCR requires an endpoint URL.")]


def test_controller_skips_ocr_preflight_without_ocr_inputs(controller, monkeypatch):
    controller.addFiles(
        ["https://example.com/article", "C:/tmp/presentation.pptx", "C:/tmp/readme.txt"]
    )
    controller.setOcrEnabled(True)
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.validate_ocr_setup",
        lambda _options: pytest.fail("native and URL inputs should not need OCR setup"),
    )

    assert controller._preflight_conversion() is True


def test_controller_preflights_only_failed_inputs_before_retry(controller, monkeypatch):
    pdf_source = "C:/tmp/successful.pdf"
    url_source = "https://example.com/retry"
    controller.addFiles([pdf_source, url_source])
    _complete_results(
        controller,
        {
            pdf_source: ConversionOutcome("# PDF", backend="native"),
            url_source: ConversionOutcome("# Failed", backend="defuddle"),
        },
        failed_sources={url_source},
    )
    controller.setOcrEnabled(True)
    starts: list[dict[str, bool]] = []
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.validate_ocr_setup",
        lambda _options: pytest.fail("the failed URL does not need OCR setup"),
    )
    monkeypatch.setattr(
        controller,
        "_start_conversion",
        lambda **kwargs: starts.append(kwargs),
    )

    controller.retryFailedResults()

    assert controller.queue_model.sources() == [url_source]
    assert starts == [{"preserve_results": True, "preflight_validated": True}]


def test_controller_tests_ocr_connection(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller.setOcrEnabled(True)
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.test_ocr_provider_connection",
        lambda _options: "HTTP OCR endpoint is reachable.",
    )

    controller.testOcrConnection()

    assert messages == [("success", "HTTP OCR endpoint is reachable.")]


def test_controller_reports_ocr_connection_error(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )

    def fake_test(_options):
        raise RuntimeError("HTTP OCR endpoint responded with 404.")

    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.test_ocr_provider_connection",
        fake_test,
    )

    controller.testOcrConnection()

    assert messages == [("error", "HTTP OCR endpoint responded with 404.")]


def test_controller_exposes_diagnostic_readiness_items(controller, monkeypatch):
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_source_update_command",
        lambda: "git -C repo pull --ff-only && uv pip install -e repo",
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.is_packaged_app",
        lambda: False,
    )
    controller.setOcrEnabled(True)
    controller.setOcrProvider("http")

    items = controller.diagnosticReadinessItems
    by_label = {item["label"]: item for item in items}

    assert [item["label"] for item in items] == [
        "OCR",
        "Packaged updates",
        "Source updates",
        "Update checks",
        "Logs",
    ]
    assert by_label["OCR"] == {
        "label": "OCR",
        "status": "Needs setup",
        "detail": "HTTP OCR requires an endpoint URL.",
        "severity": "warn",
    }
    assert by_label["Packaged updates"]["status"] == "Source build"
    assert by_label["Source updates"]["status"] == "Available"
    assert by_label["Update checks"]["status"] == "Auto-check on"
    assert by_label["Logs"]["status"] == "Ready"


def test_controller_diagnostic_readiness_updates_after_ocr_change(controller):
    changes: list[None] = []
    controller.diagnosticsChanged.connect(lambda: changes.append(None))

    controller.setOcrEnabled(True)
    controller.setOcrProvider("http")
    controller.setOcrFallbackProvider("none")
    controller.setHttpOcrEndpoint("http://localhost:8000/ocr")

    by_label = {item["label"]: item for item in controller.diagnosticReadinessItems}
    assert by_label["OCR"]["status"] == "Ready"
    assert by_label["OCR"]["severity"] == "ok"
    assert changes


def test_controller_builds_fast_pdf_conversion_option(controller):
    controller.setFastPdfConversion(True)

    options = controller._build_conversion_options(create_asset_root=False)

    assert controller.fastPdfConversion is True
    assert options.fast_pdf_conversion is True


def test_diagnostic_readiness_does_not_create_temp_asset_root(controller, monkeypatch):
    controller.setPreservePdfImages(True)
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.create_temp_asset_root",
        lambda: pytest.fail("diagnostics should not prepare conversion assets"),
    )

    controller.diagnosticReadinessItems


def test_controller_retains_all_asset_roots_while_results_are_kept(
    controller,
    monkeypatch,
    tmp_path,
):
    first_root = tmp_path / "first-assets"
    second_root = tmp_path / "second-assets"
    first_root.mkdir()
    second_root.mkdir()
    roots = iter([first_root, second_root])
    cleaned: list[str] = []
    controller.setPreservePdfImages(True)
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.create_temp_asset_root",
        lambda: next(roots),
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.cleanup_temp_asset_root",
        lambda path: cleaned.append(str(path)),
    )

    first_options = controller._build_conversion_options()
    second_options = controller._build_conversion_options()

    assert first_options.pdf_artifacts_dir == str(first_root)
    assert second_options.pdf_artifacts_dir == str(second_root)

    controller._cleanup_temp_assets()

    assert set(cleaned) == {str(first_root), str(second_root)}


def test_controller_copies_source_update_command(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    copied: list[str] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_source_update_command",
        lambda: "git -C repo pull --ff-only && uv pip install -e repo",
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.clipboard",
        lambda: SimpleNamespace(setText=lambda value: copied.append(value)),
    )

    controller.copySourceUpdateCommand()

    assert copied == ["git -C repo pull --ff-only && uv pip install -e repo"]
    assert messages == [("success", "Source update command copied.")]


def test_source_update_installer_emits_progress_and_success(monkeypatch):
    progress: list[tuple[str, int]] = []
    finished: list[None] = []
    errors: list[str] = []

    def fake_update(progress_callback):
        progress_callback("Pulling latest source", 15)
        progress_callback("Source update complete", 100)
        return 0

    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.run_source_update",
        fake_update,
    )
    installer = SourceUpdateInstaller()
    installer.progressChanged.connect(
        lambda status, value: progress.append((status, value))
    )
    installer.updateFinished.connect(lambda: finished.append(None))
    installer.updateError.connect(lambda message: errors.append(message))

    installer.run()

    assert progress == [("Pulling latest source", 15), ("Source update complete", 100)]
    assert finished == [None]
    assert errors == []


def test_source_update_installer_reports_dirty_checkout(monkeypatch):
    progress: list[tuple[str, int]] = []
    finished: list[None] = []
    errors: list[str] = []

    def fake_update(progress_callback):
        progress_callback("Checking source checkout", 5)
        return SOURCE_UPDATE_DIRTY

    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.run_source_update",
        fake_update,
    )
    installer = SourceUpdateInstaller()
    installer.progressChanged.connect(
        lambda status, value: progress.append((status, value))
    )
    installer.updateFinished.connect(lambda: finished.append(None))
    installer.updateError.connect(lambda message: errors.append(message))

    installer.run()

    assert progress == [("Checking source checkout", 5)]
    assert finished == []
    assert errors == [
        "Source checkout has local changes. Commit, stash, or discard them before updating."
    ]


def test_controller_runs_source_update_from_help(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_source_update_command",
        lambda: "git -C repo pull --ff-only && uv pip install -e repo",
    )
    monkeypatch.setattr(
        controller,
        "_create_source_update_runner",
        lambda: _FakeSourceUpdateRunner(),
    )

    assert controller.canRunSourceUpdate is True

    controller.runSourceUpdate()

    assert controller.sourceUpdateRunning is False
    assert controller.sourceUpdateProgress == 100
    assert controller.sourceUpdateStatus == "Source update complete. Restart the app."
    assert controller.sourceUpdateNeedsRestart is True
    assert controller.canRunSourceUpdate is False
    assert messages == [("success", "Source update complete. Restart the app.")]


def test_controller_blocks_source_update_after_success_until_restart(
    controller, monkeypatch
):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_source_update_command",
        lambda: "git -C repo pull --ff-only && uv pip install -e repo",
    )
    controller._source_update_status = "Source update complete. Restart the app."
    controller._source_update_progress = 100

    controller.runSourceUpdate()

    assert messages == [("success", "Restart the app to finish updating.")]


def test_controller_restarts_app(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    started: list[None] = []
    quit_calls: list[None] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    monkeypatch.setattr(
        controller,
        "_start_restart_process",
        lambda: started.append(None) or True,
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.quit",
        lambda: quit_calls.append(None),
    )

    controller.restartApp()

    assert started == [None]
    assert quit_calls == [None]
    assert messages == [("success", "Restarting app.")]


def test_controller_confirms_before_restarting_with_unsaved_results(
    controller, monkeypatch, tmp_path
):
    source = str(tmp_path / "result.pdf")
    _complete_results(
        controller,
        {source: ConversionOutcome("# Converted", backend="native")},
    )
    requests: list[str] = []
    started: list[None] = []
    quit_calls: list[None] = []
    controller.discardResultsRequested.connect(requests.append)
    monkeypatch.setattr(
        controller,
        "_start_restart_process",
        lambda: started.append(None) or True,
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.quit",
        lambda: quit_calls.append(None),
    )

    controller.restartApp()

    assert requests == ["restart the application"]
    assert started == []
    assert quit_calls == []

    controller.discardPendingResults()

    assert controller.hasResults is False
    assert started == [None]
    assert quit_calls == [None]


def test_controller_confirms_before_closing_for_update_with_unsaved_results(
    controller, monkeypatch, tmp_path
):
    source = str(tmp_path / "result.pdf")
    _complete_results(
        controller,
        {source: ConversionOutcome("# Converted", backend="native")},
    )
    requests: list[str] = []
    quit_calls: list[None] = []
    controller.discardResultsRequested.connect(requests.append)
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.quit",
        lambda: quit_calls.append(None),
    )

    controller._on_update_install_started()

    assert requests == ["close the application and install the update"]
    assert quit_calls == []

    controller.discardPendingResults()

    assert controller.hasResults is False
    assert quit_calls == [None]


def test_controller_reports_restart_failure(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    quit_calls: list[None] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    monkeypatch.setattr(controller, "_start_restart_process", lambda: False)
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.quit",
        lambda: quit_calls.append(None),
    )

    controller.restartApp()

    assert quit_calls == []
    assert messages == [("error", "Could not restart the app.")]


def test_controller_reports_source_update_error(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_source_update_command",
        lambda: "git -C repo pull --ff-only && uv pip install -e repo",
    )
    monkeypatch.setattr(
        controller,
        "_create_source_update_runner",
        lambda: _FakeSourceUpdateRunner("error"),
    )

    controller.runSourceUpdate()

    assert controller.sourceUpdateRunning is False
    assert controller.sourceUpdateProgress == 0
    assert controller.sourceUpdateStatus == "Source update failed with exit code 1."
    assert messages == [("error", "Source update failed with exit code 1.")]


def test_controller_blocks_source_update_while_converting(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    created: list[None] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller._converting = True
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_source_update_command",
        lambda: "git -C repo pull --ff-only && uv pip install -e repo",
    )
    monkeypatch.setattr(
        controller,
        "_create_source_update_runner",
        lambda: created.append(None) or _FakeSourceUpdateRunner(),
    )

    controller.runSourceUpdate()

    assert created == []
    assert messages == [
        ("error", "Wait for conversion to finish before updating the source checkout.")
    ]


def test_controller_blocks_source_update_while_packaged_update_runs(
    controller,
    monkeypatch,
):
    messages: list[tuple[str, str]] = []
    created: list[None] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller._update_install_running = True
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_source_update_command",
        lambda: "git -C repo pull --ff-only && uv pip install -e repo",
    )
    monkeypatch.setattr(
        controller,
        "_create_source_update_runner",
        lambda: created.append(None) or _FakeSourceUpdateRunner(),
    )

    assert controller.canRunSourceUpdate is False

    controller.runSourceUpdate()

    assert created == []
    assert messages == [
        ("error", "Wait for packaged update install to finish before updating source.")
    ]


def test_controller_copies_diagnostics(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    copied: list[str] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_diagnostic_report",
        lambda: (
            f"diagnostic report\n"
            f"Executable: {Path.home() / 'app' / 'MarkItDown.exe'}\n"
            "api_key=secret-value"
        ),
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.clipboard",
        lambda: SimpleNamespace(setText=lambda value: copied.append(value)),
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_source_update_command",
        lambda: "",
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.is_packaged_app",
        lambda: False,
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.AppLogger.log_dir",
        lambda: str(Path.home() / ".markitdown"),
    )

    controller.copyDiagnostics()

    assert copied == [
        "\n".join(
            [
                "diagnostic report",
                "Executable: ~/app/MarkItDown.exe",
                "api_key=[redacted]",
                "",
                "Readiness",
                "- OCR: Off - OCR is disabled.",
                "- Packaged updates: Source build - Packaged install helper runs only in frozen builds.",
                "- Source updates: Unavailable - No Git checkout detected for source updates.",
                "- Update checks: Auto-check on - The app checks GitHub releases after startup.",
                "- Logs: Ready - Log directory: ~/.markitdown",
            ]
        )
    ]
    assert messages == [("success", "Diagnostics copied.")]


def test_controller_copied_diagnostics_include_last_packaged_update_result(
    controller, monkeypatch
):
    copied: list[str] = []
    controller._last_packaged_update_result = (
        f"Status: failed\nBackup: {Path.home() / 'Apps' / 'MarkItDown.backup'}\n"
        "Authorization: Bearer token-value"
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_diagnostic_report",
        lambda: "diagnostic report",
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.QGuiApplication.clipboard",
        lambda: SimpleNamespace(setText=lambda value: copied.append(value)),
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.build_source_update_command",
        lambda: "",
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.AppLogger.log_dir",
        lambda: "C:/logs",
    )

    controller.copyDiagnostics()

    assert "Last packaged update\nStatus: failed\nBackup: ~/Apps/MarkItDown.backup" in copied[0]
    assert "Authorization: Bearer [redacted]" in copied[0]
    assert str(Path.home()) not in copied[0]
    assert "- Packaged updates: Last result - Status: failed" in copied[0]


def test_controller_opens_log_folder(controller, monkeypatch, tmp_path):
    opened: list[str] = []
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.AppLogger.log_dir",
        lambda: str(tmp_path / "logs"),
    )
    monkeypatch.setattr(controller, "openExternalUrl", lambda url: opened.append(url))

    controller.openLogFolder()

    assert (tmp_path / "logs").is_dir()
    assert opened and opened[0].startswith("file:")


def test_controller_exports_support_bundle(controller, monkeypatch, tmp_path):
    messages: list[tuple[str, str]] = []
    opened: list[str] = []
    bundle = tmp_path / "markitdown-support.zip"
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.create_support_bundle",
        lambda settings: bundle,
    )
    monkeypatch.setattr(controller, "openExternalUrl", lambda url: opened.append(url))

    controller.exportSupportBundle()

    assert messages == [("success", "Created markitdown-support.zip.")]
    assert opened and opened[0].startswith("file:")


def test_controller_exports_settings_profile(controller, tmp_path):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller.setOcrEnabled(True)
    controller.setOcrProvider("http")
    controller.setHttpOcrEndpoint("http://localhost:8000/ocr")
    profile_path = tmp_path / "profile"

    controller.exportSettingsProfile(QUrl.fromLocalFile(str(profile_path)).toString())

    exported_path = tmp_path / "profile.json"
    assert exported_path.is_file()
    assert messages[-1] == ("success", "Exported profile.json.")
    assert "http://localhost:8000/ocr" in exported_path.read_text(encoding="utf-8")


def test_controller_imports_settings_profile(controller, tmp_path):
    messages: list[tuple[str, str]] = []
    changes: list[str] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller.settingsChanged.connect(lambda: changes.append("settings"))
    controller.themeChanged.connect(lambda: changes.append("theme"))
    controller.saveDefaultsChanged.connect(lambda: changes.append("save"))
    controller.diagnosticsChanged.connect(lambda: changes.append("diagnostics"))
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        """{
  "schema": 1,
  "settings": {
    "appearance": {"themeMode": "dark"},
    "output": {"defaultFormat": ".txt", "combinedSaveMode": false},
    "ocr": {
      "enabled": true,
      "provider": "http",
      "httpEndpoint": "http://localhost:8000/ocr"
    },
    "updates": {"notificationsEnabled": false}
  }
}
""",
        encoding="utf-8",
    )

    controller.importSettingsProfile(QUrl.fromLocalFile(str(profile_path)).toString())

    assert controller.themeMode == "dark"
    assert controller.settings.get_default_output_format() == ".txt"
    assert controller.saveCombined is False
    assert controller.ocrEnabled is True
    assert controller.ocrProvider == "http"
    assert controller.httpOcrEndpoint == "http://localhost:8000/ocr"
    assert controller.settings.get_update_notifications_enabled() is False
    assert messages == [("success", "Settings profile imported.")]
    assert changes == ["settings", "theme", "save", "diagnostics"]


def test_controller_reports_support_bundle_error(controller, monkeypatch):
    messages: list[tuple[str, str]] = []
    logged: list[str] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.create_support_bundle",
        lambda settings: (_ for _ in ()).throw(RuntimeError("disk full")),
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.AppLogger.error",
        lambda message: logged.append(message),
    )

    controller.exportSupportBundle()

    assert messages == [("error", "Support bundle failed: disk full")]
    assert logged == ["Failed creating support bundle: disk full"]


def test_controller_dismisses_update_notification(controller, monkeypatch):
    release = ReleaseInfo(
        tag_name="v1.2.0",
        html_url="https://github.com/example/releases/tag/v1.2.0",
        body="- Installer progress\n- OCR setup checks",
    )
    monkeypatch.setattr(
        controller,
        "_create_update_checker",
        lambda: _FakeUpdateChecker(("available", "v1.2.0"), release),
    )
    controller.startAutomaticUpdateCheck()
    assert controller.availableReleaseNotes == "Installer progress OCR setup checks"

    controller.dismissUpdateNotification()

    assert controller.hasUpdateNotification is False
    assert controller.availableUpdateVersion == ""
    assert controller.availableReleaseNotes == ""


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


def test_controller_enables_update_notifications_without_dismissing_update(controller):
    controller.settings.set_update_notifications_enabled(False)
    controller._available_update_version = "v1.2.0"
    controller._available_release_url = "https://github.com/example/releases/tag/v1.2.0"
    messages: list[tuple[str, str]] = []
    changes: list[None] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))
    controller.updateNotificationChanged.connect(lambda: changes.append(None))

    controller.setUpdateNotificationsEnabled(True)

    assert controller.settings.get_update_notifications_enabled() is True
    assert controller.hasUpdateNotification is True
    assert controller.availableUpdateVersion == "v1.2.0"
    assert messages == []
    assert changes == [None]


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


def test_controller_add_files_requires_discarding_unsaved_results(controller, tmp_path):
    source_a = str(tmp_path / "a.pdf")
    source_b = str(tmp_path / "b.pdf")
    controller.addFiles([source_a])
    _complete_results(
        controller,
        {source_a: ConversionOutcome("# Converted", backend="native")},
    )
    requests: list[str] = []
    controller.discardResultsRequested.connect(requests.append)

    controller.addFiles([source_b])

    assert requests == ["add inputs to the queue"]
    assert controller.hasUnsavedSuccessfulResults is True
    assert controller.result_model.rowCount() == 1
    assert controller.queue_model.sources() == [source_a]

    controller.cancelPendingResultDiscard()

    assert controller.result_model.rowCount() == 1
    assert controller.queue_model.sources() == [source_a]

    controller.addFiles([source_b])
    controller.discardPendingResults()

    assert controller.result_model.rowCount() == 0
    assert controller.selectedResultIndex == -1
    assert controller.queue_model.sources() == [source_a, source_b]


def test_controller_remove_queued_requires_discarding_unsaved_results(controller, tmp_path):
    source_a = str(tmp_path / "a.pdf")
    source_b = str(tmp_path / "b.pdf")
    controller.addFiles([source_a, source_b])
    _complete_results(
        controller,
        {source_a: ConversionOutcome("# Converted", backend="native")},
    )
    requests: list[str] = []
    controller.discardResultsRequested.connect(requests.append)

    controller.removeQueued(0)

    assert requests == ["change the queue"]
    assert controller.result_model.rowCount() == 1
    assert controller.queue_model.sources() == [source_a, source_b]

    controller.discardPendingResults()

    assert controller.result_model.rowCount() == 0
    assert controller.selectedResultIndex == -1
    assert controller.queue_model.sources() == [source_b]


def test_controller_clear_queue_requires_discarding_unsaved_results(controller, tmp_path):
    source = str(tmp_path / "a.pdf")
    controller.addFiles([source])
    _complete_results(
        controller,
        {source: ConversionOutcome("# Converted", backend="native")},
    )
    requests: list[str] = []
    controller.discardResultsRequested.connect(requests.append)

    controller.clearQueue()

    assert requests == ["clear the queue"]
    assert controller.result_model.rowCount() == 1
    assert controller.queue_model.sources() == [source]

    controller.discardPendingResults()

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


def test_controller_back_to_queue_requires_discarding_unsaved_results(controller, tmp_path):
    source = str(tmp_path / "a.pdf")
    controller.addFiles([source])
    _complete_results(
        controller,
        {source: ConversionOutcome("# Converted", backend="native")},
    )
    requests: list[str] = []
    controller.discardResultsRequested.connect(requests.append)

    controller.backToQueue()

    assert requests == ["return to the queue"]
    assert controller.hasResults is True
    assert controller.queue_model.sources() == [source]

    controller.discardPendingResults()

    assert controller.hasResults is False
    assert controller.queue_model.sources() == [source]


def test_controller_start_new_requires_discarding_unsaved_results(controller, tmp_path):
    source = str(tmp_path / "a.pdf")
    controller.addFiles([source])
    _complete_results(
        controller,
        {source: ConversionOutcome("# Converted", backend="native")},
    )
    requests: list[str] = []
    controller.discardResultsRequested.connect(requests.append)

    controller.startNew()

    assert requests == ["start a new conversion"]
    assert controller.hasResults is True
    assert controller.queue_model.sources() == [source]

    controller.discardPendingResults()

    assert controller.hasResults is False
    assert controller.queue_model.sources() == []


def test_controller_confirms_before_closing_with_unsaved_results(controller, tmp_path):
    source = str(tmp_path / "a.pdf")
    controller.addFiles([source])
    _complete_results(
        controller,
        {source: ConversionOutcome("# Converted", backend="native")},
    )
    requests: list[str] = []
    close_approved: list[None] = []
    controller.discardResultsRequested.connect(requests.append)
    controller.closeApproved.connect(lambda: close_approved.append(None))

    assert controller.requestShutdown() is False
    assert requests == ["close the application"]
    assert controller.hasResults is True

    controller.cancelPendingResultDiscard()
    assert controller.hasResults is True
    assert close_approved == []

    assert controller.requestShutdown() is False
    controller.discardPendingResults()

    assert controller.hasResults is False
    assert close_approved == [None]


def test_controller_stops_active_conversion_before_discarding_for_close(
    controller,
    monkeypatch,
):
    source = "C:/tmp/report.pdf"
    controller.result_model.set_results(
        {source: ConversionOutcome("# Converted", backend="native")}
    )
    controller._unsaved_result_sources.add(source)
    controller._temp_asset_root = "C:/tmp/markitdown-assets"
    events: list[str] = []
    controller.worker = SimpleNamespace(
        is_cancelled=False,
        is_paused=False,
        isRunning=lambda: True,
        wait=lambda _timeout: events.append("wait") or True,
    )
    monkeypatch.setattr(
        "markitdowngui.ui_qml.controller.cleanup_temp_asset_root",
        lambda path: events.append(f"cleanup:{path}"),
    )

    assert controller.requestShutdown() is False
    controller.discardPendingResults()

    assert controller.worker.is_cancelled is True
    assert events == ["wait", "cleanup:C:/tmp/markitdown-assets"]
    assert controller.hasResults is False


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
    _complete_results(
        controller,
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
    assert controller.hasUnsavedSuccessfulResults is True

    controller.saveCombinedOutput(str(output_path))

    saved = output_path.read_text(encoding="utf-8")
    assert "# Converted" in saved
    assert "Error converting broken.pdf" not in saved
    assert "C:/tmp/broken.pdf" not in saved
    assert controller.hasUnsavedSuccessfulResults is False


def test_controller_save_separate_skips_failed_results(controller, tmp_path):
    output_dir = tmp_path / "exports"
    _complete_results(
        controller,
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
    assert controller.hasUnsavedSuccessfulResults is False


def test_controller_save_separate_reports_partial_save_failures(controller, tmp_path, monkeypatch):
    output_dir = tmp_path / "exports"
    _complete_results(
        controller,
        {
            "C:/tmp/ok.pdf": ConversionOutcome("# Converted", backend="native"),
            "C:/tmp/fail.pdf": ConversionOutcome("# Also converted", backend="native"),
        },
    )
    original_save = controller._save_prepared_markdown

    def fail_one_output(output_path, prepared_output):
        if output_path.endswith("fail.md"):
            raise OSError("disk full")
        original_save(output_path, prepared_output)

    monkeypatch.setattr(controller, "_save_prepared_markdown", fail_one_output)
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))

    controller.saveSeparateOutputs(str(output_dir))

    assert messages == [("error", "Saved 1 file; 1 file failed to save.")]
    assert controller.hasUnsavedSuccessfulResults is True


def test_controller_restores_asset_root_when_markdown_replace_fails(
    controller,
    monkeypatch,
    tmp_path,
):
    output_path = tmp_path / "report.md"
    old_asset_path = tmp_path / "source" / "old.png"
    new_asset_path = tmp_path / "source" / "new.png"
    old_asset_path.parent.mkdir()
    old_asset_path.write_bytes(b"old asset")
    new_asset_path.write_bytes(b"new asset")
    old_asset = ConversionAsset(
        filename="page.png",
        source_path=str(old_asset_path),
        preview_markdown_path="C:/temp/old.png",
        page_number=None,
        kind="image",
    )
    new_asset = ConversionAsset(
        filename="page.png",
        source_path=str(new_asset_path),
        preview_markdown_path="C:/temp/new.png",
        page_number=None,
        kind="image",
    )
    old_markdown = prepare_markdown_for_separate_save(
        "# Old\n![old](C:/temp/old.png)",
        [old_asset],
        output_path,
    )
    controller.file_manager.save_markdown_file(str(output_path), old_markdown)
    prepared = prepare_markdown_for_separate_save_transaction(
        "# New\n![new](C:/temp/new.png)",
        [new_asset],
        output_path,
    )
    staged_file = controller.file_manager.stage_markdown_file(
        str(output_path),
        prepared.markdown,
    )
    monkeypatch.setattr(
        controller.file_manager,
        "stage_markdown_file",
        lambda *_args: staged_file,
    )
    monkeypatch.setattr(
        staged_file,
        "commit",
        lambda: (_ for _ in ()).throw(OSError("disk is unavailable")),
    )

    with pytest.raises(OSError, match="disk is unavailable"):
        controller._save_prepared_markdown(str(output_path), prepared)

    assert output_path.read_text(encoding="utf-8") == old_markdown
    assert (tmp_path / "report_assets" / "page.png").read_bytes() == b"old asset"
    assert not list(tmp_path.glob(".markitdowngui-assets-*.backup"))
    assert not list(tmp_path.glob(".markitdowngui-assets-*.staging"))
    assert not list(tmp_path.glob(".markitdowngui-*.tmp"))


def test_controller_restores_owned_assets_when_asset_free_save_fails(
    controller,
    monkeypatch,
    tmp_path,
):
    output_path = tmp_path / "report.md"
    asset_path = tmp_path / "source" / "page.png"
    asset_path.parent.mkdir()
    asset_path.write_bytes(b"old asset")
    asset = ConversionAsset(
        filename="page.png",
        source_path=str(asset_path),
        preview_markdown_path="C:/temp/page.png",
        page_number=None,
        kind="image",
    )
    old_markdown = prepare_markdown_for_separate_save(
        "# Old\n![page](C:/temp/page.png)",
        [asset],
        output_path,
    )
    controller.file_manager.save_markdown_file(str(output_path), old_markdown)
    prepared = prepare_markdown_for_separate_save_transaction("# New", [], output_path)
    staged_file = controller.file_manager.stage_markdown_file(
        str(output_path),
        prepared.markdown,
    )
    monkeypatch.setattr(
        controller.file_manager,
        "stage_markdown_file",
        lambda *_args: staged_file,
    )
    monkeypatch.setattr(
        staged_file,
        "commit",
        lambda: (_ for _ in ()).throw(OSError("disk is unavailable")),
    )

    with pytest.raises(OSError, match="disk is unavailable"):
        controller._save_prepared_markdown(str(output_path), prepared)

    assert output_path.read_text(encoding="utf-8") == old_markdown
    assert (tmp_path / "report_assets" / "page.png").read_bytes() == b"old asset"
    assert not list(tmp_path.glob(".markitdowngui-assets-*.backup"))


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


def test_controller_exposes_completed_items_before_the_worker_finishes(controller):
    controller._handle_item_finished(
        "C:/tmp/first.pdf",
        ConversionOutcome("# First", backend="native"),
        False,
    )

    assert controller.result_model.rowCount() == 1
    assert controller.selectedResultIndex == 0
    assert controller.hasUnsavedSuccessfulResults is True

    controller.worker = SimpleNamespace(is_cancelled=False, failed_files=set())
    controller._converting = True
    controller._handle_finished(
        {"C:/tmp/first.pdf": ConversionOutcome("# First", backend="native")}
    )

    assert controller.result_model.rowCount() == 1
    assert controller.hasUnsavedSuccessfulResults is True


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


def test_controller_retries_failed_results_without_discarding_successes(
    controller,
    monkeypatch,
):
    messages: list[tuple[str, str]] = []
    changes: list[str] = []
    requests: list[str] = []
    starts: list[dict[str, bool]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller.queueChanged.connect(lambda: changes.append("queue"))
    controller.resultsChanged.connect(lambda: changes.append("results"))
    controller.selectedResultChanged.connect(lambda: changes.append("selected"))
    controller.discardResultsRequested.connect(requests.append)
    monkeypatch.setattr(
        controller,
        "_start_conversion",
        lambda **kwargs: starts.append(kwargs),
    )
    controller.addFiles(["C:/tmp/original.pdf"])
    changes.clear()
    _complete_results(
        controller,
        {
            "C:/tmp/ok.pdf": ConversionOutcome("# Converted", backend="native"),
            "C:/tmp/broken-a.pdf": ConversionOutcome("A failed", backend="native"),
            "https://example.com/broken": ConversionOutcome("B failed", backend="defuddle"),
        },
        {"C:/tmp/broken-a.pdf", "https://example.com/broken"},
    )
    controller.selectResult(1)
    changes.clear()
    messages.clear()

    assert controller.hasFailedResults is True
    assert controller.failedResultCount == 2
    assert controller.hasUnsavedSuccessfulResults is True

    controller.retryFailedResults()

    assert requests == []
    assert controller.queue_model.sources() == [
        "C:/tmp/broken-a.pdf",
        "https://example.com/broken",
    ]
    assert controller.hasResults is True
    assert controller.hasFailedResults is False
    assert controller.result_model.item_at(0).source == "C:/tmp/ok.pdf"
    assert controller.selectedResultIndex == 0
    assert controller.hasUnsavedSuccessfulResults is True
    assert starts == [{"preserve_results": True, "preflight_validated": True}]
    assert messages == [("success", "Retrying 2 failed inputs.")]
    assert changes == ["queue", "results", "selected"]


def test_controller_retry_failed_results_reports_when_none_failed(controller):
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )
    controller.result_model.set_results(
        {"C:/tmp/ok.pdf": ConversionOutcome("# Converted", backend="native")}
    )

    controller.retryFailedResults()

    assert controller.queue_model.sources() == []
    assert controller.hasResults is True
    assert controller.hasFailedResults is False
    assert controller.failedResultCount == 0
    assert messages == [("error", "No failed conversions to retry.")]


def test_controller_can_save_retained_successes_while_retrying_failures(
    controller,
    monkeypatch,
    tmp_path,
):
    output_path = tmp_path / "converted.md"
    starts: list[dict[str, bool]] = []
    monkeypatch.setattr(
        controller,
        "_start_conversion",
        lambda **kwargs: starts.append(kwargs),
    )
    controller.addFiles(["C:/tmp/original.pdf"])
    _complete_results(
        controller,
        {
            "C:/tmp/ok.pdf": ConversionOutcome("# Converted", backend="native"),
            "C:/tmp/broken.pdf": ConversionOutcome("Conversion failed", backend="native"),
        },
        {"C:/tmp/broken.pdf"},
    )
    requests: list[str] = []
    controller.discardResultsRequested.connect(requests.append)

    controller.retryFailedResults()

    assert requests == []
    assert controller.hasResults is True
    assert controller.hasFailedResults is False
    assert controller.queue_model.sources() == ["C:/tmp/broken.pdf"]
    assert starts == [{"preserve_results": True, "preflight_validated": True}]

    controller.saveCombinedOutput(str(output_path))

    saved = output_path.read_text(encoding="utf-8")
    assert "# Converted" in saved
    assert "broken.pdf" not in saved
    assert controller.hasUnsavedSuccessfulResults is False


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


def test_controller_shutdown_rejects_close_during_update_install(controller):
    installer = _FakeUpdateInstaller()
    installer.started = True
    controller._update_installer = installer
    controller._update_install_running = True
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )

    accepted = controller.shutdown()

    assert accepted is False
    assert messages == [
        ("error", "Update install is still preparing. Close after it finishes.")
    ]


def test_controller_shutdown_rejects_close_during_source_update(controller):
    runner = _FakeSourceUpdateRunner()
    runner.started = True
    controller._source_update_runner = runner
    controller._source_update_running = True
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(
        lambda kind, message: messages.append((kind, message))
    )

    accepted = controller.shutdown()

    assert accepted is False
    assert messages == [
        ("error", "Source update is still running. Close after it finishes.")
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
