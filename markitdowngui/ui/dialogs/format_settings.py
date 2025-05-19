from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox, QSpinBox, QPushButton
from PySide6.QtCore import QSettings
from markitdowngui.core.settings import SettingsManager

class FormatSettings(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Format Settings")
        self.settings_manager = settings_manager
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header style settings
        headerGroup = QVBoxLayout()
        headerGroup.addWidget(QLabel("Header Style:"))
        self.headerStyle = QComboBox()
        self.headerStyle.addItems(["ATX (#)", "Setext (===)"])
        headerGroup.addWidget(self.headerStyle)
        
        # Table settings
        tableGroup = QVBoxLayout()
        tableGroup.addWidget(QLabel("Table Style:"))
        self.tableStyle = QComboBox()
        self.tableStyle.addItems(["Simple", "Grid", "Pipe"])
        tableGroup.addWidget(self.tableStyle)
        
        # Auto-save settings
        self.autoSaveCheck = QCheckBox("Enable Auto-save")
        self.autoSaveInterval = QSpinBox()
        self.autoSaveInterval.setRange(1, 60)
        self.autoSaveInterval.setValue(5)
        self.autoSaveInterval.setSuffix(" minutes")
        
        # Add all groups to main layout
        layout.addLayout(headerGroup)
        layout.addLayout(tableGroup)
        layout.addWidget(self.autoSaveCheck)
        layout.addWidget(self.autoSaveInterval)
        
        # Buttons
        buttons = QHBoxLayout()
        saveButton = QPushButton("Save")
        saveButton.clicked.connect(self.save_settings)
        cancelButton = QPushButton("Cancel")
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