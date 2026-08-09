from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from markitdowngui.core.conversion import ConversionOutcome
from markitdowngui.core.input_sources import is_web_url, source_display_name


@dataclass(frozen=True)
class QueueItem:
    source: str

    @property
    def name(self) -> str:
        return source_display_name(self.source)

    @property
    def kind(self) -> str:
        return "URL" if is_web_url(self.source) else "File"


@dataclass(frozen=True)
class ResultItem:
    source: str
    outcome: ConversionOutcome
    failed: bool = False

    @property
    def name(self) -> str:
        return source_display_name(self.source)

    @property
    def backend_label(self) -> str:
        labels = {
            "azure": "Azure OCR",
            "defuddle": "Defuddle",
            "glmocr": "GLM-OCR",
            "http-ocr": "HTTP OCR",
            "local": "Tesseract",
            "native": "Native",
            "anydoc": "anydoc",
            "docx-images": "DOCX assets",
            "pdf-images": "PDF assets",
            "pdf-inspector": "Fast PDF",
        }
        return labels.get(self.outcome.backend, self.outcome.backend or "Native")

    @property
    def backend_key(self) -> str:
        keys = {
            "azure": "conversion_backend_azure",
            "defuddle": "conversion_backend_defuddle",
            "glmocr": "conversion_backend_glmocr",
            "http-ocr": "conversion_backend_http_ocr",
            "local": "conversion_backend_local",
            "native": "conversion_backend_native",
            "anydoc": "conversion_backend_anydoc",
            "docx-images": "conversion_backend_docx_images",
            "pdf-images": "conversion_backend_pdf_images",
            "pdf-inspector": "conversion_backend_pdf_inspector",
        }
        return keys.get(self.outcome.backend, "")

    @property
    def word_count(self) -> int:
        return len(self.outcome.markdown.split())


class QueueModel(QAbstractListModel):
    SourceRole = Qt.ItemDataRole.UserRole + 1
    NameRole = SourceRole + 1
    KindRole = SourceRole + 2

    def __init__(self) -> None:
        super().__init__()
        self._items: list[QueueItem] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None

        item = self._items[index.row()]
        if role in {Qt.ItemDataRole.DisplayRole, self.NameRole}:
            return item.name
        if role == self.SourceRole:
            return item.source
        if role == self.KindRole:
            return item.kind
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.SourceRole: b"source",
            self.NameRole: b"name",
            self.KindRole: b"kind",
        }

    def add_sources(self, sources: list[str]) -> int:
        existing = {item.source for item in self._items}
        new_items: list[QueueItem] = []
        for source in sources:
            if source in existing:
                continue
            existing.add(source)
            new_items.append(QueueItem(source))
        if not new_items:
            return 0

        start = len(self._items)
        self.beginInsertRows(QModelIndex(), start, start + len(new_items) - 1)
        self._items.extend(new_items)
        self.endInsertRows()
        return len(new_items)

    def remove(self, row: int) -> None:
        if not 0 <= row < len(self._items):
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        self._items.pop(row)
        self.endRemoveRows()

    def clear(self) -> None:
        if not self._items:
            return
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def sources(self) -> list[str]:
        return [item.source for item in self._items]


class ResultModel(QAbstractListModel):
    SourceRole = Qt.ItemDataRole.UserRole + 1
    NameRole = SourceRole + 1
    BackendRole = SourceRole + 2
    FailedRole = SourceRole + 3
    WordCountRole = SourceRole + 4
    BackendKeyRole = SourceRole + 5

    def __init__(self) -> None:
        super().__init__()
        self._items: list[ResultItem] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None

        item = self._items[index.row()]
        if role in {Qt.ItemDataRole.DisplayRole, self.NameRole}:
            return item.name
        if role == self.SourceRole:
            return item.source
        if role == self.BackendRole:
            return item.backend_label
        if role == self.BackendKeyRole:
            return item.backend_key
        if role == self.FailedRole:
            return item.failed
        if role == self.WordCountRole:
            return item.word_count
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.SourceRole: b"source",
            self.NameRole: b"name",
            self.BackendRole: b"backend",
            self.FailedRole: b"failed",
            self.WordCountRole: b"wordCount",
            self.BackendKeyRole: b"backendKey",
        }

    def set_results(
        self,
        results: dict[str, ConversionOutcome],
        failed_sources: set[str] | None = None,
    ) -> None:
        failed_sources = failed_sources or set()
        self.beginResetModel()
        self._items = [
            ResultItem(source, outcome, source in failed_sources)
            for source, outcome in results.items()
        ]
        self.endResetModel()

    def add_result(
        self,
        source: str,
        outcome: ConversionOutcome,
        *,
        failed: bool = False,
    ) -> None:
        """Append or replace one completed conversion without resetting the model."""
        item = ResultItem(source, outcome, failed)
        for row, existing in enumerate(self._items):
            if existing.source != source:
                continue
            self._items[row] = item
            model_index = self.index(row, 0)
            self.dataChanged.emit(model_index, model_index)
            return

        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()

    def remove_sources(self, sources: set[str]) -> None:
        """Remove completed entries that are about to be retried."""
        if not sources:
            return
        remaining = [item for item in self._items if item.source not in sources]
        if len(remaining) == len(self._items):
            return
        self.beginResetModel()
        self._items = remaining
        self.endResetModel()

    def clear(self) -> None:
        if not self._items:
            return
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def item_at(self, row: int) -> ResultItem | None:
        if not 0 <= row < len(self._items):
            return None
        return self._items[row]

    def items(self) -> list[ResultItem]:
        return list(self._items)
