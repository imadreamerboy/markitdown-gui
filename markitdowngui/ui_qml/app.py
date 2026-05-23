from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from markitdowngui.ui_qml.controller import AppController
from markitdowngui.utils.logger import AppLogger


def main() -> int:
    AppLogger.initialize()
    _configure_style()

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QCoreApplication.setOrganizationName("MarkItDown")
    QCoreApplication.setApplicationName("MarkItDown GUI")

    app = QGuiApplication(sys.argv)
    icon_path = Path(__file__).resolve().parents[1] / "resources" / "markitdown-gui.png"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    controller = AppController()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("app", controller)

    qml_path = Path(__file__).resolve().parents[1] / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    app.aboutToQuit.connect(controller.shutdown)
    return app.exec()


def _configure_style() -> None:
    if sys.platform == "win32":
        QQuickStyle.setStyle("FluentWinUI3")
    elif sys.platform == "darwin":
        QQuickStyle.setStyle("macOS")
    else:
        QQuickStyle.setStyle("Fusion")

    os.environ.setdefault("QT_QUICK_CONTROLS_CONF", "")

