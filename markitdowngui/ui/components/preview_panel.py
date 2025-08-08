from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextBrowser


class PreviewPanel(QWidget):
    """Preview label + QTextBrowser wrapper."""

    def __init__(self, translate):
        super().__init__()
        self.translate = translate
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.label = QLabel(self.translate("preview_label"))
        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(True)
        self.text.setPlaceholderText(self.translate("preview_placeholder") or "")

        layout.addWidget(self.label)
        layout.addWidget(self.text)

    def clear(self):
        self.text.clear()
        self.text.setPlaceholderText(self.translate("preview_placeholder") or "")

    def set_markdown(self, md_text: str):
        self.text.setMarkdown(md_text)

    def set_plain(self, text: str):
        self.text.setPlainText(text)

    def retranslate_ui(self, translate):
        self.translate = translate
        self.label.setText(self.translate("preview_label"))
        self.text.setPlaceholderText(self.translate("preview_placeholder") or "")


