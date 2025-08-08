import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMenuBar, QMenu,
    QFileDialog,
    QApplication, QMessageBox, QSplitter, QDialog, QToolButton
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import (
    QKeySequence,
    QPalette,
    QShortcut,
    QAction,
    QActionGroup,
    QColor,
)
from typing import cast
from markitdown import MarkItDown

from markitdowngui.core.settings import SettingsManager
from markitdowngui.core.conversion import ConversionWorker
from markitdowngui.core.file_utils import FileManager
from markitdowngui.utils.logger import AppLogger
from markitdowngui.ui.themes import apply_dark_theme, apply_light_theme, markdown_css
from markitdowngui.ui.components.file_panel import FilePanel
from markitdowngui.ui.components.settings_bar import SettingsBar
from markitdowngui.ui.components.convert_controls import ConvertControls
from markitdowngui.ui.components.output_panel import OutputPanel
from markitdowngui.ui.components.preview_panel import PreviewPanel
from markitdowngui.ui.dialogs.format_settings import FormatSettings
from markitdowngui.ui.dialogs.shortcuts import ShortcutDialog
from markitdowngui.ui.dialogs.update_dialog import UpdateDialog
from markitdowngui.ui.dialogs.about import AboutDialog
from markitdowngui.ui.icons import make_tinted_svg_icon
from markitdowngui.ui.preview_worker import PreviewWorker
from markitdowngui.utils.translations import get_translation, get_available_languages, DEFAULT_LANG
from markitdowngui.utils.update_checker import UpdateChecker

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.is_main_window = True
        self.settings_manager = SettingsManager()
        self.file_manager = FileManager()
        self.current_lang = self.settings_manager.get_current_language() or DEFAULT_LANG
        self._preview_request_id = 0
        self._preview_worker = None
        self._preview_config_cache = None  # tuple(enable_plugins:bool, endpoint:str)
        self.setup_window()
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_auto_save()
        self.preview_md = MarkItDown()
        self.setup_update_checker()
        AppLogger.info("Application started")

    def setup_window(self):
        """Initialize window properties."""
        self.setWindowTitle(self.translate("app_title") or "MarkItDown GUI")
        self.setMinimumSize(600, 500) # Keep minimum size
        self.isDarkMode = self.settings_manager.get_dark_mode()
        self.apply_theme()

        # Restore window geometry
        geometry = self.settings_manager.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)

    def setup_ui(self):
        """Set up the user interface."""
        # Create menu bar
        self.setup_menu_bar()
        
        # Main layout
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setMenuBar(self.menuBar)

        # Top controls row: left spacer + theme toggle 
        topControls = QHBoxLayout()
        topControls.addStretch()
        self.themeToggleButton = QToolButton(self)
        self.themeToggleButton.setToolTip(self.translate("menu_dark_mode") or "Dark Mode")
        self.themeToggleButton.setAutoRaise(True)
        self.themeToggleButton.clicked.connect(self.toggle_dark_mode)
        self._update_theme_toggle_icon()
        topControls.addWidget(self.themeToggleButton)
        self.mainLayout.addLayout(topControls)

        # File handling area component
        self.filePanel = FilePanel(self.translate)
        self.filePanel.current_item_changed.connect(self.update_preview)
        self.filePanel.files_added.connect(self.handle_files_added)

        # Create a splitter for file list and preview
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: File list
        leftWidget = QWidget()
        leftLayout = QVBoxLayout(leftWidget)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setSpacing(6)
        leftLayout.addWidget(self.filePanel)
        leftWidget.setMinimumWidth(180)

        # Right side: Preview (component)
        self.previewPanel = PreviewPanel(self.translate)
        rightWidget = self.previewPanel
        rightWidget.setMinimumWidth(240)

        # Add widgets to splitter
        self.splitter.addWidget(leftWidget)
        self.splitter.addWidget(rightWidget)
        # Improve alignment and prevent collapsing
        self.splitter.setChildrenCollapsible(False)
        try:
            # PySide6 6.6+ supports per-section collapsible control
            self.splitter.setCollapsible(0, False)
            self.splitter.setCollapsible(1, False)
        except Exception:
            pass
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        # Update main layout
        self.mainLayout.addWidget(self.splitter)

        # Restore splitter state
        splitter_state = self.settings_manager.get_splitter_state()
        if splitter_state:
            self.splitter.restoreState(splitter_state)
        
        # Settings bar and controls (components) above output, in a vertical splitter
        self.settingsBar = SettingsBar(self.translate)
        self.convertControls = ConvertControls(self.translate)
        self.convertControls.pause_button.toggled.connect(self.toggle_pause)
        self.convertControls.cancel_button.clicked.connect(self.cancel_conversion)
        self.convertControls.convert_button.clicked.connect(self.convert_files)

        # React to settings changes for preview cache invalidation
        self.settingsBar.plugins_toggled.connect(lambda _: self._invalidate_preview_cache())
        self.settingsBar.endpoint_changed.connect(lambda _t: self._invalidate_preview_cache())

        # Output area component
        self.outputPanel = OutputPanel(self.translate, self.settings_manager.get_save_mode())
        # wire save mode to settings
        self.outputPanel.combined_toggle.toggled.connect(self.settings_manager.set_save_mode)
        self.outputPanel.copy_button.clicked.connect(self.copy_output)
        self.outputPanel.save_button.clicked.connect(self.save_output)

        # Build lower splitter directly (no reparenting)
        lower_controls_container = QWidget(self)
        lower_v = QVBoxLayout(lower_controls_container)
        lower_v.setContentsMargins(0, 0, 0, 0)
        lower_v.setSpacing(6)
        lower_v.addWidget(self.settingsBar)
        lower_v.addWidget(self.convertControls)

        lower_splitter = QSplitter(Qt.Orientation.Vertical, self)
        lower_splitter.addWidget(lower_controls_container)
        lower_splitter.addWidget(self.outputPanel)
        lower_splitter.setChildrenCollapsible(False)
        try:
            lower_splitter.setCollapsible(0, False)
            lower_splitter.setCollapsible(1, False)
        except Exception:
            pass
        lower_splitter.setStretchFactor(0, 0)
        lower_splitter.setStretchFactor(1, 1)
        lower_splitter.setSizes([240, 420])
        self.mainLayout.addWidget(lower_splitter)
        self.lower_splitter = lower_splitter

    def setup_menu_bar(self):
        """Set up the application menu bar."""
        self.menuBar = QMenuBar()
        self.update_menu_bar_texts()

    def update_menu_bar_texts(self):
        """Update all texts in the menubar based on the current language."""
        self.menuBar.clear()

        # View menu
        viewMenu = QMenu(self.translate("menu_view") or "View", self)
        self.menuBar.addMenu(viewMenu)
        
        # Dark mode toggle
        self.darkModeAction = viewMenu.addAction(self.translate("menu_dark_mode") or "Dark Mode")
        self.darkModeAction.setCheckable(True)
        self.darkModeAction.setChecked(self.isDarkMode)
        self.darkModeAction.triggered.connect(self.toggle_dark_mode)

        # Language menu
        self.languageMenu = viewMenu.addMenu(self.translate("menu_language") or "Language")
        self.languageActionGroup = QActionGroup(self)
        self.languageActionGroup.setExclusive(True)
        self.languageActionGroup.triggered.connect(self.change_language)

        available_langs = get_available_languages()
        for lang_code, lang_name in available_langs.items():
            action = QAction(lang_name, self, checkable=True)
            action.setData(lang_code)
            if lang_code == self.current_lang:
                action.setChecked(True)
            self.languageMenu.addAction(action)
            self.languageActionGroup.addAction(action)
        
        # Settings menu
        settingsMenu = self.menuBar.addMenu(self.translate("menu_settings") or "Settings")
        formatAction = settingsMenu.addAction(self.translate("menu_format_settings") or "Format Settings")
        formatAction.triggered.connect(self.show_format_settings)
        
        # Help menu
        helpMenu = self.menuBar.addMenu(self.translate("menu_help") or "Help")
        shortcutsAction = helpMenu.addAction(self.translate("menu_keyboard_shortcuts") or "Keyboard Shortcuts")
        shortcutsAction.triggered.connect(self.show_shortcuts)
        
        checkUpdateAction = helpMenu.addAction(self.translate("menu_check_updates") or "Check for Updates")
        checkUpdateAction.triggered.connect(self.manual_update_check)

        # About dialog
        aboutAction = helpMenu.addAction(self.translate("about_menu") or "About")
        aboutAction.triggered.connect(self.show_about_dialog)

    # Removed legacy file area; handled by FilePanel

    # Removed legacy settings area (handled by SettingsBar)

    # Removed legacy conversion controls (handled by ConvertControls)

    # Removed legacy output area; handled by OutputPanel

    # Removed legacy reparenting; lower splitter is constructed in setup_ui

    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+O"), self, self.browse_files)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_output)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_output)
        QShortcut(QKeySequence("Ctrl+P"), self, lambda: self.convertControls.pause_button.toggle())
        QShortcut(QKeySequence("Ctrl+B"), self, self.convert_files)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_file_list)
        QShortcut(QKeySequence("Ctrl+K"), self, self.show_shortcuts)
        QShortcut(QKeySequence("Esc"), self, self.cancel_conversion)
        QShortcut(QKeySequence("Ctrl+Shift+L"), self, self.clear_file_list) # New shortcut for clear all

    def setup_auto_save(self):
        """Initialize auto-save functionality."""
        self.autoSaveTimer = QTimer()
        self.autoSaveTimer.timeout.connect(self.perform_auto_save)
        self.update_auto_save_timer()

    def toggle_dark_mode(self):
        """Toggle between light and dark themes."""
        self.isDarkMode = not self.isDarkMode
        self.settings_manager.set_dark_mode(self.isDarkMode)
        self.apply_theme()
        # Update toggle icon
        self._update_theme_toggle_icon()

    def apply_theme(self):
        """Apply the current theme to the application."""
        palette = apply_dark_theme(QPalette()) if self.isDarkMode else apply_light_theme()
        QApplication.setPalette(palette)
        # Apply centralized QSS for markdown area + menubar/menus
        app = QApplication.instance()
        if app is not None:
            cast(QApplication, app).setStyleSheet(markdown_css(self.isDarkMode))
        # Component owns its styling via global QSS now
        # Ensure toggle icon matches theme
        if hasattr(self, "themeToggleButton"):
            self._update_theme_toggle_icon()

    def convert_files(self):
        """Start the file conversion process."""
        try:
            # Check if conversion is already in progress
            if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
                AppLogger.warning("Conversion already in progress")
                QMessageBox.warning(
                    self, 
                    self.translate("conversion_in_progress_title"), 
                    self.translate("conversion_in_progress_message")
                )
                return

            # Get file list
            files = self.filePanel.get_all_files()
            
            if not files:
                AppLogger.info("Conversion attempted with no files")
                QMessageBox.warning(self, self.translate("no_files_to_convert_title"), self.translate("no_files_to_convert_message"))
                return

            # Validate files exist and are accessible
            valid_files = []
            for file in files:
                if not os.path.exists(file):
                    AppLogger.warning(f"File not found: {file}")
                    continue
                if not os.access(file, os.R_OK):
                    AppLogger.warning(f"File not readable: {file}")
                    continue
                valid_files.append(file)
            
            if not valid_files:
                QMessageBox.warning(
                    self, 
                    self.translate("no_valid_files_title"), 
                    self.translate("no_valid_files_message")
                )
                return

            AppLogger.info(f"Starting conversion of {len(valid_files)} files")
            
            # Prepare conversion settings
            try:
                settings = self.settings_manager.get_format_settings()
            except Exception as e:
                AppLogger.error(f"Error loading format settings: {str(e)}")
                QMessageBox.critical(
                    self, 
                    self.translate("settings_error_title"), 
                    self.translate("settings_error_message").format(error=str(e))
                )
                return
            
            # Create and configure MarkItDown instance
            try:
                # Prepare MarkItDown configuration
                md_kwargs = {}
                
                # Configure plugins if enabled
                if self.settingsBar.is_plugins_enabled():
                    md_kwargs['enable_plugins'] = True
                
                # Configure Document Intelligence if endpoint provided
                endpoint = self.settingsBar.get_docintel_endpoint()
                if endpoint:
                    md_kwargs['docintel_endpoint'] = endpoint
                    AppLogger.info("Document Intelligence endpoint configured")
                
                md = MarkItDown(**md_kwargs)
                    
            except Exception as e:
                AppLogger.error(f"Error configuring MarkItDown: {str(e)}")
                QMessageBox.critical(
                    self, 
                    self.translate("markitdown_config_error_title"), 
                    self.translate("markitdown_config_error_message").format(error=str(e))
                )
                return

            # Clean up any existing worker
            self._cleanup_worker()

            # Start conversion with configured instance
            try:
                self.worker = ConversionWorker([md, valid_files, settings], self.convertControls.batch_spin.value())
                self.worker.progress.connect(self.update_progress)
                self.worker.finished.connect(self.handle_conversion_finished)
                self.worker.error.connect(self.handle_conversion_error)

                # Update UI state
                self.convertControls.pause_button.setEnabled(True)
                self.convertControls.cancel_button.setEnabled(True)
                self.convertControls.convert_button.setEnabled(False)
                self.convertControls.progress.setValue(0)
                self.convertControls.progress.setFormat(self.translate("conversion_starting_message"))
                
                self.worker.start()
                AppLogger.info("Conversion worker started successfully")
                
            except Exception as e:
                AppLogger.error(f"Error starting conversion worker: {str(e)}")
                QMessageBox.critical(
                    self, 
                    self.translate("conversion_start_error_title"), 
                    self.translate("conversion_start_error_message").format(error=str(e))
                )
                self._reset_ui_state()
                
        except Exception as e:
            AppLogger.error(f"Unexpected error in convert_files: {str(e)}")
            QMessageBox.critical(
                self, 
                self.translate("unexpected_error_title"), 
                self.translate("unexpected_error_message").format(error=str(e))
            )
            self._reset_ui_state()

    def update_progress(self, progress, current_file):
        """Update the progress bar during conversion."""
        self.convertControls.progress.setValue(progress)
        self.convertControls.progress.setFormat(self.translate("conversion_progress_format").format(progress=progress, file=os.path.basename(current_file)))

    def handle_conversion_finished(self, results):
        """Handle completion of the conversion process."""
        self.conversionResults = results
        parts = []
        for file, content in results.items():
            parts.append(f"File: {file}\n{content}")
        combined_output = "\n\n".join(parts)
        
        self.outputPanel.set_text(combined_output)
        self.convertControls.progress.setValue(100)
        self.convertControls.progress.setFormat(self.translate("conversion_complete_message"))
        
        self.convertControls.pause_button.setEnabled(False)
        self.convertControls.cancel_button.setEnabled(False)
        self.convertControls.convert_button.setEnabled(True)
        self.worker = None

    def handle_conversion_error(self, error_msg):
        """Handle conversion errors."""
        AppLogger.error(error_msg)
        QMessageBox.critical(self, self.translate("conversion_error_title"), error_msg)
        self.convertControls.pause_button.setEnabled(False)
        self.convertControls.cancel_button.setEnabled(False)
        self.convertControls.convert_button.setEnabled(True)
        self.worker = None

    def copy_output(self):
        """Copy the output text to clipboard."""
        QApplication.clipboard().setText(self.outputPanel.get_text())

    def save_output(self):
        """Save the conversion output."""
        if self.outputPanel.is_combined():
            self.save_combined_output()
        else:
            self.save_individual_outputs()

    def save_combined_output(self):
        """Save all conversions in a single file."""
        output_path, _ = QFileDialog.getSaveFileName(
            self, self.translate("save_combined_title"), "", 
            self.translate("markdown_files_filter")
        )
        if output_path:
            try:
                self.file_manager.save_markdown_file(output_path, self.outputPanel.get_text())
                AppLogger.info(self.translate("auto_save_backup_log").format(path=output_path))
                
                # Add to recent outputs
                self.settings_manager.set_recent_outputs(
                    self.file_manager.update_recent_list(
                        output_path,
                        self.settings_manager.get_recent_outputs()
                    )
                )
            except Exception as e:
                AppLogger.error(f"Error saving combined output: {str(e)}")
                QMessageBox.critical(self, self.translate("error_saving_combined_title"), 
                                     self.translate("error_saving_combined_message").format(error=str(e)))

    def save_individual_outputs(self):
        """Save each conversion to a separate file."""
        if not hasattr(self, 'conversionResults') or not self.conversionResults:
            QMessageBox.warning(self, self.translate("no_output_to_save_title"), 
                                self.translate("no_output_to_save_message"))
            return
            
        output_dir = QFileDialog.getExistingDirectory(
            self,
            self.translate("select_directory_title")
        )
        
        if output_dir:
            success_count = 0
            for input_file, content in self.conversionResults.items():
                try:
                    # Create output filename based on input filename
                    base_name = os.path.splitext(os.path.basename(input_file))[0]
                    output_path = os.path.join(output_dir, f"{base_name}.md")
                    
                    # Ensure unique filename
                    counter = 1
                    while os.path.exists(output_path):
                        output_path = os.path.join(output_dir, f"{base_name}_{counter}.md")
                        counter += 1
                    
                    self.file_manager.save_markdown_file(output_path, content)
                    success_count += 1
                    AppLogger.info(self.translate("added_file_to_recent_log").format(file=output_path))
                except Exception as e:
                    AppLogger.error(self.translate("error_handling_new_file_log").format(error=str(e)))
            
            if success_count > 0:
                QMessageBox.information(
                    self,
                    self.translate("save_individual_complete_title"),
                    self.translate("save_individual_complete_message").format(count=success_count, dir=output_dir)
                )
                
                # Add to recent outputs
                self.settings_manager.set_recent_outputs(
                    self.file_manager.update_recent_list(
                        output_dir,
                        self.settings_manager.get_recent_outputs()
                    )
                )

    def show_shortcuts(self):
        """Show the keyboard shortcuts dialog."""
        dialog = ShortcutDialog(self.translate, self)
        dialog.exec()

    def show_format_settings(self):
        """Show the format settings dialog."""
        dialog = FormatSettings(self.settings_manager, self.translate, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_auto_save_timer()
            AppLogger.info(self.translate("format_settings_updated_log"))

    def show_about_dialog(self):
        """Display an About dialog with version and license info."""
        # Delegate to dedicated dialog
        dlg = AboutDialog(self.translate, self)
        dlg.exec()

    def perform_auto_save(self):
        """Perform auto-save of current output."""
        if hasattr(self, 'conversionResults') and self.conversionResults:
            backup_path = os.path.join(
                self.file_manager.get_backup_dir(),
                self.file_manager.create_backup_filename()
            )
            try:
                self.file_manager.save_markdown_file(backup_path, self.outputPanel.get_text())
                AppLogger.info(self.translate("auto_save_backup_log").format(path=backup_path))
            except Exception as e:
                AppLogger.error(self.translate("auto_save_failed_log").format(error=str(e)))

    def update_auto_save_timer(self):
        """Update the auto-save timer based on current settings."""
        settings = self.settings_manager.get_format_settings()
        if settings['autoSave']:
            interval = settings['autoSaveInterval'] * 60 * 1000  # Convert to milliseconds
            self.autoSaveTimer.start(interval)
        else:
            self.autoSaveTimer.stop()

    def _update_theme_toggle_icon(self):
        """Update theme toggle icon to reflect current theme."""
        try:
            icon_name = "sun" if self.isDarkMode else "moon"
            tint_color = QColor("#FFD76A") if self.isDarkMode else QColor("#2F2F2F")
            resources_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "resources"))
            desired_size: QSize = (
                self.themeToggleButton.iconSize()
                if self.themeToggleButton.iconSize().isValid()
                else self.themeToggleButton.sizeHint()
            )
            icon = make_tinted_svg_icon(resources_dir, icon_name, tint_color, desired_size)
            self.themeToggleButton.setIcon(icon)
            self.themeToggleButton.setIconSize(desired_size)
        except Exception:
            self.themeToggleButton.setText("☀" if self.isDarkMode else "🌙")

    # Removed: icon rendering is handled by ui.icons.make_tinted_svg_icon

    def update_preview(self, current, previous):
        """Update the preview of the selected file."""
        if not current:
            self.previewPanel.clear()
            return
            
        try:
            filepath = current.text()
            AppLogger.info(f"Generating preview for {filepath}")
            
            # Rebuild preview MarkItDown only if settings changed
            enable_plugins = bool(self.settingsBar.is_plugins_enabled())
            endpoint = self.settingsBar.get_docintel_endpoint()
            cfg = (enable_plugins, endpoint)
            if cfg != self._preview_config_cache:
                md_kwargs = {}
                if enable_plugins:
                    md_kwargs['enable_plugins'] = True
                if endpoint:
                    md_kwargs['docintel_endpoint'] = endpoint
                self.preview_md = MarkItDown(**md_kwargs)
                self._preview_config_cache = cfg

            # Cancel previous worker if running
            if self._preview_worker and self._preview_worker.isRunning():
                try:
                    self._preview_worker.terminate()
                    self._preview_worker.wait()
                except Exception:
                    pass

            # Start new worker
            self._preview_request_id += 1
            req_id = self._preview_request_id
            worker = PreviewWorker(self.preview_md, filepath, req_id)
            worker.result.connect(self._on_preview_ready)
            worker.error.connect(self._on_preview_error)
            self._preview_worker = worker
            worker.start()
            
        except Exception as e:
            error_msg = f"Error previewing file: {str(e)}"
            self.previewPanel.set_plain(error_msg)
            AppLogger.error(self.translate("preview_error_log").format(error=str(e)), filepath)

    def _on_preview_ready(self, request_id: int, text: str):
        # Ignore stale results
        if request_id != self._preview_request_id:
            return
        # Render Markdown vs plain
        current_text = self.filePanel.current_item_text()
        if not current_text:
            return
        lower = current_text.lower()
        if lower.endswith(".md") or lower.endswith(".markdown"):
            self.previewPanel.set_markdown(text)
        else:
            self.previewPanel.set_plain(text)
        AppLogger.info("Preview generated successfully")

    def _on_preview_error(self, request_id: int, message: str):
        if request_id != self._preview_request_id:
            return
        self.previewPanel.set_plain(f"Error previewing file: {message}")
        AppLogger.error(self.translate("preview_error_log").format(error=message))

    def _invalidate_preview_cache(self) -> None:
        """Invalidate preview MarkItDown cache so next selection recreates it."""
        self._preview_config_cache = None

    def browse_files(self):
        """Open file browser dialog to select files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.translate("select_files_title"),
            "",
            self.translate("all_files_filter")
        )
        for file in files:
            self.filePanel.add_file(file)
            self.handleNewFile(file)
    
    def clear_file_list(self):
        """Clear the file list."""
        self.filePanel.clear()
        self.previewPanel.clear()
        AppLogger.info(self.translate("file_list_cleared_log"))
    
    def handleNewFile(self, filepath):
        """Handle newly added file."""
        try:
            self.settings_manager.set_recent_files(
                self.file_manager.update_recent_list(
                    filepath, 
                    self.settings_manager.get_recent_files()
                )
            )
            AppLogger.info(self.translate("added_file_to_recent_log").format(file=filepath))
        except Exception as e:
            AppLogger.error(self.translate("error_handling_new_file_log").format(error=str(e)))

    def toggle_pause(self, paused):
        """Toggle conversion pause state."""
        if hasattr(self, 'worker') and self.worker:
            self.worker.is_paused = paused
            self.convertControls.pause_button.setText(self.translate("resume_button") if paused else self.translate("pause_button"))
            AppLogger.info(self.translate("conversion_paused_log") if paused else self.translate("conversion_resumed_log"))

    def cancel_conversion(self):
        """Cancel the ongoing conversion."""
        if hasattr(self, 'worker') and self.worker:
            self.worker.is_cancelled = True
            self.worker.is_paused = False
            self.convertControls.pause_button.setChecked(False)
            AppLogger.info(self.translate("conversion_cancelled_log"))
    

    def _cleanup_worker(self):
        """Clean up any existing worker thread."""
        if hasattr(self, 'worker') and self.worker:
            if self.worker.isRunning():
                self.worker.is_cancelled = True
                self.worker.is_paused = False
                self.worker.wait(3000)  # Wait up to 3 seconds
                if self.worker.isRunning():
                    self.worker.terminate()
                    self.worker.wait()
            
            # Disconnect signals to prevent conflicts
            try:
                self.worker.progress.disconnect()
                self.worker.finished.disconnect()
                self.worker.error.disconnect()
            except Exception:
                # Signals might already be disconnected
                pass
                
            self.worker = None
            AppLogger.info("Worker thread cleaned up")
    
    def _reset_ui_state(self):
        """Reset UI to initial state after error or completion."""
        self.convertControls.pause_button.setEnabled(False)
        self.convertControls.cancel_button.setEnabled(False)
        self.convertControls.convert_button.setEnabled(True)
        self.convertControls.pause_button.setChecked(False)
        self.convertControls.pause_button.setText(self.translate("pause_button"))
        self.convertControls.progress.setValue(0)
        self.convertControls.progress.setFormat("")

    def change_language(self, action):
        """Change the application language."""
        lang_code = action.data()
        if lang_code and lang_code != self.current_lang:
            self.current_lang = lang_code
            self.settings_manager.set_current_language(lang_code)
        self.retranslate_ui()

    def translate(self, key) -> str:
        """Translate a key using the current language, ensuring a string is always returned."""
        translation = get_translation(self.current_lang, key)
        return translation if translation is not None else ""

    def retranslate_ui(self):
        """Retranslate all UI elements after language change."""
        AppLogger.info(f"Changing language to: {self.current_lang}")
        self.setup_window()
        self.update_menu_bar_texts()

        # Retranslate other UI elements
        self.filePanel.retranslate_ui(self.translate)
        self.previewPanel.retranslate_ui(self.translate)
        self.settingsBar.retranslate_ui(self.translate)
        self.convertControls.retranslate_ui(self.translate)

        self.outputPanel.retranslate_ui(self.translate)
        
        self.update()
        QApplication.processEvents()

    def handle_files_added(self, files):
        # Add only files not already in the list
        existing = set(self.filePanel.get_all_files())
        for file in files:
            if file not in existing:
                self.filePanel.add_file(file)
                self.handleNewFile(file)

    def closeEvent(self, event):
        """Save window geometry and splitter state on close."""
        self.settings_manager.set_window_geometry(self.saveGeometry().data())
        # QWidget does not have saveState, only QMainWindow.
        # self.settings_manager.set_window_state(self.saveState().data())
        self.settings_manager.set_splitter_state(self.splitter.saveState().data())
        super().closeEvent(event)

    def setup_update_checker(self):
        """Set up the update checker to run after the app has started."""
        # Only check for updates if notifications are enabled
        if self.settings_manager.get_update_notifications_enabled():
            # Use a timer to delay the update check until after the UI is fully loaded
            self.update_check_timer = QTimer()
            self.update_check_timer.setSingleShot(True)
            self.update_check_timer.timeout.connect(self.start_update_check)
            self.update_check_timer.start(2000)  # Check for updates 2 seconds after startup

    def start_update_check(self):
        """Start the update check in a separate thread."""
        self.update_checker = UpdateChecker(self)
        self.update_checker.update_available.connect(self._on_update_available)
        self.update_checker.update_error.connect(self._on_update_error)
        self.update_checker.no_update_available.connect(self._on_no_update)
        self.update_checker.start()

    def _on_update_available(self, new_version):
        dialog = UpdateDialog(new_version, self.translate, self.settings_manager, self)
        dialog.exec()

    def _on_update_error(self, error_message):
        AppLogger.error(f"Update check failed: {error_message}")

    def _on_no_update(self):
        AppLogger.info("No updates available")

    def manual_update_check(self):
        """Manually trigger an update check."""
        # For manual checks, always proceed regardless of notification settings
        self.update_checker = UpdateChecker(self)
        self.update_checker.update_available.connect(self._on_update_available)
        self.update_checker.update_error.connect(self._on_update_error_manual)
        self.update_checker.no_update_available.connect(self._on_no_update_manual)
        self.update_checker.start()

    def _on_update_error_manual(self, error_message):
        QMessageBox.warning(
            self,
            self.translate("update_check_error_title"),
            self.translate("update_check_error_message").format(error=error_message)
        )

    def _on_no_update_manual(self):
        QMessageBox.information(
            self,
            self.translate("update_check_no_update_title"),
            self.translate("update_check_no_update_message")
        )
