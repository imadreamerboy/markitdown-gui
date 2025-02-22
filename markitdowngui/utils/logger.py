import os
import logging
from datetime import datetime

class AppLogger:
    """Centralized logging configuration for the application."""
    
    @staticmethod
    def initialize():
        """Initialize the application logger."""
        log_dir = os.path.join(os.path.expanduser("~"), ".markitdown")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"markitdown_{datetime.now().strftime('%Y%m%d')}.log")
        
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