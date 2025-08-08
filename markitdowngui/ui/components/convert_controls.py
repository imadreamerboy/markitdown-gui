from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QSpinBox


class ConvertControls(QWidget):
    """Conversion controls: convert button, progress, batch size, pause/cancel."""

    def __init__(self, translate):
        super().__init__()
        self.translate = translate

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.convert_button = QPushButton(self.translate("convert_files_button") or "")
        layout.addWidget(self.convert_button)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        row = QHBoxLayout()
        self.batch_label = QLabel(self.translate("batch_size_label") or "")
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 10)
        self.batch_spin.setValue(3)
        self.batch_spin.setToolTip(self.translate("batch_size_tooltip") or "")
        self.pause_button = QPushButton(self.translate("pause_button") or "")
        self.pause_button.setEnabled(False)
        self.pause_button.setCheckable(True)
        self.cancel_button = QPushButton(self.translate("cancel_button") or "")
        self.cancel_button.setEnabled(False)

        row.addWidget(self.batch_label)
        row.addWidget(self.batch_spin)
        row.addWidget(self.pause_button)
        row.addWidget(self.cancel_button)
        layout.addLayout(row)

    def retranslate_ui(self, translate):
        self.translate = translate
        self.convert_button.setText(self.translate("convert_files_button"))
        self.batch_label.setText(self.translate("batch_size_label"))
        self.batch_spin.setToolTip(self.translate("batch_size_tooltip"))
        self.pause_button.setText(self.translate("resume_button") if self.pause_button.isChecked() else self.translate("pause_button"))
        self.cancel_button.setText(self.translate("cancel_button"))


