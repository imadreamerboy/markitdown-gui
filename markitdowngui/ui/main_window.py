import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMenuBar, QMenu,
    QFileDialog, QCheckBox, QLineEdit, QLabel, QTextEdit, QProgressBar,
    QApplication, QComboBox, QSpinBox, QMessageBox, QSplitter, QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QPalette, QShortcut
from markitdown import MarkItDown

from markitdowngui.core.settings import SettingsManager
from markitdowngui.core.conversion import ConversionWorker
from markitdowngui.core.file_utils import FileManager
from markitdowngui.utils.logger import AppLogger
from markitdowngui.ui.themes import apply_dark_theme, apply_light_theme
from markitdowngui.ui.drop_widget import DropWidget
from markitdowngui.ui.dialogs.format_settings import FormatSettings
from markitdowngui.ui.dialogs.shortcuts import ShortcutDialog

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.file_manager = FileManager()
        self.setup_window()
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_auto_save()
        self.preview_md = MarkItDown()
        AppLogger.info("Application started")

    def setup_window(self):
        """Initialize window properties."""
        self.setWindowTitle("MarkItDown GUI Wrapper")
        self.setMinimumSize(600, 500)
        self.isDarkMode = self.settings_manager.get_dark_mode()
        self.apply_theme()

    def setup_ui(self):
        """Set up the user interface."""
        # Create menu bar
        self.setup_menu_bar()
        
        # Main layout
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setMenuBar(self.menuBar)
        
        # File handling area
        self.setup_file_area()
        
        # Create a splitter for file list and preview
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left side: File list
        leftWidget = QWidget()
        leftLayout = QVBoxLayout(leftWidget)
        leftLayout.addWidget(self.dropWidget)
        
        # Right side: Preview
        rightWidget = QWidget()
        rightLayout = QVBoxLayout(rightWidget)
        previewLabel = QLabel("Preview:")
        self.previewText = QTextEdit()
        self.previewText.setReadOnly(True)
        self.previewText.setPlaceholderText("Select a file to see preview")
        rightLayout.addWidget(previewLabel)
        rightLayout.addWidget(self.previewText)
        
        # Add widgets to splitter
        self.splitter.addWidget(leftWidget)
        self.splitter.addWidget(rightWidget)
        
        # Update main layout
        self.mainLayout.addWidget(self.splitter)
        
        # Settings area
        self.setup_settings_area()
        
        # Conversion controls
        self.setup_conversion_controls()
        
        # Output area
        self.setup_output_area()

    def setup_menu_bar(self):
        """Set up the application menu bar."""
        self.menuBar = QMenuBar()
        
        # View menu
        viewMenu = QMenu("View", self)
        self.menuBar.addMenu(viewMenu)
        
        # Dark mode toggle
        self.darkModeAction = viewMenu.addAction("Dark Mode")
        self.darkModeAction.setCheckable(True)
        self.darkModeAction.setChecked(self.isDarkMode)
        self.darkModeAction.triggered.connect(self.toggle_dark_mode)
        
        # Settings menu
        settingsMenu = self.menuBar.addMenu("Settings")
        formatAction = settingsMenu.addAction("Format Settings")
        formatAction.triggered.connect(self.show_format_settings)
        
        # Help menu
        helpMenu = self.menuBar.addMenu("Help")
        shortcutsAction = helpMenu.addAction("Keyboard Shortcuts")
        shortcutsAction.triggered.connect(self.show_shortcuts)

    def setup_file_area(self):
        """Set up the file handling area."""
        self.dropWidget = DropWidget()
        self.dropWidget.listWidget.currentItemChanged.connect(self.update_preview)
        
        # Add file list to main layout
        self.mainLayout.addWidget(self.dropWidget)

    def setup_file_controls(self):
        """Set up the file control buttons."""
        fileControls = QHBoxLayout()
        
        # Browse button
        browseButton = QPushButton("Browse Files")
        browseButton.clicked.connect(self.browse_files)
        browseButton.setToolTip("Open file browser to select files")
        
        # Clear button
        clearButton = QPushButton("Clear List")
        clearButton.clicked.connect(self.clear_file_list)
        clearButton.setToolTip("Clear the file list")
        
        fileControls.addWidget(browseButton)
        fileControls.addWidget(clearButton)
        
        self.mainLayout.addLayout(fileControls)
        return fileControls

    def setup_settings_area(self):
        """Set up the settings area."""
        settingsLayout = QHBoxLayout()
        
        self.enablePluginsCheck = QCheckBox("Enable Plugins")
        self.enablePluginsCheck.setToolTip("Enable third-party plugins for additional conversion features")
        
        self.docIntelLine = QLineEdit()
        self.docIntelLine.setPlaceholderText("Document Intelligence Endpoint (optional)")
        self.docIntelLine.setToolTip("Enter your Azure Document Intelligence endpoint if you want to use it")
        
        settingsLayout.addWidget(self.enablePluginsCheck)
        settingsLayout.addWidget(self.docIntelLine)
        
        self.mainLayout.addWidget(QLabel("Settings:"))
        self.mainLayout.addLayout(settingsLayout)

    def setup_conversion_controls(self):
        """Set up the conversion control area."""
        # Batch processing controls
        batchLayout = QHBoxLayout()
        self.batchSizeSpinBox = QSpinBox()
        self.batchSizeSpinBox.setRange(1, 10)
        self.batchSizeSpinBox.setValue(3)
        self.batchSizeSpinBox.setToolTip("Number of files to process simultaneously")
        
        self.pauseButton = QPushButton("Pause")
        self.pauseButton.setEnabled(False)
        self.pauseButton.setCheckable(True)
        self.pauseButton.toggled.connect(self.toggle_pause)
        
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setEnabled(False)
        self.cancelButton.clicked.connect(self.cancel_conversion)
        
        batchLayout.addWidget(QLabel("Batch Size:"))
        batchLayout.addWidget(self.batchSizeSpinBox)
        batchLayout.addWidget(self.pauseButton)
        batchLayout.addWidget(self.cancelButton)
        
        # Convert button and progress bar
        self.convertButton = QPushButton("Convert Files")
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
        self.combinedSaveCheck = QCheckBox("Save all files in one document")
        self.combinedSaveCheck.setChecked(self.settings_manager.get_save_mode())
        self.combinedSaveCheck.setToolTip("When unchecked, each file will be saved separately")
        self.combinedSaveCheck.toggled.connect(self.settings_manager.set_save_mode)
        saveModeLayout.addWidget(self.combinedSaveCheck)
        saveModeLayout.addStretch()
        
        # Output controls
        outputControls = QHBoxLayout()
        self.copyButton = QPushButton("Copy Output")
        self.copyButton.clicked.connect(self.copy_output)
        self.saveButton = QPushButton("Save Output")
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

    def apply_theme(self):
        """Apply the current theme to the application."""
        palette = apply_dark_theme(QPalette()) if self.isDarkMode else apply_light_theme()
        QApplication.setPalette(palette)

    def convert_files(self):
        """Start the file conversion process."""
        files = [self.dropWidget.listWidget.item(i).text() 
                for i in range(self.dropWidget.listWidget.count())]
        
        if not files:
            AppLogger.info("Conversion attempted with no files")
            QMessageBox.warning(self, "No Files", "Please add files to convert.")
            return

        AppLogger.info(f"Starting conversion of {len(files)} files")
        
        # Prepare conversion settings
        settings = self.settings_manager.get_format_settings()
        # Create a base MarkItDown instance
        md = MarkItDown()
        
        # Configure plugins if enabled
        if self.enablePluginsCheck.isChecked():
            md.enable_plugins()
        
        # Configure Document Intelligence if endpoint provided
        endpoint = self.docIntelLine.text().strip()
        if endpoint:
            md.set_docintel_endpoint(endpoint)

        # Start conversion with configured instance
        self.worker = ConversionWorker([md, files, settings], self.batchSizeSpinBox.value())
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.handle_conversion_finished)
        self.worker.error.connect(self.handle_conversion_error)

        self.pauseButton.setEnabled(True)
        self.cancelButton.setEnabled(True)
        self.convertButton.setEnabled(False)
        self.worker.start()

    def update_progress(self, progress, current_file):
        """Update the progress bar during conversion."""
        self.progressBar.setValue(progress)
        self.progressBar.setFormat(f"{progress}% - Processing: {os.path.basename(current_file)}")

    def handle_conversion_finished(self, results):
        """Handle completion of the conversion process."""
        self.conversionResults = results
        combined_output = ""
        for file, content in results.items():
            combined_output += f"File: {file}\n{content}\n\n"
        
        self.outputText.setPlainText(combined_output)
        self.progressBar.setValue(100)
        self.progressBar.setFormat("Conversion Complete")
        
        self.pauseButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        self.convertButton.setEnabled(True)
        self.worker = None

    def handle_conversion_error(self, error_msg):
        """Handle conversion errors."""
        AppLogger.error(error_msg)
        QMessageBox.critical(self, "Error", error_msg)
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
            self, "Save Combined Markdown Output", "", "Markdown Files (*.md);;All Files (*)"
        )
        if output_path:
            try:
                self.file_manager.save_markdown_file(output_path, self.outputText.toPlainText())
                AppLogger.info(f"Combined output saved to {output_path}")
                
                # Add to recent outputs
                self.settings_manager.set_recent_outputs(
                    self.file_manager.update_recent_list(
                        output_path,
                        self.settings_manager.get_recent_outputs()
                    )
                )
            except Exception as e:
                AppLogger.error(f"Error saving combined output: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to save output: {str(e)}")

    def save_individual_outputs(self):
        """Save each conversion to a separate file."""
        if not hasattr(self, 'conversionResults') or not self.conversionResults:
            QMessageBox.warning(self, "No Output", "No conversion results to save.")
            return
            
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Directory for Individual Files"
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
                    AppLogger.info(f"Saved individual output to {output_path}")
                except Exception as e:
                    AppLogger.error(f"Error saving {input_file}: {str(e)}")
            
            if success_count > 0:
                QMessageBox.information(
                    self,
                    "Save Complete",
                    f"Successfully saved {success_count} file(s) to {output_dir}"
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
        dialog = ShortcutDialog(self)
        dialog.exec()

    def show_format_settings(self):
        """Show the format settings dialog."""
        dialog = FormatSettings(self.settings_manager, self)
        if dialog.exec() == QDialog.Accepted:
            self.update_auto_save_timer()
            AppLogger.info("Format settings updated")

    def perform_auto_save(self):
        """Perform auto-save of current output."""
        if hasattr(self, 'conversionResults') and self.conversionResults:
            backup_path = os.path.join(
                self.file_manager.get_backup_dir(),
                self.file_manager.create_backup_filename()
            )
            try:
                self.file_manager.save_markdown_file(backup_path, self.outputText.toPlainText())
                AppLogger.info(f"Auto-saved backup to {backup_path}")
            except Exception as e:
                AppLogger.error(f"Auto-save failed: {str(e)}")

    def update_auto_save_timer(self):
        """Update the auto-save timer based on current settings."""
        settings = self.settings_manager.get_format_settings()
        if settings['autoSave']:
            interval = settings['autoSaveInterval'] * 60 * 1000  # Convert to milliseconds
            self.autoSaveTimer.start(interval)
        else:
            self.autoSaveTimer.stop()

    def update_preview(self, current, previous):
        """Update the preview of the selected file."""
        if not current:
            self.previewText.clear()
            self.previewText.setPlaceholderText("Select a file to see preview")
            return
            
        try:
            filepath = current.text()
            AppLogger.info(f"Generating preview for {filepath}")
            
            # Get current format settings
            settings = self.settings_manager.get_format_settings()
            # Create MarkItDown instance with format settings only
            self.preview_md = MarkItDown()
            
            # Configure plugins if enabled
            if self.enablePluginsCheck.isChecked():
                self.preview_md.enable_plugins()
            
            # Configure Document Intelligence if endpoint provided
            endpoint = self.docIntelLine.text().strip()
            if endpoint:
                self.preview_md.set_docintel_endpoint(endpoint)
            
            result = self.preview_md.convert(filepath)
            self.previewText.setPlainText(result.text_content)
            AppLogger.info("Preview generated successfully")
            
        except Exception as e:
            error_msg = f"Error previewing file: {str(e)}"
            self.previewText.setPlainText(error_msg)
            AppLogger.error(error_msg, filepath)

    def browse_files(self):
        """Open file browser dialog to select files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Convert",
            "",
            "All Files (*.*)"
        )
        for file in files:
            self.dropWidget.listWidget.addItem(file)
            self.handleNewFile(file)
    
    def clear_file_list(self):
        """Clear the file list."""
        self.dropWidget.listWidget.clear()
        self.previewText.clear()
        self.previewText.setPlaceholderText("Select a file to see preview")
        AppLogger.info("File list cleared")
    
    def handleNewFile(self, filepath):
        """Handle newly added file."""
        try:
            self.settings_manager.set_recent_files(
                self.file_manager.update_recent_list(
                    filepath, 
                    self.settings_manager.get_recent_files()
                )
            )
            AppLogger.info(f"Added file to recent list: {filepath}")
        except Exception as e:
            AppLogger.error(f"Error handling new file: {str(e)}")

    def toggle_pause(self, paused):
        """Toggle conversion pause state."""
        if hasattr(self, 'worker') and self.worker:
            self.worker.is_paused = paused
            self.pauseButton.setText("Resume" if paused else "Pause")
            AppLogger.info("Conversion " + ("paused" if paused else "resumed"))

    def cancel_conversion(self):
        """Cancel the ongoing conversion."""
        if hasattr(self, 'worker') and self.worker:
            self.worker.is_cancelled = True
            self.worker.is_paused = False
            self.pauseButton.setChecked(False)
            AppLogger.info("Conversion cancelled")