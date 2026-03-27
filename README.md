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
- Optional OCR for scanned PDFs and image files, with Azure Document Intelligence first and local Tesseract fallback.
- PDF pipeline toggle: `MarkItDown` for conservative wrapper behavior, or `PyMuPDF` for alternate PDF parsing.
- Optional `Preserve PDF images in Markdown` export with `separate` or `single` asset layouts.
- `PyMuPDF` PDF mode can place extracted images near the closest preceding text block and show them in preview before save.
- Settings for output folder, batch size, header style, table style, OCR, PDF behavior, and theme mode (light/dark/system).
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

### OCR Notes

- OCR is optional and disabled by default.
- Local OCR requires a system `tesseract` binary. Install it from the [official Tesseract project](https://github.com/tesseract-ocr/tesseract). If it is not on your `PATH`, set the executable path in Settings.
- Azure OCR requires an Azure Document Intelligence endpoint in Settings.
- Azure Document Intelligence pricing includes [500 free pages per month](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing) at the time of writing.
- For API-key auth, set `AZURE_OCR_API_KEY`.
- If `AZURE_OCR_API_KEY` is not set, Azure OCR falls back to Azure identity credentials supported by `DefaultAzureCredential`.
- `PyMuPDF` is used internally for local PDF OCR, PDF image extraction, and the alternate PDF parsing pipeline.

### PDF Notes

- `MarkItDown` remains the default PDF pipeline and keeps the conservative wrapper behavior.
- `PyMuPDF` is the alternate PDF pipeline and is the only mode that supports best-effort inline placement of extracted PDF images near the closest preceding text block.
- Inline image placement is based on page coordinates and is best-effort, not a full layout reconstruction.
- If no reliable preceding text block is found, the image is placed at the end of that page instead of in a global trailing image section.
- If PDF conversion falls back to Azure OCR or local OCR text extraction, inline image placement is not preserved because that fallback path does not carry a shared page-layout model.
- When image preservation is enabled, extracted images are saved as files and linked from the Markdown; preview materializes those assets before final save.

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
The bundled spec also collects the runtime pieces required for `PyMuPDF` / `fitz`.
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
python -m pytest
```

5. Open a pull request with a clear summary.

## Credits

- MarkItDown ([MIT License](https://opensource.org/licenses/MIT))
- PySide6 ([LGPLv3 License](https://www.gnu.org/licenses/lgpl-3.0.html))
- PySide6-Fluent-Widgets / QFluentWidgets ([Project site](https://qfluentwidgets.com))

