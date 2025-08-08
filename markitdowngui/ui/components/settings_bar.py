from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QLineEdit
from PySide6.QtCore import Signal


class SettingsBar(QWidget):
    """Settings row with a group label, plugin toggle and doc intel endpoint input."""

    plugins_toggled = Signal(bool)
    endpoint_changed = Signal(str)

    def __init__(self, translate):
        super().__init__()
        self.translate = translate

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.group_label = QLabel(self.translate("settings_group_label") or "")
        layout.addWidget(self.group_label)

        row = QHBoxLayout()
        self.enable_plugins_check = QCheckBox(self.translate("enable_plugins_checkbox") or "")
        self.enable_plugins_check.setToolTip(self.translate("enable_plugins_tooltip") or "")
        self.docintel_line = QLineEdit()
        self.docintel_line.setPlaceholderText(self.translate("doc_intel_placeholder") or "")
        self.docintel_line.setToolTip(self.translate("doc_intel_tooltip") or "")
        # Signals
        self.enable_plugins_check.toggled.connect(self.plugins_toggled)
        self.docintel_line.textChanged.connect(self._on_endpoint_changed)
        row.addWidget(self.enable_plugins_check)
        row.addWidget(self.docintel_line)
        layout.addLayout(row)

    def is_plugins_enabled(self) -> bool:
        return bool(self.enable_plugins_check.isChecked())

    def get_docintel_endpoint(self) -> str:
        text = self.docintel_line.text().strip()
        # Simple validation: accept empty or http(s) URL-like
        if text and not (text.startswith("http://") or text.startswith("https://")):
            return ""
        return text

    def retranslate_ui(self, translate):
        self.translate = translate
        self.group_label.setText(self.translate("settings_group_label"))
        self.enable_plugins_check.setText(self.translate("enable_plugins_checkbox"))
        self.enable_plugins_check.setToolTip(self.translate("enable_plugins_tooltip"))
        self.docintel_line.setPlaceholderText(self.translate("doc_intel_placeholder"))
        self.docintel_line.setToolTip(self.translate("doc_intel_tooltip"))

    def _on_endpoint_changed(self, text: str) -> None:
        self.endpoint_changed.emit(text)


