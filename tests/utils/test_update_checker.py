import pytest
from unittest.mock import MagicMock, patch
from packaging.version import parse

from markitdowngui.utils import update_checker

@pytest.fixture
def mock_requests_get(monkeypatch):
    """Fixture to mock requests.get."""
    mock_get = MagicMock()
    monkeypatch.setattr(update_checker.requests, 'get', mock_get)
    return mock_get

def test_check_for_updates_new_version_available(mock_requests_get, monkeypatch):
    """
    Test that the update dialog is shown when a newer version is available on GitHub.
    """
    # Mock the current version and GitHub API response
    monkeypatch.setattr(update_checker, 'get_current_version', lambda: 'v1.0.0')
    mock_response = MagicMock()
    mock_response.json.return_value = {'tag_name': 'v1.1.0'}
    mock_requests_get.return_value = mock_response

    # Mock the UI dialog to prevent it from actually running
    mock_dialog = MagicMock()
    monkeypatch.setattr(update_checker, 'UpdateDialog', mock_dialog)
    
    # Run the checker
    update_checker.check_for_updates()

    # Assert that the dialog was created and shown
    mock_dialog.assert_called_once()
    mock_dialog.return_value.exec.assert_called_once()

def test_check_for_updates_up_to_date(mock_requests_get, monkeypatch):
    """
    Test that no dialog is shown when the application is up to date.
    """
    monkeypatch.setattr(update_checker, 'get_current_version', lambda: 'v1.1.0')
    mock_response = MagicMock()
    mock_response.json.return_value = {'tag_name': 'v1.1.0'}
    mock_requests_get.return_value = mock_response
    
    mock_dialog = MagicMock()
    monkeypatch.setattr(update_checker, 'UpdateDialog', mock_dialog)

    update_checker.check_for_updates()

    mock_dialog.assert_not_called()

def test_check_for_updates_request_exception(mock_requests_get, monkeypatch):
    """

    Test that no dialog is shown and no error is raised when a request exception occurs.
    """
    monkeypatch.setattr(update_checker, 'get_current_version', lambda: 'v1.0.0')
    mock_requests_get.side_effect = update_checker.requests.exceptions.RequestException
    
    mock_dialog = MagicMock()
    monkeypatch.setattr(update_checker, 'UpdateDialog', mock_dialog)

    # This should run without raising an exception
    update_checker.check_for_updates()
    
    mock_dialog.assert_not_called() 