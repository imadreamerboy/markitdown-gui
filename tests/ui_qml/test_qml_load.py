from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, QSettings, QUrl, Qt
from PySide6.QtGui import QAccessible, QColor, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtQuickControls2 import QQuickStyle

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


def _load_main_qml(monkeypatch, tmp_path):
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


def test_main_qml_loads_with_controller_context(monkeypatch, tmp_path):
    app, controller, engine, _ = _load_main_qml(monkeypatch, tmp_path)

    try:
        assert len(engine.rootObjects()) == 1
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

    fallback_marker = 'label: "Fallback provider"'
    glm_panel_marker = 'title: "GLM-OCR"'

    assert main_text.count(fallback_marker) == 1
    assert main_text.index(fallback_marker) < main_text.index(glm_panel_marker)
    assert 'visible: app.ocrEnabled && app.ocrProvider !== "azure_tesseract"' in main_text
    assert "model: root.ocrFallbackLabels()" in main_text


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

    assert main_text.count('text: "Stop after current"') == 2
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
        'Accessible.name: "Application theme"',
        'Accessible.name: "Primary OCR provider"',
        'Accessible.name: "Fallback OCR provider"',
        'Accessible.name: "GLM-OCR mode"',
        'Accessible.name: "GLM-OCR Ollama host"',
        'Accessible.name: "GLM-OCR Ollama port"',
        'Accessible.name: "GLM-OCR Ollama model"',
        'Accessible.name: "GLM-OCR SDK server endpoint"',
        'Accessible.name: "HTTP OCR endpoint"',
        'Accessible.name: "HTTP OCR model"',
        'Accessible.name: "HTTP OCR timeout in seconds"',
        'Accessible.name: "HTTP OCR API key environment variable"',
        'Accessible.name: "Dismiss update notification"',
    )

    for accessible_name in expected_names:
        assert accessible_name in main_text

    assert (
        'Accessible.name: app.ocrProvider === "glmocr" ? "Fallback Azure endpoint" : "Azure endpoint"'
        in main_text
    )
    assert (
        'Accessible.name: app.ocrProvider === "glmocr" ? "Fallback Tesseract languages" : "Tesseract languages"'
        in main_text
    )
    assert (
        'Accessible.name: app.ocrProvider === "glmocr" ? "Fallback Tesseract executable" : "Tesseract executable"'
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
            _find_by_property(root, "currentText", "Azure + Tesseract")
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
