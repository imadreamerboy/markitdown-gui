from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QResizeEvent, QShowEvent
from PySide6.QtWidgets import QFrame, QScrollArea, QWidget, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    ExpandSettingCard,
    FluentIcon as FIF,
    HyperlinkButton,
    PushButton,
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
        self._faq_cards: list[ExpandSettingCard] = []
        self._faq_layout_update_pending = False
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("HelpScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root_layout.addWidget(self.scroll_area)

        self.content = QWidget(self.scroll_area)
        self.content.setObjectName("HelpContent")
        self.scroll_area.setWidget(self.content)

        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(12)

        layout.addWidget(TitleLabel(self.translate("help_title")))
        self.help_description_label = BodyLabel(self.translate("help_description"))
        self.help_description_label.setWordWrap(True)
        layout.addWidget(self.help_description_label)

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

        defuddle_docs_btn = HyperlinkButton()
        defuddle_docs_btn.setText(self.translate("help_open_defuddle_docs"))
        defuddle_docs_btn.setIcon(FIF.LINK)
        defuddle_docs_btn.setUrl(QUrl("https://defuddle.md/docs"))
        layout.addWidget(defuddle_docs_btn, 0, Qt.AlignmentFlag.AlignLeft)

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

        layout.addWidget(
            self._build_faq_card(
                FIF.GLOBE,
                "help_faq_defuddle_question",
                "help_faq_defuddle_answer",
            )
        )
        layout.addWidget(
            self._build_faq_card(
                FIF.GLOBE,
                "help_faq_defuddle_limits_question",
                "help_faq_defuddle_limits_answer",
            )
        )
        layout.addWidget(
            self._build_faq_card(
                FIF.FOLDER,
                "help_faq_tesseract_windows_question",
                "help_faq_tesseract_windows_answer",
            )
        )
        layout.addWidget(
            self._build_faq_card(
                FIF.FOLDER,
                "help_faq_tesseract_macos_question",
                "help_faq_tesseract_macos_answer",
            )
        )
        layout.addWidget(
            self._build_faq_card(
                FIF.FOLDER,
                "help_faq_tesseract_linux_question",
                "help_faq_tesseract_linux_answer",
            )
        )
        layout.addWidget(
            self._build_faq_card(
                FIF.SYNC,
                "help_faq_azure_question",
                "help_faq_azure_answer",
            )
        )
        layout.addWidget(
            self._build_faq_card(
                FIF.INFO,
                "help_faq_local_fallback_question",
                "help_faq_local_fallback_answer",
            )
        )

        layout.addStretch(1)

    def _build_faq_card(
        self,
        icon,
        question_key: str,
        answer_key: str,
    ) -> ExpandSettingCard:
        card = ExpandSettingCard(icon, self.translate(question_key), parent=self)
        answer = BodyLabel(self.translate(answer_key), card.view)
        answer.setWordWrap(True)
        answer.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        answer.setStyleSheet("font-size: 14px; padding: 6px 0 10px 0;")
        card.viewLayout.setContentsMargins(20, 12, 20, 18)
        card.viewLayout.addWidget(answer)
        card._adjustViewSize()
        card.expandAni.finished.connect(lambda c=card: self._finalize_faq_card_height(c))
        self._faq_cards.append(card)
        return card

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._schedule_faq_layout_update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._schedule_faq_layout_update()

    def _schedule_faq_layout_update(self) -> None:
        if self._faq_layout_update_pending:
            return
        self._faq_layout_update_pending = True
        QTimer.singleShot(0, self._update_faq_card_sizes)

    def _update_faq_card_sizes(self) -> None:
        self._faq_layout_update_pending = False
        for card in self._faq_cards:
            card._adjustViewSize()
            card.adjustSize()
            self._finalize_faq_card_height(card)
        if hasattr(self, "content"):
            self.content.adjustSize()

    def _finalize_faq_card_height(self, card: ExpandSettingCard) -> None:
        if card.isExpand:
            return
        card.verticalScrollBar().setValue(card.verticalScrollBar().maximum())
        card.setFixedHeight(card.card.height())
