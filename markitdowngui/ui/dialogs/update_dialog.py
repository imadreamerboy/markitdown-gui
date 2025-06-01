"""Dialog to notify users about available updates."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
    QSizePolicy
)
from PySide6.QtCore import Qt

class UpdateDialog(QDialog):
    """A dialog to inform the user about a new application update."""

    def __init__(self, new_version_tag, translate_func, parent=None):
        super().__init__(parent)
        self.translate = translate_func

        self.setWindowTitle(self.translate("update_dialog_title"))

        self.new_version_tag = new_version_tag
        self.releases_url = "https://github.com/imadreamerboy/markitdown-gui/releases"

        layout = QVBoxLayout(self)

        message_label = QLabel(
            self.translate("update_dialog_message").format(version=self.new_version_tag)
        )
        message_label.setTextFormat(Qt.RichText)
        message_label.setWordWrap(True)

        info_label = QLabel(
            self.translate("update_dialog_info").format(url=self.releases_url)
        )
        info_label.setTextFormat(Qt.RichText)
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)

        layout.addWidget(message_label)
        layout.addWidget(info_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.adjustSize() # Adjust dialog size to content

    def accept(self):
        super().accept() 