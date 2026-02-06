from __future__ import annotations

import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QMessageBox,
    QSplitter,
    QTextEdit,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import BodyLabel, CaptionLabel, CardWidget, PrimaryPushButton, ProgressBar, PushButton

from markitdowngui.core.conversion import ConversionWorker
from markitdowngui.core.file_utils import FileManager
from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui.components.file_panel import FilePanel
from markitdowngui.ui.dialogs.shortcuts import ShortcutDialog
from markitdowngui.utils.logger import AppLogger
from markitdowngui.utils.translations import DEFAULT_LANG


class HomeInterface(QWidget):
    """Home page with queue and conversion result states."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("HomeInterface")
        self.settings_manager = settings_manager
        self.file_manager = FileManager()
        self.worker: ConversionWorker | None = None
        self.conversionResults: dict[str, str] = {}
        self.setAcceptDrops(True)

        self._build_ui()
        self.setup_shortcuts()
        self.setup_update_checker()
        self._set_state_empty()

    def translate(self, key: str) -> str:
        if self.window() and hasattr(self.window(), "translate"):
            return self.window().translate(key)
        from markitdowngui.utils.translations import get_translation

        lang = self.settings_manager.get_current_language() or DEFAULT_LANG
        return get_translation(lang, key)

    def _build_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(10)

        self.empty_card = CardWidget(self)
        empty_layout = QVBoxLayout(self.empty_card)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title = BodyLabel(self.translate("home_empty_title"))
        self.empty_subtitle = CaptionLabel(self.translate("home_empty_subtitle"))
        self.empty_supported = CaptionLabel(self.translate("home_supported_formats"))
        self.empty_select_btn = PrimaryPushButton(self.translate("browse_files_button"))
        self.empty_select_btn.clicked.connect(self.browse_files)
        empty_layout.addWidget(self.empty_title, 0, Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addWidget(self.empty_subtitle, 0, Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addWidget(self.empty_select_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addWidget(self.empty_supported, 0, Qt.AlignmentFlag.AlignHCenter)

        self.queue_card = CardWidget(self)
        queue_layout = QVBoxLayout(self.queue_card)
        queue_layout.setContentsMargins(12, 12, 12, 12)
        queue_layout.setSpacing(8)
        queue_layout.addWidget(BodyLabel(self.translate("home_queue_title")))

        self.filePanel = FilePanel(self.translate)
        self.filePanel.files_added.connect(self.handle_files_added)
        queue_layout.addWidget(self.filePanel, 1)

        queue_actions = QHBoxLayout()
        queue_actions.setSpacing(8)
        self.remove_selected_btn = PushButton(self.translate("remove_selected_action"))
        self.remove_selected_btn.clicked.connect(self.remove_selected_files)
        self.clear_list_btn = PushButton(self.translate("clear_list_action"))
        self.clear_list_btn.clicked.connect(self.clear_file_list)
        queue_actions.addWidget(self.remove_selected_btn)
        queue_actions.addWidget(self.clear_list_btn)
        queue_actions.addStretch(1)
        queue_layout.addLayout(queue_actions)

        self.progress = ProgressBar()
        queue_layout.addWidget(self.progress)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.convert_button = PrimaryPushButton(self.translate("convert_files_button"))
        self.pause_button = PushButton(self.translate("pause_button"))
        self.cancel_button = PushButton(self.translate("cancel_button"))
        self.pause_button.setCheckable(True)
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.convert_button.clicked.connect(self.convert_files)
        self.pause_button.toggled.connect(self.toggle_pause)
        self.cancel_button.clicked.connect(self.cancel_conversion)
        controls.addWidget(self.convert_button)
        controls.addStretch(1)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.cancel_button)
        queue_layout.addLayout(controls)

        self.results_card = CardWidget(self)
        results_layout = QVBoxLayout(self.results_card)
        results_layout.setContentsMargins(12, 12, 12, 12)
        results_layout.setSpacing(8)
        results_layout.addWidget(BodyLabel(self.translate("home_results_title")))

        splitter = QSplitter(Qt.Orientation.Horizontal, self.results_card)
        self.result_file_list = QListWidget(splitter)
        self.result_file_list.currentItemChanged.connect(self._on_result_file_changed)

        left_panel = QWidget(splitter)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(BodyLabel(self.translate("home_source_label")))
        self.source_text = QTextEdit(left_panel)
        self.source_text.setReadOnly(True)
        left_layout.addWidget(self.source_text, 1)

        right_panel = QWidget(splitter)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        right_layout.addWidget(BodyLabel(self.translate("home_markdown_preview_label")))
        self.markdown_preview = QTextBrowser(right_panel)
        self.markdown_preview.setOpenExternalLinks(True)
        right_layout.addWidget(self.markdown_preview, 1)

        splitter.addWidget(self.result_file_list)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)
        results_layout.addWidget(splitter, 1)

        result_actions = QHBoxLayout()
        result_actions.setSpacing(8)
        result_actions.addStretch(1)
        self.copy_btn = PushButton(self.translate("copy_output_button"))
        self.copy_btn.clicked.connect(self.copy_output)
        self.save_btn = PushButton(self.translate("save_output_button"))
        self.save_btn.clicked.connect(self.save_output)
        result_actions.addWidget(self.copy_btn)
        result_actions.addWidget(self.save_btn)
        results_layout.addLayout(result_actions)

        self.main_layout.addWidget(self.empty_card)
        self.main_layout.addWidget(self.queue_card)
        self.main_layout.addWidget(self.results_card, 1)

    def setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self, self.browse_files)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_output)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_output)
        QShortcut(QKeySequence("Ctrl+P"), self, lambda: self.pause_button.toggle())
        QShortcut(QKeySequence("Ctrl+B"), self, self.convert_files)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_file_list)
        QShortcut(QKeySequence("Ctrl+K"), self, self.show_shortcuts)
        QShortcut(QKeySequence("Esc"), self, self.cancel_conversion)

    def setup_update_checker(self) -> None:
        if self.settings_manager.get_update_notifications_enabled():
            self.update_check_timer = QTimer(self)
            self.update_check_timer.setSingleShot(True)
            self.update_check_timer.timeout.connect(self.start_update_check)
            self.update_check_timer.start(2000)

    def start_update_check(self) -> None:
        from markitdowngui.utils.update_checker import UpdateChecker

        self.update_checker = UpdateChecker(self)
        self.update_checker.update_available.connect(self._on_update_available)
        self.update_checker.update_error.connect(self._on_update_error)
        self.update_checker.no_update_available.connect(self._on_no_update)
        self.update_checker.start()

    def _on_update_available(self, new_version: str) -> None:
        from markitdowngui.ui.dialogs.update_dialog import UpdateDialog

        dialog = UpdateDialog(new_version, self.translate, self.settings_manager, self)
        dialog.exec()

    def _on_update_error(self, error_message: str) -> None:
        AppLogger.error(f"Update check failed: {error_message}")

    def _on_no_update(self) -> None:
        AppLogger.info("No updates available")

    def manual_update_check(self) -> None:
        from markitdowngui.utils.update_checker import UpdateChecker

        self.update_checker = UpdateChecker(self)
        self.update_checker.update_available.connect(self._on_update_available)
        self.update_checker.update_error.connect(self._on_update_error_manual)
        self.update_checker.no_update_available.connect(self._on_no_update_manual)
        self.update_checker.start()

    def _on_update_error_manual(self, error_message: str) -> None:
        QMessageBox.warning(
            self, self.translate("update_check_error_title"), error_message
        )

    def _on_no_update_manual(self) -> None:
        QMessageBox.information(
            self,
            self.translate("update_check_no_update_title"),
            self.translate("update_check_no_update_message"),
        )

    def shutdown(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.is_cancelled = True
            self.worker.wait(2000)
        if hasattr(self, "update_checker") and self.update_checker.isRunning():
            self.update_checker.wait(2000)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasUrls():
            return
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                files.append(path)
        if files:
            self._add_files_to_queue(files)
            event.acceptProposedAction()

    def browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.translate("select_files_title"),
            "",
            self.translate("all_files_filter"),
        )
        if files:
            self._add_files_to_queue(files)

    def handle_files_added(self, files: list[str]) -> None:
        self._add_files_to_queue(files, add_to_panel=False)

    def _add_files_to_queue(self, files: list[str], add_to_panel: bool = True) -> None:
        existing = set(self.filePanel.get_all_files())
        added = False

        for file in files:
            if not file or file in existing:
                continue
            if add_to_panel:
                self.filePanel.add_file(file)
            existing.add(file)
            added = True
            self.handleNewFile(file)

        if added:
            self._set_state_queue()
            self._clear_result_views()

    def handleNewFile(self, filepath: str) -> None:
        try:
            self.settings_manager.set_recent_files(
                self.file_manager.update_recent_list(
                    filepath, self.settings_manager.get_recent_files()
                )
            )
            AppLogger.info(
                self.translate("added_file_to_recent_log").format(file=filepath)
            )
        except Exception as e:
            AppLogger.error(
                self.translate("error_handling_new_file_log").format(error=str(e))
            )

    def remove_selected_files(self) -> None:
        widget = self.filePanel.drop.listWidget
        selected = sorted(
            widget.selectedItems(),
            key=lambda item: widget.row(item),
            reverse=True,
        )
        for item in selected:
            widget.takeItem(widget.row(item))
        if widget.count() == 0:
            self._set_state_empty()
        self._clear_result_views()

    def clear_file_list(self) -> None:
        self.filePanel.clear()
        self._clear_result_views()
        self._set_state_empty()
        AppLogger.info(self.translate("file_list_cleared_log"))

    def toggle_pause(self, paused: bool) -> None:
        if self.worker:
            self.worker.is_paused = paused
            self.pause_button.setText(
                self.translate("resume_button")
                if paused
                else self.translate("pause_button")
            )

    def cancel_conversion(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.is_cancelled = True
            self.worker.is_paused = False
            self.pause_button.setChecked(False)
            AppLogger.info(self.translate("conversion_cancelled_log"))

    def convert_files(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self,
                self.translate("conversion_in_progress_title"),
                self.translate("conversion_in_progress_message"),
            )
            return

        files = self.filePanel.get_all_files()
        if not files:
            QMessageBox.warning(
                self,
                self.translate("no_files_to_convert_title"),
                self.translate("no_files_to_convert_message"),
            )
            return

        valid_files = [f for f in files if os.path.exists(f) and os.access(f, os.R_OK)]
        if not valid_files:
            QMessageBox.warning(
                self,
                self.translate("no_valid_files_title"),
                self.translate("no_valid_files_message"),
            )
            return

        try:
            # Delay importing MarkItDown until conversion actually starts.
            from markitdown import MarkItDown

            md = MarkItDown()
            settings = self.settings_manager.get_format_settings()
            batch_size = self.settings_manager.get_batch_size()

            self.worker = ConversionWorker([md, valid_files, settings], batch_size)
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.handle_conversion_finished)
            self.worker.error.connect(self.handle_conversion_error)

            self.pause_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.convert_button.setEnabled(False)
            self.progress.setValue(0)
            self.progress.setFormat(self.translate("conversion_starting_message"))
            self.worker.start()
            self._set_state_queue()
        except Exception as e:
            AppLogger.error(f"Error starting conversion: {str(e)}")
            QMessageBox.critical(
                self,
                self.translate("conversion_start_error_title"),
                self.translate("conversion_start_error_message").format(error=str(e)),
            )
            self._reset_controls()

    def update_progress(self, progress: int, current_file: str) -> None:
        self.progress.setValue(progress)
        self.progress.setFormat(
            self.translate("conversion_progress_format").format(
                progress=progress, file=os.path.basename(current_file)
            )
        )

    def handle_conversion_finished(self, results: dict[str, str]) -> None:
        self.conversionResults = results
        self.progress.setValue(100)
        self.progress.setFormat(self.translate("conversion_complete_message"))
        self._reset_controls()
        self._populate_result_view()
        self._set_state_results()

    def handle_conversion_error(self, error_msg: str) -> None:
        AppLogger.error(error_msg)
        QMessageBox.critical(self, self.translate("conversion_error_title"), error_msg)
        self._reset_controls()

    def _reset_controls(self) -> None:
        self.pause_button.setEnabled(False)
        self.pause_button.setChecked(False)
        self.pause_button.setText(self.translate("pause_button"))
        self.cancel_button.setEnabled(False)
        self.convert_button.setEnabled(True)
        self.worker = None

    def _populate_result_view(self) -> None:
        self.result_file_list.clear()
        for file in self.conversionResults.keys():
            item_text = os.path.basename(file)
            self.result_file_list.addItem(item_text)
            self.result_file_list.item(self.result_file_list.count() - 1).setData(
                Qt.ItemDataRole.UserRole, file
            )
        if self.result_file_list.count() > 0:
            self.result_file_list.setCurrentRow(0)

    def _on_result_file_changed(self, current, _previous) -> None:
        if not current:
            self.source_text.clear()
            self.markdown_preview.clear()
            return
        file_path = current.data(Qt.ItemDataRole.UserRole)
        markdown = self.conversionResults.get(file_path, "")
        self.source_text.setPlainText(markdown)
        self.markdown_preview.setMarkdown(markdown)

    def copy_output(self) -> None:
        text = self.markdown_preview.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def save_output(self) -> None:
        if not self.conversionResults:
            QMessageBox.warning(
                self,
                self.translate("no_output_to_save_title"),
                self.translate("no_output_to_save_message"),
            )
            return

        if self.settings_manager.get_save_mode():
            self.save_combined_output()
        else:
            self.save_individual_outputs()

    def save_combined_output(self) -> None:
        output_ext = self.settings_manager.get_default_output_format()
        output_dir = self._get_default_output_dir()
        default_name = f"converted{output_ext}"
        if output_dir:
            default_name = os.path.join(output_dir, default_name)
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translate("save_combined_title"),
            default_name,
            self.translate("markdown_files_filter"),
        )
        if not output_path:
            return
        if not output_path.lower().endswith(output_ext.lower()):
            output_path += output_ext

        parts = []
        for file, content in self.conversionResults.items():
            parts.append(f"File: {file}\n{content}")
        combined_output = "\n\n".join(parts)

        try:
            self.file_manager.save_markdown_file(output_path, combined_output)
            self.settings_manager.set_recent_outputs(
                self.file_manager.update_recent_list(
                    output_path, self.settings_manager.get_recent_outputs()
                )
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("error_saving_combined_title"),
                self.translate("error_saving_combined_message").format(error=str(e)),
            )

    def save_individual_outputs(self) -> None:
        output_dir = QFileDialog.getExistingDirectory(
            self,
            self.translate("select_directory_title"),
            self._get_default_output_dir(),
        )
        if not output_dir:
            return

        output_ext = self.settings_manager.get_default_output_format()
        for input_file, content in self.conversionResults.items():
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_path = os.path.join(output_dir, f"{base_name}{output_ext}")
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(output_dir, f"{base_name}_{counter}{output_ext}")
                counter += 1
            try:
                self.file_manager.save_markdown_file(output_path, content)
            except Exception:
                AppLogger.error(f"Failed saving file: {output_path}")

    def _get_default_output_dir(self) -> str:
        output_dir = self.settings_manager.get_default_output_folder()
        if output_dir and os.path.isdir(output_dir):
            return output_dir
        return ""

    def _clear_result_views(self) -> None:
        self.conversionResults = {}
        self.result_file_list.clear()
        self.source_text.clear()
        self.markdown_preview.clear()

    def _set_state_empty(self) -> None:
        self.empty_card.setVisible(True)
        self.queue_card.setVisible(False)
        self.results_card.setVisible(False)

    def _set_state_queue(self) -> None:
        self.empty_card.setVisible(False)
        self.queue_card.setVisible(True)
        self.results_card.setVisible(False)

    def _set_state_results(self) -> None:
        self.empty_card.setVisible(False)
        self.queue_card.setVisible(False)
        self.results_card.setVisible(True)

    def show_shortcuts(self) -> None:
        dialog = ShortcutDialog(self.translate, self)
        dialog.exec()
