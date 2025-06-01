from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit

class ShortcutDialog(QDialog):
    SHORTCUTS = [
        ("Ctrl+O", "shortcut_open_files"),
        ("Ctrl+S", "shortcut_save_output"),
        ("Ctrl+C", "shortcut_copy_output"),
        ("Ctrl+P", "shortcut_pause_resume"),
        ("Ctrl+B", "shortcut_begin_conversion"),
        ("Ctrl+L", "shortcut_clear_list"),
        ("Ctrl+K", "shortcut_show_shortcuts"),
        ("Esc", "shortcut_cancel_conversion")
    ]

    def __init__(self, translate_func, parent=None):
        super().__init__(parent)
        self.translate = translate_func
        self.setWindowTitle(self.translate("shortcuts_title"))
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        text_content = "\n".join(
            f"{key}\t{self.translate(translation_key)}" 
            for key, translation_key in self.SHORTCUTS
        )
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(text_content)
        layout.addWidget(text)