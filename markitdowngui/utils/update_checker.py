"""Handles application update checks."""

import requests
import json

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QThread, Signal
from packaging.version import parse

from markitdowngui import __version__ as app_version
from markitdowngui.ui.dialogs.update_dialog import UpdateDialog


GITHUB_API_URL = "https://api.github.com/repos/imadreamerboy/markitdown-gui/releases/latest"

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

class UpdateChecker(QThread):
    """Thread for checking updates asynchronously."""
    
    update_available = Signal(str)  # Emits the new version tag
    update_error = Signal(str)      # Emits error message
    no_update_available = Signal()  # Emits when no update is found
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def run(self):
        """Check for updates in a separate thread."""
        try:
            current_version = get_current_version()
            if not current_version:
                self.update_error.emit("Could not determine current application version.")
                return

            response = requests.get(GITHUB_API_URL, timeout=10)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release.get("tag_name")

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
    """Legacy function for command-line checking (kept for compatibility)."""
    print("Checking for updates...")
    current_version = get_current_version()
    if not current_version:
        print("Could not determine current application version. Skipping update check.")
        return

    try:
        from markitdowngui.ui.main_window import MainWindow
        MAIN_WINDOW_CLASS_LOADED = True
    except ImportError:
        print("Warning: MainWindow class could not be imported for update_checker. Update dialog may lack optimal parent or translations.")
        MainWindow = None 
        MAIN_WINDOW_CLASS_LOADED = False

    try:
        response = requests.get(GITHUB_API_URL)
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release.get("tag_name")

        if latest_version:
            normalized_latest = normalize_version(latest_version)
            normalized_current = normalize_version(current_version)

            print(f"Current version: {normalized_current}, Latest version from GitHub: {normalized_latest}")

            if parse(normalized_latest) > parse(normalized_current):
                print(f"A new version ({latest_version}) is available!")
                
                main_window_for_dialog: QWidget | None = None
                translate_func_for_dialog = lambda key: key

                if MAIN_WINDOW_CLASS_LOADED and MainWindow is not None:
                    for widget in QApplication.topLevelWidgets():
                        if isinstance(widget, MainWindow):
                            if widget.is_main_window:
                                main_window_for_dialog = widget
                                if hasattr(widget, 'translate'):
                                    translate_func_for_dialog = widget.translate
                                else:
                                    print("Warning: MainWindow instance found, but 'translate' method is unexpectedly missing.")
                                break 
                
                if not main_window_for_dialog:
                    print("Info: MainWindow instance not found via specific type check. Update dialog may be parentless and use default translations.")

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