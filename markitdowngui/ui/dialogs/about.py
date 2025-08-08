from __future__ import annotations

import os
import sys
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextBrowser,
    QPushButton,
    QHBoxLayout,
)


class AboutDialog(QDialog):
    """About dialog with version and license info."""

    def __init__(self, translate, parent=None):
        super().__init__(parent)
        self.translate = translate
        self.setWindowTitle(self.translate("about_title") or "About")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        tb = QTextBrowser(self)
        tb.setOpenExternalLinks(True)

        lic_html = self._build_about_html()
        tb.setHtml(lic_html)
        layout.addWidget(tb, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton(self.translate("update_dialog_ok") or "OK", self)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        self.resize(720, 560)
        self.setMinimumSize(560, 420)

    def _build_about_html(self) -> str:
        from markitdowngui.__init__ import __version__ as APP_VERSION

        python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        try:
            from PySide6 import __version__ as pyside_ver
        except Exception:
            pyside_ver = "Unknown"

        try:
            qt_ver = os.environ.get("QT_API_VERSION", "")
        except Exception:
            qt_ver = ""

        license_text = self._read_license_text()

        lic_html = (
            "<h3>MarkItDown GUI</h3>"
            f"<p><b>Version:</b> {APP_VERSION}</p>"
            f"<p><b>Python:</b> {python_ver}<br>"
            f"<b>PySide6:</b> {pyside_ver}"
            f"{('<br><b>Qt:</b> ' + qt_ver) if qt_ver else ''}</p>"
            "<h4>License</h4>"
            f"<pre style='white-space:pre-wrap; font-family:monospace;'>{license_text if license_text else 'License file not found.'}</pre>"
            "<h4>Repository</h4>"
            "<p><a href='https://github.com/imadreamerboy/markitdown-gui'>github.com/imadreamerboy/markitdown-gui</a></p>"
        )
        return lic_html

    def _read_license_text(self) -> str:
        try:
            base_dir = getattr(sys, "_MEIPASS", None) or os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            license_path = os.path.join(base_dir, "LICENSE")
        except Exception:
            license_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "LICENSE")
            )

        try:
            with open(license_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "License file not found."


