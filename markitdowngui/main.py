"""Main entry point for the MarkItDown GUI application."""

import sys

from markitdowngui.ui_qml.app import main as run_qml_app


def main() -> None:
    """Start the MarkItDown GUI application."""
    sys.exit(run_qml_app())

if __name__ == '__main__':
    main()
