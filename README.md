# MarkItDown GUI Wrapper

A simple **GUI wrapper** for `MarkItDown`, built with **PySide6**. Easily convert files to markdown using drag & drop.

## Features

- 📂 **Drag & Drop** for batch processing
- ⚙️ **Options**:
  - Enable plugins
  - Optional **Document Intelligence API**
- 📜 **Output Choices**:
  - Save all in **one file** or **separately**
  - Choose output directory
  - Save & copy output


## Installation

### Prerequisites

- Python **3.10+**
- Install dependencies:

```sh
pip install -r requirements.txt
```

### Run the App

```sh
python -m markitdowngui.main
```

## Build a Standalone Executable

Use `PyInstaller`:

```sh
pyinstaller --onefile --windowed --name "MarkItDownGUI" main.py
```

For cross-platform builds, try `cx_Freeze` or `briefcase`.


## License

Licensed under **MIT**.

**Note:** `PySide6` uses **LGPLv3**, requiring dynamic linking.

## Contributing

Contributions welcome! Fork, open issues, or submit PRs.

## Credits

- **MarkItDown** ([MIT License](https://opensource.org/licenses/MIT))
- **PySide6** ([LGPLv3 License](https://www.gnu.org/licenses/lgpl-3.0.html))


