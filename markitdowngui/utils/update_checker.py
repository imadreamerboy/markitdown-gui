import json
import os
import sys
from dataclasses import dataclass

import requests
from PySide6.QtCore import QThread, Signal
from packaging.version import parse

from markitdowngui import __version__ as app_version


GITHUB_API_URL = "https://api.github.com/repos/imadreamerboy/markitdown-gui/releases/latest"


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    browser_download_url: str
    size: int = 0
    platform: str = ""
    sha256: str = ""


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    html_url: str
    body: str = ""
    assets: tuple[ReleaseAsset, ...] = ()


def get_current_version():
    """Retrieves the current application version.

    This version is sourced from the `__version__` attribute
    in the `markitdowngui` package, which is updated during the
    build process based on Git tags.
    """
    return app_version

def normalize_version(ver):
    # Remove leading 'v' and any leading '.'
    return ver.lstrip('v').lstrip('.')


def parse_release_manifest(payload: dict) -> dict[str, dict[str, object]]:
    """Parse optional release metadata keyed by asset name."""
    entries = payload.get("assets") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return {}

    manifest_assets: dict[str, dict[str, object]] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        manifest_assets[name] = {
            "platform": str(item.get("platform") or "").strip(),
            "sha256": str(item.get("sha256") or "").strip(),
            "size": _safe_int(item.get("size")),
        }
    return manifest_assets


def parse_release_info(
    payload: dict,
    manifest_assets: dict[str, dict[str, object]] | None = None,
) -> ReleaseInfo | None:
    tag_name = str(payload.get("tag_name") or "").strip()
    if not tag_name:
        return None

    manifest_assets = manifest_assets or {}
    assets = []
    for item in payload.get("assets") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        url = str(item.get("browser_download_url") or "").strip()
        if not name or not url:
            continue
        manifest_item = manifest_assets.get(name, {})
        size = _safe_int(manifest_item.get("size") or item.get("size"))
        assets.append(
            ReleaseAsset(
                name=name,
                browser_download_url=url,
                size=size,
                platform=str(manifest_item.get("platform") or "").strip(),
                sha256=str(manifest_item.get("sha256") or "").strip(),
            )
        )

    return ReleaseInfo(
        tag_name=tag_name,
        html_url=str(payload.get("html_url") or "").strip(),
        body=str(payload.get("body") or "").strip(),
        assets=tuple(assets),
    )


def get_latest_release_info(timeout: int | None = None) -> ReleaseInfo | None:
    kwargs = {"timeout": timeout} if timeout is not None else {}
    response = requests.get(GITHUB_API_URL, **kwargs)
    response.raise_for_status()
    payload = response.json()
    release = parse_release_info(payload)
    if release is None:
        return None

    manifest_asset = next(
        (
            asset
            for asset in release.assets
            if asset.name.lower() == "markitdown-release-manifest.json"
        ),
        None,
    )
    if manifest_asset is None:
        return release

    try:
        manifest_response = requests.get(manifest_asset.browser_download_url, **kwargs)
        manifest_response.raise_for_status()
        manifest_assets = parse_release_manifest(manifest_response.json())
    except (requests.exceptions.RequestException, ValueError, TypeError):
        return release
    return parse_release_info(payload, manifest_assets) or release


def current_platform_label() -> str:
    if sys.platform == "win32":
        return "Windows"
    if sys.platform == "darwin":
        return "macOS"
    if sys.platform.startswith("linux"):
        return "Linux"
    return sys.platform


def is_appimage_runtime() -> bool:
    return bool(os.environ.get("APPIMAGE"))


def select_release_asset(
    release: ReleaseInfo | None,
    platform_label: str | None = None,
    *,
    appimage_runtime: bool | None = None,
) -> ReleaseAsset | None:
    if release is None:
        return None

    platform = (platform_label or current_platform_label()).lower()
    running_appimage = (
        is_appimage_runtime() if appimage_runtime is None else appimage_runtime
    )
    candidates = [
        asset
        for asset in release.assets
        if not asset.name.lower().endswith((".json", ".sha256", ".txt"))
    ]
    if not candidates:
        return None

    def extension_priority(name: str) -> int:
        if platform == "macos":
            if name.endswith(".dmg"):
                return 4
            if name.endswith(".zip"):
                return 3
        if platform in {"windows", "linux"}:
            if platform == "linux" and running_appimage and name.endswith(".appimage"):
                return 5
            if name.endswith(".zip"):
                return 4
            if platform == "windows" and name.endswith((".exe", ".msi")):
                return 3
            if platform == "linux" and name.endswith(".appimage"):
                return 3
        if name.endswith((".zip", ".dmg")):
            return 2
        if name.endswith((".msi", ".exe", ".appimage")):
            return 1
        return 0

    def score(asset: ReleaseAsset) -> tuple[int, int]:
        asset_platform = asset.platform.lower()
        name = asset.name.lower()
        platform_match = int(asset_platform == platform or platform in name)
        return platform_match, extension_priority(name)

    return max(candidates, key=score)


class UpdateChecker(QThread):
    """Thread for checking updates asynchronously."""
    
    update_available = Signal(str)  # Emits the new version tag
    update_error = Signal(str)      # Emits error message
    no_update_available = Signal()  # Emits when no update is found
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.latest_release: ReleaseInfo | None = None
        
    def run(self):
        """Check for updates in a separate thread."""
        try:
            current_version = get_current_version()
            if not current_version:
                self.update_error.emit("Could not determine current application version.")
                return

            latest_release = get_latest_release_info(timeout=10)
            self.latest_release = latest_release
            latest_version = latest_release.tag_name if latest_release else ""

            if latest_version:
                normalized_latest = normalize_version(latest_version)
                normalized_current = normalize_version(current_version)

                if parse(normalized_latest) > parse(normalized_current):
                    self.update_available.emit(latest_version)
                else:
                    self.no_update_available.emit()
            else:
                self.update_error.emit("Could not retrieve latest version information from GitHub.")

        except requests.exceptions.RequestException as e:
            self.update_error.emit(f"Network error checking for updates: {e}")
        except json.JSONDecodeError:
            self.update_error.emit("Error parsing GitHub API response.")
        except Exception as e:
            self.update_error.emit(f"An unexpected error occurred during update check: {e}")

def check_for_updates():
    """Check for application updates using GitHub releases.

    The desktop UI uses ``UpdateChecker`` for async signals. This synchronous
    helper is kept for tests and direct CLI-style checks.
    """
    print("Checking for updates...")
    current_version = get_current_version()
    if not current_version:
        print("Could not determine current application version. Skipping update check.")
        return None

    try:
        latest_release = get_latest_release_info()
        latest_version = latest_release.tag_name if latest_release else ""

        if latest_version:
            normalized_latest = latest_version.lstrip('v')
            normalized_current = current_version.lstrip('v')

            print(f"Current version: {normalized_current}, Latest version from GitHub: {normalized_latest}")

            if parse(normalized_latest) > parse(normalized_current):
                print(f"A new version ({latest_version}) is available!")
                return latest_version
            else:
                print("Application is up to date.")
                return None
        else:
            print("Could not retrieve latest version information from GitHub.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error checking for updates: {e}")
    except json.JSONDecodeError:
        print("Error parsing GitHub API response.")
    except Exception as e:
        print(f"An unexpected error occurred during update check: {e}")
    return None

if __name__ == '__main__':
    # For testing the update checker directly
    check_for_updates() 
