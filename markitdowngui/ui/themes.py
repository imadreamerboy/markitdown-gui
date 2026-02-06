from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from qfluentwidgets import Theme, isDarkTheme, setTheme, setThemeColor

ACCENT_COLOR = "#0E7490"


def apply_app_theme(theme_mode: str) -> bool:
    """Apply app theme and return whether dark mode is active."""
    normalized = (theme_mode or "").strip().lower()
    if normalized == "dark":
        setTheme(Theme.DARK)
    elif normalized == "system":
        setTheme(Theme.AUTO)
    else:
        setTheme(Theme.LIGHT)

    setThemeColor(ACCENT_COLOR)
    return bool(isDarkTheme())


def build_app_stylesheet(is_dark: bool) -> str:
    """Return global app QSS for cleaner card and section visuals."""
    if is_dark:
        panel_bg_a = "#1b2129"
        panel_bg_b = "#202834"
        card_bg = "#262f3a"
        card_bg_alt = "#222a35"
        border = "#3a4656"
        text = "#eaf0f7"
        subtext = "#bdc9d8"
        input_bg = "#1d232b"
        hover = "#334456"
        title = "#d9e7f8"
    else:
        panel_bg_a = "#f7f9fd"
        panel_bg_b = "#eef3f9"
        card_bg = "#ffffff"
        card_bg_alt = "#fbfdff"
        border = "#dfe6f0"
        text = "#1f2937"
        subtext = "#5d6c83"
        input_bg = "#fcfdff"
        hover = "#e9f2ff"
        title = "#2f3d55"

    return f"""
QWidget#SettingsInterface, QWidget#HelpInterface, QWidget#HomeInterface {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {panel_bg_a}, stop:1 {panel_bg_b});
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
    padding: 12px 12px 12px 12px;
    font-weight: 600;
    color: {title};
    background: {card_bg_alt};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {subtext};
    background: transparent;
}}
BodyLabel, CaptionLabel, TitleLabel, SubtitleLabel {{
    color: {text};
}}
QTextEdit, QTextBrowser, QListWidget, QLineEdit {{
    background: {input_bg};
    border: 1px solid {border};
    border-radius: 8px;
    color: {text};
}}
QTextEdit:focus, QTextBrowser:focus, QListWidget:focus, QLineEdit:focus {{
    border: 1px solid {ACCENT_COLOR};
}}
QListWidget::item {{
    padding: 6px 8px;
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
        bg = "#1d232b"
        text = "#eaf0f7"
        link = "#6cd8ff"
        code_bg = "#2a3340"
        border = "#445365"
        muted = "#b7c4d3"
    else:
        bg = "#ffffff"
        text = "#17212e"
        link = "#0b63ce"
        code_bg = "#f0f5fa"
        border = "#d7e0ea"
        muted = "#52657c"

    return (
        "body {"
        f"background:{bg}; color:{text}; font-size:13px; line-height:1.5; "
        "font-family:'Segoe UI', 'Noto Sans', sans-serif; margin:8px;"
        "}"
        f"a {{ color:{link}; }}"
        "h1,h2,h3,h4 { margin-top: 14px; margin-bottom: 8px; }"
        f"pre, code {{ background:{code_bg}; border-radius:6px; }}"
        "pre { padding:10px; overflow:auto; border:1px solid transparent; }"
        "code { padding:1px 4px; }"
        f"blockquote {{ border-left:4px solid {border}; margin:8px 0; padding:4px 10px; color:{muted}; }}"
        f"table, th, td {{ border: 1px solid {border}; border-collapse: collapse; }}"
        "th, td { padding: 6px 8px; }"
    )


def apply_dark_theme(palette: QPalette | None = None) -> QPalette:
    """Backward-compatible helper."""
    setTheme(Theme.DARK)
    setThemeColor(ACCENT_COLOR)
    return palette or QPalette()


def apply_light_theme() -> QPalette:
    """Backward-compatible helper."""
    setTheme(Theme.LIGHT)
    setThemeColor(ACCENT_COLOR)
    return QPalette()


def markdown_css(is_dark: bool) -> str:
    """Backward-compatible alias for markdown style retrieval."""
    return markdown_html_css(is_dark)


def qcolor(hex_color: str) -> QColor:
    return QColor(hex_color)
