"""Main entry point for the MarkItDown GUI application."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from markitdowngui.ui.main_window import MainWindow
from markitdowngui.utils.logger import AppLogger
from markitdowngui.utils.update_checker import check_for_updates

def main():
    """Start the MarkItDown GUI application."""
    # Initialize logging
    AppLogger.initialize()
    
    # Check for updates
    check_for_updates()
    
    # Set High DPI scaling policy
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create and start application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
