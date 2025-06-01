from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox, QSpinBox, QPushButton
from PySide6.QtCore import QSettings
# Removed: from markitdowngui.core.settings import SettingsManager
# No direct use of SettingsManager, translate function is passed instead

class FormatSettings(QDialog):
    def __init__(self, settings_manager, translate_func, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.translate = translate_func # Store the passed translate function
        self.setWindowTitle(self.translate("format_settings_title"))
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header style settings
        headerGroup = QVBoxLayout()
        headerGroup.addWidget(QLabel(self.translate("header_style_label")))
        self.headerStyle = QComboBox()
        self.headerStyle.addItems([self.translate("header_style_atx"), self.translate("header_style_setext")])
        headerGroup.addWidget(self.headerStyle)
        
        # Table settings
        tableGroup = QVBoxLayout()
        tableGroup.addWidget(QLabel(self.translate("table_style_label")))
        self.tableStyle = QComboBox()
        self.tableStyle.addItems([self.translate("table_style_simple"), self.translate("table_style_grid"), self.translate("table_style_pipe")])
        tableGroup.addWidget(self.tableStyle)
        
        # Auto-save settings
        self.autoSaveCheck = QCheckBox(self.translate("auto_save_enable_checkbox"))
        self.autoSaveInterval = QSpinBox()
        self.autoSaveInterval.setRange(1, 60)
        self.autoSaveInterval.setValue(5)
        self.autoSaveInterval.setSuffix(self.translate("auto_save_interval_suffix"))
        
        # Add all groups to main layout
        layout.addLayout(headerGroup)
        layout.addLayout(tableGroup)
        layout.addWidget(self.autoSaveCheck)
        layout.addWidget(self.autoSaveInterval)
        
        # Buttons
        buttons = QHBoxLayout()
        saveButton = QPushButton(self.translate("save_button"))
        saveButton.clicked.connect(self.save_settings)
        cancelButton = QPushButton(self.translate("cancel_dialog_button"))
        cancelButton.clicked.connect(self.reject)
        buttons.addWidget(saveButton)
        buttons.addWidget(cancelButton)
        layout.addLayout(buttons)
    
    def load_settings(self):
        settings = self.settings_manager.get_format_settings()
        self.headerStyle.setCurrentText(settings['headerStyle'])
        self.tableStyle.setCurrentText(settings['tableStyle'])
        self.autoSaveCheck.setChecked(settings['autoSave'])
        self.autoSaveInterval.setValue(settings['autoSaveInterval'])
    
    def save_settings(self):
        settings = {
            'headerStyle': self.headerStyle.currentText(),
            'tableStyle': self.tableStyle.currentText(),
            'autoSave': self.autoSaveCheck.isChecked(),
            'autoSaveInterval': self.autoSaveInterval.value()
        }
        self.settings_manager.save_format_settings(settings)
        self.accept()