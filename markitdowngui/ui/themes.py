from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

# Custom Dark and Light themes
DARK_THEME_COLORS = {
    "background": "#202020",
    "text": "#E0E0E0",
    "base": "#2B2B2B",
    "alternate_base": "#353535",
    "tooltip_base": "#2B2B2B",
    "tooltip_text": "#E0E0E0",
    "button": "#404040",
    "button_text": "#E0E0E0",
    "link": "#6DA3FF",
    "highlight": "#6DA3FF",
    "highlighted_text": "#FFFFFF",
    "placeholder_text": "#A0A0A0",
}

LIGHT_THEME_COLORS = {
    "background": "#F0F0F0",
    "text": "#1E1E1E",
    "base": "#FFFFFF",
    "alternate_base": "#F5F5F5",
    "tooltip_base": "#FFFFFF",
    "tooltip_text": "#1E1E1E",
    "button": "#E0E0E0",
    "button_text": "#1E1E1E",
    "link": "#0078D7",
    "highlight": "#0078D7",
    "highlighted_text": "#FFFFFF",
    "placeholder_text": "#606060",
}

# Solarized palette (classic) - kept for markdown CSS if needed, but not for main palette
SOLARIZED = {
    "base03": "#002b36", "base02": "#073642", "base01": "#586e75", "base00": "#657b83",
    "base0":  "#839496", "base1":  "#93a1a1", "base2":  "#eee8d5", "base3":  "#fdf6e3",
    "yellow": "#b58900", "orange": "#cb4b16", "red":    "#dc322f", "magenta":"#d33682",
    "violet": "#6c71c4", "blue":   "#268bd2", "cyan":   "#2aa198", "green":  "#859900",
}

def _qcolor(hex_str: str) -> QColor:
    c = QColor()
    c.setNamedColor(hex_str)
    return c

def apply_dark_theme(palette: QPalette) -> QPalette:
    """Apply a dark theme palette to the given QPalette."""
    p = QPalette(palette)  # copy in case a palette is passed in
    # Use ColorRole enum for PySide6 type checkers
    p.setColor(QPalette.ColorRole.Window,       _qcolor(DARK_THEME_COLORS["background"]))
    p.setColor(QPalette.ColorRole.WindowText,   _qcolor(DARK_THEME_COLORS["text"]))
    p.setColor(QPalette.ColorRole.Base,         _qcolor(DARK_THEME_COLORS["base"]))
    p.setColor(QPalette.ColorRole.AlternateBase,_qcolor(DARK_THEME_COLORS["alternate_base"]))
    p.setColor(QPalette.ColorRole.ToolTipBase,  _qcolor(DARK_THEME_COLORS["tooltip_base"]))
    p.setColor(QPalette.ColorRole.ToolTipText,  _qcolor(DARK_THEME_COLORS["tooltip_text"]))
    p.setColor(QPalette.ColorRole.Text,         _qcolor(DARK_THEME_COLORS["text"]))
    p.setColor(QPalette.ColorRole.Button,       _qcolor(DARK_THEME_COLORS["button"]))
    p.setColor(QPalette.ColorRole.ButtonText,   _qcolor(DARK_THEME_COLORS["button_text"]))
    p.setColor(QPalette.ColorRole.Link,         _qcolor(DARK_THEME_COLORS["link"]))
    p.setColor(QPalette.ColorRole.Highlight,    _qcolor(DARK_THEME_COLORS["highlight"]))
    p.setColor(QPalette.ColorRole.HighlightedText, _qcolor(DARK_THEME_COLORS["highlighted_text"]))
    p.setColor(QPalette.ColorRole.PlaceholderText, _qcolor(DARK_THEME_COLORS["placeholder_text"]))
    return p

def apply_light_theme() -> QPalette:
    """Return a light theme palette."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,       _qcolor(LIGHT_THEME_COLORS["background"]))
    p.setColor(QPalette.ColorRole.WindowText,   _qcolor(LIGHT_THEME_COLORS["text"]))
    p.setColor(QPalette.ColorRole.Base,         _qcolor(LIGHT_THEME_COLORS["base"]))
    p.setColor(QPalette.ColorRole.AlternateBase,_qcolor(LIGHT_THEME_COLORS["alternate_base"]))
    p.setColor(QPalette.ColorRole.ToolTipBase,  _qcolor(LIGHT_THEME_COLORS["tooltip_base"]))
    p.setColor(QPalette.ColorRole.ToolTipText,  _qcolor(LIGHT_THEME_COLORS["tooltip_text"]))
    p.setColor(QPalette.ColorRole.Text,         _qcolor(LIGHT_THEME_COLORS["text"]))
    p.setColor(QPalette.ColorRole.Button,       _qcolor(LIGHT_THEME_COLORS["button"]))
    p.setColor(QPalette.ColorRole.ButtonText,   _qcolor(LIGHT_THEME_COLORS["button_text"]))
    p.setColor(QPalette.ColorRole.Link,         _qcolor(LIGHT_THEME_COLORS["link"]))
    p.setColor(QPalette.ColorRole.Highlight,    _qcolor(LIGHT_THEME_COLORS["highlight"]))
    p.setColor(QPalette.ColorRole.HighlightedText, _qcolor(LIGHT_THEME_COLORS["highlighted_text"]))
    p.setColor(QPalette.ColorRole.PlaceholderText, _qcolor(LIGHT_THEME_COLORS["placeholder_text"]))
    return p

def markdown_css(is_dark: bool) -> str:
    """Return CSS string for Markdown preview styled in Solarized."""
    if is_dark:
        return (
            "QTextBrowser { background:%s; color:%s; }"
            "a { color:%s; }"
            "h1,h2,h3 { color:%s; }"
            "code, pre { background:%s; color:%s; border-radius:4px; padding:2px 4px; }"
        ) % (DARK_THEME_COLORS["background"], DARK_THEME_COLORS["text"], DARK_THEME_COLORS["link"],
             DARK_THEME_COLORS["highlighted_text"], DARK_THEME_COLORS["base"], DARK_THEME_COLORS["text"])
    else:
        return (
            "QTextBrowser { background:%s; color:%s; }"
            "a { color:%s; }"
            "h1,h2,h3 { color:%s; }"
            "code, pre { background:%s; color:%s; border-radius:4px; padding:2px 4px; }"
        ) % (LIGHT_THEME_COLORS["background"], LIGHT_THEME_COLORS["text"], LIGHT_THEME_COLORS["link"],
             LIGHT_THEME_COLORS["text"], LIGHT_THEME_COLORS["base"], LIGHT_THEME_COLORS["text"])
