import os
import sys
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QWidget,
)


def _install_qfluentwidgets_stub() -> None:
    try:
        __import__("qfluentwidgets")
        return
    except ImportError:
        pass

    module = types.ModuleType("qfluentwidgets")

    class _BaseButton(QPushButton):
        def setIcon(self, _icon):
            return None

    class BodyLabel(QLabel):
        pass

    class CaptionLabel(QLabel):
        pass

    class TitleLabel(QLabel):
        pass

    class ElevatedCardWidget(QFrame):
        pass

    class PushButton(_BaseButton):
        pass

    class PrimaryPushButton(_BaseButton):
        pass

    class PillPushButton(_BaseButton):
        pass

    class ComboBox(QComboBox):
        pass

    class CheckBox(QCheckBox):
        pass

    class RadioButton(QRadioButton):
        pass

    class SpinBox(QSpinBox):
        pass

    class LineEdit(QLineEdit):
        pass

    class ProgressBar(QProgressBar):
        pass

    class SegmentedWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._callbacks = {}
            self._current = None

        def addItem(self, key, _text, callback, _icon=None):
            self._callbacks[key] = callback

        def setCurrentItem(self, key):
            self._current = key

        def currentItem(self):
            return self._current

    class InfoBar:
        @staticmethod
        def success(*_args, **_kwargs):
            return None

        @staticmethod
        def warning(*_args, **_kwargs):
            return None

        @staticmethod
        def error(*_args, **_kwargs):
            return None

    class InfoBarPosition:
        TOP_RIGHT = "TOP_RIGHT"

    class Theme:
        DARK = "dark"
        LIGHT = "light"
        AUTO = "auto"

    fluent_icon = types.SimpleNamespace(
        FOLDER_ADD=object(),
        ADD=object(),
        REMOVE=object(),
        DELETE=object(),
        PLAY=object(),
        PAUSE=object(),
        CANCEL=object(),
        RETURN=object(),
        CLEAR_SELECTION=object(),
        VIEW=object(),
        CODE=object(),
        DOCUMENT=object(),
        FOLDER=object(),
        COPY=object(),
        SAVE_AS=object(),
        SYNC=object(),
    )

    module.BodyLabel = BodyLabel
    module.CaptionLabel = CaptionLabel
    module.TitleLabel = TitleLabel
    module.ElevatedCardWidget = ElevatedCardWidget
    module.PushButton = PushButton
    module.PrimaryPushButton = PrimaryPushButton
    module.PillPushButton = PillPushButton
    module.ComboBox = ComboBox
    module.CheckBox = CheckBox
    module.RadioButton = RadioButton
    module.SpinBox = SpinBox
    module.LineEdit = LineEdit
    module.ProgressBar = ProgressBar
    module.SegmentedWidget = SegmentedWidget
    module.InfoBar = InfoBar
    module.InfoBarPosition = InfoBarPosition
    module.FluentIcon = fluent_icon
    module.Theme = Theme
    module.isDarkTheme = lambda: False
    module.setTheme = lambda *_args, **_kwargs: None
    module.setThemeColor = lambda *_args, **_kwargs: None

    sys.modules["qfluentwidgets"] = module


import pytest


_install_qfluentwidgets_stub()


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
