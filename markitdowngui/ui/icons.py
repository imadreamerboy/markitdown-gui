from __future__ import annotations

import os
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QSize
from PySide6.QtSvg import QSvgRenderer


def make_tinted_svg_icon(resources_dir: str, base_name: str, color: QColor, size: QSize | None = None) -> QIcon:
    """Render an SVG and tint it with the provided color.

    - resources_dir: directory containing the SVGs
    - base_name: file name without extension
    - color: tint color
    - size: desired icon size (defaults to 20x20)
    """
    if size is None:
        size = QSize(20, 20)

    svg_path = os.path.join(resources_dir, f"{base_name}.svg")
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    painter = QPainter(pixmap)
    painter.setCompositionMode(getattr(QPainter, "CompositionMode_SourceIn"))
    painter.fillRect(pixmap.rect(), color)
    painter.end()

    return QIcon(pixmap)


