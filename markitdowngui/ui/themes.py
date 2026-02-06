from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from qfluentwidgets import Theme, isDarkTheme, setTheme, setThemeColor

SOLARIZED_ACCENT = "#2AA198"
NORD_ACCENT = "#88C0D0"
ACCENT_COLOR = SOLARIZED_ACCENT


def apply_app_theme(theme_mode: str) -> bool:
    """Apply app theme and return whether dark mode is active."""
    normalized = (theme_mode or "").strip().lower()
    if normalized == "dark":
        setTheme(Theme.DARK)
    elif normalized == "system":
        setTheme(Theme.AUTO)
    else:
        setTheme(Theme.LIGHT)

    dark_mode = bool(isDarkTheme())
    setThemeColor(NORD_ACCENT if dark_mode else SOLARIZED_ACCENT)
    return dark_mode


def build_app_stylesheet(is_dark: bool) -> str:
    """Return global app QSS for cleaner card and section visuals."""
    if is_dark:
        panel_bg_a = "#2E3440"
        panel_bg_b = "#3B4252"
        window_bg = "#2B313D"
        stack_bg = "#313947"
        nav_bg = "#2E3440"
        nav_border = "#4C566A"
        card_bg = "#3B4252"
        card_bg_alt = "#434C5E"
        border = "#4C566A"
        text = "#ECEFF4"
        subtext = "#D8DEE9"
        input_bg = "#2F3644"
        hover = "#4C566A"
        title = "#ECEFF4"
        accent = NORD_ACCENT
    else:
        panel_bg_a = "#FDF6E3"
        panel_bg_b = "#F7F0DB"
        window_bg = "#F6EFD8"
        stack_bg = "#FAF4E2"
        nav_bg = "#F2EAD3"
        nav_border = "#D9CCA8"
        card_bg = "#FFFDF7"
        card_bg_alt = "#FFF9EB"
        border = "#D9CCA8"
        text = "#4F646A"
        subtext = "#61767C"
        input_bg = "#FFFDF6"
        hover = "#EFE5CB"
        title = "#2B3F45"
        accent = SOLARIZED_ACCENT

    return f"""
FluentWindowBase {{
    background-color: {window_bg};
}}

FluentTitleBar, SplitTitleBar {{
    background-color: transparent;
}}

FluentTitleBar>QLabel#titleLabel, SplitTitleBar>QLabel#titleLabel {{
    color: {title};
    font-size: 14px;
    font-weight: 600;
}}

StackedWidget {{
    background-color: {stack_bg};
    border: 1px solid {border};
    border-right: none;
    border-bottom: none;
    border-top-left-radius: 12px;
}}

NavigationInterface {{
    background-color: {nav_bg};
}}

NavigationPanel[menu=false] {{
    background-color: {nav_bg};
    border: none;
    border-right: 1px solid {nav_border};
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
}}

NavigationPanel[menu=true] {{
    background-color: {nav_bg};
    border: 1px solid {nav_border};
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}}

NavigationPanel QScrollArea, NavigationPanel #scrollWidget {{
    border: none;
    background: transparent;
}}

QWidget#SettingsInterface, QWidget#HelpInterface, QWidget#HomeInterface {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {panel_bg_a}, stop:1 {panel_bg_b});
    font-size: 14px;
}}

CardWidget, ElevatedCardWidget, SimpleCardWidget {{
    background: {card_bg};
    border: 1px solid {border};
    border-radius: 14px;
}}

QGroupBox {{
    border: 1px solid {border};
    border-radius: 12px;
    margin-top: 16px;
    padding: 14px 14px 14px 14px;
    font-size: 16px;
    font-weight: 700;
    color: {title};
    background: {card_bg_alt};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: {title};
    font-size: 16px;
    font-weight: 700;
    background: transparent;
}}

BodyLabel, CaptionLabel, TitleLabel, SubtitleLabel {{
    color: {text};
}}

TitleLabel {{
    font-size: 30px;
    font-weight: 800;
    color: {title};
    letter-spacing: 0.2px;
}}

SubtitleLabel {{
    font-size: 18px;
    font-weight: 700;
    color: {title};
}}

BodyLabel {{
    font-size: 15px;
    font-weight: 500;
}}

CaptionLabel {{
    font-size: 13px;
    color: {subtext};
}}

QPushButton, PrimaryPushButton, PillPushButton, HyperlinkButton, QRadioButton, QCheckBox {{
    font-size: 14px;
    font-weight: 500;
}}

QComboBox, ComboBox, SpinBox, QAbstractSpinBox, QLineEdit {{
    font-size: 15px;
}}

QTextEdit, QTextBrowser, QListWidget, QLineEdit {{
    background: {input_bg};
    border: 1px solid {border};
    border-radius: 8px;
    color: {text};
    font-size: 15px;
}}

QTextEdit:focus, QTextBrowser:focus, QListWidget:focus, QLineEdit:focus {{
    border: 1px solid {accent};
}}

QListWidget::item {{
    padding: 8px 10px;
}}

QListWidget::item:selected {{
    background: {hover};
}}

QSplitter::handle {{
    background: {border};
    margin: 2px;
    border-radius: 2px;
}}

QSplitter::handle:hover {{
    background: {subtext};
}}
"""


def markdown_html_css(is_dark: bool) -> str:
    """Return CSS for rendered markdown HTML."""
    if is_dark:
        bg = "#2F3644"
        text = "#ECEFF4"
        link = "#88C0D0"
        code_bg = "#3B4252"
        border = "#4C566A"
        muted = "#D8DEE9"
    else:
        bg = "#FFFDF6"
        text = "#4F646A"
        link = "#2AA198"
        code_bg = "#FFF9EB"
        border = "#D9CCA8"
        muted = "#61767C"

    return (
        "body {"
        f"background:{bg}; color:{text}; font-size:15px; line-height:1.65; "
        "font-family:'Segoe UI', 'Noto Sans', sans-serif; margin:8px;"
        "}"
        f"a {{ color:{link}; }}"
        "h1,h2,h3,h4 { margin-top: 18px; margin-bottom: 10px; font-weight: 800; color: inherit; }"
        "h1 { font-size: 1.65em; }"
        "h2 { font-size: 1.40em; }"
        "h3 { font-size: 1.20em; }"
        "h4 { font-size: 1.05em; }"
        f"pre, code {{ background:{code_bg}; border-radius:6px; }}"
        f"pre {{ padding:10px; overflow:auto; border:1px solid {border}; }}"
        "code { padding:1px 4px; }"
        f"blockquote {{ border-left:4px solid {border}; margin:8px 0; padding:4px 10px; color:{muted}; }}"
        f"table, th, td {{ border: 1px solid {border}; border-collapse: collapse; }}"
        "th, td { padding: 6px 8px; }"
        "th { font-weight: 700; }"
    )


def apply_dark_theme(palette: QPalette | None = None) -> QPalette:
    """Backward-compatible helper."""
    setTheme(Theme.DARK)
    setThemeColor(NORD_ACCENT)
    return palette or QPalette()


def apply_light_theme() -> QPalette:
    """Backward-compatible helper."""
    setTheme(Theme.LIGHT)
    setThemeColor(SOLARIZED_ACCENT)
    return QPalette()


def markdown_css(is_dark: bool) -> str:
    """Backward-compatible alias for markdown style retrieval."""
    return markdown_html_css(is_dark)


def qcolor(hex_color: str) -> QColor:
    return QColor(hex_color)
