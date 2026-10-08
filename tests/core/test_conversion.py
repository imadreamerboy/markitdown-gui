import base64
import importlib
import io
import logging
import sys
import types
import zipfile
import zlib

import pytest


@pytest.fixture
def docx_with_image_and_underline(tmp_path):
    docx_path = tmp_path / "illustrated.docx"
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/"
        "x8AAusB9Wl2nNwAAAAASUVORK5CYII="
    )
    with zipfile.ZipFile(docx_path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            'Target="media/image1.png"/>'
            "</Relationships>",
        )
        archive.writestr(
            "word/document.xml",
            '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
                xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <w:body>
                <w:p><w:r><w:rPr><w:u w:val="single"/></w:rPr><w:t>DOCX_SENTINEL</w:t></w:r></w:p>
                <w:tbl><w:tr><w:tc><w:p><w:r><w:drawing><wp:inline>
                  <wp:docPr id="1" name="Image"/><a:graphic>
                    <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                      <pic:pic><pic:blipFill><a:blip r:embed="rId1"/></pic:blipFill><pic:spPr/></pic:pic>
                    </a:graphicData>
                  </a:graphic>
                </wp:inline></w:drawing></w:r></w:p></w:tc></w:tr></w:tbl>
              </w:body>
            </w:document>''',
        )
        archive.writestr("word/media/image1.png", png_bytes)
    return docx_path


@pytest.fixture
def multipage_tiff(tmp_path):
    from PIL import Image

    tiff_path = tmp_path / "multipage.tiff"
    pages = [
        Image.new("RGB", (8, 8), "red"),
        Image.new("RGB", (8, 8), "green"),
        Image.new("RGB", (8, 8), "blue"),
    ]
    try:
        pages[0].save(tiff_path, save_all=True, append_images=pages[1:])
    finally:
        for page in pages:
            page.close()
    return tiff_path


@pytest.fixture
def pdf_factory(tmp_path):
    """Build small real PDFs without adding a test-only PDF dependency."""

    def build(name, pages):
        objects: dict[int, bytes] = {}
        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects[3] = (
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        )
        next_object_id = 4
        page_ids: list[int] = []

        for page in pages:
            page_id = next_object_id
            content_id = page_id + 1
            next_object_id += 2
            page_ids.append(page_id)

            content_parts: list[bytes] = []
            text_lines = page.get("text_lines")
            if text_lines is None:
                text = page.get("text")
                text_lines = [text] if text else []
            for line_index, text in enumerate(text_lines):
                escaped = (
                    str(text)
                    .replace("\\", "\\\\")
                    .replace("(", "\\(")
                    .replace(")", "\\)")
                )
                content_parts.append(
                    (
                        f"BT /F1 11 Tf 72 {720 - line_index * 22} Td "
                        f"({escaped}) Tj ET"
                    ).encode("ascii")
                )

            resources = b"<< /Font << /F1 3 0 R >>"
            if page.get("image"):
                image_id = next_object_id
                next_object_id += 1
                pixels = zlib.compress(bytes([255, 0, 255, 0] * 4))
                objects[image_id] = (
                    b"<< /Type /XObject /Subtype /Image /Width 4 /Height 4 "
                    b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
                    + f"/Length {len(pixels)} >>\nstream\n".encode("ascii")
                    + pixels
                    + b"\nendstream"
                )
                resources += f" /XObject << /Im1 {image_id} 0 R >>".encode("ascii")
                content_parts.append(b"q 320 0 0 160 72 430 cm /Im1 Do Q")
            resources += b" >>"

            content = b"\n".join(content_parts)
            objects[content_id] = (
                f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
                + content
                + b"\nendstream"
            )
            objects[page_id] = (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                + b"/Resources "
                + resources
                + f" /Contents {content_id} 0 R >>".encode("ascii")
            )

        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        objects[2] = (
            f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode(
                "ascii"
            )
        )

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for object_id in range(1, max(objects) + 1):
            offsets.append(len(output))
            output.extend(f"{object_id} 0 obj\n".encode("ascii"))
            output.extend(objects[object_id])
            output.extend(b"\nendobj\n")

        xref_offset = len(output)
        output.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(
            (
                f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )

        path = tmp_path / name
        path.write_bytes(output)
        return path

    return build


class _FakeSignal:
    def __init__(self, *_args, **_kwargs):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in self._callbacks:
            callback(*args, **kwargs)


class _FakeQThread:
    def __init__(self, *_args, **_kwargs):
        pass

    def msleep(self, _milliseconds):
        pass


@pytest.fixture
def conversion(monkeypatch):
    qtcore = types.ModuleType("PySide6.QtCore")
    qtcore.QThread = _FakeQThread
    qtcore.Signal = _FakeSignal

    monkeypatch.setitem(sys.modules, "PySide6", types.ModuleType("PySide6"))
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qtcore)

    module = importlib.import_module("markitdowngui.core.conversion")
    return importlib.reload(module)


def _install_fake_glmocr(monkeypatch, glmocr_cls):
    glmocr_package = types.ModuleType("glmocr")
    glmocr_api_module = types.ModuleType("glmocr.api")
    glmocr_api_module.GlmOcr = glmocr_cls
    glmocr_package.api = glmocr_api_module
    monkeypatch.setitem(sys.modules, "glmocr", glmocr_package)
    monkeypatch.setitem(sys.modules, "glmocr.api", glmocr_api_module)


def _install_fake_pdf_images(monkeypatch, convert_pdf):
    package = types.ModuleType("markitdown_pdf_images")
    package.convert_pdf = convert_pdf
    monkeypatch.setitem(sys.modules, "markitdown_pdf_images", package)


def _install_fake_pdf_inspector(monkeypatch, conversion, process_pdf):
    monkeypatch.setattr(conversion, "process_pdf", process_pdf)


def _install_fake_anydoc(monkeypatch, to_markdown):
    package = types.ModuleType("anydoc")
    package.to_markdown = to_markdown
    monkeypatch.setitem(sys.modules, "anydoc", package)


def test_convert_file_uses_markitdown_when_ocr_disabled(monkeypatch, conversion):
    calls = []

    def fake_convert(file_path, options, use_docintel=False):
        calls.append((file_path, use_docintel))
        return "native text"

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)

    result = conversion.convert_file(
        "scan.png",
        conversion.ConversionOptions(ocr_enabled=False),
    )

    assert result == "native text"
    assert calls == [("scan.png", False)]


def test_convert_pdf_without_preserve_images_keeps_native_path(monkeypatch, conversion):
    calls = []

    def fake_convert(file_path, options, use_docintel=False):
        calls.append((file_path, use_docintel))
        return "native pdf text"

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)

    result = conversion.convert_file(
        "scan.pdf",
        conversion.ConversionOptions(ocr_enabled=False, preserve_pdf_images=False),
    )

    assert result == "native pdf text"
    assert calls == [("scan.pdf", False)]


@pytest.mark.parametrize("suffix", [".tif", ".tiff"])
def test_convert_tiff_uses_azure_for_both_supported_extensions(
    monkeypatch,
    conversion,
    tmp_path,
    suffix,
):
    source_path = tmp_path / f"scan{suffix}"
    source_path.write_bytes(b"TIFF fixture bytes are not read by the Azure stub")
    calls = []

    def fake_convert(file_path, _options, use_docintel=False):
        calls.append((file_path, use_docintel))
        return "azure tiff text"

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_convert_image_with_local_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("local OCR must not run after successful Azure TIFF OCR")
        ),
    )

    outcome = conversion.convert_file_with_details(
        str(source_path),
        conversion.ConversionOptions(
            ocr_enabled=True,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        ),
    )

    assert outcome.backend == conversion.BACKEND_AZURE
    assert outcome.markdown == "azure tiff text"
    assert calls == [(str(source_path), True)]
    assert source_path.suffix == suffix


@pytest.mark.parametrize(
    "accelerator_options",
    [
        {"anydoc_conversion": True},
        {"fast_pdf_conversion": True},
        {"anydoc_conversion": True, "fast_pdf_conversion": True},
    ],
    ids=("anydoc", "pdf-inspector", "both"),
)
def test_pdf_ocr_precedes_native_only_accelerators_for_rich_mixed_pdf(
    monkeypatch,
    conversion,
    pdf_factory,
    accelerator_options,
):
    source_pdf = pdf_factory(
        "rich-mixed.pdf",
        [
            {
                "text_lines": [
                    f"NATIVE_LINE_{index:02d} sufficient extractable digital text"
                    for index in range(18)
                ],
                "image": True,
            }
        ],
    )
    monkeypatch.setattr(
        conversion,
        "_try_convert_with_anydoc",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("AnyDoc must not run for an OCR-enabled PDF")
        ),
    )
    monkeypatch.setattr(
        conversion,
        "_try_convert_pdf_with_pdf_inspector",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("pdf-inspector must not run for an OCR-enabled PDF")
        ),
    )
    monkeypatch.setattr(
        conversion,
        "_run_tesseract_ocr",
        lambda *_args, **_kwargs: "SCANNED_BODY_SENTINEL",
    )

    outcome = conversion.convert_file_with_details(
        str(source_pdf),
        conversion.ConversionOptions(
            ocr_enabled=True,
            **accelerator_options,
        ),
    )

    assert outcome.backend == conversion.BACKEND_LOCAL
    assert "NATIVE\\_LINE\\_00" in outcome.markdown
    assert "SCANNED\\_BODY\\_SENTINEL" in outcome.markdown


def test_convert_digital_pdf_with_ocr_keeps_native_markitdown_output(
    monkeypatch,
    conversion,
    pdf_factory,
):
    source_pdf = pdf_factory(
        "digital.pdf",
        [{"text": "DIGITAL_SENTINEL"}],
    )
    native_markdown = "| native table |\n| --- |\n| preserved |"

    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: native_markdown,
    )
    monkeypatch.setattr(
        conversion,
        "_run_tesseract_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("digital-only PDF should not invoke OCR")
        ),
    )

    outcome = conversion.convert_file_with_details(
        str(source_pdf),
        conversion.ConversionOptions(ocr_enabled=True),
    )

    assert outcome.backend == conversion.BACKEND_NATIVE
    assert outcome.markdown == native_markdown


def test_convert_mixed_pdf_ocrs_image_even_with_native_page_stamp(
    monkeypatch,
    conversion,
    pdf_factory,
):
    source_pdf = pdf_factory(
        "mixed.pdf",
        [{"text": "PAGE_NUMBER_STAMP", "image": True}],
    )
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: "PAGE_NUMBER_STAMP",
    )
    monkeypatch.setattr(
        conversion,
        "_run_tesseract_ocr",
        lambda *_args, **_kwargs: "SCANNED_BODY_SENTINEL",
    )

    outcome = conversion.convert_file_with_details(
        str(source_pdf),
        conversion.ConversionOptions(ocr_enabled=True),
    )

    assert outcome.backend == conversion.BACKEND_LOCAL
    native_position = outcome.markdown.index("PAGE\\_NUMBER\\_STAMP")
    scan_position = outcome.markdown.index("SCANNED\\_BODY\\_SENTINEL")
    assert native_position < scan_position


def test_convert_mixed_pdf_propagates_page_ocr_failure(
    monkeypatch,
    conversion,
    pdf_factory,
):
    source_pdf = pdf_factory(
        "mixed-failure.pdf",
        [{"text": "PAGE_NUMBER_STAMP", "image": True}],
    )
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: "PAGE_NUMBER_STAMP",
    )

    def fail_ocr(_image, _options):
        raise RuntimeError("forced page OCR failure")

    monkeypatch.setattr(conversion, "_run_tesseract_ocr", fail_ocr)

    with pytest.raises(RuntimeError, match="forced page OCR failure"):
        conversion.convert_file_with_details(
            str(source_pdf),
            conversion.ConversionOptions(ocr_enabled=True),
        )


def test_convert_pdf_accepts_empty_ocr_for_legitimate_blank_page(
    monkeypatch,
    conversion,
    pdf_factory,
):
    source_pdf = pdf_factory(
        "blank-and-digital.pdf",
        [{}, {"text": "DIGITAL_SENTINEL"}],
    )
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: "DIGITAL_SENTINEL",
    )
    calls = 0

    def empty_ocr(_image, _options):
        nonlocal calls
        calls += 1
        return ""

    monkeypatch.setattr(conversion, "_run_tesseract_ocr", empty_ocr)

    outcome = conversion.convert_file_with_details(
        str(source_pdf),
        conversion.ConversionOptions(ocr_enabled=True),
    )

    assert outcome.backend == conversion.BACKEND_LOCAL
    assert "DIGITAL\\_SENTINEL" in outcome.markdown
    assert calls == 1


def test_convert_pdf_surfaces_selective_parser_failure_without_whole_page_retry(
    monkeypatch,
    conversion,
    pdf_factory,
):
    source_pdf = pdf_factory(
        "selective-parser-failure.pdf",
        [{"text": "DIGITAL_SENTINEL"}],
    )
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: "DIGITAL_SENTINEL",
    )
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_image_aware_pipeline",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("selective parser failed")
        ),
    )
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_local_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("whole-page OCR must not retry a parser failure")
        ),
    )

    with pytest.raises(RuntimeError, match="selective parser failed"):
        conversion.convert_file_with_details(
            str(source_pdf),
            conversion.ConversionOptions(ocr_enabled=True),
        )


def test_anydoc_conversion_is_opt_in(monkeypatch, conversion):
    native_calls = []

    _install_fake_anydoc(monkeypatch, lambda file_path: "# anydoc output")
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *args, **kwargs: native_calls.append((args, kwargs)) or "native output",
    )

    outcome = conversion.convert_file_with_details(
        "report.docx",
        conversion.ConversionOptions(anydoc_conversion=True),
    )

    assert outcome.markdown == "# anydoc output"
    assert outcome.backend == conversion.BACKEND_ANYDOC
    assert native_calls == []


def test_anydoc_conversion_falls_back_to_native(monkeypatch, conversion):
    _install_fake_anydoc(
        monkeypatch,
        lambda _file_path: (_ for _ in ()).throw(RuntimeError("unsupported")),
    )
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: "native fallback",
    )

    outcome = conversion.convert_file_with_details(
        "report.docx",
        conversion.ConversionOptions(anydoc_conversion=True),
    )

    assert outcome.markdown == "native fallback"
    assert outcome.backend == conversion.BACKEND_NATIVE


def test_anydoc_does_not_override_docx_image_preservation(monkeypatch, conversion):
    _install_fake_anydoc(
        monkeypatch,
        lambda _file_path: pytest.fail("anydoc must not run when preserving DOCX images"),
    )
    expected = conversion.ConversionOutcome("with assets", backend="docx-images")
    monkeypatch.setattr(
        conversion,
        "_convert_docx_with_preserved_images",
        lambda *_args: expected,
    )

    outcome = conversion.convert_file_with_details(
        "illustrated.docx",
        conversion.ConversionOptions(
            anydoc_conversion=True,
            preserve_docx_images=True,
        ),
    )

    assert outcome is expected


@pytest.mark.parametrize(
    "extension",
    [".odt", ".odp", ".ods", ".rtf", ".doc", ".ppt", ".pptm", ".xlsm"],
)
def test_anydoc_covers_widened_office_formats(monkeypatch, conversion, extension):
    _install_fake_anydoc(monkeypatch, lambda _file_path: "# anydoc output")
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: pytest.fail("native converter must not run"),
    )

    outcome = conversion.convert_file_with_details(
        f"report{extension}",
        conversion.ConversionOptions(anydoc_conversion=True),
    )

    assert outcome.markdown == "# anydoc output"
    assert outcome.backend == conversion.BACKEND_ANYDOC


@pytest.mark.parametrize(
    "source",
    ["notes.txt", "notes.md", "report.xml", "data.json", "page.html", "sheet.csv"],
)
def test_text_inputs_keep_the_native_pipeline_when_anydoc_is_enabled(
    monkeypatch,
    conversion,
    source,
):
    _install_fake_anydoc(
        monkeypatch,
        lambda _file_path: pytest.fail(f"anydoc must not convert {source}"),
    )
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: "native text",
    )

    outcome = conversion.convert_file_with_details(
        source,
        conversion.ConversionOptions(anydoc_conversion=True),
    )

    assert outcome.markdown == "native text"
    assert outcome.backend == conversion.BACKEND_NATIVE


def test_fast_pdf_conversion_uses_pdf_inspector_for_trusted_text_pdf(monkeypatch, conversion):
    native_calls = []

    def process_pdf(file_path):
        assert file_path == "report.pdf"
        return types.SimpleNamespace(
            pdf_type="text_based",
            confidence=0.99,
            has_encoding_issues=False,
            markdown="# Fast report",
        )

    def native_convert(*args, **kwargs):
        native_calls.append((args, kwargs))
        return "native fallback"

    _install_fake_pdf_inspector(monkeypatch, conversion, process_pdf)
    monkeypatch.setattr(conversion, "_convert_with_markitdown", native_convert)

    outcome = conversion.convert_file_with_details(
        "report.pdf",
        conversion.ConversionOptions(fast_pdf_conversion=True),
    )

    assert outcome.markdown == "# Fast report"
    assert outcome.backend == conversion.BACKEND_PDF_INSPECTOR
    assert native_calls == []


@pytest.mark.parametrize(
    "result",
    [
        types.SimpleNamespace(
            pdf_type="scanned",
            confidence=1.0,
            has_encoding_issues=False,
            markdown="# OCR needed",
        ),
        types.SimpleNamespace(
            pdf_type="text_based",
            confidence=0.5,
            has_encoding_issues=False,
            markdown="# Low confidence",
        ),
        types.SimpleNamespace(
            pdf_type="text_based",
            confidence=1.0,
            has_encoding_issues=True,
            markdown="# Encoding issue",
        ),
        types.SimpleNamespace(
            pdf_type="text_based",
            confidence=1.0,
            has_encoding_issues=False,
            markdown="  ",
        ),
    ],
)
def test_fast_pdf_conversion_falls_back_for_untrusted_result(
    monkeypatch,
    conversion,
    result,
):
    _install_fake_pdf_inspector(monkeypatch, conversion, lambda _file_path: result)
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: "native fallback",
    )

    outcome = conversion.convert_file_with_details(
        "report.pdf",
        conversion.ConversionOptions(fast_pdf_conversion=True),
    )

    assert outcome.markdown == "native fallback"
    assert outcome.backend == conversion.BACKEND_NATIVE


def test_fast_pdf_conversion_falls_back_to_ocr_when_enabled(monkeypatch, conversion):
    _install_fake_pdf_inspector(
        monkeypatch,
        conversion,
        lambda _file_path: types.SimpleNamespace(
            pdf_type="mixed",
            confidence=1.0,
            has_encoding_issues=False,
            markdown="# Partial text",
        ),
    )
    expected = conversion.ConversionOutcome("ocr fallback", backend="local")
    monkeypatch.setattr(conversion, "_convert_pdf_with_ocr", lambda *_args: expected)

    outcome = conversion.convert_file_with_details(
        "mixed.pdf",
        conversion.ConversionOptions(ocr_enabled=True, fast_pdf_conversion=True),
    )

    assert outcome is expected


def test_fast_pdf_conversion_falls_back_when_dependency_is_unavailable(
    monkeypatch,
    conversion,
):
    monkeypatch.setattr(conversion, "process_pdf", None)
    monkeypatch.setitem(sys.modules, "pdf_inspector", None)
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: "native fallback",
    )

    outcome = conversion.convert_file_with_details(
        "report.pdf",
        conversion.ConversionOptions(fast_pdf_conversion=True),
    )

    assert outcome.markdown == "native fallback"
    assert outcome.backend == conversion.BACKEND_NATIVE


def test_fast_pdf_conversion_fallback_logs_do_not_include_source_path(
    monkeypatch,
    conversion,
    caplog,
):
    source_path = "/private/customer-records/report.pdf"
    _install_fake_pdf_inspector(
        monkeypatch,
        conversion,
        lambda _file_path: types.SimpleNamespace(
            pdf_type="scanned",
            confidence=1.0,
            has_encoding_issues=False,
            markdown="# OCR needed",
        ),
    )
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: "native fallback",
    )

    with caplog.at_level(logging.WARNING):
        outcome = conversion.convert_file_with_details(
            source_path,
            conversion.ConversionOptions(fast_pdf_conversion=True),
        )

    assert outcome.backend == conversion.BACKEND_NATIVE
    assert source_path not in caplog.text
    assert "classified it as scanned" in caplog.text


def test_fast_pdf_conversion_keeps_image_preservation_authoritative(
    monkeypatch,
    conversion,
):
    _install_fake_pdf_inspector(
        monkeypatch,
        conversion,
        lambda _file_path: pytest.fail("fast parser must not run when preserving images"),
    )
    expected = conversion.ConversionOutcome("with assets", backend="pdf-images")
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_preserved_images",
        lambda *_args: expected,
    )

    outcome = conversion.convert_file_with_details(
        "illustrated.pdf",
        conversion.ConversionOptions(
            fast_pdf_conversion=True,
            preserve_pdf_images=True,
        ),
    )

    assert outcome is expected


def test_convert_url_uses_defuddle_http_api(monkeypatch, conversion):
    captured = {}

    class FakeResponse:
        status_code = 200
        ok = True
        text = "# Article\n"

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr(conversion.requests, "get", fake_get)

    outcome = conversion.convert_file_with_details("https://example.com/article")

    assert outcome.markdown == "# Article"
    assert outcome.backend == conversion.BACKEND_DEFUDDLE
    expected_url = conversion._build_defuddle_request_url("https://example.com/article")
    assert captured["url"] == expected_url
    assert captured["kwargs"]["timeout"] == conversion.DEFUDDLE_REQUEST_TIMEOUT_SECONDS


def test_build_defuddle_request_url_encodes_embedded_url(conversion):
    request_url = conversion._build_defuddle_request_url(
        "https://example.com/article?a=1&key=abc#intro"
    )

    assert (
        request_url
        == "https://defuddle.md/https%3A%2F%2Fexample.com%2Farticle%3Fa%3D1%26key%3Dabc%23intro"
    )


def test_convert_url_surfaces_rate_limit(monkeypatch, conversion):
    class FakeResponse:
        status_code = 429
        ok = False
        text = "Too many requests"

    monkeypatch.setattr(conversion.requests, "get", lambda *_args, **_kwargs: FakeResponse())

    with pytest.raises(conversion.DefuddleRateLimitError) as exc_info:
        conversion.convert_file("https://example.com/article")

    assert exc_info.value.status_code == 429
    assert "1,000 requests per month per IP" in str(exc_info.value)


def test_convert_url_surfaces_request_errors(monkeypatch, conversion):
    def fake_get(*_args, **_kwargs):
        raise conversion.requests.RequestException("network down")

    monkeypatch.setattr(conversion.requests, "get", fake_get)

    with pytest.raises(RuntimeError) as exc_info:
        conversion.convert_file("https://example.com/article")

    assert "failed to reach the Defuddle service" in str(exc_info.value)


def test_convert_image_prefers_docintel_when_configured(monkeypatch, conversion):
    calls = []

    def fake_convert(file_path, options, use_docintel=False):
        calls.append(use_docintel)
        return "azure text"

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_convert_image_with_local_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("local OCR should not run")),
    )

    result = conversion.convert_file(
        "scan.png",
        conversion.ConversionOptions(
            ocr_enabled=True,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        ),
    )

    assert result == "azure text"
    assert calls == [True]


def test_convert_image_falls_back_to_local_ocr(monkeypatch, conversion):
    def fake_convert(_file_path, _options, use_docintel=False):
        if use_docintel:
            raise RuntimeError("azure unavailable")
        return ""

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_convert_image_with_local_ocr",
        lambda *_args, **_kwargs: "local image text",
    )

    result = conversion.convert_file(
        "scan.png",
        conversion.ConversionOptions(
            ocr_enabled=True,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        ),
    )

    assert result == "local image text"


def test_convert_image_uses_glmocr_when_selected(monkeypatch, conversion):
    captured = {}

    class FakeGlmOcr:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def parse(self, _file_path):
            return types.SimpleNamespace(markdown_result="glm image text")

    _install_fake_glmocr(monkeypatch, FakeGlmOcr)
    monkeypatch.setenv("ZHIPU_API_KEY", "secret")
    monkeypatch.setattr(
        conversion,
        "_convert_image_with_azure_tesseract_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Azure/Tesseract OCR should not run")
        ),
    )

    outcome = conversion.convert_file_with_details(
        "scan.png",
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
        ),
    )

    assert outcome.markdown == "glm image text"
    assert outcome.backend == conversion.BACKEND_GLMOCR
    assert captured["mode"] == conversion.GLMOCR_MODE_MAAS
    assert captured["model"] == "glm-ocr"


def test_convert_pdf_keeps_native_text_when_available(
    monkeypatch,
    conversion,
    pdf_factory,
):
    calls = []
    source_pdf = pdf_factory("native.pdf", [{"text": "native pdf text"}])

    def fake_convert(_file_path, _options, use_docintel=False):
        calls.append(use_docintel)
        return "native pdf text"

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_local_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("local OCR should not run")),
    )

    result = conversion.convert_file(
        str(source_pdf),
        conversion.ConversionOptions(ocr_enabled=True),
    )

    assert result == "native pdf text"
    assert calls == [False]


def test_convert_pdf_falls_back_to_docintel(monkeypatch, conversion):
    calls = []

    def fake_convert(_file_path, _options, use_docintel=False):
        calls.append(use_docintel)
        if use_docintel:
            return "azure pdf text"
        return ""

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_local_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("local OCR should not run")),
    )

    result = conversion.convert_file(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        ),
    )

    assert result == "azure pdf text"
    assert calls == [False, True]


def test_convert_pdf_uses_glmocr_when_selected(monkeypatch, conversion):
    class FakeGlmOcr:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def parse(self, _file_path):
            return types.SimpleNamespace(markdown_result="glm pdf text")

    _install_fake_glmocr(monkeypatch, FakeGlmOcr)
    monkeypatch.setenv("GLMOCR_API_KEY", "secret")
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_azure_tesseract_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Azure/Tesseract OCR should not run")
        ),
    )

    outcome = conversion.convert_file_with_details(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
        ),
    )

    assert outcome.markdown == "glm pdf text"
    assert outcome.backend == conversion.BACKEND_GLMOCR


def test_convert_pdf_with_preserved_images_uses_plugin(monkeypatch, conversion, tmp_path):
    captured = {}
    asset_path = tmp_path / "artifacts" / "report-123" / "page-1.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"png")

    def fake_convert_pdf(file_path, **kwargs):
        captured["file_path"] = file_path
        captured["kwargs"] = kwargs
        return types.SimpleNamespace(
            markdown="![page](C:/temp/report-123/page-1.png)\n\ntext",
            assets=[
                types.SimpleNamespace(
                    filename="page-1.png",
                    path=asset_path,
                    markdown_path="C:/temp/report-123/page-1.png",
                    page_number=1,
                    kind="bitmap",
                    ocr_text=None,
                )
            ],
        )

    _install_fake_pdf_images(monkeypatch, fake_convert_pdf)
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("native MarkItDown should not run")
        ),
    )

    outcome = conversion.convert_file_with_details(
        "scan.pdf",
        conversion.ConversionOptions(
            preserve_pdf_images=True,
            pdf_artifacts_dir=str(tmp_path / "artifacts"),
        ),
    )

    assert outcome.backend == conversion.BACKEND_PDF_IMAGES
    assert outcome.markdown == "![page](C:/temp/report-123/page-1.png)\n\ntext"
    assert captured["file_path"] == "scan.pdf"
    assert captured["kwargs"] == {
        "preserve_images": True,
        "image_mode": "external",
        "artifacts_dir": str(tmp_path / "artifacts"),
        "path_mode": "absolute",
        "ocr_enabled": False,
        "tesseract_path": None,
        "ocr_languages": "",
    }
    assert outcome.assets == [
        conversion.ConversionAsset(
            filename="page-1.png",
            source_path=str(asset_path.resolve()),
            preview_markdown_path="C:/temp/report-123/page-1.png",
            page_number=1,
            kind="bitmap",
            ocr_text=None,
        )
    ]


def test_convert_pdf_with_preserved_images_and_local_ocr_uses_plugin(
    monkeypatch,
    conversion,
    tmp_path,
):
    captured = {}

    def fake_convert_pdf(_file_path, **kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(markdown="ocr pdf text", assets=[])

    _install_fake_pdf_images(monkeypatch, fake_convert_pdf)
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_azure_tesseract_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Azure/Tesseract OCR routing should not run")
        ),
    )

    outcome = conversion.convert_file_with_details(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            preserve_pdf_images=True,
            pdf_artifacts_dir=str(tmp_path / "artifacts"),
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
            tesseract_path=" /usr/bin/tesseract ",
            ocr_languages=" eng+deu ",
        ),
    )

    assert outcome.backend == conversion.BACKEND_PDF_IMAGES
    assert captured["ocr_enabled"] is True
    assert captured["tesseract_path"] == "/usr/bin/tesseract"
    assert captured["ocr_languages"] == "eng+deu"


def test_convert_pdf_with_preserved_images_and_glmocr_preserves_assets_then_uses_provider(
    monkeypatch,
    conversion,
    tmp_path,
):
    captured = {}

    def fake_convert_pdf(_file_path, **kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(markdown="ocr pdf text", assets=[])

    _install_fake_pdf_images(monkeypatch, fake_convert_pdf)
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_glmocr",
        lambda *_args, **_kwargs: conversion.ConversionOutcome(
            markdown="glm pdf text",
            backend=conversion.BACKEND_GLMOCR,
        ),
    )

    outcome = conversion.convert_file_with_details(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            preserve_pdf_images=True,
            pdf_artifacts_dir=str(tmp_path / "artifacts"),
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
            tesseract_path=" /usr/bin/tesseract ",
        ),
    )

    assert outcome.backend == conversion.BACKEND_PDF_IMAGES
    assert outcome.markdown == "ocr pdf text\n\nglm pdf text"
    assert captured["ocr_enabled"] is False
    assert captured["tesseract_path"] == "/usr/bin/tesseract"


def test_convert_docx_without_preserve_images_keeps_native_path(monkeypatch, conversion):
    calls = []

    def fake_convert(file_path, options, use_docintel=False):
        calls.append((file_path, use_docintel))
        return "native docx text"

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)

    result = conversion.convert_file(
        "report.docx",
        conversion.ConversionOptions(ocr_enabled=False, preserve_docx_images=False),
    )

    assert result == "native docx text"
    assert calls == [("report.docx", False)]


def test_convert_docx_with_preserved_images_uses_upstream_converter_and_assets(
    conversion,
    tmp_path,
    docx_with_image_and_underline,
):
    outcome = conversion.convert_file_with_details(
        str(docx_with_image_and_underline),
        conversion.ConversionOptions(
            preserve_docx_images=True,
            docx_artifacts_dir=str(tmp_path / "artifacts"),
        ),
    )

    assert outcome.backend == conversion.BACKEND_DOCX_IMAGES
    assert "<u>DOCX_SENTINEL</u>" in outcome.markdown.replace("\\_", "_")
    assert "| --- |" not in outcome.markdown
    assert len(outcome.assets) == 1
    asset = outcome.assets[0]
    assert outcome.assets == [
        conversion.ConversionAsset(
            filename="image-001.png",
            source_path=asset.source_path,
            preview_markdown_path=asset.preview_markdown_path,
            page_number=None,
            kind="docx-image",
        )
    ]
    assert asset.source_path is not None
    assert asset.preview_markdown_path in outcome.markdown
    assert asset.preview_markdown_path.startswith("/")
    assert asset.preview_markdown_path.endswith("/image-001.png")
    assert io.open(asset.source_path, "rb").read().startswith(b"\x89PNG")

    from markitdowngui.core.markdown_assets import prepare_markdown_for_separate_save

    output_path = tmp_path / "saved" / "report.md"
    output_path.parent.mkdir()
    rewritten = prepare_markdown_for_separate_save(
        outcome.markdown,
        outcome.assets,
        output_path,
    )

    assert "report_assets/image-001.png" in rewritten
    assert asset.preview_markdown_path not in rewritten
    assert (tmp_path / "saved" / "report_assets" / "image-001.png").is_file()


def test_convert_docx_image_hook_failure_is_surfaced(
    monkeypatch,
    conversion,
    tmp_path,
    docx_with_image_and_underline,
):
    def fail_write(_path, _data):
        raise OSError("asset write failed")

    monkeypatch.setattr(conversion.Path, "write_bytes", fail_write)

    with pytest.raises(OSError, match="asset write failed"):
        conversion.convert_file_with_details(
            str(docx_with_image_and_underline),
            conversion.ConversionOptions(
                preserve_docx_images=True,
                docx_artifacts_dir=str(tmp_path / "artifacts"),
            ),
        )


def test_convert_docx_with_preserved_images_requires_artifact_dir(conversion):
    with pytest.raises(RuntimeError) as exc_info:
        conversion.convert_file_with_details(
            "report.docx",
            conversion.ConversionOptions(preserve_docx_images=True),
        )

    assert "writable temporary asset directory" in str(exc_info.value)


def test_extract_images_from_single_cell_tables(conversion):
    html = '<table><tr><td><img src="image.png"/></td></tr></table>'

    converted = conversion._extract_images_from_single_cell_tables(html)

    assert "<table" not in converted
    assert '<img src="image.png"/>' in converted


def test_map_pdf_assets_uses_app_owned_asset_model(conversion, tmp_path):
    asset_path = tmp_path / "assets" / "page-1.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"png")

    mapped = conversion._map_pdf_assets(
        [
            types.SimpleNamespace(
                filename="page-1.png",
                path=asset_path,
                markdown_path="/tmp/assets/page-1.png",
                page_number=2,
                kind="bitmap",
                ocr_text="page text",
            )
        ]
    )

    assert mapped == [
        conversion.ConversionAsset(
            filename="page-1.png",
            source_path=str(asset_path.resolve()),
            preview_markdown_path="/tmp/assets/page-1.png",
            page_number=2,
            kind="bitmap",
            ocr_text="page text",
        )
    ]


def test_convert_file_with_details_reports_azure_backend(monkeypatch, conversion):
    def fake_convert(_file_path, _options, use_docintel=False):
        if use_docintel:
            return "azure pdf text"
        return ""

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_local_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("local OCR should not run")
        ),
    )

    outcome = conversion.convert_file_with_details(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        ),
    )

    assert outcome.markdown == "azure pdf text"
    assert outcome.backend == conversion.BACKEND_AZURE


def test_convert_pdf_falls_back_to_azure_tesseract_ocr_after_glmocr_failure(
    monkeypatch,
    conversion,
):
    class FakeGlmOcr:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def parse(self, _file_path):
            raise RuntimeError("glm unavailable")

    _install_fake_glmocr(monkeypatch, FakeGlmOcr)
    monkeypatch.setenv("ZHIPU_API_KEY", "secret")
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_azure_tesseract_ocr",
        lambda *_args, **_kwargs: conversion.ConversionOutcome(
            markdown="Azure/Tesseract PDF text",
            backend=conversion.BACKEND_NATIVE,
        ),
    )

    outcome = conversion.convert_file_with_details(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
            ocr_fallback_enabled=True,
            ocr_fallback_provider=conversion.OCR_PROVIDER_AZURE_TESSERACT,
        ),
    )

    assert outcome.markdown == "Azure/Tesseract PDF text"
    assert outcome.backend == conversion.BACKEND_NATIVE


def test_convert_pdf_skips_fallback_when_fallback_provider_is_none(
    monkeypatch,
    conversion,
):
    class FakeGlmOcr:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def parse(self, _file_path):
            raise RuntimeError("glm unavailable")

    _install_fake_glmocr(monkeypatch, FakeGlmOcr)
    monkeypatch.setenv("ZHIPU_API_KEY", "secret")
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_azure_tesseract_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Fallback OCR should not run")
        ),
    )

    with pytest.raises(RuntimeError) as exc_info:
        conversion.convert_file(
            "scan.pdf",
            conversion.ConversionOptions(
                ocr_enabled=True,
                ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
                ocr_fallback_provider=conversion.OCR_PROVIDER_NONE,
            ),
        )

    assert "GLM-OCR failed for the PDF" in str(exc_info.value)
    assert "glm unavailable" in str(exc_info.value)


def test_convert_pdf_surfaces_glmocr_failure_without_fallback(monkeypatch, conversion):
    class FakeGlmOcr:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def parse(self, _file_path):
            raise RuntimeError("glm unavailable")

    _install_fake_glmocr(monkeypatch, FakeGlmOcr)
    monkeypatch.setenv("ZHIPU_API_KEY", "secret")
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_azure_tesseract_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Azure/Tesseract OCR should not run")
        ),
    )

    with pytest.raises(RuntimeError) as exc_info:
        conversion.convert_file(
            "scan.pdf",
            conversion.ConversionOptions(
                ocr_enabled=True,
                ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
                ocr_fallback_enabled=False,
            ),
        )

    assert "GLM-OCR failed for the PDF" in str(exc_info.value)
    assert "glm unavailable" in str(exc_info.value)


def test_convert_pdf_falls_back_to_local_ocr_after_native_markitdown_failure(
    monkeypatch,
    conversion,
    pdf_factory,
):
    calls = []
    source_pdf = pdf_factory(
        "native-failure.pdf",
        [{"text": "DIGITAL_SENTINEL", "image": True}],
    )

    def fake_convert(_file_path, _options, use_docintel=False):
        calls.append(use_docintel)
        if not use_docintel:
            raise RuntimeError("native parser failed")
        return ""

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_run_tesseract_ocr",
        lambda *_args, **_kwargs: "local pdf text",
    )

    result = conversion.convert_file(
        str(source_pdf),
        conversion.ConversionOptions(ocr_enabled=True),
    )

    assert "DIGITAL\\_SENTINEL" in result
    assert "local pdf text" in result
    assert calls == [False]


def test_convert_pdf_falls_back_to_local_ocr_after_docintel_failure(
    monkeypatch,
    conversion,
    pdf_factory,
):
    calls = []
    source_pdf = pdf_factory(
        "docintel-failure.pdf",
        [{"text": "DIGITAL_SENTINEL", "image": True}],
    )

    def fake_convert(_file_path, _options, use_docintel=False):
        calls.append(use_docintel)
        if use_docintel:
            raise RuntimeError("azure unavailable")
        return ""

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_run_tesseract_ocr",
        lambda *_args, **_kwargs: "local pdf text",
    )

    result = conversion.convert_file(
        str(source_pdf),
        conversion.ConversionOptions(
            ocr_enabled=True,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        ),
    )

    assert "DIGITAL\\_SENTINEL" in result
    assert "local pdf text" in result
    assert calls == [False, True]


def test_convert_with_glmocr_requires_package(monkeypatch, conversion):
    monkeypatch.setitem(sys.modules, "glmocr", types.ModuleType("glmocr"))
    monkeypatch.delitem(sys.modules, "glmocr.api", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        conversion._convert_with_glmocr(
            "scan.png",
            conversion.ConversionOptions(
                ocr_enabled=True,
                ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
            ),
        )

    assert "requires the `glmocr` package" in str(exc_info.value)


def test_convert_with_glmocr_requires_maas_api_key(monkeypatch, conversion):
    class FakeGlmOcr:
        def __init__(self, **_kwargs):
            raise AssertionError("GLM-OCR should not be constructed without an API key")

    _install_fake_glmocr(monkeypatch, FakeGlmOcr)
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    monkeypatch.delenv("GLMOCR_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        conversion._convert_with_glmocr(
            "scan.png",
            conversion.ConversionOptions(
                ocr_enabled=True,
                ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
                glmocr_mode=conversion.GLMOCR_MODE_MAAS,
            ),
        )

    assert "ZHIPU_API_KEY or GLMOCR_API_KEY" in str(exc_info.value)


def test_convert_with_glmocr_sdk_server_uses_maas_client_without_env_key(
    monkeypatch,
    conversion,
):
    captured = {}

    class FakeGlmOcr:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def parse(self, _file_path):
            return types.SimpleNamespace(markdown_result="glm text")

    _install_fake_glmocr(monkeypatch, FakeGlmOcr)
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    monkeypatch.delenv("GLMOCR_API_KEY", raising=False)

    result = conversion._convert_with_glmocr(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
            glmocr_mode=conversion.GLMOCR_MODE_SDK_SERVER,
            glmocr_sdk_server_url=" http://localhost:5002/glmocr/parse ",
        ),
    )

    assert result == "glm text"
    assert captured == {
        "mode": "maas",
        "model": "glm-ocr",
        "api_url": "http://localhost:5002/glmocr/parse",
        "api_key": "markitdown-gui-sdk-server",
    }


def test_convert_with_glmocr_ollama_calls_native_api_without_glmocr(
    monkeypatch,
    conversion,
    tmp_path,
):
    captured = {}

    from PIL import Image

    image_path = tmp_path / "scan.png"
    Image.new("RGB", (4, 4), "white").save(image_path)

    monkeypatch.setitem(sys.modules, "glmocr", None)
    monkeypatch.setitem(sys.modules, "glmocr.api", None)

    class FakeResponse:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {"response": "glm text"}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["payload"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(conversion.requests, "post", fake_post)

    result = conversion._convert_with_glmocr(
        str(image_path),
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
            glmocr_mode=conversion.GLMOCR_MODE_OLLAMA,
            glmocr_ollama_host=" localhost ",
            glmocr_ollama_port=11434,
            glmocr_ollama_model=" glm-ocr:latest ",
        ),
    )

    assert result == "glm text"
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["timeout"] == conversion.GLMOCR_OLLAMA_TIMEOUT_SECONDS
    assert captured["payload"]["model"] == "glm-ocr:latest"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["prompt"] == conversion.GLMOCR_OLLAMA_PROMPT
    assert captured["payload"]["images"]
    assert captured["payload"]["options"]["num_predict"] == 16384


def test_convert_with_glmocr_ollama_joins_page_results(monkeypatch, conversion):
    from PIL import Image

    images = [
        Image.new("RGB", (4, 4), "white"),
        Image.new("RGB", (4, 4), "black"),
    ]
    responses = ["page one", "page two"]

    monkeypatch.setattr(
        conversion,
        "_iter_glmocr_ollama_images",
        lambda _file_path: iter(images),
    )

    class FakeResponse:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {"response": responses.pop(0)}

    monkeypatch.setattr(
        conversion.requests,
        "post",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    result = conversion._convert_with_glmocr(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
            glmocr_mode=conversion.GLMOCR_MODE_OLLAMA,
        ),
    )

    assert result == "page one\n\npage two"
    assert responses == []


def test_convert_multipage_tiff_with_local_ocr_preserves_frame_order(
    monkeypatch,
    conversion,
    multipage_tiff,
):
    frame_colours = {
        (255, 0, 0): "red frame",
        (0, 128, 0): "green frame",
        (0, 0, 255): "blue frame",
    }

    monkeypatch.setattr(
        conversion,
        "_run_tesseract_ocr",
        lambda image, _options: frame_colours[image.getpixel((0, 0))],
    )

    markdown = conversion._convert_image_with_local_ocr(
        str(multipage_tiff),
        conversion.ConversionOptions(ocr_enabled=True),
    )

    assert markdown == "red frame\n\ngreen frame\n\nblue frame"


def test_convert_multipage_tiff_with_ollama_preserves_frame_order(
    monkeypatch,
    conversion,
    multipage_tiff,
):
    frame_colours = {
        (255, 0, 0): "red frame",
        (0, 128, 0): "green frame",
        (0, 0, 255): "blue frame",
    }
    monkeypatch.setattr(
        conversion,
        "_call_glmocr_ollama",
        lambda image, _options: frame_colours[image.getpixel((0, 0))],
    )

    markdown = conversion._convert_with_glmocr(
        str(multipage_tiff),
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
            glmocr_mode=conversion.GLMOCR_MODE_OLLAMA,
        ),
    )

    assert markdown == "red frame\n\ngreen frame\n\nblue frame"


def test_convert_multipage_tiff_surfaces_later_frame_failure(
    monkeypatch,
    conversion,
    multipage_tiff,
):
    calls = 0

    def fail_on_second_frame(_image, _options):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("second TIFF frame failed")
        return "frame text"

    monkeypatch.setattr(conversion, "_run_tesseract_ocr", fail_on_second_frame)

    with pytest.raises(RuntimeError, match="second TIFF frame failed"):
        conversion._convert_image_with_local_ocr(
            str(multipage_tiff),
            conversion.ConversionOptions(ocr_enabled=True),
        )

    assert calls == 2


def test_convert_image_uses_http_ocr_provider(monkeypatch, conversion, tmp_path):
    captured = {}
    image_path = tmp_path / "scan.png"
    image_path.write_bytes(b"image-bytes")

    class FakeResponse:
        ok = True
        status_code = 200
        text = ""
        headers = {"content-type": "application/json"}

        def json(self):
            return {"markdown": "http image text"}

    def fake_post(url, data, files, headers, timeout):
        file_name, file_obj, content_type = files["file"]
        captured["url"] = url
        captured["data"] = data
        captured["file_name"] = file_name
        captured["file_bytes"] = file_obj.read()
        captured["content_type"] = content_type
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("OCR_HTTP_API_KEY", "secret")
    monkeypatch.setattr(conversion.requests, "post", fake_post)

    outcome = conversion.convert_file_with_details(
        str(image_path),
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_HTTP,
            http_ocr_endpoint=" http://localhost:8000/ocr ",
            http_ocr_model=" surya ",
            http_ocr_timeout_seconds=45,
        ),
    )

    assert outcome.markdown == "http image text"
    assert outcome.backend == conversion.BACKEND_HTTP_OCR
    assert captured == {
        "url": "http://localhost:8000/ocr",
        "data": {"model": "surya"},
        "file_name": "scan.png",
        "file_bytes": b"image-bytes",
        "content_type": "image/png",
        "headers": {"Authorization": "Bearer secret"},
        "timeout": 45,
    }


def test_http_ocr_extracts_nested_response_text(conversion):
    response = types.SimpleNamespace(
        headers={"content-type": "application/json; charset=utf-8"},
        json=lambda: {"result": {"content": "nested text"}},
    )

    assert conversion._extract_http_ocr_response_text(response) == "nested text"


def test_http_ocr_skips_blank_fields_before_later_text(conversion):
    response = types.SimpleNamespace(
        headers={"content-type": "application/json"},
        json=lambda: {"markdown": "  ", "text": "recognized text"},
    )

    assert conversion._extract_http_ocr_response_text(response) == "recognized text"


def test_http_ocr_extracts_nested_list_response_text(conversion):
    response = types.SimpleNamespace(
        headers={"content-type": "application/json"},
        json=lambda: {"result": [{"text": "page one"}, {"text": "page two"}]},
    )

    assert (
        conversion._extract_http_ocr_response_text(response)
        == "page one\n\npage two"
    )


def test_convert_pdf_falls_back_from_http_to_azure_tesseract(
    monkeypatch,
    conversion,
):
    monkeypatch.setattr(
        conversion,
        "_convert_with_http_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("http server down")
        ),
    )
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_azure_tesseract_ocr",
        lambda *_args, **_kwargs: conversion.ConversionOutcome(
            markdown="fallback text",
            backend=conversion.BACKEND_AZURE,
        ),
    )

    outcome = conversion.convert_file_with_details(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_HTTP,
            ocr_fallback_provider=conversion.OCR_PROVIDER_AZURE_TESSERACT,
            http_ocr_endpoint="http://localhost:8000/ocr",
        ),
    )

    assert outcome.markdown == "fallback text"
    assert outcome.backend == conversion.BACKEND_AZURE


def test_convert_pdf_surfaces_azure_failure_when_local_ocr_is_unavailable(
    monkeypatch,
    conversion,
    pdf_factory,
):
    source_pdf = pdf_factory(
        "azure-and-local-failure.pdf",
        [{"text": "DIGITAL_SENTINEL", "image": True}],
    )

    def fake_convert(_file_path, _options, use_docintel=False):
        if use_docintel:
            raise RuntimeError("azure auth failed")
        return ""

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_run_tesseract_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("Local OCR failed. Install Tesseract or set its path in Settings.")
        ),
    )

    with pytest.raises(RuntimeError) as exc_info:
        conversion.convert_file(
            str(source_pdf),
            conversion.ConversionOptions(
                ocr_enabled=True,
                docintel_endpoint="https://example.cognitiveservices.azure.com/",
            ),
        )

    assert "Azure OCR failed for the PDF" in str(exc_info.value)
    assert "azure auth failed" in str(exc_info.value)
    assert "Local OCR failed" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert str(exc_info.value.__cause__) == "azure auth failed"


def test_convert_with_markitdown_passes_docintel_api_key(monkeypatch, conversion):
    captured = {}

    class FakeResult:
        markdown = "azure text"

    class FakeMarkItDown:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def convert(self, _file_path):
            return FakeResult()

    azure_module = types.ModuleType("azure")
    azure_core_module = types.ModuleType("azure.core")
    azure_credentials_module = types.ModuleType("azure.core.credentials")

    class FakeAzureKeyCredential:
        def __init__(self, key):
            self.key = key

    azure_credentials_module.AzureKeyCredential = FakeAzureKeyCredential

    monkeypatch.setitem(
        sys.modules,
        "markitdown",
        types.SimpleNamespace(MarkItDown=FakeMarkItDown),
    )
    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.core", azure_core_module)
    monkeypatch.setitem(sys.modules, "azure.core.credentials", azure_credentials_module)
    monkeypatch.setenv("AZURE_OCR_API_KEY", " secret-key ")

    result = conversion._convert_with_markitdown(
        "scan.png",
        conversion.ConversionOptions(
            ocr_enabled=True,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        ),
        use_docintel=True,
    )

    assert result == "azure text"
    assert captured["docintel_endpoint"] == "https://example.cognitiveservices.azure.com/"
    assert isinstance(captured["docintel_credential"], FakeAzureKeyCredential)
    assert captured["docintel_credential"].key == "secret-key"


def test_convert_with_markitdown_uses_default_azure_credential_without_api_key(
    monkeypatch,
    conversion,
):
    captured = {}

    class FakeResult:
        markdown = "azure text"

    class FakeMarkItDown:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def convert(self, _file_path):
            return FakeResult()

    azure_module = types.ModuleType("azure")
    azure_identity_module = types.ModuleType("azure.identity")

    class FakeDefaultAzureCredential:
        pass

    monkeypatch.setitem(
        sys.modules,
        "markitdown",
        types.SimpleNamespace(MarkItDown=FakeMarkItDown),
    )
    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.identity", azure_identity_module)
    azure_identity_module.DefaultAzureCredential = FakeDefaultAzureCredential
    monkeypatch.delenv("AZURE_OCR_API_KEY", raising=False)
    monkeypatch.setenv("AZURE_API_KEY", "should-not-be-used")

    result = conversion._convert_with_markitdown(
        "scan.png",
        conversion.ConversionOptions(
            ocr_enabled=True,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        ),
        use_docintel=True,
    )

    assert result == "azure text"
    assert captured["docintel_endpoint"] == "https://example.cognitiveservices.azure.com/"
    assert isinstance(captured["docintel_credential"], FakeDefaultAzureCredential)


def test_test_azure_ocr_connection_uses_admin_client_with_api_key(monkeypatch, conversion):
    captured = {}

    class FakeAzureKeyCredential:
        def __init__(self, key):
            self.key = key

    class FakeClient:
        def __init__(self, *, endpoint, credential):
            captured["endpoint"] = endpoint
            captured["credential"] = credential
            captured["closed"] = False
            captured["listed"] = False

        def list_models(self):
            captured["listed"] = True
            yield object()

        def close(self):
            captured["closed"] = True

    azure_module = types.ModuleType("azure")
    azure_core_module = types.ModuleType("azure.core")
    azure_credentials_module = types.ModuleType("azure.core.credentials")
    azure_ai_module = types.ModuleType("azure.ai")
    azure_docintel_module = types.ModuleType("azure.ai.documentintelligence")

    azure_credentials_module.AzureKeyCredential = FakeAzureKeyCredential
    azure_docintel_module.DocumentIntelligenceAdministrationClient = FakeClient

    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.core", azure_core_module)
    monkeypatch.setitem(sys.modules, "azure.core.credentials", azure_credentials_module)
    monkeypatch.setitem(sys.modules, "azure.ai", azure_ai_module)
    monkeypatch.setitem(sys.modules, "azure.ai.documentintelligence", azure_docintel_module)
    monkeypatch.setenv("AZURE_OCR_API_KEY", " secret-key ")

    auth_method = conversion.test_azure_ocr_connection(
        conversion.ConversionOptions(
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        )
    )

    assert auth_method == "api_key"
    assert captured["endpoint"] == "https://example.cognitiveservices.azure.com/"
    assert isinstance(captured["credential"], FakeAzureKeyCredential)
    assert captured["credential"].key == "secret-key"
    assert captured["listed"] is True
    assert captured["closed"] is True


def test_test_azure_ocr_connection_requires_api_key(monkeypatch, conversion):
    monkeypatch.delenv("AZURE_OCR_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        conversion.test_azure_ocr_connection(
            conversion.ConversionOptions(
                docintel_endpoint="https://example.cognitiveservices.azure.com/",
            )
        )

    assert "Set AZURE_OCR_API_KEY" in str(exc_info.value)


def test_test_http_ocr_connection_uses_options_request(monkeypatch, conversion):
    captured = {}

    class FakeResponse:
        status_code = 405

    def fake_options(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(conversion.requests, "options", fake_options)

    message = conversion.test_http_ocr_connection(
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_HTTP,
            http_ocr_endpoint="http://localhost:8000/ocr",
            http_ocr_timeout_seconds=45,
        )
    )

    assert message == "HTTP OCR endpoint is reachable."
    assert captured == {"url": "http://localhost:8000/ocr", "timeout": 10}


def test_test_http_ocr_connection_reports_missing_route(monkeypatch, conversion):
    class FakeResponse:
        status_code = 404

    monkeypatch.setattr(
        conversion.requests,
        "options",
        lambda _url, timeout: FakeResponse(),
    )

    with pytest.raises(RuntimeError) as exc_info:
        conversion.test_http_ocr_connection(
            conversion.ConversionOptions(
                ocr_enabled=True,
                ocr_provider=conversion.OCR_PROVIDER_HTTP,
                http_ocr_endpoint="http://localhost:8000/missing",
            )
        )

    assert "responded with 404" in str(exc_info.value)


def test_test_glmocr_ollama_connection_checks_model(monkeypatch, conversion):
    captured = {}

    class FakeResponse:
        ok = True
        text = ""

        def json(self):
            return {"models": [{"name": "glm-ocr:latest"}]}

    def fake_get(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(conversion.requests, "get", fake_get)

    message = conversion.test_glmocr_ollama_connection(
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
            glmocr_mode=conversion.GLMOCR_MODE_OLLAMA,
            glmocr_ollama_host="localhost",
            glmocr_ollama_port=11434,
            glmocr_ollama_model="glm-ocr:latest",
        )
    )

    assert message == "GLM-OCR Ollama is reachable and `glm-ocr:latest` is installed."
    assert captured == {"url": "http://localhost:11434/api/tags", "timeout": 10}


def test_test_glmocr_ollama_connection_reports_missing_model(monkeypatch, conversion):
    class FakeResponse:
        ok = True
        text = ""

        def json(self):
            return {"models": [{"name": "other-model"}]}

    monkeypatch.setattr(conversion.requests, "get", lambda _url, timeout: FakeResponse())

    with pytest.raises(RuntimeError) as exc_info:
        conversion.test_glmocr_ollama_connection(
            conversion.ConversionOptions(
                ocr_enabled=True,
                ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
                glmocr_mode=conversion.GLMOCR_MODE_OLLAMA,
                glmocr_ollama_model="glm-ocr:latest",
            )
        )

    assert "model `glm-ocr:latest` is not installed" in str(exc_info.value)


def test_validate_ocr_setup_reports_disabled_ocr(conversion):
    result = conversion.validate_ocr_setup(conversion.ConversionOptions())

    assert result.ok is False
    assert result.message == "OCR is disabled."


def test_validate_ocr_setup_accepts_azure_endpoint_without_tesseract(
    monkeypatch,
    conversion,
):
    monkeypatch.setattr(conversion.shutil, "which", lambda _name: None)

    result = conversion.validate_ocr_setup(
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_AZURE_TESSERACT,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
            ocr_fallback_enabled=False,
        )
    )

    assert result.ok is True
    assert result.checked_providers == (conversion.OCR_PROVIDER_AZURE_TESSERACT,)


def test_validate_ocr_setup_requires_azure_endpoint_or_tesseract(
    monkeypatch,
    conversion,
):
    monkeypatch.setattr(conversion.shutil, "which", lambda _name: None)

    result = conversion.validate_ocr_setup(
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_AZURE_TESSERACT,
            ocr_fallback_enabled=False,
        )
    )

    assert result.ok is False
    assert result.message == (
        "Azure + Tesseract needs an Azure endpoint or a usable Tesseract executable."
    )


def test_validate_ocr_setup_requires_http_endpoint(conversion):
    result = conversion.validate_ocr_setup(
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_HTTP,
            ocr_fallback_enabled=False,
        )
    )

    assert result.ok is False
    assert result.message == "HTTP OCR requires an endpoint URL."


def test_validate_ocr_setup_requires_glmocr_maas_api_key(monkeypatch, conversion):
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    monkeypatch.delenv("GLMOCR_API_KEY", raising=False)

    result = conversion.validate_ocr_setup(
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
            glmocr_mode=conversion.GLMOCR_MODE_MAAS,
            ocr_fallback_enabled=False,
        )
    )

    assert result.ok is False
    assert result.message == "GLM-OCR Official API requires ZHIPU_API_KEY or GLMOCR_API_KEY."


def test_validate_ocr_setup_deduplicates_duplicate_fallback_provider(conversion):
    result = conversion.validate_ocr_setup(
        conversion.ConversionOptions(
            ocr_enabled=True,
            ocr_provider=conversion.OCR_PROVIDER_HTTP,
            http_ocr_endpoint="http://localhost:8000/ocr",
            ocr_fallback_enabled=True,
            ocr_fallback_provider=conversion.OCR_PROVIDER_HTTP,
        )
    )

    assert result.ok is True
    assert result.checked_providers == (conversion.OCR_PROVIDER_HTTP,)


def test_conversion_worker_tracks_failed_files_separately_from_result_text(
    monkeypatch,
    conversion,
):
    def fake_convert_with_details(file_path, _options, **_kwargs):
        if file_path == "failure.pdf":
            raise RuntimeError("azure unavailable")
        return conversion.ConversionOutcome(
            markdown="Error converting is part of this document",
            backend=conversion.BACKEND_NATIVE,
        )

    monkeypatch.setattr(conversion, "convert_file_with_details", fake_convert_with_details)

    worker = conversion.ConversionWorker(
        ["success.md", "failure.pdf"],
        batch_size=2,
    )
    worker.run()

    assert worker.failed_files == {"failure.pdf"}


def test_conversion_worker_tracks_processing_backends(monkeypatch, conversion):
    def fake_convert_with_details(file_path, _options, **_kwargs):
        backend = (
            conversion.BACKEND_AZURE
            if file_path.endswith(".pdf")
            else conversion.BACKEND_NATIVE
        )
        return conversion.ConversionOutcome(markdown="converted", backend=backend)

    monkeypatch.setattr(conversion, "convert_file_with_details", fake_convert_with_details)

    worker = conversion.ConversionWorker(
        ["scan.pdf", "notes.txt"],
        batch_size=2,
    )
    worker.run()

    assert worker.processing_backends == {
        "scan.pdf": conversion.BACKEND_AZURE,
        "notes.txt": conversion.BACKEND_NATIVE,
    }


def test_conversion_worker_stops_later_urls_after_defuddle_rate_limit(
    monkeypatch,
    conversion,
):
    first_url = "https://example.com/first"
    limited_url = "https://example.com/limited"
    skipped_url = "https://example.com/skipped"
    local_file = "notes.txt"
    later_skipped_url = "https://example.com/later"
    attempted: list[str] = []

    def fake_convert_with_details(file_path, _options, **_kwargs):
        attempted.append(file_path)
        if file_path == limited_url:
            raise conversion.DefuddleRateLimitError("Defuddle rate limit reached.")
        return conversion.ConversionOutcome(
            markdown=f"converted {file_path}",
            backend=(
                conversion.BACKEND_DEFUDDLE
                if file_path.startswith("https://")
                else conversion.BACKEND_NATIVE
            ),
        )

    monkeypatch.setattr(conversion, "convert_file_with_details", fake_convert_with_details)

    worker = conversion.ConversionWorker(
        [first_url, limited_url, skipped_url, local_file, later_skipped_url],
        batch_size=99,
    )
    started: list[str] = []
    completed: list[tuple[str, str, bool]] = []
    finished: list[dict[str, object]] = []
    progress: list[int] = []
    worker.itemStarted.connect(started.append)
    worker.itemFinished.connect(
        lambda source, outcome, failed: completed.append(
            (source, outcome.markdown, failed)
        )
    )
    worker.finished.connect(finished.append)
    worker.progress.connect(lambda value, _source: progress.append(value))

    worker.run()

    assert attempted == [first_url, limited_url, local_file]
    assert started == [first_url, limited_url, local_file]
    assert worker.failed_files == {limited_url, skipped_url, later_skipped_url}
    assert worker.unattempted_files == {skipped_url, later_skipped_url}
    assert worker.processing_backends == {
        first_url: conversion.BACKEND_DEFUDDLE,
        local_file: conversion.BACKEND_NATIVE,
    }
    assert [source for source, _markdown, _failed in completed] == [
        first_url,
        limited_url,
        skipped_url,
        local_file,
        later_skipped_url,
    ]
    assert [failed for _source, _markdown, failed in completed] == [
        False,
        True,
        True,
        False,
        True,
    ]
    assert "Not attempted because Defuddle rate-limited an earlier URL" in completed[2][1]
    assert "Retry this URL later" in completed[4][1]
    assert set(finished[0]) == {
        first_url,
        limited_url,
        skipped_url,
        local_file,
        later_skipped_url,
    }
    assert progress[-1] == 100


def test_conversion_worker_resets_rate_limit_state_for_retry(monkeypatch, conversion):
    limited_url = "https://example.com/limited"
    skipped_url = "https://example.com/skipped"

    def rate_limited(file_path, _options, **_kwargs):
        if file_path == limited_url:
            raise conversion.DefuddleRateLimitError("Defuddle rate limit reached.")
        pytest.fail("The later URL must not be attempted after a rate limit")

    monkeypatch.setattr(conversion, "convert_file_with_details", rate_limited)
    worker = conversion.ConversionWorker([limited_url, skipped_url], batch_size=1)
    worker.run()

    assert worker.failed_files == {limited_url, skipped_url}
    assert worker.unattempted_files == {skipped_url}

    monkeypatch.setattr(
        conversion,
        "convert_file_with_details",
        lambda file_path, _options, **_kwargs: conversion.ConversionOutcome(
            markdown=f"retried {file_path}",
            backend=conversion.BACKEND_DEFUDDLE,
        ),
    )
    worker.run()

    assert worker.failed_files == set()
    assert worker.unattempted_files == set()
    assert worker.processing_backends == {
        limited_url: conversion.BACKEND_DEFUDDLE,
        skipped_url: conversion.BACKEND_DEFUDDLE,
    }


def test_conversion_worker_keeps_trying_urls_after_non_rate_limit_failure(
    monkeypatch,
    conversion,
):
    failed_url = "https://example.com/unavailable"
    later_url = "https://example.com/later"
    attempted: list[str] = []

    def fake_convert_with_details(file_path, _options, **_kwargs):
        attempted.append(file_path)
        if file_path == failed_url:
            raise RuntimeError("Defuddle is temporarily unavailable.")
        return conversion.ConversionOutcome(
            markdown="converted",
            backend=conversion.BACKEND_DEFUDDLE,
        )

    monkeypatch.setattr(conversion, "convert_file_with_details", fake_convert_with_details)
    worker = conversion.ConversionWorker([failed_url, later_url], batch_size=1)

    worker.run()

    assert attempted == [failed_url, later_url]
    assert worker.failed_files == {failed_url}
    assert worker.unattempted_files == set()
    assert worker.processing_backends == {later_url: conversion.BACKEND_DEFUDDLE}


def test_conversion_worker_emits_finished_when_cancelled_while_paused(conversion):
    worker = conversion.ConversionWorker(["scan.pdf"], batch_size=1)
    worker.is_paused = True
    worker.is_cancelled = True
    finished: list[dict] = []
    worker.finished.connect(lambda results: finished.append(results))

    worker.run()

    assert finished == [{}]


def test_conversion_worker_reuses_markitdown_instance_for_native_files(
    monkeypatch,
    conversion,
):
    constructions: list[dict[str, object]] = []
    converted: list[str] = []

    class FakeMarkItDown:
        def __init__(self, **kwargs):
            constructions.append(kwargs)

        def convert(self, file_path):
            converted.append(file_path)
            return types.SimpleNamespace(markdown=f"# {file_path}")

    monkeypatch.setitem(
        sys.modules,
        "markitdown",
        types.SimpleNamespace(MarkItDown=FakeMarkItDown),
    )

    worker = conversion.ConversionWorker(
        ["first.txt", "second.txt", "third.txt"],
        batch_size=10,
    )
    completed: list[tuple[str, bool]] = []
    started: list[str] = []
    worker.itemStarted.connect(started.append)
    worker.itemFinished.connect(
        lambda source, _outcome, failed: completed.append((source, failed))
    )

    worker.run()

    assert constructions == [{}]
    assert converted == ["first.txt", "second.txt", "third.txt"]
    assert started == ["first.txt", "second.txt", "third.txt"]
    assert completed == [
        ("first.txt", False),
        ("second.txt", False),
        ("third.txt", False),
    ]


def test_run_tesseract_ocr_resets_executable_path_when_custom_path_is_cleared(
    monkeypatch,
    conversion,
):
    pytesseract_impl = types.SimpleNamespace(tesseract_cmd="tesseract")
    fake_pytesseract = types.SimpleNamespace(
        pytesseract=pytesseract_impl,
        image_to_string=lambda *_args, **_kwargs: "ocr text",
    )

    monkeypatch.setitem(sys.modules, "pytesseract", fake_pytesseract)

    first_result = conversion._run_tesseract_ocr(
        object(),
        conversion.ConversionOptions(tesseract_path=" /custom/tesseract "),
    )
    second_result = conversion._run_tesseract_ocr(
        object(),
        conversion.ConversionOptions(),
    )

    assert first_result == "ocr text"
    assert second_result == "ocr text"
    assert pytesseract_impl.tesseract_cmd == "tesseract"
