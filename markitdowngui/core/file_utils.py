import os
from datetime import datetime
from typing import List, Dict

class FileManager:
    """Handles file operations and tracking of recent files."""
    
    SUPPORTED_TYPES = {
        "Word Documents": "*.docx",
        "PowerPoint": "*.pptx",
        "Excel": "*.xlsx",
        "PDF": "*.pdf",
        "Text": "*.txt",
        "All Files": "*.*"
    }

    @staticmethod
    def get_backup_dir() -> str:
        """Get the backup directory path, creating it if it doesn't exist."""
        backup_dir = os.path.join(os.path.expanduser("~"), ".markitdown", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @staticmethod
    def create_backup_filename() -> str:
        """Generate a timestamped backup filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"autosave_{timestamp}.md"

    @staticmethod
    def save_markdown_file(filepath: str, content: str) -> None:
        """Save markdown content to a file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def update_recent_list(filepath: str, recent_list: List[str], max_items: int = 10) -> List[str]:
        """Update a list of recent files."""
        if filepath in recent_list:
            recent_list.remove(filepath)
        recent_list.insert(0, filepath)
        return recent_list[:max_items]