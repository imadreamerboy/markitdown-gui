from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class PreviewWorker(QThread):
    """Background worker to generate text preview for a file.

    Emits result(request_id:int, text:str) or error(request_id:int, message:str).
    """

    result = Signal(int, str)
    error = Signal(int, str)

    def __init__(self, md, filepath: str, request_id: int):
        super().__init__()
        self._md = md
        self._filepath = filepath
        self._request_id = request_id

    def run(self):
        try:
            res = self._md.convert(self._filepath)
            text = res.text_content or ""
            self.result.emit(self._request_id, text)
        except Exception as e:
            self.error.emit(self._request_id, str(e))


