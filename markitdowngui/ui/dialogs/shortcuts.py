from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit

class ShortcutDialog(QDialog):
    SHORTCUTS = [
        ("Ctrl+O", "Open Files"),
        ("Ctrl+S", "Save Output"),
        ("Ctrl+C", "Copy Output"),
        ("Ctrl+P", "Pause/Resume"),
        ("Ctrl+B", "Begin Conversion"),
        ("Ctrl+L", "Clear List"),
        ("Ctrl+K", "Show Shortcuts"),
        ("Esc", "Cancel Conversion")
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText("\n".join(f"{key}\t{desc}" for key, desc in self.SHORTCUTS))
        layout.addWidget(text)