from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from markitdowngui.ui.drop_widget import DropWidget


class FilePanel(QWidget):
    """Wraps DropWidget and exposes a small API for file list operations."""

    files_added = Signal(list)
    current_item_changed = Signal(object, object)

    def __init__(self, translate):
        super().__init__()
        self.translate = translate
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.drop = DropWidget(self.translate)
        # Re-emit QListWidget currentItemChanged via a slot to avoid signal-to-signal connect issues
        self.drop.listWidget.currentItemChanged.connect(self._on_current_item_changed)
        # Forward filesAdded explicitly via emit for consistency
        self.drop.filesAdded.connect(self.files_added.emit)
        layout.addWidget(self.drop)

    def _on_current_item_changed(self, current, previous) -> None:
        self.current_item_changed.emit(current, previous)

    def get_all_files(self) -> list[str]:
        return [self.drop.listWidget.item(i).text() for i in range(self.drop.listWidget.count())]

    def add_file(self, path: str) -> None:
        self.drop.listWidget.addItem(path)

    def add_files(self, paths: list[str]) -> None:
        for p in paths:
            self.add_file(p)

    def clear(self) -> None:
        self.drop.listWidget.clear()

    def current_item_text(self) -> str | None:
        item = self.drop.listWidget.currentItem()
        return item.text() if item else None

    def retranslate_ui(self, translate):
        self.translate = translate
        self.drop.retranslate_ui(self.translate)


