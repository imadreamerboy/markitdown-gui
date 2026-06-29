from pathlib import Path

from PySide6.QtCore import QCoreApplication, QSettings, QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui_qml.controller import AppController


def test_main_qml_loads_with_controller_context(monkeypatch, tmp_path):
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

    try:
        assert len(engine.rootObjects()) == 1
    finally:
        controller.shutdown()
        for root in engine.rootObjects():
            root.close()
        app.processEvents()


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
