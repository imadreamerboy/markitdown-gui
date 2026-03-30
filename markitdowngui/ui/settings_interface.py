from __future__ import annotations

import os

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PushButton,
    RadioButton,
    SpinBox,
    TitleLabel,
)

from markitdowngui.core.conversion import ConversionOptions, test_azure_ocr_connection
from markitdowngui.core.settings import (
    GLMOCR_MODE_MAAS,
    GLMOCR_MODE_SELFHOSTED,
    OCR_PROVIDER_GLMOCR,
    OCR_PROVIDER_LEGACY,
    SettingsManager,
)


class AzureConnectionTestWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, options: ConversionOptions):
        super().__init__()
        self.options = options

    def run(self) -> None:
        try:
            auth_method = test_azure_ocr_connection(self.options)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(auth_method)


class SettingsInterface(QWidget):
    """Settings page shown inside the Fluent navigation."""

    theme_mode_changed = Signal(str)

    def __init__(self, settings_manager: SettingsManager, translate, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingsInterface")
        self.settings_manager = settings_manager
        self.translate = translate
        self._azure_test_worker: AzureConnectionTestWorker | None = None
        self._ocr_provider_values = [OCR_PROVIDER_LEGACY, OCR_PROVIDER_GLMOCR]
        self._glmocr_mode_values = [GLMOCR_MODE_MAAS, GLMOCR_MODE_SELFHOSTED]
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("SettingsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        root_layout.addWidget(self.scroll_area)

        self.content = QWidget(self.scroll_area)
        self.content.setObjectName("SettingsContent")
        self.scroll_area.setWidget(self.content)

        layout = QVBoxLayout(self.content)
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
        self.output_folder_button.setIcon(FIF.FOLDER)
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

        self.ocr_group = QGroupBox(self.translate("settings_ocr_group"))
        ocr_layout = QVBoxLayout(self.ocr_group)
        ocr_layout.setSpacing(10)

        self.ocr_enabled_check = CheckBox(self.translate("settings_ocr_enable_label"))
        self.ocr_enabled_check.setToolTip(self.translate("settings_ocr_enable_tooltip"))
        self.ocr_enabled_check.toggled.connect(self._save_ocr_enabled)
        ocr_layout.addWidget(self.ocr_enabled_check)

        ocr_layout.addWidget(BodyLabel(self.translate("settings_ocr_provider_label")))
        self.ocr_provider_combo = ComboBox()
        self.ocr_provider_combo.addItems(
            [
                self.translate("settings_ocr_provider_legacy"),
                self.translate("settings_ocr_provider_glmocr"),
            ]
        )
        self.ocr_provider_combo.currentTextChanged.connect(self._save_ocr_provider)
        ocr_layout.addWidget(self.ocr_provider_combo)

        self.glmocr_group = QGroupBox(self.translate("settings_glmocr_group"))
        glmocr_layout = QVBoxLayout(self.glmocr_group)
        glmocr_layout.setSpacing(10)

        self.ocr_fallback_check = CheckBox(
            self.translate("settings_ocr_fallback_label")
        )
        self.ocr_fallback_check.setToolTip(
            self.translate("settings_ocr_fallback_tooltip")
        )
        self.ocr_fallback_check.toggled.connect(self._save_ocr_fallback_enabled)
        glmocr_layout.addWidget(self.ocr_fallback_check)

        glmocr_layout.addWidget(BodyLabel(self.translate("settings_glmocr_mode_label")))
        self.glmocr_mode_combo = ComboBox()
        self.glmocr_mode_combo.addItems(
            [
                self.translate("settings_glmocr_mode_maas"),
                self.translate("settings_glmocr_mode_selfhosted"),
            ]
        )
        self.glmocr_mode_combo.currentTextChanged.connect(self._save_glmocr_mode)
        glmocr_layout.addWidget(self.glmocr_mode_combo)

        self.glmocr_maas_note = CaptionLabel(
            self.translate("settings_glmocr_maas_note")
        )
        self.glmocr_maas_note.setWordWrap(True)
        glmocr_layout.addWidget(self.glmocr_maas_note)

        self.glmocr_selfhost_note = CaptionLabel(
            self.translate("settings_glmocr_selfhost_note")
        )
        self.glmocr_selfhost_note.setWordWrap(True)
        glmocr_layout.addWidget(self.glmocr_selfhost_note)

        self.glmocr_selfhost_fields = QWidget(self.glmocr_group)
        self.glmocr_selfhost_fields_layout = QVBoxLayout(self.glmocr_selfhost_fields)
        self.glmocr_selfhost_fields_layout.setContentsMargins(0, 0, 0, 0)
        self.glmocr_selfhost_fields_layout.setSpacing(10)

        self.glmocr_api_host_label = BodyLabel(
            self.translate("settings_glmocr_api_host_label")
        )
        self.glmocr_selfhost_fields_layout.addWidget(self.glmocr_api_host_label)
        self.glmocr_api_host_edit = LineEdit()
        self.glmocr_api_host_edit.setPlaceholderText(
            self.translate("settings_glmocr_api_host_placeholder")
        )
        self.glmocr_api_host_edit.editingFinished.connect(self._save_glmocr_api_host)
        self.glmocr_selfhost_fields_layout.addWidget(self.glmocr_api_host_edit)

        self.glmocr_api_port_label = BodyLabel(
            self.translate("settings_glmocr_api_port_label")
        )
        self.glmocr_selfhost_fields_layout.addWidget(self.glmocr_api_port_label)
        self.glmocr_api_port_spin = SpinBox()
        self.glmocr_api_port_spin.setRange(1, 65535)
        self.glmocr_api_port_spin.valueChanged.connect(self._save_glmocr_api_port)
        self.glmocr_selfhost_fields_layout.addWidget(self.glmocr_api_port_spin)

        self.glmocr_model_label = BodyLabel(
            self.translate("settings_glmocr_model_label")
        )
        self.glmocr_selfhost_fields_layout.addWidget(self.glmocr_model_label)
        self.glmocr_model_edit = LineEdit()
        self.glmocr_model_edit.setPlaceholderText(
            self.translate("settings_glmocr_model_placeholder")
        )
        self.glmocr_model_edit.editingFinished.connect(self._save_glmocr_model)
        self.glmocr_selfhost_fields_layout.addWidget(self.glmocr_model_edit)

        self.glmocr_config_path_label = BodyLabel(
            self.translate("settings_glmocr_config_path_label")
        )
        self.glmocr_selfhost_fields_layout.addWidget(self.glmocr_config_path_label)
        glmocr_config_row = QHBoxLayout()
        glmocr_config_row.setSpacing(8)
        self.glmocr_config_path_edit = LineEdit()
        self.glmocr_config_path_edit.setPlaceholderText(
            self.translate("settings_glmocr_config_path_placeholder")
        )
        self.glmocr_config_path_edit.editingFinished.connect(
            self._save_glmocr_config_path
        )
        self.glmocr_config_path_button = PushButton(
            self.translate("browse_button_compact")
        )
        self.glmocr_config_path_button.setIcon(FIF.FOLDER)
        self.glmocr_config_path_button.clicked.connect(self._browse_glmocr_config_path)
        glmocr_config_row.addWidget(self.glmocr_config_path_edit, 1)
        glmocr_config_row.addWidget(self.glmocr_config_path_button)
        self.glmocr_selfhost_fields_layout.addLayout(glmocr_config_row)
        glmocr_layout.addWidget(self.glmocr_selfhost_fields)
        ocr_layout.addWidget(self.glmocr_group)

        self.legacy_ocr_group = QGroupBox(
            self.translate("settings_legacy_ocr_group")
        )
        legacy_layout = QVBoxLayout(self.legacy_ocr_group)
        legacy_layout.setSpacing(10)

        legacy_layout.addWidget(BodyLabel(self.translate("settings_docintel_label")))
        self.docintel_endpoint_edit = LineEdit()
        self.docintel_endpoint_edit.setPlaceholderText(
            self.translate("settings_docintel_placeholder")
        )
        self.docintel_endpoint_edit.setToolTip(
            self.translate("settings_docintel_tooltip")
        )
        self.docintel_endpoint_edit.editingFinished.connect(
            self._save_docintel_endpoint
        )
        self.docintel_endpoint_edit.textChanged.connect(
            lambda *_args: self._update_azure_test_button_state()
        )
        legacy_layout.addWidget(self.docintel_endpoint_edit)

        azure_test_row = QHBoxLayout()
        azure_test_row.setSpacing(8)
        self.test_azure_button = PushButton(
            self.translate("settings_test_azure_button")
        )
        self.test_azure_button.setIcon(FIF.SYNC)
        self.test_azure_button.setToolTip(
            self.translate("settings_test_azure_tooltip")
        )
        self.test_azure_button.clicked.connect(self._test_azure_connection)
        azure_test_row.addWidget(self.test_azure_button)
        azure_test_row.addStretch(1)
        legacy_layout.addLayout(azure_test_row)

        legacy_layout.addWidget(
            BodyLabel(self.translate("settings_ocr_language_label"))
        )
        self.ocr_languages_edit = LineEdit()
        self.ocr_languages_edit.setPlaceholderText(
            self.translate("settings_ocr_language_placeholder")
        )
        self.ocr_languages_edit.setToolTip(
            self.translate("settings_ocr_language_tooltip")
        )
        self.ocr_languages_edit.editingFinished.connect(self._save_ocr_languages)
        legacy_layout.addWidget(self.ocr_languages_edit)

        legacy_layout.addWidget(
            BodyLabel(self.translate("settings_tesseract_path_label"))
        )
        tesseract_row = QHBoxLayout()
        tesseract_row.setSpacing(8)
        self.tesseract_path_edit = LineEdit()
        self.tesseract_path_edit.setPlaceholderText(
            self.translate("settings_tesseract_path_placeholder")
        )
        self.tesseract_path_edit.setToolTip(
            self.translate("settings_tesseract_path_tooltip")
        )
        self.tesseract_path_edit.editingFinished.connect(self._save_tesseract_path)
        self.tesseract_path_button = PushButton(
            self.translate("browse_button_compact")
        )
        self.tesseract_path_button.setIcon(FIF.FOLDER)
        self.tesseract_path_button.clicked.connect(self._browse_tesseract_path)
        tesseract_row.addWidget(self.tesseract_path_edit, 1)
        tesseract_row.addWidget(self.tesseract_path_button)
        legacy_layout.addLayout(tesseract_row)
        ocr_layout.addWidget(self.legacy_ocr_group)
        layout.addWidget(self.ocr_group)

        self.appearance_group = QGroupBox(self.translate("settings_appearance_group"))
        appearance_layout = QVBoxLayout(self.appearance_group)
        appearance_layout.setSpacing(8)

        self.theme_light = RadioButton(self.translate("theme_light"))
        self.theme_dark = RadioButton(self.translate("theme_dark"))
        self.theme_system = RadioButton(self.translate("theme_system"))
        self.theme_light.toggled.connect(
            lambda checked: self._save_theme("light", checked)
        )
        self.theme_dark.toggled.connect(
            lambda checked: self._save_theme("dark", checked)
        )
        self.theme_system.toggled.connect(
            lambda checked: self._save_theme("system", checked)
        )

        appearance_layout.addWidget(self.theme_light)
        appearance_layout.addWidget(self.theme_dark)
        appearance_layout.addWidget(self.theme_system)
        layout.addWidget(self.appearance_group)

        layout.addStretch(1)

    def _load_settings(self) -> None:
        self.output_format_combo.setCurrentText(
            self.settings_manager.get_default_output_format()
        )
        self.output_folder_edit.setText(
            self.settings_manager.get_default_output_folder()
        )
        self.batch_size_spin.setValue(self.settings_manager.get_batch_size())

        format_settings = self.settings_manager.get_format_settings()
        self.header_style_combo.setCurrentText(
            str(format_settings.get("headerStyle", ""))
        )
        self.table_style_combo.setCurrentText(
            str(format_settings.get("tableStyle", ""))
        )

        self.ocr_enabled_check.setChecked(self.settings_manager.get_ocr_enabled())
        self._set_combo_value(
            self.ocr_provider_combo,
            self._ocr_provider_values,
            self.settings_manager.get_ocr_provider(),
        )
        self.ocr_fallback_check.setChecked(
            self.settings_manager.get_ocr_fallback_enabled()
        )
        self._set_combo_value(
            self.glmocr_mode_combo,
            self._glmocr_mode_values,
            self.settings_manager.get_glmocr_mode(),
        )
        self.glmocr_api_host_edit.setText(self.settings_manager.get_glmocr_api_host())
        self.glmocr_api_port_spin.setValue(self.settings_manager.get_glmocr_api_port())
        self.glmocr_model_edit.setText(self.settings_manager.get_glmocr_model())
        self.glmocr_config_path_edit.setText(
            self.settings_manager.get_glmocr_config_path()
        )
        self.docintel_endpoint_edit.setText(
            self.settings_manager.get_docintel_endpoint()
        )
        self.ocr_languages_edit.setText(self.settings_manager.get_ocr_languages())
        self.tesseract_path_edit.setText(self.settings_manager.get_tesseract_path())
        self._update_azure_test_button_state()
        self._update_ocr_sections_visibility()

        theme_mode = self.settings_manager.get_theme_mode()
        self.theme_light.setChecked(theme_mode == "light")
        self.theme_dark.setChecked(theme_mode == "dark")
        self.theme_system.setChecked(theme_mode == "system")

    def _set_combo_value(self, combo: ComboBox, values: list[str], value: str) -> None:
        try:
            index = values.index(value)
        except ValueError:
            index = 0
        combo.setCurrentIndex(index)

    def _current_ocr_provider(self) -> str:
        index = self.ocr_provider_combo.currentIndex()
        if 0 <= index < len(self._ocr_provider_values):
            return self._ocr_provider_values[index]
        return OCR_PROVIDER_LEGACY

    def _current_glmocr_mode(self) -> str:
        index = self.glmocr_mode_combo.currentIndex()
        if 0 <= index < len(self._glmocr_mode_values):
            return self._glmocr_mode_values[index]
        return GLMOCR_MODE_MAAS

    def _build_conversion_options(self) -> ConversionOptions:
        return ConversionOptions(
            ocr_enabled=self.ocr_enabled_check.isChecked(),
            ocr_provider=self._current_ocr_provider(),
            ocr_fallback_enabled=self.ocr_fallback_check.isChecked(),
            docintel_endpoint=self.docintel_endpoint_edit.text(),
            ocr_languages=self.ocr_languages_edit.text(),
            tesseract_path=self.tesseract_path_edit.text(),
            glmocr_mode=self._current_glmocr_mode(),
            glmocr_api_host=self.glmocr_api_host_edit.text(),
            glmocr_api_port=self.glmocr_api_port_spin.value(),
            glmocr_model=self.glmocr_model_edit.text(),
            glmocr_config_path=self.glmocr_config_path_edit.text(),
        )

    def _update_ocr_sections_visibility(self) -> None:
        provider = self._current_ocr_provider()
        glm_mode = self._current_glmocr_mode()
        use_glmocr = provider == OCR_PROVIDER_GLMOCR
        legacy_visible = provider == OCR_PROVIDER_LEGACY or (
            use_glmocr and self.ocr_fallback_check.isChecked()
        )

        self.glmocr_group.setVisible(use_glmocr)
        self.glmocr_maas_note.setVisible(use_glmocr and glm_mode == GLMOCR_MODE_MAAS)
        self.glmocr_selfhost_note.setVisible(
            use_glmocr and glm_mode == GLMOCR_MODE_SELFHOSTED
        )
        self.glmocr_selfhost_fields.setVisible(
            use_glmocr and glm_mode == GLMOCR_MODE_SELFHOSTED
        )
        self.legacy_ocr_group.setVisible(legacy_visible)
        self._update_azure_test_button_state()

    def _save_output_folder(self) -> None:
        self.settings_manager.set_default_output_folder(
            self.output_folder_edit.text().strip()
        )

    def _browse_output_folder(self) -> None:
        start_dir = self.settings_manager.get_default_output_folder()
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = ""
        folder = QFileDialog.getExistingDirectory(
            self,
            self.translate("settings_output_folder_dialog"),
            start_dir,
        )
        if folder:
            self.output_folder_edit.setText(folder)
            self.settings_manager.set_default_output_folder(folder)

    def _save_batch_size(self, value: int) -> None:
        self.settings_manager.set_batch_size(value)

    def _save_ocr_enabled(self, checked: bool) -> None:
        self.settings_manager.set_ocr_enabled(checked)

    def _save_ocr_provider(self, *_args) -> None:
        self.settings_manager.set_ocr_provider(self._current_ocr_provider())
        self._update_ocr_sections_visibility()

    def _save_ocr_fallback_enabled(self, checked: bool) -> None:
        self.settings_manager.set_ocr_fallback_enabled(checked)
        self._update_ocr_sections_visibility()

    def _save_glmocr_mode(self, *_args) -> None:
        self.settings_manager.set_glmocr_mode(self._current_glmocr_mode())
        self._update_ocr_sections_visibility()

    def _save_glmocr_api_host(self) -> None:
        self.settings_manager.set_glmocr_api_host(self.glmocr_api_host_edit.text())

    def _save_glmocr_api_port(self, value: int) -> None:
        self.settings_manager.set_glmocr_api_port(value)

    def _save_glmocr_model(self) -> None:
        self.settings_manager.set_glmocr_model(self.glmocr_model_edit.text())

    def _save_glmocr_config_path(self) -> None:
        self.settings_manager.set_glmocr_config_path(
            self.glmocr_config_path_edit.text()
        )

    def _browse_glmocr_config_path(self) -> None:
        start_path = self.settings_manager.get_glmocr_config_path()
        if start_path and not os.path.exists(start_path):
            start_path = ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translate("settings_glmocr_config_path_dialog"),
            start_path,
            self.translate("yaml_files_filter"),
        )
        if file_path:
            self.glmocr_config_path_edit.setText(file_path)
            self.settings_manager.set_glmocr_config_path(file_path)

    def _save_docintel_endpoint(self) -> None:
        self.settings_manager.set_docintel_endpoint(self.docintel_endpoint_edit.text())
        self._update_azure_test_button_state()

    def _save_ocr_languages(self) -> None:
        self.settings_manager.set_ocr_languages(self.ocr_languages_edit.text())

    def _save_tesseract_path(self) -> None:
        self.settings_manager.set_tesseract_path(self.tesseract_path_edit.text())

    def _browse_tesseract_path(self) -> None:
        start_path = self.settings_manager.get_tesseract_path()
        if start_path and not os.path.exists(start_path):
            start_path = ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translate("settings_tesseract_dialog"),
            start_path,
            self.translate("all_files_filter"),
        )
        if file_path:
            self.tesseract_path_edit.setText(file_path)
            self.settings_manager.set_tesseract_path(file_path)

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

    def _update_azure_test_button_state(self) -> None:
        if self._azure_test_worker is not None:
            return
        self.test_azure_button.setEnabled(
            bool(self.docintel_endpoint_edit.text().strip())
            and not self.legacy_ocr_group.isHidden()
        )

    def _test_azure_connection(self) -> None:
        self._save_docintel_endpoint()
        self.test_azure_button.setEnabled(False)
        self.test_azure_button.setText(
            self.translate("settings_test_azure_in_progress")
        )

        worker = AzureConnectionTestWorker(self._build_conversion_options())
        self._azure_test_worker = worker
        worker.succeeded.connect(self._handle_azure_test_success)
        worker.failed.connect(self._handle_azure_test_failure)
        worker.finished.connect(self._finish_azure_test)
        worker.start()

    def _handle_azure_test_success(self, auth_method: str) -> None:
        auth_label_key = "settings_test_azure_auth_identity"
        if auth_method == "api_key":
            auth_label_key = "settings_test_azure_auth_api_key"

        InfoBar.success(
            self.translate("settings_test_azure_success_title"),
            self.translate("settings_test_azure_success_message").format(
                auth_method=self.translate(auth_label_key)
            ),
            duration=4000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _handle_azure_test_failure(self, error: str) -> None:
        InfoBar.error(
            self.translate("settings_test_azure_failure_title"),
            self.translate("settings_test_azure_failure_message").format(error=error),
            duration=5000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _finish_azure_test(self) -> None:
        if self._azure_test_worker is not None:
            self._azure_test_worker.deleteLater()
            self._azure_test_worker = None
        self.test_azure_button.setText(self.translate("settings_test_azure_button"))
        self._update_azure_test_button_state()
