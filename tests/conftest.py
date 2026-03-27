import os
from pathlib import Path
import struct
import sys
import types
import zlib

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


def _import_pymupdf_module():
    try:
        import pymupdf  # type: ignore
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required for PDF runtime tests.") from exc
    return pymupdf


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", checksum)
    )


def _pattern_png_bytes(width: int, height: int, seed: int) -> bytes:
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend(
                (
                    (x * 3 + y * 5 + seed) % 256,
                    (x * 7 + y * 11 + seed * 3) % 256,
                    (x * 13 + y * 17 + seed * 5) % 256,
                )
            )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    compressed = zlib.compress(bytes(rows), level=6)
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", header),
            _png_chunk(b"IDAT", compressed),
            _png_chunk(b"IEND", b""),
        )
    )


@pytest.fixture
def sample_pdf_factory():
    try:
        pymupdf = _import_pymupdf_module()
    except RuntimeError as exc:
        pytest.skip(str(exc))

    def factory(output_path: Path) -> Path:
        output_path = Path(output_path)
        document = pymupdf.open()
        try:
            image_one = _pattern_png_bytes(128, 96, 1)
            image_two = _pattern_png_bytes(128, 96, 2)
            image_three = _pattern_png_bytes(128, 96, 3)

            page_one = document.new_page(width=420, height=640)
            page_one.insert_textbox(
                pymupdf.Rect(40, 40, 360, 90),
                "Alpha paragraph",
            )
            page_one.insert_image(
                pymupdf.Rect(40, 120, 240, 240),
                stream=image_one,
            )
            page_one.insert_textbox(
                pymupdf.Rect(40, 280, 360, 330),
                "Beta paragraph",
            )
            page_one.insert_image(
                pymupdf.Rect(40, 360, 240, 480),
                stream=image_two,
            )

            page_two = document.new_page(width=420, height=640)
            page_two.insert_image(
                pymupdf.Rect(40, 40, 240, 160),
                stream=image_three,
            )
            page_two.insert_textbox(
                pymupdf.Rect(40, 220, 360, 270),
                "Gamma paragraph",
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            document.save(output_path)
        finally:
            document.close()

        return output_path

    return factory
