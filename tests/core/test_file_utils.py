import os
import stat
import pytest
from markitdowngui.core import file_utils
from markitdowngui.core.file_utils import FileManager

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


def test_save_markdown_file_replaces_existing_content_without_temp_files(
    file_manager,
    tmp_path,
):
    output_path = tmp_path / "nested" / "report.md"
    output_path.parent.mkdir()
    output_path.write_text("old output", encoding="utf-8")

    file_manager.save_markdown_file(str(output_path), "new output")

    assert output_path.read_text(encoding="utf-8") == "new output"
    assert list(output_path.parent.glob(".report.md.*.tmp")) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions are not portable to Windows")
def test_save_markdown_file_preserves_existing_permissions(file_manager, tmp_path):
    output_path = tmp_path / "report.md"
    output_path.write_text("old output", encoding="utf-8")
    output_path.chmod(0o640)

    file_manager.save_markdown_file(str(output_path), "new output")

    assert stat.S_IMODE(output_path.stat().st_mode) == 0o640


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions are not portable to Windows")
def test_stage_markdown_file_closes_descriptor_when_permission_setup_fails(
    file_manager,
    tmp_path,
    monkeypatch,
):
    output_path = tmp_path / "report.md"
    output_path.write_text("old output", encoding="utf-8")
    closed_descriptors: list[int] = []
    original_close = os.close

    def fail_fchmod(_descriptor, _mode):
        raise OSError("permission setup failed")

    def track_close(descriptor):
        closed_descriptors.append(descriptor)
        original_close(descriptor)

    monkeypatch.setattr(file_utils.os, "fchmod", fail_fchmod)
    monkeypatch.setattr(file_utils.os, "close", track_close)

    with pytest.raises(OSError, match="permission setup failed"):
        file_manager.stage_markdown_file(str(output_path), "new output")

    assert len(closed_descriptors) == 1
    assert list(tmp_path.glob(".report.md.*.tmp")) == []
