from unittest.mock import Mock

from PySide6.QtCore import QThread

from markitdowngui.ui_qml.app import _shutdown_without_result
from markitdowngui.ui_qml.controller import AppController


def test_shutdown_without_result_uses_non_vetoable_shutdown_path():
    controller = Mock(spec=AppController)

    result = _shutdown_without_result(controller)

    assert result is None
    controller.shutdownForQuit.assert_called_once_with()


class _DelayedThread(QThread):
    def run(self) -> None:
        self.msleep(40)


def test_shutdown_without_result_joins_live_threads():
    controller = AppController()
    checker = _DelayedThread()
    controller._update_checker = checker
    checker.start()

    _shutdown_without_result(controller)

    assert checker.isRunning() is False
