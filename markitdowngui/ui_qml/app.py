from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer, Qt, QUrl
from PySide6.QtGui import QFont, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from markitdowngui.ui_qml.controller import AppController
from markitdowngui.utils.logger import AppLogger


def main() -> int:
    AppLogger.initialize()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    _configure_style()

    QCoreApplication.setOrganizationName("MarkItDown")
    QCoreApplication.setApplicationName("MarkItDown GUI")

    app = QGuiApplication(sys.argv)
    app.setFont(_platform_font())
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

    QTimer.singleShot(500, controller.checkLastPackagedUpdateResult)
    QTimer.singleShot(2000, controller.startAutomaticUpdateCheck)
    app.aboutToQuit.connect(controller.shutdown)
    return app.exec()


def _configure_style() -> None:
    QQuickStyle.setStyle("Basic")


def _platform_font() -> QFont:
    if sys.platform == "win32":
        return QFont("Segoe UI", 10)
    if sys.platform == "darwin":
        return QFont(".AppleSystemUIFont", 13)
    return QFont("Noto Sans", 10)
