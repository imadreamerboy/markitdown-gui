"""Handles application update checks."""

import requests
import json

from PySide6.QtWidgets import QApplication # Added for main window access
from packaging.version import parse # Import parse

from markitdowngui import __version__ as app_version # Import the version
from markitdowngui.ui.dialogs.update_dialog import UpdateDialog # Added import
# It's better to get translate from the main_window if possible
# from markitdowngui.utils.translations import get_translation # Fallback if needed

# Placeholder for current application version
# This should be replaced with a proper version retrieval mechanism
# CURRENT_VERSION = "0.1.0" # Example version, replace with actual version logic - REMOVED

GITHUB_API_URL = "https://api.github.com/repos/imadreamerboy/markitdown-gui/releases/latest"

def get_current_version():
    """Retrieves the current application version.
    
    This is a placeholder. In a real implementation, this would read the version
    from a file or a variable set during the build process.
    """
    #    return CURRENT_VERSION - REMOVED
    return app_version # Use the imported version

def check_for_updates():
    """Checks for application updates using GitHub releases."""
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
            # Simple version comparison (can be improved with packaging.version)
            # Assuming versions are like v0.3.0 or 0.3.0
            normalized_latest = latest_version.lstrip('v')
            normalized_current = current_version.lstrip('v')

            print(f"Current version: {normalized_current}, Latest version from GitHub: {normalized_latest}")

            # A more robust comparison would use packaging.version
            # from packaging.version import parse
            # if parse(normalized_latest) > parse(normalized_current):
            if parse(normalized_latest) > parse(normalized_current): # USE packaging.version
                print(f"A new version ({latest_version}) is available!")
                # Here you would typically notify the user, e.g., show a dialog
                # Find the main window to use as parent for the dialog
                main_window = next((w for w in QApplication.topLevelWidgets() if hasattr(w, 'is_main_window') and w.is_main_window), None)
                
                translate_func = lambda key: key # Default pass-through
                if main_window and hasattr(main_window, 'translate'):
                    translate_func = main_window.translate
                # else: # If main_window or its translate method isn't found, we could use get_translation directly
                #     # This would require knowing the current language, which might be tricky here.
                #     # For simplicity, using a pass-through if main_window.translate is not available.
                #     pass

                dialog = UpdateDialog(latest_version, translate_func, parent=main_window)
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