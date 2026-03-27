from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import LineEdit, PushButton


class UrlInputBar(QWidget):
    url_submitted = Signal(str)

    def __init__(self, translate, parent=None):
        super().__init__(parent=parent)
        self.translate = translate

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.url_edit = LineEdit(self)
        self.url_edit.returnPressed.connect(self.submit_url)

        self.submit_button = PushButton(self)
        self.submit_button.clicked.connect(self.submit_url)

        layout.addWidget(self.url_edit, 1)
        layout.addWidget(self.submit_button)

        self.retranslate_ui(translate)

    def submit_url(self) -> None:
        value = self.url_edit.text().strip()
        if value:
            self.url_submitted.emit(value)

    def clear(self) -> None:
        self.url_edit.clear()

    def retranslate_ui(self, translate) -> None:
        self.translate = translate
        self.url_edit.setPlaceholderText(self.translate("home_url_placeholder"))
        self.submit_button.setText(self.translate("home_add_url_button"))
