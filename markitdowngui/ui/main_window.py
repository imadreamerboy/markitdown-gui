import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMenuBar, QMenu,
    QFileDialog, QCheckBox, QLineEdit, QLabel, QTextEdit, QProgressBar,
    QApplication, QComboBox, QSpinBox, QMessageBox, QSplitter, QDialog, QToolButton, QTextBrowser
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QPalette, QShortcut, QAction, QActionGroup, QIcon
from markitdown import MarkItDown

from markitdowngui.core.settings import SettingsManager
from markitdowngui.core.conversion import ConversionWorker
from markitdowngui.core.file_utils import FileManager
from markitdowngui.utils.logger import AppLogger
from markitdowngui.ui.themes import apply_dark_theme, apply_light_theme, markdown_css
from markitdowngui.ui.drop_widget import DropWidget
from markitdowngui.ui.dialogs.format_settings import FormatSettings
from markitdowngui.ui.dialogs.shortcuts import ShortcutDialog
from markitdowngui.ui.dialogs.update_dialog import UpdateDialog
from markitdowngui.__init__ import __version__ as APP_VERSION
from markitdowngui.utils.translations import get_translation, get_available_languages, DEFAULT_LANG
from markitdowngui.utils.update_checker import UpdateChecker

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.is_main_window = True
        self.settings_manager = SettingsManager()
        self.file_manager = FileManager()
        self.current_lang = self.settings_manager.get_current_language() or DEFAULT_LANG
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
        # Note: QWidget does not have restoreState. Only QMainWindow has it.
        # If window state (maximized/minimized) needs to be persisted,
        # the main window should inherit from QMainWindow.
        # For now, only geometry is restored for QWidget.

    def setup_ui(self):
        """Set up the user interface."""
        # Create menu bar
        self.setup_menu_bar()
        
        # Main layout
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setMenuBar(self.menuBar)

        # Top bar with theme toggle button (right-aligned)
        topBar = QHBoxLayout()
        topBar.addStretch()
        self.themeToggleButton = QToolButton(self)
        self.themeToggleButton.setToolTip(self.translate("menu_dark_mode") or "Dark Mode")
        self.themeToggleButton.setAutoRaise(True)
        self.themeToggleButton.clicked.connect(self.toggle_dark_mode)
        self._update_theme_toggle_icon()
        topBar.addWidget(self.themeToggleButton)
        self.mainLayout.addLayout(topBar)
        
        # File handling area
        self.setup_file_area()
        
        # Create a splitter for file list and preview
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: File list
        leftWidget = QWidget()
        leftLayout = QVBoxLayout(leftWidget)
        leftLayout.addWidget(self.dropWidget)
        
        # Right side: Preview
        rightWidget = QWidget()
        rightLayout = QVBoxLayout(rightWidget)
        self.previewLabel = QLabel(self.translate("preview_label"))
        # Use QTextBrowser to support rich text/Markdown display
        self.previewText = QTextBrowser()
        self.previewText.setOpenExternalLinks(True)
        # Guard translate() returning None for type checkers
        self.previewText.setPlaceholderText(self.translate("preview_placeholder") or "")
        rightLayout.addWidget(self.previewLabel)
        rightLayout.addWidget(self.previewText)
        
        # Add widgets to splitter
        self.splitter.addWidget(leftWidget)
        self.splitter.addWidget(rightWidget)
        
        # Update main layout
        self.mainLayout.addWidget(self.splitter)

        # Restore splitter state
        splitter_state = self.settings_manager.get_splitter_state()
        if splitter_state:
            self.splitter.restoreState(splitter_state)
        
        # Settings area
        self.setup_settings_area()
        
        # Conversion controls
        self.setup_conversion_controls()
        
        # Output area
        self.setup_output_area()

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
        aboutAction = helpMenu.addAction(self.translate("menu_about") or "About")
        aboutAction.triggered.connect(self.show_about_dialog)

    def setup_file_area(self):
        """Set up the file handling area."""
        self.dropWidget = DropWidget(self.translate)
        self.dropWidget.listWidget.currentItemChanged.connect(self.update_preview)
        self.dropWidget.filesAdded.connect(self.handle_files_added)

        # Clear all button for file list
        self.clearAllButton = QPushButton(self.translate("clear_all_button") or "Clear All")
        self.clearAllButton.clicked.connect(self.clear_file_list)

        fileListLayout = QVBoxLayout()
        fileListLayout.addWidget(self.dropWidget)
        fileListLayout.addWidget(self.clearAllButton)
        
        # Add file list to main layout
        self.mainLayout.addLayout(fileListLayout)

    def setup_settings_area(self):
        """Set up the settings area."""
        settingsLayout = QHBoxLayout()
        
        self.enablePluginsCheck = QCheckBox(self.translate("enable_plugins_checkbox") or "")
        self.enablePluginsCheck.setToolTip(self.translate("enable_plugins_tooltip") or "")
        
        self.docIntelLine = QLineEdit()
        self.docIntelLine.setPlaceholderText(self.translate("doc_intel_placeholder") or "")
        self.docIntelLine.setToolTip(self.translate("doc_intel_tooltip") or "")
        
        settingsLayout.addWidget(self.enablePluginsCheck)
        settingsLayout.addWidget(self.docIntelLine)
        
        self.settingsGroupLabel = QLabel(self.translate("settings_group_label") or "")
        self.mainLayout.addWidget(self.settingsGroupLabel)
        self.mainLayout.addLayout(settingsLayout)

    def setup_conversion_controls(self):
        """Set up the conversion control area."""
        # Batch processing controls
        batchLayout = QHBoxLayout()
        self.batchSizeSpinBox = QSpinBox()
        self.batchSizeSpinBox.setRange(1, 10)
        self.batchSizeSpinBox.setValue(3)
        self.batchSizeSpinBox.setToolTip(self.translate("batch_size_tooltip") or "")
        
        self.pauseButton = QPushButton(self.translate("pause_button") or "")
        self.pauseButton.setEnabled(False)
        self.pauseButton.setCheckable(True)
        self.pauseButton.toggled.connect(self.toggle_pause)
        
        self.cancelButton = QPushButton(self.translate("cancel_button") or "")
        self.cancelButton.setEnabled(False)
        self.cancelButton.clicked.connect(self.cancel_conversion)
        
        self.batchSizeLabel = QLabel(self.translate("batch_size_label") or "")
        batchLayout.addWidget(self.batchSizeLabel)
        batchLayout.addWidget(self.batchSizeSpinBox)
        batchLayout.addWidget(self.pauseButton)
        batchLayout.addWidget(self.cancelButton)
        
        # Convert button and progress bar
        self.convertButton = QPushButton(self.translate("convert_files_button") or "")
        self.convertButton.clicked.connect(self.convert_files)
        self.progressBar = QProgressBar()
        
        self.mainLayout.addWidget(self.convertButton)
        self.mainLayout.addWidget(self.progressBar)
        self.mainLayout.addLayout(batchLayout)

    def setup_output_area(self):
        """Set up the output display area."""
        self.outputText = QTextEdit()
        self.outputText.setReadOnly(True)
        
        # Save mode toggle with saved preference
        saveModeLayout = QHBoxLayout()
        self.combinedSaveCheck = QCheckBox(self.translate("output_save_all_in_one_checkbox") or "")
        self.combinedSaveCheck.setChecked(self.settings_manager.get_save_mode())
        self.combinedSaveCheck.setToolTip(self.translate("output_save_all_in_one_tooltip") or "")
        self.combinedSaveCheck.toggled.connect(self.settings_manager.set_save_mode)
        saveModeLayout.addWidget(self.combinedSaveCheck)
        saveModeLayout.addStretch()
        
        # Output controls
        outputControls = QHBoxLayout()
        self.copyButton = QPushButton(self.translate("copy_output_button") or "")
        self.copyButton.clicked.connect(self.copy_output)
        self.saveButton = QPushButton(self.translate("save_output_button") or "")
        self.saveButton.clicked.connect(self.save_output)
        
        outputControls.addWidget(self.copyButton)
        outputControls.addWidget(self.saveButton)
        
        self.mainLayout.addLayout(saveModeLayout)
        self.mainLayout.addLayout(outputControls)
        self.mainLayout.addWidget(self.outputText)

    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+O"), self, self.browse_files)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_output)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_output)
        QShortcut(QKeySequence("Ctrl+P"), self, lambda: self.pauseButton.toggle())
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
        # Apply centralized Markdown CSS
        if hasattr(self, "previewText"):
            self.previewText.setStyleSheet(markdown_css(self.isDarkMode))
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
            files = [self.dropWidget.listWidget.item(i).text() 
                    for i in range(self.dropWidget.listWidget.count())]
            
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
                if self.enablePluginsCheck.isChecked():
                    md_kwargs['enable_plugins'] = True
                
                # Configure Document Intelligence if endpoint provided
                endpoint = self.docIntelLine.text().strip()
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
                self.worker = ConversionWorker([md, valid_files, settings], self.batchSizeSpinBox.value())
                self.worker.progress.connect(self.update_progress)
                self.worker.finished.connect(self.handle_conversion_finished)
                self.worker.error.connect(self.handle_conversion_error)

                # Update UI state
                self.pauseButton.setEnabled(True)
                self.cancelButton.setEnabled(True)
                self.convertButton.setEnabled(False)
                self.progressBar.setValue(0)
                self.progressBar.setFormat(self.translate("conversion_starting_message"))
                
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
        self.progressBar.setValue(progress)
        self.progressBar.setFormat(self.translate("conversion_progress_format").format(progress=progress, file=os.path.basename(current_file)))

    def handle_conversion_finished(self, results):
        """Handle completion of the conversion process."""
        self.conversionResults = results
        combined_output = ""
        for file, content in results.items():
            combined_output += f"File: {file}\n{content}\n\n"
        
        self.outputText.setPlainText(combined_output)
        self.progressBar.setValue(100)
        self.progressBar.setFormat(self.translate("conversion_complete_message"))
        
        self.pauseButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        self.convertButton.setEnabled(True)
        self.worker = None

    def handle_conversion_error(self, error_msg):
        """Handle conversion errors."""
        AppLogger.error(error_msg)
        QMessageBox.critical(self, self.translate("conversion_error_title"), error_msg)
        self.pauseButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        self.convertButton.setEnabled(True)
        self.worker = None

    def copy_output(self):
        """Copy the output text to clipboard."""
        QApplication.clipboard().setText(self.outputText.toPlainText())

    def save_output(self):
        """Save the conversion output."""
        if self.combinedSaveCheck.isChecked():
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
                self.file_manager.save_markdown_file(output_path, self.outputText.toPlainText())
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
        try:
            qt_ver = os.environ.get("QT_API_VERSION", "")
        except Exception:
            qt_ver = ""
        import sys, traceback
        python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        try:
            from PySide6 import __version__ as pyside_ver
        except Exception:
            pyside_ver = "Unknown"

        # Resolve LICENSE both in dev and frozen (PyInstaller) builds
        try:
            base_dir = getattr(sys, "_MEIPASS", None) or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            license_path = os.path.join(base_dir, "LICENSE")
        except Exception:
            license_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "LICENSE"))
        license_text = ""
        try:
            with open(license_path, "r", encoding="utf-8") as f:
                license_text = f.read()
        except Exception:
            license_text = "License file not found."

        msg = (
            f"MarkItDown GUI\n"
            f"Version: {APP_VERSION}\n\n"
            f"Python: {python_ver}\n"
            f"PySide6: {pyside_ver}\n"
            f"{'Qt: ' + qt_ver if qt_ver else ''}\n\n"
            f"License summary:\n"
            f"{license_text[:800]}{'...' if len(license_text) > 800 else ''}\n\n"
            f"Repository: https://github.com/imadreamerboy/markitdown-gui"
        )

        # Use a dialog with QTextBrowser so the repo link is clickable
        dlg = QDialog(self)
        dlg.setWindowTitle(self.translate("about_title") or "About")
        layout = QVBoxLayout(dlg)
        tb = QTextBrowser(dlg)
        tb.setOpenExternalLinks(True)
        lic_snippet = (license_text[:1200] + ("..." if len(license_text) > 1200 else "")) if license_text else "License file not found."
        html = (
            "<h3>MarkItDown GUI</h3>"
            f"<p><b>Version:</b> {APP_VERSION}</p>"
            f"<p><b>Python:</b> {python_ver}<br>"
            f"<b>PySide6:</b> {pyside_ver}"
            f"{('<br><b>Qt:</b> ' + qt_ver) if qt_ver else ''}</p>"
            "<h4>License summary</h4>"
            f"<pre style='white-space:pre-wrap; font-family:monospace;'>{lic_snippet}</pre>"
            "<p><a href='https://github.com/imadreamerboy/markitdown-gui'>Repository: github.com/imadreamerboy/markitdown-gui</a></p>"
        )
        tb.setHtml(html)
        layout.addWidget(tb)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK", dlg)
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)
        dlg.resize(560, 460)
        dlg.exec()

    def perform_auto_save(self):
        """Perform auto-save of current output."""
        if hasattr(self, 'conversionResults') and self.conversionResults:
            backup_path = os.path.join(
                self.file_manager.get_backup_dir(),
                self.file_manager.create_backup_filename()
            )
            try:
                self.file_manager.save_markdown_file(backup_path, self.outputText.toPlainText())
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
            # Show icon indicating the action (switch to the opposite theme)
            icon_path = "markitdowngui/resources/sun.svg" if self.isDarkMode else "markitdowngui/resources/moon.svg"
            self.themeToggleButton.setIcon(QIcon(icon_path))
        except Exception:
            # No icon fallback: set text
            self.themeToggleButton.setText("☀" if self.isDarkMode else "🌙")

    def update_preview(self, current, previous):
        """Update the preview of the selected file."""
        if not current:
            self.previewText.clear()
            self.previewText.setPlaceholderText(self.translate("preview_placeholder") or "")
            return
            
        try:
            filepath = current.text()
            AppLogger.info(f"Generating preview for {filepath}")
            
            # Get current format settings
            settings = self.settings_manager.get_format_settings()
            # Create MarkItDown instance with format settings only
            preview_kwargs = {}
            
            # Configure plugins if enabled
            if self.enablePluginsCheck.isChecked():
                preview_kwargs['enable_plugins'] = True
            
            # Configure Document Intelligence if endpoint provided
            endpoint = self.docIntelLine.text().strip()
            if endpoint:
                preview_kwargs['docintel_endpoint'] = endpoint
                
            self.preview_md = MarkItDown(**preview_kwargs)
            
            result = self.preview_md.convert(filepath)
            text = result.text_content or ""
            # Use Markdown rendering for markdown files, else plain text
            lower = filepath.lower()
            if lower.endswith(".md") or lower.endswith(".markdown"):
                # PySide6 supports Markdown rendering via QTextBrowser.setMarkdown
                self.previewText.setMarkdown(text)
            else:
                self.previewText.setPlainText(text)
            AppLogger.info("Preview generated successfully")
            
        except Exception as e:
            error_msg = f"Error previewing file: {str(e)}"
            self.previewText.setPlainText(error_msg)
            AppLogger.error(self.translate("preview_error_log").format(error=str(e)), filepath)

    def browse_files(self):
        """Open file browser dialog to select files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.translate("select_files_title"),
            "",
            self.translate("all_files_filter")
        )
        for file in files:
            self.dropWidget.listWidget.addItem(file)
            self.handleNewFile(file)
    
    def clear_file_list(self):
        """Clear the file list."""
        self.dropWidget.listWidget.clear()
        self.previewText.clear()
        self.previewText.setPlaceholderText(self.translate("preview_placeholder") or "")
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
            self.pauseButton.setText(self.translate("resume_button") if paused else self.translate("pause_button"))
            AppLogger.info(self.translate("conversion_paused_log") if paused else self.translate("conversion_resumed_log"))

    def cancel_conversion(self):
        """Cancel the ongoing conversion."""
        if hasattr(self, 'worker') and self.worker:
            self.worker.is_cancelled = True
            self.worker.is_paused = False
            self.pauseButton.setChecked(False)
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
            except:
                pass  # Signals might already be disconnected
                
            self.worker = None
            AppLogger.info("Worker thread cleaned up")
    
    def _reset_ui_state(self):
        """Reset UI to initial state after error or completion."""
        self.pauseButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        self.convertButton.setEnabled(True)
        self.pauseButton.setChecked(False)
        self.pauseButton.setText(self.translate("pause_button"))
        self.progressBar.setValue(0)
        self.progressBar.setFormat("")

    def change_language(self, action):
        """Change the application language."""
        lang_code = action.data()
        if lang_code and lang_code != self.current_lang:
            self.current_lang = lang_code
            self.settings_manager.set_current_language(lang_code)
        self.retranslate_ui()
        self.clearAllButton.setText(self.translate("clear_all_button"))

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
        self.dropWidget.retranslate_ui(self.translate)
        self.previewText.setPlaceholderText(self.translate("preview_placeholder"))

        self.settingsGroupLabel.setText(self.translate("settings_group_label"))
        self.enablePluginsCheck.setText(self.translate("enable_plugins_checkbox"))
        self.enablePluginsCheck.setToolTip(self.translate("enable_plugins_tooltip"))
        self.docIntelLine.setPlaceholderText(self.translate("doc_intel_placeholder"))
        self.docIntelLine.setToolTip(self.translate("doc_intel_tooltip"))

        self.batchSizeLabel.setText(self.translate("batch_size_label"))
        self.batchSizeSpinBox.setToolTip(self.translate("batch_size_tooltip"))
        self.pauseButton.setText(self.translate("pause_button") if not self.pauseButton.isChecked() else self.translate("resume_button"))
        self.cancelButton.setText(self.translate("cancel_button"))
        self.convertButton.setText(self.translate("convert_files_button"))

        self.combinedSaveCheck.setText(self.translate("output_save_all_in_one_checkbox"))
        self.combinedSaveCheck.setToolTip(self.translate("output_save_all_in_one_tooltip"))
        self.copyButton.setText(self.translate("copy_output_button"))
        self.saveButton.setText(self.translate("save_output_button"))
        
        self.update()
        QApplication.processEvents()

    def handle_files_added(self, files):
        # Add only files not already in the list
        existing = set(self.dropWidget.listWidget.item(i).text() for i in range(self.dropWidget.listWidget.count()))
        for file in files:
            if file not in existing:
                self.dropWidget.listWidget.addItem(file)
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
        self.update_checker.update_available.connect(self.show_update_notification)
        self.update_checker.update_error.connect(self.handle_update_error)
        self.update_checker.no_update_available.connect(self.handle_no_update)
        self.update_checker.start()

    def show_update_notification(self, new_version):
        """Show the update notification dialog."""
        dialog = UpdateDialog(new_version, self.translate, self.settings_manager, self)
        dialog.exec()

    def handle_update_error(self, error_message):
        """Handle update check errors (silently log them)."""
        AppLogger.error(f"Update check failed: {error_message}")

    def handle_no_update(self):
        """Handle when no update is available (silently log)."""
        AppLogger.info("No updates available")

    def manual_update_check(self):
        """Manually trigger an update check."""
        # For manual checks, always proceed regardless of notification settings
        self.update_checker = UpdateChecker(self)
        self.update_checker.update_available.connect(self.show_update_notification_manual)
        self.update_checker.update_error.connect(self.handle_manual_update_error)
        self.update_checker.no_update_available.connect(self.handle_manual_no_update)
        self.update_checker.start()

    def show_update_notification_manual(self, new_version):
        """Show the update notification dialog for manual checks."""
        dialog = UpdateDialog(new_version, self.translate, self.settings_manager, self)
        dialog.exec()

    def handle_manual_update_error(self, error_message):
        """Handle update check errors for manual checks with user feedback."""
        QMessageBox.warning(
            self,
            self.translate("update_check_error_title"),
            self.translate("update_check_error_message").format(error=error_message)
        )

    def handle_manual_no_update(self):
        """Handle when no update is available for manual checks with user feedback."""
        QMessageBox.information(
            self,
            self.translate("update_check_no_update_title"),
            self.translate("update_check_no_update_message")
        )
