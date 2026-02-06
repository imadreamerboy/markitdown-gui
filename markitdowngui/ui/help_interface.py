from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import BodyLabel, PushButton, TitleLabel


class HelpInterface(QWidget):
    """Help page with app support actions."""

    check_updates_requested = Signal()
    show_shortcuts_requested = Signal()
    show_about_requested = Signal()

    def __init__(self, translate, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("HelpInterface")
        self.translate = translate
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(12)

        layout.addWidget(TitleLabel(self.translate("help_title")))
        layout.addWidget(BodyLabel(self.translate("help_description")))

        check_updates_btn = PushButton(self.translate("menu_check_updates"))
        check_updates_btn.clicked.connect(self.check_updates_requested.emit)
        layout.addWidget(check_updates_btn, 0, Qt.AlignmentFlag.AlignLeft)

        shortcuts_btn = PushButton(self.translate("menu_keyboard_shortcuts"))
        shortcuts_btn.clicked.connect(self.show_shortcuts_requested.emit)
        layout.addWidget(shortcuts_btn, 0, Qt.AlignmentFlag.AlignLeft)

        about_btn = PushButton(self.translate("about_menu"))
        about_btn.clicked.connect(self.show_about_requested.emit)
        layout.addWidget(about_btn, 0, Qt.AlignmentFlag.AlignLeft)

        releases_btn = PushButton(self.translate("help_open_releases"))
        releases_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://github.com/imadreamerboy/markitdown-gui/releases")
            )
        )
        layout.addWidget(releases_btn, 0, Qt.AlignmentFlag.AlignLeft)

        repo_btn = PushButton(self.translate("help_open_repository"))
        repo_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://github.com/imadreamerboy/markitdown-gui")
            )
        )
        layout.addWidget(repo_btn, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addStretch(1)

