import os
import pytest
from markitdowngui.core.file_utils import FileManager
from markitdowngui.core.markdown_assets import (
    MarkdownAssetReference,
    SavedMarkdownAsset,
    build_markdown_with_asset_references,
)

@pytest.fixture
def file_manager(tmp_path, monkeypatch):
    """Fixture to create a FileManager instance with a temporary backup directory."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    
    # Mock get_backup_dir to return the temporary directory, accepting and ignoring any args
    monkeypatch.setattr(FileManager, "get_backup_dir", lambda *args, **kwargs: str(backup_dir))
    return FileManager()

@pytest.fixture
def create_test_files(tmp_path):
    """Fixture to create a set of temporary files for testing."""
    files = []
    for i in range(12):
        file_path = tmp_path / f"file{i}.txt"
        file_path.touch()
        files.append(str(file_path))
    return files

def test_update_recent_list(file_manager, create_test_files):
    """Test that the recent files list is correctly updated."""
    recent_files = create_test_files[:2]
    new_file = create_test_files[2]
    updated_list = file_manager.update_recent_list(new_file, recent_files.copy())
    
    assert len(updated_list) == 3
    assert updated_list[0] == new_file
    assert updated_list[1] == recent_files[0]

def test_update_recent_list_with_existing_file(file_manager, create_test_files):
    """Test that adding an existing file moves it to the top."""
    recent_files = create_test_files[:2]
    new_file = recent_files[1]
    updated_list = file_manager.update_recent_list(new_file, recent_files.copy())
    
    assert len(updated_list) == 2
    assert updated_list[0] == new_file
    assert updated_list[1] == recent_files[0]

def test_update_recent_list_limit(file_manager, create_test_files):
    """Test that the recent files list does not exceed the limit."""
    recent_files = create_test_files[:10]
    new_file = create_test_files[10]
    updated_list = file_manager.update_recent_list(new_file, recent_files.copy())
    
    assert len(updated_list) == 10
    assert updated_list[0] == new_file
    assert recent_files[-1] not in updated_list

def test_create_backup_filename(file_manager):
    """Test the backup filename format."""
    filename = file_manager.create_backup_filename()
    assert filename.startswith("autosave_")
    assert filename.endswith(".md")

def test_save_and_get_backup_dir(file_manager):
    """Test saving a markdown file and verify it's in the backup directory."""
    content = "# Test Content"
    backup_filename = file_manager.create_backup_filename()
    backup_path = os.path.join(file_manager.get_backup_dir(), backup_filename)
    
    file_manager.save_markdown_file(backup_path, content)
    
    assert os.path.exists(backup_path)
    with open(backup_path, "r", encoding="utf-8") as f:
        assert f.read() == content 


def test_save_markdown_assets(file_manager, tmp_path):
    source_one = tmp_path / "source-one.png"
    source_one.write_bytes(b"png-bytes")
    source_two = tmp_path / "source-two.png"
    source_two.write_bytes(b"more-bytes")
    assets = [
        SavedMarkdownAsset(relative_path="doc_assets/image-1.png", source_path=str(source_one)),
        SavedMarkdownAsset(relative_path="doc_assets/nested/image-2.png", source_path=str(source_two)),
    ]

    file_manager.save_markdown_assets(str(tmp_path), assets)

    assert (tmp_path / "doc_assets" / "image-1.png").read_bytes() == b"png-bytes"
    assert (tmp_path / "doc_assets" / "nested" / "image-2.png").read_bytes() == b"more-bytes"


def test_build_markdown_with_asset_references_groups_images_by_page():
    markdown = "# Report"
    references = [
        MarkdownAssetReference(
            relative_path="report_assets/page-001-image-01.png",
            page_number=1,
            alt_text="Page 1 image 1",
        ),
        MarkdownAssetReference(
            relative_path="report_assets/page-002-image-01.png",
            page_number=2,
            alt_text="Page 2 image 1",
        ),
    ]

    rendered = build_markdown_with_asset_references(markdown, references)

    assert rendered.startswith("# Report")
    assert "## Extracted Images" in rendered
    assert "### Page 1" in rendered
    assert "### Page 2" in rendered
    assert "![Page 1 image 1](report_assets/page-001-image-01.png)" in rendered
    assert "![Page 2 image 1](report_assets/page-002-image-01.png)" in rendered
