[English](README.md) | [简体中文](README_zh.md) | [繁體中文](README_zh_TW.md)


# MarkItDown GUI Wrapper

A desktop GUI for `MarkItDown`, built with `PySide6` and official Qt Quick Controls/QML.
It focuses on fast multi-file conversion to Markdown with a modern, native-styled desktop interface.

![Current UI screenshot](image.png)

## Features

- Queue-based file workflow with drag and drop.
- Paste website URLs and convert article content to Markdown with the hosted Defuddle API.
- Batch conversion with start, pause/resume, cancel, and progress feedback.
- Results view with per-file selection and Markdown preview.
- Preview modes: rendered Markdown view and raw Markdown view.
- Save modes: export as one combined file or separate files.
- Quick actions: copy Markdown, save output, back to queue, start over.
- Optional OCR for scanned PDFs and image files, with selectable `Azure/Tesseract OCR` and `GLM-OCR` providers.
- Settings for output folder, save mode, source-folder saves, batch size, OCR, and theme mode (light/dark/system).
- Help view with project links, OCR references, conversion references, and keyboard shortcuts.

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
- `Azure/Tesseract OCR` uses Azure Document Intelligence first when configured, then local Tesseract fallback.
- `GLM-OCR` is available as a separate OCR provider for PDFs and images. It runs first and can fall back to Azure/Tesseract OCR if enabled in Settings.
- GLM-OCR offers three modes in Settings:
  - `Official API`: easiest zero-setup path, reads `ZHIPU_API_KEY` or `GLMOCR_API_KEY` from the environment.
  - `Ollama`: easiest local path. The GUI calls Ollama's native `/api/generate` endpoint directly, with defaults `127.0.0.1:11434` and `glm-ocr:latest`.
  - `SDK Server (vLLM / SGLang)`: stronger self-hosted path. Point the app at an existing `/glmocr/parse` endpoint. Default: `http://127.0.0.1:5002/glmocr/parse`.
- The packaged desktop app does not bundle the GLM-OCR self-hosted runtime stack (`torch`, `transformers`, `vLLM`, `SGLang`, and related server/runtime pieces stay external).
- The project depends on `glmocr==0.1.4` for client-side Official API and SDK Server connectivity. Ollama is called directly over HTTP.
- Local OCR requires a system `tesseract` binary. Install it from the [official Tesseract project](https://github.com/tesseract-ocr/tesseract). If it is not on your `PATH`, set the executable path in Settings.
- Azure OCR requires an Azure Document Intelligence endpoint in Settings.
- Azure Document Intelligence pricing includes [500 free pages per month](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing) at the time of writing.
- For API-key auth, set `AZURE_OCR_API_KEY`.
- If `AZURE_OCR_API_KEY` is not set, Azure OCR falls back to Azure identity credentials supported by `DefaultAzureCredential`.
- GLM-OCR project reference: [zai-org/GLM-OCR](https://github.com/zai-org/GLM-OCR)

### Recommended Local Hosting

For normal local use, the easiest path is Ollama. For stronger self-hosted deployments, use the GLM-OCR SDK Server with vLLM or SGLang.

### Ollama

1. Install Ollama.
2. Pull the model:

```sh
ollama pull glm-ocr:latest
```

3. Start the service if it is not already running:

```sh
ollama serve
```

4. In this app, choose `GLM-OCR` -> `Ollama`.
5. Keep the defaults unless you changed them:
   - host: `127.0.0.1`
   - port: `11434`
   - model: `glm-ocr:latest`

### SDK Server

1. Create a separate Python environment for GLM-OCR.
2. Install `glmocr[selfhosted,server]` in that environment.
3. Start a local `vLLM` or `SGLang` backend for `zai-org/GLM-OCR`.
4. Start the SDK server:

```sh
python -m glmocr.server --config config.yaml
```

5. In this app, choose `GLM-OCR` -> `SDK Server (vLLM / SGLang)` and keep `http://127.0.0.1:5002/glmocr/parse`.

Minimal server-side `config.yaml`:

```yaml
pipeline:
  maas:
    enabled: false
  ocr_api:
    api_host: 127.0.0.1
    api_port: 8080
```

The official GLM-OCR docs show the full Ollama, `vLLM`, and `SGLang` setup commands:

- [Official Ollama deployment guide](https://github.com/zai-org/GLM-OCR/blob/main/examples/ollama-deploy/README.md)
- [Self-hosted SDK Server + Client Guide](https://github.com/zai-org/GLM-OCR/blob/main/examples/self-host/README.md)
- [GLM-OCR README](https://github.com/zai-org/GLM-OCR)

### Website URL Notes

- Website conversion uses the hosted [Defuddle](https://defuddle.md/) API.
- The app sends the pasted `http://` or `https://` URL to `https://defuddle.md/<url>` and stores the returned Markdown in the normal results view.
- Defuddle responses typically include YAML frontmatter metadata at the top when available.
- According to the [Defuddle Terms](https://defuddle.md/terms), unauthenticated requests are limited to `1,000` requests per month per IP address as of March 14, 2026.
- Because requests are sent directly from the desktop app, that free-tier limit applies to the user's own network IP.
- Website conversion requires an internet connection and depends on the external Defuddle service being available.
### OCR Notes

- OCR is optional and disabled by default.
- Local OCR requires a system `tesseract` binary. Install it from the [official Tesseract project](https://github.com/tesseract-ocr/tesseract). If it is not on your `PATH`, set the executable path in Settings.
- Azure OCR requires an Azure Document Intelligence endpoint in Settings.
- Azure Document Intelligence pricing includes [500 free pages per month](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing) at the time of writing.
- For API-key auth, set `AZURE_OCR_API_KEY`.
- If `AZURE_OCR_API_KEY` is not set, Azure OCR falls back to Azure identity credentials supported by `DefaultAzureCredential`.

### Website URL Notes

- Website conversion uses the hosted [Defuddle](https://defuddle.md/) API.
- The app sends the pasted `http://` or `https://` URL to `https://defuddle.md/<url>` and stores the returned Markdown in the normal results view.
- Defuddle responses typically include YAML frontmatter metadata at the top when available.
- According to the [Defuddle Terms](https://defuddle.md/terms), unauthenticated requests are limited to `1,000` requests per month per IP address as of March 14, 2026.
- Because requests are sent directly from the desktop app, that free-tier limit applies to the user's own network IP.
- Website conversion requires an internet connection and depends on the external Defuddle service being available.

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
That build intentionally excludes the GLM-OCR self-hosted runtime stack; local hosting stays external to the GUI.

## License

Licensed under the **MIT License**.

The app uses `PySide6`/Qt under Qt's LGPL/commercial licensing model. The previous `PySide6-Fluent-Widgets` dependency has been removed.

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
- Qt Quick Controls ([Qt documentation](https://doc.qt.io/qt-6/qtquickcontrols-index.html))

