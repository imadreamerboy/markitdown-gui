import os
import logging
from datetime import datetime
from pathlib import Path

class AppLogger:
    """Centralized logging configuration for the application."""

    _log_file: str = ""

    @staticmethod
    def log_dir() -> str:
        """Return the application log directory."""
        return os.path.join(os.path.expanduser("~"), ".markitdown")

    @staticmethod
    def current_log_file() -> str:
        """Return the current process log file path."""
        return AppLogger._log_file
    
    @staticmethod
    def initialize():
        """Initialize the application logger."""
        log_dir = AppLogger.log_dir()
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"markitdown_{datetime.now().strftime('%Y%m%d')}.log")
        AppLogger._log_file = log_file
        
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    @staticmethod
    def error(message: str, file: str = None):
        """Log an error message."""
        if file:
            logging.error(f"File: {file} - {message}")
        else:
            logging.error(message)
    
    @staticmethod
    def info(message: str):
        """Log an info message."""
        logging.info(message)
    
    @staticmethod
    def warning(message: str):
        """Log a warning message."""
        logging.warning(message)
    
    @staticmethod
    def debug(message: str):
        """Log a debug message."""
        logging.debug(message)


def build_diagnostic_report() -> str:
    """Build a compact diagnostic report suitable for support requests."""
    import platform
    import sys

    from markitdowngui import __version__

    log_file = AppLogger.current_log_file()
    log_dir = AppLogger.log_dir()
    return "\n".join(
        [
            "MarkItDown GUI diagnostics",
            f"Version: {__version__}",
            f"Python: {sys.version.split()[0]}",
            f"Platform: {platform.platform()}",
            f"Executable: {sys.executable}",
            f"Frozen: {getattr(sys, 'frozen', False)}",
            f"Log directory: {Path(log_dir)}",
            f"Current log: {Path(log_file) if log_file else 'not initialised'}",
        ]
    )
