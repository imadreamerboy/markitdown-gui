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
    mock_response.json.return_value = {
        'tag_name': 'v1.1.0',
        'html_url': 'https://github.com/example/releases/tag/v1.1.0',
        'assets': [
            {
                'name': 'MarkItDown-Windows.exe',
                'browser_download_url': 'https://example.com/MarkItDown-Windows.exe',
                'size': 123,
            }
        ],
    }
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


def test_parse_release_info_extracts_download_assets():
    release = update_checker.parse_release_info(
        {
            "tag_name": "v2.0.0",
            "html_url": "https://github.com/example/releases/tag/v2.0.0",
            "body": "Fixes and installer changes.",
            "assets": [
                {
                    "name": "MarkItDown-Windows.exe",
                    "browser_download_url": "https://example.com/windows.exe",
                    "size": 42,
                },
                {"name": "broken"},
            ],
        }
    )

    assert release == update_checker.ReleaseInfo(
        tag_name="v2.0.0",
        html_url="https://github.com/example/releases/tag/v2.0.0",
        body="Fixes and installer changes.",
        assets=(
            update_checker.ReleaseAsset(
                name="MarkItDown-Windows.exe",
                browser_download_url="https://example.com/windows.exe",
                size=42,
            ),
        ),
    )


def test_parse_release_info_merges_manifest_metadata():
    release = update_checker.parse_release_info(
        {
            "tag_name": "v2.0.0",
            "assets": [
                {
                    "name": "MarkItDown-Windows-2.0.0.zip",
                    "browser_download_url": "https://example.com/windows.zip",
                    "size": 1,
                },
            ],
        },
        {
            "MarkItDown-Windows-2.0.0.zip": {
                "platform": "Windows",
                "size": 42,
                "sha256": "abc123",
            }
        },
    )

    assert release.assets == (
        update_checker.ReleaseAsset(
            name="MarkItDown-Windows-2.0.0.zip",
            browser_download_url="https://example.com/windows.zip",
            size=42,
            platform="Windows",
            sha256="abc123",
        ),
    )


def test_get_latest_release_info_uses_base_release_when_manifest_fetch_fails(mock_requests_get):
    release_response = MagicMock()
    release_response.json.return_value = {
        "tag_name": "v2.0.0",
        "html_url": "https://github.com/example/releases/tag/v2.0.0",
        "assets": [
            {
                "name": "MarkItDown-Windows-2.0.0.zip",
                "browser_download_url": "https://example.com/windows.zip",
                "size": 42,
            },
            {
                "name": "markitdown-release-manifest.json",
                "browser_download_url": "https://example.com/manifest.json",
            },
        ],
    }
    mock_requests_get.side_effect = [
        release_response,
        update_checker.requests.exceptions.RequestException("manifest unavailable"),
    ]

    release = update_checker.get_latest_release_info(timeout=1)

    assert release is not None
    assert release.tag_name == "v2.0.0"
    assert release.assets[0].name == "MarkItDown-Windows-2.0.0.zip"


def test_select_release_asset_prefers_current_platform():
    release = update_checker.ReleaseInfo(
        tag_name="v2.0.0",
        html_url="",
        assets=(
            update_checker.ReleaseAsset(
                name="MarkItDown-Linux-2.0.0.zip",
                browser_download_url="https://example.com/linux.zip",
                platform="Linux",
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-Windows-2.0.0.zip",
                browser_download_url="https://example.com/windows.zip",
                platform="Windows",
            ),
            update_checker.ReleaseAsset(
                name="markitdown-release-manifest.json",
                browser_download_url="https://example.com/manifest.json",
            ),
        ),
    )

    asset = update_checker.select_release_asset(release, platform_label="Windows")

    assert asset is not None
    assert asset.browser_download_url == "https://example.com/windows.zip"


def test_select_release_asset_prefers_zip_over_windows_installer():
    release = update_checker.ReleaseInfo(
        tag_name="v2.0.0",
        html_url="",
        assets=(
            update_checker.ReleaseAsset(
                name="MarkItDown-Windows-Setup-2.0.0.exe",
                browser_download_url="https://example.com/setup.exe",
                platform="Windows",
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-Windows-2.0.0.zip",
                browser_download_url="https://example.com/windows.zip",
                platform="Windows",
            ),
        ),
    )

    asset = update_checker.select_release_asset(release, platform_label="Windows")

    assert asset is not None
    assert asset.name == "MarkItDown-Windows-2.0.0.zip"


def test_select_release_asset_prefers_zip_over_linux_appimage():
    release = update_checker.ReleaseInfo(
        tag_name="v2.0.0",
        html_url="",
        assets=(
            update_checker.ReleaseAsset(
                name="MarkItDown-Linux-2.0.0.AppImage",
                browser_download_url="https://example.com/linux.AppImage",
                platform="Linux",
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-Linux-2.0.0.zip",
                browser_download_url="https://example.com/linux.zip",
                platform="Linux",
            ),
        ),
    )

    asset = update_checker.select_release_asset(release, platform_label="Linux")

    assert asset is not None
    assert asset.name == "MarkItDown-Linux-2.0.0.zip"


def test_select_release_asset_prefers_appimage_for_appimage_runtime():
    release = update_checker.ReleaseInfo(
        tag_name="v2.0.0",
        html_url="",
        assets=(
            update_checker.ReleaseAsset(
                name="MarkItDown-Linux-2.0.0.zip",
                browser_download_url="https://example.com/linux.zip",
                platform="Linux",
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-Linux-2.0.0.AppImage",
                browser_download_url="https://example.com/linux.AppImage",
                platform="Linux",
            ),
        ),
    )

    asset = update_checker.select_release_asset(
        release,
        platform_label="Linux",
        appimage_runtime=True,
    )

    assert asset is not None
    assert asset.name == "MarkItDown-Linux-2.0.0.AppImage"


def test_select_release_asset_prefers_macos_dmg():
    release = update_checker.ReleaseInfo(
        tag_name="v2.0.0",
        html_url="",
        assets=(
            update_checker.ReleaseAsset(
                name="MarkItDown-macOS-2.0.0.zip",
                browser_download_url="https://example.com/macos.zip",
                platform="macOS",
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-macOS-2.0.0.dmg",
                browser_download_url="https://example.com/macos.dmg",
                platform="macOS",
            ),
        ),
    )

    asset = update_checker.select_release_asset(release, platform_label="macOS")

    assert asset is not None
    assert asset.name == "MarkItDown-macOS-2.0.0.dmg"
