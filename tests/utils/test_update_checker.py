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
    Test that the latest version is returned when a newer release is available.
    """
    # Mock the current version and GitHub API response
    monkeypatch.setattr(update_checker, 'get_current_version', lambda: 'v1.0.0')
    mock_response = MagicMock()
    mock_response.json.return_value = {'tag_name': 'v1.1.0'}
    mock_requests_get.return_value = mock_response

    latest_version = update_checker.check_for_updates()

    assert latest_version == 'v1.1.0'

def test_check_for_updates_up_to_date(mock_requests_get, monkeypatch):
    """
    Test that no dialog is shown when the application is up to date.
    """
    monkeypatch.setattr(update_checker, 'get_current_version', lambda: 'v1.1.0')
    mock_response = MagicMock()
    mock_response.json.return_value = {'tag_name': 'v1.1.0'}
    mock_requests_get.return_value = mock_response
    
    assert update_checker.check_for_updates() is None

def test_check_for_updates_request_exception(mock_requests_get, monkeypatch):
    """

    Test that no dialog is shown and no error is raised when a request exception occurs.
    """
    monkeypatch.setattr(update_checker, 'get_current_version', lambda: 'v1.0.0')
    mock_requests_get.side_effect = update_checker.requests.exceptions.RequestException
    
    # This should run without raising an exception
    assert update_checker.check_for_updates() is None
