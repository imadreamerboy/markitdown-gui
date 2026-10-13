"""Main entry point for the MarkItDown GUI application."""

import sys

def main() -> None:
    """Start the GUI or run the internal package checks."""
    if "--check-package" in sys.argv[1:]:
        import argparse
        from pathlib import Path

        from markitdowngui.package_check import run_package_checks

        parser = argparse.ArgumentParser(description="Check packaged native backends.")
        parser.add_argument("--check-package", action="store_true", required=True)
        parser.add_argument("--report", type=Path, required=True)
        args = parser.parse_args()
        sys.exit(run_package_checks(args.report))

    from markitdowngui.ui_qml.app import main as run_qml_app

    sys.exit(run_qml_app())

if __name__ == '__main__':
    main()
