from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QTextEdit


class OutputPanel(QWidget):
    """Output area with combined-save toggle, copy/save buttons, and text box."""

    def __init__(self, translate, initial_combined_checked: bool):
        super().__init__()
        self.translate = translate

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Combined save toggle row
        toggle_row = QHBoxLayout()
        self.combined_toggle = QCheckBox(self.translate("output_save_all_in_one_checkbox") or "")
        self.combined_toggle.setChecked(initial_combined_checked)
        self.combined_toggle.setToolTip(self.translate("output_save_all_in_one_tooltip") or "")
        toggle_row.addWidget(self.combined_toggle)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        # Controls row
        controls_row = QHBoxLayout()
        self.copy_button = QPushButton(self.translate("copy_output_button") or "")
        self.save_button = QPushButton(self.translate("save_output_button") or "")
        controls_row.addWidget(self.copy_button)
        controls_row.addWidget(self.save_button)
        layout.addLayout(controls_row)

        # Text area
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

    def set_text(self, text: str) -> None:
        self.text_edit.setPlainText(text)

    def get_text(self) -> str:
        return self.text_edit.toPlainText()

    def is_combined(self) -> bool:
        return bool(self.combined_toggle.isChecked())

    def retranslate_ui(self, translate):
        self.translate = translate
        self.combined_toggle.setText(self.translate("output_save_all_in_one_checkbox"))
        self.combined_toggle.setToolTip(self.translate("output_save_all_in_one_tooltip"))
        self.copy_button.setText(self.translate("copy_output_button"))
        self.save_button.setText(self.translate("save_output_button"))


