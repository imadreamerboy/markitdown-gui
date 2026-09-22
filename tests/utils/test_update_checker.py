from pathlib import Path
from unittest.mock import MagicMock

import pytest

from markitdowngui.utils import update_checker


LIVE_V150_ASSETS = (
    (
        "MarkItDown-Linux-1.5.0.AppImage",
        251615736,
        "db4e5e8a182b8172996933fae642607dc337b815fb51ba2e6a4e72e7e1daaf5d",
    ),
    (
        "MarkItDown-Linux-1.5.0.zip",
        433970917,
        "68a9f6109c9ad34a18f84a0b0d2c0cf5d95fb1f50c6bade4fbcac1a5a804525c",
    ),
    (
        "MarkItDown-macOS-1.5.0.dmg",
        268160492,
        "7074da7da0e72725dca81290cce00c1854e3a93b7029b1113ff754b754e3deb5",
    ),
    (
        "markitdown-release-manifest.json",
        1035,
        "b4c9b5783b9e050794908c6680fb4e3577eedac3e881c52b44fd1a53d062cb64",
    ),
    (
        "MarkItDown-Windows-1.5.0.zip",
        245405147,
        "1308fc3796b10e42cc93209b86728007133214cf3ea73b3cd1841a0b514e10d5",
    ),
    (
        "MarkItDown-Windows-Setup-1.5.0.exe",
        163892498,
        "34589123132d961def4a71f273882fa576eab9072440766cc09252e44d4dd553",
    ),
)
LEGACY_V150_MANIFEST_SHA256 = {
    "MarkItDown-Linux-1.5.0.AppImage": (
        "db4e5e8a182b8172996933fae642607dc337b815fb51ba2e6a4e72e7e1daaf5d"
    ),
    "MarkItDown-Linux-1.5.0.zip": (
        "68a9f6109c9ad34a18f84a0b0d2c0cf5d95fb1f50c6bade4fbcac1a5a804525c"
    ),
    "MarkItDown-macOS-1.5.0.dmg": (
        "7074da7da0e72725dca81290cce00c1854e3a93b7029b1113ff754b754e3deb5"
    ),
    "MarkItDown-Windows-1.5.0.zip": (
        "1308fc3796b10e42cc93209b86728007133214cf3ea73b3cd1841a0b514e10d5"
    ),
    "MarkItDown-Windows-Setup-1.5.0.exe": (
        "34589123132d961def4a71f273882fa576eab9072440766cc09252e44d4dd553"
    ),
}


def live_v150_release_payload():
    return {
        "tag_name": "v.1.5.0",
        "html_url": "https://github.com/imadreamerboy/markitdown-gui/releases/tag/v.1.5.0",
        "assets": [
            {
                "name": name,
                "size": size,
                "digest": f"sha256:{sha256}",
                "browser_download_url": (
                    "https://github.com/imadreamerboy/markitdown-gui/releases/"
                    f"download/v.1.5.0/{name}"
                ),
            }
            for name, size, sha256 in LIVE_V150_ASSETS
        ],
    }

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


def test_parse_release_info_consumes_live_github_native_asset_digests():
    release = update_checker.parse_release_info(live_v150_release_payload())

    assert release is not None
    assert [
        (asset.name, asset.size, asset.sha256) for asset in release.assets
    ] == list(LIVE_V150_ASSETS)
    assert [asset.platform for asset in release.assets] == [
        "Linux",
        "Linux",
        "macOS",
        "",
        "Windows",
        "Windows",
    ]


@pytest.mark.parametrize(
    ("name", "platform"),
    [
        ("MarkItDown-Windows-2.0.0.zip", "Windows"),
        ("MarkItDown-Linux-2.0.0.AppImage", "Linux"),
        ("MarkItDown-macOS-2.0.0.dmg", "macOS"),
        ("markitdown-release-manifest.json", ""),
        ("unrelated-windows-package.zip", ""),
    ],
)
def test_platform_from_asset_name_uses_canonical_filename_markers(name, platform):
    assert update_checker.platform_from_asset_name(name) == platform


@pytest.mark.parametrize(
    "digest",
    [
        None,
        "",
        "sha256:",
        "sha256:abc123",
        f"sha512:{'a' * 64}",
        f"sha256:{'g' * 64}",
        f"sha256:{'a' * 65}",
    ],
)
def test_parse_github_sha256_digest_rejects_missing_or_malformed_values(digest):
    assert update_checker.parse_github_sha256_digest(digest) == ""


def test_parse_github_sha256_digest_normalises_hex_case():
    assert update_checker.parse_github_sha256_digest(f"sha256:{'A' * 64}") == "a" * 64


def test_get_latest_release_info_uses_one_github_api_request(mock_requests_get):
    release_response = MagicMock()
    release_response.json.return_value = live_v150_release_payload()
    mock_requests_get.return_value = release_response

    release = update_checker.get_latest_release_info(timeout=1)

    assert release is not None
    assert release.tag_name == "v.1.5.0"
    assert release.assets[1].sha256 == LIVE_V150_ASSETS[1][2]
    mock_requests_get.assert_called_once_with(update_checker.GITHUB_API_URL, timeout=1)


def test_legacy_manifest_publisher_remains_compatible_with_native_digests():
    release = update_checker.parse_release_info(live_v150_release_payload())
    native_checksums = {
        asset.name: asset.sha256
        for asset in release.assets
        if asset.name != "markitdown-release-manifest.json"
    }
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    assert native_checksums == LEGACY_V150_MANIFEST_SHA256
    assert '"sha256": hashlib.sha256(path.read_bytes()).hexdigest()' in workflow
    assert "artifacts/markitdown-release-manifest.json" in workflow


def test_select_release_asset_prefers_current_platform():
    release = update_checker.ReleaseInfo(
        tag_name="v2.0.0",
        html_url="",
        assets=(
            update_checker.ReleaseAsset(
                name="MarkItDown-Linux-2.0.0.zip",
                browser_download_url="https://example.com/linux.zip",
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-Windows-2.0.0.zip",
                browser_download_url="https://example.com/windows.zip",
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
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-Windows-2.0.0.zip",
                browser_download_url="https://example.com/windows.zip",
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
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-Linux-2.0.0.zip",
                browser_download_url="https://example.com/linux.zip",
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
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-Linux-2.0.0.AppImage",
                browser_download_url="https://example.com/linux.AppImage",
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
            ),
            update_checker.ReleaseAsset(
                name="MarkItDown-macOS-2.0.0.dmg",
                browser_download_url="https://example.com/macos.dmg",
            ),
        ),
    )

    asset = update_checker.select_release_asset(release, platform_label="macOS")

    assert asset is not None
    assert asset.name == "MarkItDown-macOS-2.0.0.dmg"
