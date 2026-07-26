import os
from dataclasses import dataclass
from pathlib import Path
import stat
from secrets import token_hex
from datetime import datetime
from typing import List, Dict


@dataclass
class StagedMarkdownFile:
    """A fully-written Markdown file awaiting an atomic replacement."""

    destination: Path
    temporary_path: Path

    def commit(self) -> None:
        os.replace(self.temporary_path, self.destination)

    def abort(self) -> None:
        if self.temporary_path.exists():
            self.temporary_path.unlink()

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
        """Atomically replace a Markdown file after its full contents are written."""
        staged_file = FileManager.stage_markdown_file(filepath, content)
        try:
            staged_file.commit()
        finally:
            staged_file.abort()

    @staticmethod
    def stage_markdown_file(filepath: str, content: str) -> StagedMarkdownFile:
        """Write Markdown beside its destination without replacing the current file."""
        destination = Path(filepath)
        if destination.is_symlink():
            destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = _create_staged_file(destination)
        try:
            if (
                os.name != "nt"
                and destination.exists()
                and not destination.is_symlink()
            ):
                os.fchmod(descriptor, stat.S_IMODE(destination.stat().st_mode))
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                descriptor = -1
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            if descriptor != -1:
                os.close(descriptor)
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
        return StagedMarkdownFile(destination, Path(temporary_path))
    @staticmethod
    def update_recent_list(filepath: str, recent_list: List[str], max_items: int = 10) -> List[str]:
        """Update a list of recent files."""
        if filepath in recent_list:
            recent_list.remove(filepath)
        recent_list.insert(0, filepath)
        return recent_list[:max_items]


def _create_staged_file(destination: Path) -> tuple[int, str]:
    """Create an exclusive staged file using the user's normal file mode."""
    for _ in range(10):
        temporary_path = destination.parent / f".markitdowngui-{token_hex(16)}.tmp"
        try:
            descriptor = os.open(
                temporary_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o666,
            )
        except FileExistsError:
            continue
        return descriptor, str(temporary_path)
    raise FileExistsError(f"Could not create a temporary Markdown file for {destination}")
