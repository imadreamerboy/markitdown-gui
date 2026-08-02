# Third-Party Notices

MarkItDown GUI is licensed under the MIT License. Commercial use, private use,
modification, redistribution, sublicensing, and sale are permitted under that
licence, subject to preserving the copyright and licence notice.

This file summarises notable third-party components used by the application.
Each component remains under its own licence. Where a packaged build bundles a
runtime or library, distributors must also satisfy that component's licence
terms.

## Runtime And UI

- PySide6, PySide6 Addons, PySide6 Essentials, and shiboken6: LGPL-3.0-only OR
  GPL-2.0-only OR GPL-3.0-only, with a commercial Qt licensing option. The app
  uses Qt through PySide6 and does not modify Qt itself.
- Qt Quick and Qt Quick Controls: Qt modules used through PySide6. When
  distributing binaries under the LGPL route, keep the relevant Qt/PySide
  notices available and do not prevent users from replacing the LGPL-covered Qt
  libraries with compatible modified versions.
- Lucide icons: ISC License for the icon set. The bundled icon subset includes
  `markitdowngui/resources/icons/LICENSE.lucide.txt`.

## Conversion, OCR, And Document Processing

- MarkItDown: MIT License.
- markitdown-pdf-images: MIT License.
- pdf-inspector: MIT License.
- Docling Core and Docling Parse: MIT License for the codebases; any model usage
  remains subject to the applicable model licences.
- GLM-OCR Python package: Apache-2.0 License.
- pytesseract: Apache-2.0 License. Tesseract OCR itself is an external runtime
  when installed separately by the user.
- pypdfium2: BSD-3-Clause, Apache-2.0, and dependency licences.
- pdfminer.six: MIT License.
- pdfplumber: MIT License.
- mammoth: BSD-2-Clause License.
- markdownify: MIT License.
- Beautiful Soup: MIT License.
- lxml: BSD-3-Clause License.
- python-pptx: MIT License.
- pandas: BSD-3-Clause License.
- openpyxl: MIT License.
- xlrd: BSD License.
- Azure AI Document Intelligence SDK and Azure Identity SDK: MIT License.

## Services And External Tools

- Azure Document Intelligence, GLM-OCR hosted/API modes, Defuddle, Ollama, and
  Tesseract installations are external services or tools when configured by the
  user. Their service terms, model terms, billing terms, and local installation
  licences are separate from the MarkItDown GUI project licence.

## Notes For Binary Distribution

- Include `LICENSE` and this `THIRD_PARTY_NOTICES.md` file with packaged builds.
- Preserve third-party licence files that are bundled inside dependency wheels
  or copied runtime folders.
- If distributing under Qt's LGPL path rather than a Qt commercial licence,
  verify that the package layout continues to allow replacement of the
  LGPL-covered Qt/PySide libraries.
