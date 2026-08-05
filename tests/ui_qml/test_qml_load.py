from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, QPoint, QPointF, QSettings, QUrl, Qt
from PySide6.QtGui import QAccessible, QColor, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtQuickControls2 import QQuickStyle

from markitdowngui.core.conversion import ConversionOutcome
from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui_qml.controller import AppController


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear_channels = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return (
        0.2126 * linear_channels[0]
        + 0.7152 * linear_channels[1]
        + 0.0722 * linear_channels[2]
    )


def _contrast_ratio(foreground: str, background: str) -> float:
    foreground_luminance = _relative_luminance(foreground)
    background_luminance = _relative_luminance(background)
    lighter, darker = sorted((foreground_luminance, background_luminance), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _load_main_qml(monkeypatch, tmp_path, qml_warnings=None):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([])
    QCoreApplication.setOrganizationName("MarkItDown")
    QCoreApplication.setApplicationName("QML Load Test")

    controller = AppController()
    settings = SettingsManager()
    settings.settings = QSettings(
        str(tmp_path / "settings.ini"),
        QSettings.Format.IniFormat,
    )
    controller.settings = settings

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("app", controller)
    if qml_warnings is not None:
        engine.warnings.connect(
            lambda warnings: qml_warnings.extend(
                warning.toString() for warning in warnings
            )
        )
    qml_path = (
        Path(__file__).resolve().parents[2]
        / "markitdowngui"
        / "qml"
        / "Main.qml"
    )
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    assert len(engine.rootObjects()) == 1
    return app, controller, engine, engine.rootObjects()[0]


def _close_main_qml(app, controller, engine):
    controller.shutdown()
    for root in engine.rootObjects():
        root.close()
    app.processEvents()


def _find_by_property(root, property_name, value):
    matches = [
        item
        for item in root.findChildren(QObject)
        if item.property(property_name) == value
    ]
    assert len(matches) == 1
    return matches[0]


def _accessible_name(item):
    interface = QAccessible.queryAccessibleInterface(item)
    assert interface is not None
    return interface.text(QAccessible.Text.Name)


def _visible_app_buttons(root):
    return [
        item
        for item in root.findChildren(QQuickItem)
        if "AppButton" in item.metaObject().className() and item.isVisible()
    ]


def test_main_qml_loads_with_controller_context(monkeypatch, tmp_path):
    app, controller, engine, _ = _load_main_qml(monkeypatch, tmp_path)

    try:
        assert len(engine.rootObjects()) == 1
    finally:
        _close_main_qml(app, controller, engine)


def test_main_qml_loads_secondary_pages_on_demand(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        loaders = {
            item.objectName(): item
            for item in root.findChildren(QObject)
            if item.objectName() in {
                "workspacePageLoader",
                "settingsPageLoader",
                "helpPageLoader",
            }
        }

        assert loaders["workspacePageLoader"].property("item") is not None
        assert loaders["settingsPageLoader"].property("item") is None
        assert loaders["helpPageLoader"].property("item") is None

        root.setProperty("pageIndex", 1)
        app.processEvents()

        assert loaders["settingsPageLoader"].property("item") is not None
    finally:
        _close_main_qml(app, controller, engine)


def test_app_buttons_are_hoverable_and_accessible_across_pages(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        controller.addFiles([str(tmp_path / "digital.pdf")])
        for page_index in (0, 1, 2):
            root.setProperty("pageIndex", page_index)
            QTest.qWait(220)
            app.processEvents()

            buttons = _visible_app_buttons(root)
            assert buttons
            for button in buttons:
                text = button.property("text")
                if not text:
                    continue
                interface = QAccessible.queryAccessibleInterface(button)
                assert interface is not None
                assert interface.role() == QAccessible.Role.Button
                assert button.property("hoverEnabled") is True
                assert interface.text(QAccessible.Text.Name) == text

        controller.result_model.set_results(
            {
                str(tmp_path / "digital.md"): ConversionOutcome("# Converted\n\nPreview")
            }
        )
        controller._selected_result_index = 0
        controller.resultsChanged.emit()
        controller.selectedResultChanged.emit()
        root.setProperty("pageIndex", 0)
        QTest.qWait(220)
        app.processEvents()

        for button in _visible_app_buttons(root):
            text = button.property("text")
            if not text:
                continue
            interface = QAccessible.queryAccessibleInterface(button)
            assert interface is not None
            assert interface.role() == QAccessible.Role.Button
            assert button.property("hoverEnabled") is True
            assert interface.text(QAccessible.Text.Name) == text
    finally:
        _close_main_qml(app, controller, engine)


def test_buttons_and_setting_rows_provide_press_and_click_feedback(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        root.setWidth(820)
        root.setHeight(560)
        app.processEvents()

        button = next(
            item
            for item in _visible_app_buttons(root)
            if item.property("text") == "Add webpage"
        )
        button_point = button.mapToScene(button.boundingRect().center())
        point = QPoint(round(button_point.x()), round(button_point.y()))
        QTest.mouseMove(root, point)
        app.processEvents()
        assert button.property("hovered") is True

        QTest.mousePress(root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
        QTest.qWait(60)
        app.processEvents()
        assert button.property("down") is True
        assert button.scale() < 1
        QTest.mouseRelease(root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)

        controller.addFiles([str(tmp_path / "digital.pdf")])
        app.processEvents()
        toggle = _find_by_property(root, "title", "OCR")
        toggle_point = toggle.mapToScene(QPointF(40, toggle.height() / 2))
        QTest.mouseClick(
            root,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(round(toggle_point.x()), round(toggle_point.y())),
        )
        app.processEvents()
        assert controller.ocrEnabled is True
    finally:
        _close_main_qml(app, controller, engine)


def test_compact_workspace_keeps_inspector_rows_inside_the_scroll_body(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        root.setWidth(820)
        root.setHeight(560)
        controller.addFiles([str(tmp_path / "digital.pdf")])
        app.processEvents()

        rows = [
            _find_by_property(root, "title", title)
            for title in {
                "OCR",
                "Fast PDF conversion",
                "Preserve PDF images",
                "Preserve DOCX images",
            }
        ]
        available_width = float(rows[0].parent().property("width"))

        assert available_width > 0
        assert all(float(row.property("width")) <= available_width + 0.1 for row in rows)
    finally:
        _close_main_qml(app, controller, engine)


def test_compact_results_keep_preview_actions_inside_the_panel(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        controller.result_model.set_results(
            {
                str(tmp_path / "digital.md"): ConversionOutcome(
                    "# Converted\n\nA compact preview.",
                )
            }
        )
        controller._selected_result_index = 0
        controller.resultsChanged.emit()
        controller.selectedResultChanged.emit()
        root.setWidth(820)
        root.setHeight(560)
        app.processEvents()

        toolbar = next(
            item
            for item in root.findChildren(QQuickItem)
            if item.property("compactActions") is True
        )
        save_button = next(
            item
            for item in root.findChildren(QQuickItem)
            if item.isVisible()
            and item.property("text") == "Save"
                and item.property("iconName") == "save"
        )
        right_edge = save_button.mapToItem(
            toolbar,
            QPointF(save_button.width(), 0),
        ).x()

        assert toolbar.width() <= root.width()
        assert right_edge <= toolbar.width() + 0.1
    finally:
        _close_main_qml(app, controller, engine)


def test_reduce_motion_updates_qml_controls(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        motion_controls = [
            item
            for item in root.findChildren(QObject)
            if item.property("reduceMotion") is not None
        ]

        assert motion_controls
        assert {bool(item.property("reduceMotion")) for item in motion_controls} == {False}

        controller.setReduceMotion(True)
        app.processEvents()

        assert root.property("reduceMotion") is True
        assert {bool(item.property("reduceMotion")) for item in motion_controls} == {True}
    finally:
        _close_main_qml(app, controller, engine)


def test_toggle_row_exposes_a_valid_accessible_role(monkeypatch, tmp_path):
    qml_warnings = []
    app, controller, engine, root = _load_main_qml(
        monkeypatch,
        tmp_path,
        qml_warnings=qml_warnings,
    )

    try:
        controller.addFiles([str(tmp_path / "digital.pdf")])
        app.processEvents()
        toggle = _find_by_property(root, "title", "Fast PDF conversion")
        switch = next(
            item
            for item in toggle.findChildren(QQuickItem)
            if item.property("checked") is not None
        )
        interface = QAccessible.queryAccessibleInterface(switch)

        assert interface is not None
        assert interface.role() == QAccessible.Role.CheckBox
        assert not any("QAccessible::Role" in warning for warning in qml_warnings)
        assert not any("multiple key bindings" in warning for warning in qml_warnings)
    finally:
        _close_main_qml(app, controller, engine)


def test_light_olive_tokens_do_not_leak_into_component_defaults():
    qml_root = Path(__file__).resolve().parents[2] / "markitdowngui" / "qml"
    component_root = qml_root / "components"

    component_text = "\n".join(
        path.read_text(encoding="utf-8") for path in component_root.glob("*.qml")
    )
    main_text = (qml_root / "Main.qml").read_text(encoding="utf-8")

    assert "#687700" not in component_text
    assert "#7C6F00" not in component_text
    assert "#E8EBC8" not in component_text
    assert 'dark ? Qt.color("#88C0D0") : Qt.color("#687700")' in main_text


def test_ocr_fallback_selector_is_provider_independent():
    qml_root = Path(__file__).resolve().parents[2] / "markitdowngui" / "qml"
    main_text = (qml_root / "Main.qml").read_text(encoding="utf-8")

    fallback_marker = 'label: root.tr("qml_fallback_provider")'
    glm_panel_marker = 'title: root.tr("settings_glmocr_group")'

    assert main_text.count(fallback_marker) == 1
    assert main_text.index(fallback_marker) < main_text.index(glm_panel_marker)
    assert 'visible: app.ocrEnabled && app.ocrProvider !== "azure_tesseract"' in main_text
    assert "model: root.ocrFallbackLabels()" in main_text


def test_workspace_exposes_fast_pdf_conversion_control():
    qml_root = Path(__file__).resolve().parents[2] / "markitdowngui" / "qml"
    main_text = (qml_root / "Main.qml").read_text(encoding="utf-8")

    assert 'title: root.tr("home_fast_pdf_conversion_label")' in main_text
    assert 'root.tr("home_fast_pdf_conversion_label")' in main_text
    assert 'root.tr("home_fast_pdf_conversion_detail")' in main_text
    assert "checked: app.fastPdfConversion" in main_text
    assert "target: fastPdfConversionToggle" in main_text
    assert "function onToggled(enabled)" in main_text
    assert "app.setFastPdfConversion(enabled)" in main_text
    assert "required property string backendKey" in main_text


def test_fast_pdf_conversion_toggle_updates_controller(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        controller.addFiles([str(tmp_path / "digital.pdf")])
        app.processEvents()
        toggle = _find_by_property(root, "title", "Fast PDF conversion")
        switch = next(
            item
            for item in toggle.findChildren(QQuickItem)
            if item.property("checked") is not None
        )
        position = switch.mapToScene(switch.boundingRect().center())

        QTest.mouseClick(
            root,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(round(position.x()), round(position.y())),
        )
        app.processEvents()

        assert controller.fastPdfConversion is True
    finally:
        _close_main_qml(app, controller, engine)


def test_fast_pdf_conversion_strings_follow_language_setting(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        controller.addFiles([str(tmp_path / "digital.pdf")])
        app.processEvents()
        toggle = _find_by_property(root, "title", "Fast PDF conversion")
        controller.settings.set_current_language("zh_CN")
        controller.settingsChanged.emit()
        app.processEvents()

        assert toggle.property("title") == "快速 PDF 转换"
    finally:
        _close_main_qml(app, controller, engine)


def test_qml_language_selector_updates_visible_interface(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        root.setProperty("pageIndex", 1)
        app.processEvents()

        language_combo = _find_by_property(root, "currentText", "English")
        assert _accessible_name(language_combo) == "Language"

        controller.setLanguage("zh_CN")
        app.processEvents()

        assert language_combo.property("currentText") == "简体中文"
        assert _find_by_property(root, "label", "语言")
        assert _find_by_property(root, "title", "外观")
        assert _find_by_property(root, "text", "工作区")
    finally:
        _close_main_qml(app, controller, engine)


def test_toggle_row_emits_the_switch_value():
    toggle_row = (
        Path(__file__).resolve().parents[2]
        / "markitdowngui"
        / "qml"
        / "components"
        / "ToggleRow.qml"
    ).read_text(encoding="utf-8")

    assert "onToggled: root.toggled(switchControl.checked)" in toggle_row


def test_workspace_confirms_before_discarding_unsaved_results():
    main_text = (
        Path(__file__).resolve().parents[2]
        / "markitdowngui"
        / "qml"
        / "Main.qml"
    ).read_text(encoding="utf-8")

    assert "id: discardResultsDialog" in main_text
    assert "function onDiscardResultsRequested(actionDescription)" in main_text
    assert "app.cancelPendingResultDiscard()" in main_text
    assert "app.discardPendingResults()" in main_text
    assert "onClicked: app.backToQueue()" in main_text
    assert "onClicked: app.startNew()" in main_text
    assert "onClosing: close => close.accepted = app.requestShutdown()" in main_text
    assert "function onCloseApproved()" in main_text


def test_workspace_keeps_conversion_controls_with_progressive_results():
    main_text = (
        Path(__file__).resolve().parents[2]
        / "markitdowngui"
        / "qml"
        / "Main.qml"
    ).read_text(encoding="utf-8")

    assert main_text.count('text: root.tr("qml_stop_after_current")') == 2
    assert "id: activeResultControls" in main_text
    assert "visible: app.converting" in main_text


def test_workspace_clear_shortcut_does_not_steal_text_input_focus():
    main_text = (
        Path(__file__).resolve().parents[2]
        / "markitdowngui"
        / "qml"
        / "Main.qml"
    ).read_text(encoding="utf-8")

    clear_shortcut = main_text[main_text.index('sequence: "Ctrl+L"') :]

    assert (
        "enabled: root.pageIndex === 0 && !app.converting && !root.focusedTextControl()"
        in clear_shortcut
    )
    assert "onActivated: app.clearQueue()" in clear_shortcut


def test_workspace_clear_shortcut_respects_url_field_focus(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        assert controller.addUrl("https://example.com")
        url_fields = [
            item
            for item in root.findChildren(QObject)
            if item.property("placeholderText") in {"Add webpage URL", "Paste webpage URL"}
        ]
        assert len(url_fields) == 1
        url_field = url_fields[0]
        url_field.forceActiveFocus()
        app.processEvents()

        QTest.keyClick(root, Qt.Key_L, Qt.ControlModifier)
        app.processEvents()

        assert controller.queue_model.sources() == ["https://example.com"]

        workspace_buttons = [
            item
            for item in root.findChildren(QObject)
            if item.property("text") == "Add webpage" and item.property("iconName") == "link"
        ]
        assert len(workspace_buttons) == 1
        workspace_button = workspace_buttons[0]
        workspace_button.forceActiveFocus()
        app.processEvents()
        QTest.keyClick(root, Qt.Key_L, Qt.ControlModifier)
        app.processEvents()

        assert controller.queue_model.sources() == []
    finally:
        _close_main_qml(app, controller, engine)


def test_settings_controls_have_explicit_accessible_names():
    main_text = (
        Path(__file__).resolve().parents[2]
        / "markitdowngui"
        / "qml"
        / "Main.qml"
    ).read_text(encoding="utf-8")

    expected_names = (
        'Accessible.name: root.tr("qml_application_theme")',
        'Accessible.name: root.tr("qml_primary_ocr_provider")',
        'Accessible.name: root.tr("qml_fallback_ocr_provider")',
        'Accessible.name: root.tr("qml_glmocr_mode")',
        'Accessible.name: root.tr("qml_glmocr_ollama_host")',
        'Accessible.name: root.tr("qml_glmocr_ollama_port")',
        'Accessible.name: root.tr("qml_glmocr_ollama_model")',
        'Accessible.name: root.tr("qml_glmocr_sdk_server_endpoint")',
        'Accessible.name: root.tr("qml_http_ocr_endpoint")',
        'Accessible.name: root.tr("qml_http_ocr_model")',
        'Accessible.name: root.tr("qml_http_ocr_timeout")',
        'Accessible.name: root.tr("qml_http_ocr_api_key_environment_variable")',
        'Accessible.name: root.tr("qml_dismiss_update")',
    )

    for accessible_name in expected_names:
        assert accessible_name in main_text

    assert (
        'Accessible.name: app.ocrProvider === "glmocr"\n'
        '                            ? root.tr("qml_fallback_azure_endpoint")\n'
        '                            : root.tr("qml_azure_endpoint")'
        in main_text
    )
    assert (
        'Accessible.name: app.ocrProvider === "glmocr"\n'
        '                            ? root.tr("qml_fallback_tesseract_languages")\n'
        '                            : root.tr("qml_tesseract_languages")'
        in main_text
    )
    assert (
        'Accessible.name: app.ocrProvider === "glmocr"\n'
        '                            ? root.tr("qml_fallback_tesseract_executable")\n'
        '                            : root.tr("qml_tesseract_executable")'
        in main_text
    )


def test_settings_accessible_names_are_exposed_to_qt_accessibility(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        root.setProperty("pageIndex", 1)
        controller.setOcrEnabled(True)
        controller.setOcrProvider("azure_tesseract")
        app.processEvents()

        assert _accessible_name(
            _find_by_property(root, "currentText", "Solarized Light")
        ) == "Application theme"
        assert _accessible_name(
            _find_by_property(root, "currentText", "Azure/Tesseract OCR")
        ) == "Primary OCR provider"
        assert _accessible_name(
            _find_by_property(
                root,
                "placeholderText",
                "https://example.cognitiveservices.azure.com/",
            )
        ) == "Azure endpoint"
        assert _accessible_name(
            _find_by_property(root, "placeholderText", "eng or eng+deu")
        ) == "Tesseract languages"
        assert _accessible_name(
            _find_by_property(root, "placeholderText", "Optional executable path")
        ) == "Tesseract executable"

        controller.setOcrProvider("glmocr")
        controller.setGlmocrMode("ollama")
        app.processEvents()

        assert _accessible_name(
            _find_by_property(root, "currentText", "GLM-OCR")
        ) == "Primary OCR provider"
        assert _accessible_name(_find_by_property(root, "currentText", "None")) == (
            "Fallback OCR provider"
        )
        assert _accessible_name(_find_by_property(root, "currentText", "Ollama")) == (
            "GLM-OCR mode"
        )
        assert _accessible_name(
            _find_by_property(root, "placeholderText", "127.0.0.1")
        ) == "GLM-OCR Ollama host"
        assert _accessible_name(
            _find_by_property(root, "value", 11434)
        ) == "GLM-OCR Ollama port"
        assert _accessible_name(
            _find_by_property(root, "placeholderText", "glm-ocr:latest")
        ) == "GLM-OCR Ollama model"

        controller.setOcrProvider("http")
        app.processEvents()

        assert _accessible_name(
            _find_by_property(root, "placeholderText", "http://127.0.0.1:8000/ocr")
        ) == "HTTP OCR endpoint"
        assert _accessible_name(
            _find_by_property(root, "placeholderText", "surya, doctr, paddleocr, ...")
        ) == "HTTP OCR model"
        assert _accessible_name(_find_by_property(root, "value", 300)) == (
            "HTTP OCR timeout in seconds"
        )
        assert _accessible_name(
            _find_by_property(root, "placeholderText", "OCR_HTTP_API_KEY")
        ) == "HTTP OCR API key environment variable"
    finally:
        _close_main_qml(app, controller, engine)


def test_light_theme_warning_and_error_tokens_meet_normal_text_contrast():
    main_text = (
        Path(__file__).resolve().parents[2]
        / "markitdowngui"
        / "qml"
        / "Main.qml"
    ).read_text(encoding="utf-8")

    assert 'danger: dark ? Qt.color("#E8949C") : Qt.color("#C82624")' in main_text
    assert 'warning: dark ? Qt.color("#EBCB8B") : Qt.color("#7A5900")' in main_text
    assert _contrast_ratio("#7A5900", "#FFFCF0") >= 4.5
    assert _contrast_ratio("#C82624", "#FFF2F0") >= 4.5
    assert _contrast_ratio("#C82624", "#F7F0D8") >= 4.5


def test_light_theme_runtime_palette_meets_normal_text_contrast(monkeypatch, tmp_path):
    app, controller, engine, root = _load_main_qml(monkeypatch, tmp_path)

    try:
        controller.setThemeMode("light")
        app.processEvents()
        colors = root.property("colors")
        if hasattr(colors, "toVariant"):
            colors = colors.toVariant()

        def color_name(name):
            return colors[name].name()

        assert _contrast_ratio(color_name("text"), color_name("window")) >= 4.5
        assert _contrast_ratio(color_name("muted"), color_name("surface")) >= 4.5
        assert _contrast_ratio(color_name("warning"), color_name("surface")) >= 4.5
        assert _contrast_ratio(color_name("danger"), QColor("#FFF2F0").name()) >= 4.5
        assert _contrast_ratio(color_name("success"), QColor("#EEF8F0").name()) >= 4.5
        assert _contrast_ratio(color_name("onAction"), color_name("action")) >= 4.5
        assert _contrast_ratio(color_name("onAccent"), color_name("danger")) >= 4.5
    finally:
        _close_main_qml(app, controller, engine)
