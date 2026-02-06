[阅读中文版本](README_zh.md)

# MarkItDown GUI Wrapper

A desktop GUI for `MarkItDown`, built with `PySide6` and `QFluentWidgets`.
It focuses on fast multi-file conversion to Markdown with a modern Fluent-style interface.

![Current UI screenshot](image.png)

## Features

- Queue-based file workflow with drag and drop.
- Batch conversion with start, pause/resume, cancel, and progress feedback.
- Results view with per-file selection and Markdown preview.
- Preview modes: rendered Markdown view and raw Markdown view.
- Save modes: export as one combined file or separate files.
- Quick actions: copy Markdown, save output, back to queue, start over.
- Settings for output folder, batch size, header style, table style, and theme mode (light/dark/system).
- Built-in shortcuts dialog, update check action, and about dialog.

## Installation

Download prebuilt binaries from [Releases](https://github.com/imadreamerboy/markitdown-gui/releases), or run from source.

### Prerequisites

- Python `3.10+`
- `uv` (recommended)

Install dependencies:

```sh
uv sync
```

Alternative:

```sh
pip install -e .[dev]
```

## Run the App

```sh
uv run python -m markitdowngui.main
```

## Keyboard Shortcuts

- `Ctrl+O`: Open files
- `Ctrl+S`: Save output
- `Ctrl+C`: Copy output
- `Ctrl+P`: Pause/resume
- `Ctrl+B`: Start conversion
- `Ctrl+L`: Clear queue
- `Ctrl+K`: Show shortcuts
- `Esc`: Cancel conversion

## Build a Standalone Executable

```sh
uv pip install -e .[dev]
pyinstaller MarkItDown.spec --clean --noconfirm
```

The default spec builds an `onedir` app in `dist/MarkItDown/`.
Release workflows package this folder into platform-specific `.zip` artifacts.

## License

Licensed under **GPLv3 for non-commercial use**.

Commercial use requires a separate commercial license.
This follows the non-commercial licensing requirements of `PySide6-Fluent-Widgets` (`qfluentwidgets`).

## Contributing

1. Fork the repository and create a branch.
2. Install dev dependencies:

```sh
uv pip install -e .[dev]
```

3. Make your changes.
4. Run tests:

```sh
uv run pytest -q
```

5. Open a pull request with a clear summary.

## Credits

- MarkItDown ([MIT License](https://opensource.org/licenses/MIT))
- PySide6 ([LGPLv3 License](https://www.gnu.org/licenses/lgpl-3.0.html))
- PySide6-Fluent-Widgets / QFluentWidgets ([Project site](https://qfluentwidgets.com))


