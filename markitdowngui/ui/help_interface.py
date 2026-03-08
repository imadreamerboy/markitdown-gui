from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    FluentIcon as FIF,
    HyperlinkButton,
    PushButton,
    SimpleExpandGroupSettingCard,
    TitleLabel,
)


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
        check_updates_btn.setIcon(FIF.SYNC)
        check_updates_btn.clicked.connect(self.check_updates_requested.emit)
        layout.addWidget(check_updates_btn, 0, Qt.AlignmentFlag.AlignLeft)

        shortcuts_btn = PushButton(self.translate("menu_keyboard_shortcuts"))
        shortcuts_btn.setIcon(FIF.COMMAND_PROMPT)
        shortcuts_btn.clicked.connect(self.show_shortcuts_requested.emit)
        layout.addWidget(shortcuts_btn, 0, Qt.AlignmentFlag.AlignLeft)

        about_btn = PushButton(self.translate("about_menu"))
        about_btn.setIcon(FIF.INFO)
        about_btn.clicked.connect(self.show_about_requested.emit)
        layout.addWidget(about_btn, 0, Qt.AlignmentFlag.AlignLeft)

        releases_btn = HyperlinkButton()
        releases_btn.setText(self.translate("help_open_releases"))
        releases_btn.setIcon(FIF.LINK)
        releases_btn.setUrl(QUrl("https://github.com/imadreamerboy/markitdown-gui/releases"))
        layout.addWidget(releases_btn, 0, Qt.AlignmentFlag.AlignLeft)

        repo_btn = HyperlinkButton()
        repo_btn.setText(self.translate("help_open_repository"))
        repo_btn.setIcon(FIF.GITHUB)
        repo_btn.setUrl(QUrl("https://github.com/imadreamerboy/markitdown-gui"))
        layout.addWidget(repo_btn, 0, Qt.AlignmentFlag.AlignLeft)

        azure_pricing_btn = HyperlinkButton()
        azure_pricing_btn.setText(self.translate("help_open_azure_ocr_pricing"))
        azure_pricing_btn.setIcon(FIF.LINK)
        azure_pricing_btn.setUrl(
            QUrl(
                "https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing"
            )
        )
        layout.addWidget(azure_pricing_btn, 0, Qt.AlignmentFlag.AlignLeft)

        tesseract_btn = HyperlinkButton()
        tesseract_btn.setText(self.translate("help_open_tesseract"))
        tesseract_btn.setIcon(FIF.LINK)
        tesseract_btn.setUrl(QUrl("https://github.com/tesseract-ocr/tesseract"))
        layout.addWidget(tesseract_btn, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(TitleLabel(self.translate("help_faq_title")))

        faq_card = SimpleExpandGroupSettingCard(
            FIF.HELP,
            self.translate("help_faq_title"),
            self.translate("help_description"),
            self,
        )
        self._add_faq_entry(
            faq_card,
            FIF.FOLDER,
            "help_faq_tesseract_windows_question",
            "help_faq_tesseract_windows_answer",
        )
        self._add_faq_entry(
            faq_card,
            FIF.FOLDER,
            "help_faq_tesseract_macos_question",
            "help_faq_tesseract_macos_answer",
        )
        self._add_faq_entry(
            faq_card,
            FIF.FOLDER,
            "help_faq_tesseract_linux_question",
            "help_faq_tesseract_linux_answer",
        )
        self._add_faq_entry(
            faq_card,
            FIF.SYNC,
            "help_faq_azure_question",
            "help_faq_azure_answer",
        )
        self._add_faq_entry(
            faq_card,
            FIF.INFO,
            "help_faq_local_fallback_question",
            "help_faq_local_fallback_answer",
        )
        layout.addWidget(faq_card)

        layout.addStretch(1)

    def _add_faq_entry(
        self,
        card: SimpleExpandGroupSettingCard,
        icon,
        question_key: str,
        answer_key: str,
    ) -> None:
        card.addGroup(
            icon,
            self.translate(question_key),
            self.translate(answer_key),
            QWidget(card),
        )
