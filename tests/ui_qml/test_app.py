from unittest.mock import Mock

from markitdowngui.ui_qml.app import _shutdown_without_result
from markitdowngui.ui_qml.controller import AppController


def test_shutdown_without_result_discards_close_decision():
    controller = Mock(spec=AppController)
    controller.shutdown.return_value = True

    result = _shutdown_without_result(controller)

    assert result is None
    controller.shutdown.assert_called_once_with()
