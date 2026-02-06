from __future__ import annotations

import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QGroupBox,
)
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    LineEdit,
    PushButton,
    RadioButton,
    SpinBox,
    TitleLabel,
)

from markitdowngui.core.settings import SettingsManager


class SettingsInterface(QWidget):
    """Settings page shown inside the Fluent navigation."""

    theme_mode_changed = Signal(str)

    def __init__(self, settings_manager: SettingsManager, translate, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingsInterface")
        self.settings_manager = settings_manager
        self.translate = translate
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(12)

        layout.addWidget(TitleLabel(self.translate("settings_title")))

        self.general_group = QGroupBox(self.translate("settings_general_group"))
        general_layout = QVBoxLayout(self.general_group)
        general_layout.setSpacing(10)

        general_layout.addWidget(BodyLabel(self.translate("settings_output_format_label")))
        self.output_format_combo = ComboBox()
        self.output_format_combo.addItems([".md"])
        self.output_format_combo.setEnabled(False)
        general_layout.addWidget(self.output_format_combo)

        general_layout.addWidget(BodyLabel(self.translate("settings_output_folder_label")))
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.output_folder_edit = LineEdit()
        self.output_folder_edit.setPlaceholderText(
            self.translate("settings_output_folder_placeholder")
        )
        self.output_folder_edit.editingFinished.connect(self._save_output_folder)
        self.output_folder_button = PushButton(self.translate("browse_button_compact"))
        self.output_folder_button.clicked.connect(self._browse_output_folder)
        folder_row.addWidget(self.output_folder_edit, 1)
        folder_row.addWidget(self.output_folder_button)
        general_layout.addLayout(folder_row)
        layout.addWidget(self.general_group)

        self.conversion_group = QGroupBox(self.translate("settings_conversion_group"))
        conversion_layout = QVBoxLayout(self.conversion_group)
        conversion_layout.setSpacing(10)

        conversion_layout.addWidget(BodyLabel(self.translate("batch_size_label")))
        self.batch_size_spin = SpinBox()
        self.batch_size_spin.setRange(1, 10)
        self.batch_size_spin.valueChanged.connect(self._save_batch_size)
        conversion_layout.addWidget(self.batch_size_spin)

        conversion_layout.addWidget(BodyLabel(self.translate("header_style_label")))
        self.header_style_combo = ComboBox()
        self.header_style_combo.addItems(
            [
                self.translate("header_style_atx"),
                self.translate("header_style_setext"),
            ]
        )
        self.header_style_combo.currentTextChanged.connect(self._save_format_settings)
        conversion_layout.addWidget(self.header_style_combo)

        conversion_layout.addWidget(BodyLabel(self.translate("table_style_label")))
        self.table_style_combo = ComboBox()
        self.table_style_combo.addItems(
            [
                self.translate("table_style_simple"),
                self.translate("table_style_grid"),
                self.translate("table_style_pipe"),
            ]
        )
        self.table_style_combo.currentTextChanged.connect(self._save_format_settings)
        conversion_layout.addWidget(self.table_style_combo)
        layout.addWidget(self.conversion_group)

        self.appearance_group = QGroupBox(self.translate("settings_appearance_group"))
        appearance_layout = QVBoxLayout(self.appearance_group)
        appearance_layout.setSpacing(8)

        self.theme_light = RadioButton(self.translate("theme_light"))
        self.theme_dark = RadioButton(self.translate("theme_dark"))
        self.theme_system = RadioButton(self.translate("theme_system"))
        self.theme_light.toggled.connect(lambda checked: self._save_theme("light", checked))
        self.theme_dark.toggled.connect(lambda checked: self._save_theme("dark", checked))
        self.theme_system.toggled.connect(lambda checked: self._save_theme("system", checked))

        appearance_layout.addWidget(self.theme_light)
        appearance_layout.addWidget(self.theme_dark)
        appearance_layout.addWidget(self.theme_system)
        layout.addWidget(self.appearance_group)

        layout.addStretch(1)

    def _load_settings(self) -> None:
        self.output_format_combo.setCurrentText(
            self.settings_manager.get_default_output_format()
        )
        self.output_folder_edit.setText(self.settings_manager.get_default_output_folder())
        self.batch_size_spin.setValue(self.settings_manager.get_batch_size())

        format_settings = self.settings_manager.get_format_settings()
        self.header_style_combo.setCurrentText(str(format_settings.get("headerStyle", "")))
        self.table_style_combo.setCurrentText(str(format_settings.get("tableStyle", "")))

        theme_mode = self.settings_manager.get_theme_mode()
        self.theme_light.setChecked(theme_mode == "light")
        self.theme_dark.setChecked(theme_mode == "dark")
        self.theme_system.setChecked(theme_mode == "system")

    def _save_output_folder(self) -> None:
        self.settings_manager.set_default_output_folder(self.output_folder_edit.text().strip())

    def _browse_output_folder(self) -> None:
        start_dir = self.settings_manager.get_default_output_folder()
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = ""
        folder = QFileDialog.getExistingDirectory(
            self, self.translate("settings_output_folder_dialog"), start_dir
        )
        if folder:
            self.output_folder_edit.setText(folder)
            self.settings_manager.set_default_output_folder(folder)

    def _save_batch_size(self, value: int) -> None:
        self.settings_manager.set_batch_size(value)

    def _save_theme(self, mode: str, checked: bool) -> None:
        if not checked:
            return
        self.settings_manager.set_theme_mode(mode)
        self.theme_mode_changed.emit(mode)

    def _save_format_settings(self, *_args) -> None:
        current = self.settings_manager.get_format_settings()
        current["headerStyle"] = self.header_style_combo.currentText()
        current["tableStyle"] = self.table_style_combo.currentText()
        self.settings_manager.save_format_settings(current)
