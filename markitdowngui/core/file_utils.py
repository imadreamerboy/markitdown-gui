import os
from datetime import datetime
import shutil
from typing import List, Dict

from markitdowngui.core.markdown_assets import SavedMarkdownAsset

class FileManager:
    """Handles file operations and tracking of recent files."""
    
    SUPPORTED_TYPES = {
        "Auto Detect": "*.*",
        "Word Documents": "*.docx",
        "PowerPoint": "*.pptx",
        "Excel": "*.xlsx *.xls",
        "PDF": "*.pdf",
        "EPUB": "*.epub",
        "HTML": "*.html *.htm",
        "Text": "*.txt *.md *.csv *.json *.xml",
        "Images": "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp",
        "Archives": "*.zip",
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
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def save_markdown_assets(
        base_dir: str,
        assets: list[SavedMarkdownAsset],
    ) -> None:
        """Save markdown companion assets relative to a base directory."""
        for asset in assets:
            output_path = os.path.join(base_dir, *asset.relative_path.split("/"))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(asset.source_path, output_path)

    @staticmethod
    def update_recent_list(filepath: str, recent_list: List[str], max_items: int = 10) -> List[str]:
        """Update a list of recent files."""
        if filepath in recent_list:
            recent_list.remove(filepath)
        recent_list.insert(0, filepath)
        return recent_list[:max_items]
