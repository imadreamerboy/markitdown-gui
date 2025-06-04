"""Handles application update checks."""

import requests
import json

from PySide6.QtWidgets import QApplication, QWidget # MODIFIED: Added QWidget for type hinting
from packaging.version import parse # Import parse

from markitdowngui import __version__ as app_version # Import the version
from markitdowngui.ui.dialogs.update_dialog import UpdateDialog # Added import


GITHUB_API_URL = "https://api.github.com/repos/imadreamerboy/markitdown-gui/releases/latest"

def get_current_version():
    """Retrieves the current application version.

    This version is sourced from the `__version__` attribute
    in the `markitdowngui` package, which is updated during the
    build process based on Git tags.
    """
    return app_version # Use the imported version

def check_for_updates():
    """Checks for application updates using GitHub releases."""

    # Import MainWindow here to avoid potential circular imports
    # and to ensure it's only imported when needed.
    try:
        from markitdowngui.ui.main_window import MainWindow
        MAIN_WINDOW_CLASS_LOADED = True
    except ImportError:
        print("Warning: MainWindow class could not be imported for update_checker. Update dialog may lack optimal parent or translations.")
        MainWindow = None # type: ignore # Define for logic below, even if None
        MAIN_WINDOW_CLASS_LOADED = False

    print("Checking for updates...")
    current_version = get_current_version()
    if not current_version:
        print("Could not determine current application version. Skipping update check.")
        return

    try:
        response = requests.get(GITHUB_API_URL)
        response.raise_for_status()  # Raise an exception for HTTP errors
        latest_release = response.json()
        latest_version = latest_release.get("tag_name")

        if latest_version:
            # Assuming versions are like v0.3.0 or 0.3.0
            normalized_latest = latest_version.lstrip('v')
            normalized_current = current_version.lstrip('v')

            print(f"Current version: {normalized_current}, Latest version from GitHub: {normalized_latest}")

            # if parse(normalized_latest) > parse(normalized_current):
            if parse(normalized_latest) > parse(normalized_current): # USE packaging.version
                print(f"A new version ({latest_version}) is available!")
                
                main_window_for_dialog: QWidget | None = None
                translate_func_for_dialog = lambda key: key # Default pass-through

                if MAIN_WINDOW_CLASS_LOADED and MainWindow is not None:
                    for widget in QApplication.topLevelWidgets():
                        if isinstance(widget, MainWindow):
                            # Now 'widget' is confirmed to be an instance of MainWindow.
                            # Access 'is_main_window' and 'translate' safely.
                            if widget.is_main_window:
                                main_window_for_dialog = widget
                                # Ensure translate method exists, though it should per user info
                                if hasattr(widget, 'translate'):
                                    translate_func_for_dialog = widget.translate
                                else:
                                    print("Warning: MainWindow instance found, but 'translate' method is unexpectedly missing.")
                                break 
                
                if not main_window_for_dialog:
                    print("Info: MainWindow instance not found via specific type check. Update dialog may be parentless and use default translations.")
                    # As a less type-safe fallback, we could try the generic hasattr approach,
                    # but the primary goal is to resolve linter issues with the specific MainWindow type.
                    # For now, if specific check fails, the dialog proceeds with defaults.

                dialog = UpdateDialog(latest_version, translate_func_for_dialog, parent=main_window_for_dialog)
                dialog.exec()
            else:
                print("Application is up to date.")
        else:
            print("Could not retrieve latest version information from GitHub.")

    except requests.exceptions.RequestException as e:
        print(f"Error checking for updates: {e}")
    except json.JSONDecodeError:
        print("Error parsing GitHub API response.")
    except Exception as e:
        print(f"An unexpected error occurred during update check: {e}")

if __name__ == '__main__':
    # For testing the update checker directly
    check_for_updates() 