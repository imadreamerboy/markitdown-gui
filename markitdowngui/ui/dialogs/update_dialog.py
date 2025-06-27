"""Dialog to notify users about available updates."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
    QSizePolicy,
    QCheckBox,
    QPushButton
)
from PySide6.QtCore import Qt

class UpdateDialog(QDialog):
    """A dialog to inform the user about a new application update."""

    def __init__(self, new_version_tag, translate_func, settings_manager=None, parent=None):
        super().__init__(parent)
        self.translate = translate_func
        self.settings_manager = settings_manager
        self.dont_notify_again = False

        self.setWindowTitle(self.translate("update_dialog_title"))

        self.new_version_tag = new_version_tag
        self.releases_url = "https://github.com/imadreamerboy/markitdown-gui/releases"

        layout = QVBoxLayout(self)

        message_label = QLabel(
            self.translate("update_dialog_message").format(version=self.new_version_tag)
        )
        message_label.setTextFormat(Qt.TextFormat.RichText)
        message_label.setWordWrap(True)

        info_label = QLabel(
            self.translate("update_dialog_info").format(url=self.releases_url)
        )
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)

        layout.addWidget(message_label)
        layout.addWidget(info_label)
        
        # Add "Don't notify me again" checkbox
        self.dont_notify_checkbox = QCheckBox(self.translate("update_dialog_dont_notify"))
        layout.addWidget(self.dont_notify_checkbox)

        # Custom button box
        button_box = QDialogButtonBox()
        ok_button = QPushButton(self.translate("update_dialog_ok"))
        ok_button.clicked.connect(self.handle_ok_clicked)
        button_box.addButton(ok_button, QDialogButtonBox.ButtonRole.AcceptRole)
        
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.adjustSize()

    def handle_ok_clicked(self):
        """Handle OK button click, saving the don't notify preference if needed."""
        self.dont_notify_again = self.dont_notify_checkbox.isChecked()
        
        # Save the setting if settings manager is available
        if self.settings_manager and self.dont_notify_again:
            self.settings_manager.set_update_notifications_enabled(False)
            
        self.accept()

    def accept(self):
        super().accept() 