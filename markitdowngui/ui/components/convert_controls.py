from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    PrimaryPushButton,
    PushButton,
    ProgressBar,
    SpinBox,
    CaptionLabel,
)


class ConvertControls(QWidget):
    """Conversion controls: convert button, progress, batch size, pause/cancel."""

    def __init__(self, translate):
        super().__init__()
        self.translate = translate

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.convert_button = PrimaryPushButton(
            self.translate("convert_files_button") or ""
        )
        layout.addWidget(self.convert_button)

        self.progress = ProgressBar()
        layout.addWidget(self.progress)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.batch_label = CaptionLabel(self.translate("batch_size_label") or "")
        self.batch_spin = SpinBox()
        self.batch_spin.setRange(1, 10)
        self.batch_spin.setValue(3)
        self.batch_spin.setToolTip(self.translate("batch_size_tooltip") or "")

        self.pause_button = PushButton(self.translate("pause_button") or "")
        self.pause_button.setEnabled(False)
        self.pause_button.setCheckable(True)

        self.cancel_button = PushButton(self.translate("cancel_button") or "")
        self.cancel_button.setEnabled(False)

        row.addWidget(self.batch_label)
        row.addWidget(self.batch_spin)
        row.addStretch(1)  # Add stretch to keep controls left/right balanced or grouped
        row.addWidget(self.pause_button)
        row.addWidget(self.cancel_button)
        layout.addLayout(row)

    def retranslate_ui(self, translate):
        self.translate = translate
        self.convert_button.setText(self.translate("convert_files_button"))
        self.batch_label.setText(self.translate("batch_size_label"))
        self.batch_spin.setToolTip(self.translate("batch_size_tooltip"))
        self.pause_button.setText(
            self.translate("resume_button")
            if self.pause_button.isChecked()
            else self.translate("pause_button")
        )
        self.cancel_button.setText(self.translate("cancel_button"))
