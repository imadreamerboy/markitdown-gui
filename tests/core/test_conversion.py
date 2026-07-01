import importlib
import io
import sys
import types

import pytest


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


def _install_fake_docx_dependencies(
    monkeypatch,
    *,
    convert_to_html,
    markdownify=lambda html: html,
    pre_process_docx=lambda stream: stream,
):
    mammoth_module = types.ModuleType("mammoth")
    mammoth_images_module = types.SimpleNamespace(
        img_element=lambda convert_image: convert_image
    )
    mammoth_module.images = mammoth_images_module
    mammoth_module.convert_to_html = convert_to_html

    markdownify_module = types.ModuleType("markdownify")
    markdownify_module.markdownify = markdownify

    markitdown_package = types.ModuleType("markitdown")
    converter_utils_module = types.ModuleType("markitdown.converter_utils")
    docx_module = types.ModuleType("markitdown.converter_utils.docx")
    pre_process_module = types.ModuleType("markitdown.converter_utils.docx.pre_process")
    pre_process_module.pre_process_docx = pre_process_docx
    markitdown_package.__path__ = []
    converter_utils_module.__path__ = []
    docx_module.__path__ = []
    markitdown_package.converter_utils = converter_utils_module
    converter_utils_module.docx = docx_module
    docx_module.pre_process = pre_process_module

    monkeypatch.setitem(sys.modules, "mammoth", mammoth_module)
    monkeypatch.setitem(sys.modules, "markdownify", markdownify_module)
    monkeypatch.setitem(sys.modules, "markitdown", markitdown_package)
    monkeypatch.setitem(sys.modules, "markitdown.converter_utils", converter_utils_module)
    monkeypatch.setitem(sys.modules, "markitdown.converter_utils.docx", docx_module)
    monkeypatch.setitem(
        sys.modules,
        "markitdown.converter_utils.docx.pre_process",
        pre_process_module,
    )


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

    with pytest.raises(RuntimeError) as exc_info:
        conversion.convert_file("https://example.com/article")

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


def test_convert_pdf_keeps_native_text_when_available(monkeypatch, conversion):
    calls = []

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
        "scan.pdf",
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


def test_convert_docx_with_preserved_images_uses_existing_dependencies(
    monkeypatch,
    conversion,
    tmp_path,
):
    captured = {}
    source_docx = tmp_path / "report.docx"
    source_docx.write_bytes(b"docx")

    class FakeImage:
        content_type = "image/png"

        def open(self):
            return io.BytesIO(b"png")

    def fake_convert_to_html(stream, **kwargs):
        captured["stream"] = stream
        captured["kwargs"] = kwargs
        image_attrs = kwargs["convert_image"](FakeImage())
        captured["image_src"] = image_attrs["src"]
        return types.SimpleNamespace(
            value=f'<p><img src="{image_attrs["src"]}" /></p><p>Text</p>'
        )

    def fake_markdownify(_html):
        return f'![image]({captured["image_src"]})\n\nText'

    preprocessed_stream = io.BytesIO(b"preprocessed")
    _install_fake_docx_dependencies(
        monkeypatch,
        convert_to_html=fake_convert_to_html,
        markdownify=fake_markdownify,
        pre_process_docx=lambda _stream: preprocessed_stream,
    )
    monkeypatch.setattr(
        conversion,
        "_convert_with_markitdown",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("native MarkItDown should not run")
        ),
    )

    outcome = conversion.convert_file_with_details(
        str(source_docx),
        conversion.ConversionOptions(
            preserve_docx_images=True,
            docx_artifacts_dir=str(tmp_path / "artifacts"),
        ),
    )

    assert outcome.backend == conversion.BACKEND_DOCX_IMAGES
    assert outcome.markdown == f'![image]({captured["image_src"]})\n\nText'
    assert captured["stream"] is preprocessed_stream
    assert captured["kwargs"]["ignore_empty_paragraphs"] is False
    assert outcome.assets == [
        conversion.ConversionAsset(
            filename="image-001.png",
            source_path=outcome.assets[0].source_path,
            preview_markdown_path=captured["image_src"],
            page_number=None,
            kind="docx-image",
        )
    ]
    assert outcome.assets[0].source_path is not None
    assert captured["image_src"] == outcome.assets[0].preview_markdown_path
    assert captured["image_src"].endswith("/image-001.png")
    assert (tmp_path / "artifacts").is_dir()
    assert io.open(outcome.assets[0].source_path, "rb").read() == b"png"


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
):
    calls = []

    def fake_convert(_file_path, _options, use_docintel=False):
        calls.append(use_docintel)
        if not use_docintel:
            raise RuntimeError("native parser failed")
        return ""

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_local_ocr",
        lambda *_args, **_kwargs: "local pdf text",
    )

    result = conversion.convert_file(
        "scan.pdf",
        conversion.ConversionOptions(ocr_enabled=True),
    )

    assert result == "local pdf text"
    assert calls == [False]


def test_convert_pdf_falls_back_to_local_ocr_after_docintel_failure(monkeypatch, conversion):
    calls = []

    def fake_convert(_file_path, _options, use_docintel=False):
        calls.append(use_docintel)
        if use_docintel:
            raise RuntimeError("azure unavailable")
        return ""

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_local_ocr",
        lambda *_args, **_kwargs: "local pdf text",
    )

    result = conversion.convert_file(
        "scan.pdf",
        conversion.ConversionOptions(
            ocr_enabled=True,
            docintel_endpoint="https://example.cognitiveservices.azure.com/",
        ),
    )

    assert result == "local pdf text"
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
):
    def fake_convert(_file_path, _options, use_docintel=False):
        if use_docintel:
            raise RuntimeError("azure auth failed")
        return ""

    monkeypatch.setattr(conversion, "_convert_with_markitdown", fake_convert)
    monkeypatch.setattr(
        conversion,
        "_convert_pdf_with_local_ocr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("Local OCR failed. Install Tesseract or set its path in Settings.")
        ),
    )

    with pytest.raises(RuntimeError) as exc_info:
        conversion.convert_file(
            "scan.pdf",
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
        text_content = "azure text"

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
        text_content = "azure text"

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
    def fake_convert_with_details(file_path, _options):
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
    def fake_convert_with_details(file_path, _options):
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


def test_conversion_worker_emits_finished_when_cancelled_while_paused(conversion):
    worker = conversion.ConversionWorker(["scan.pdf"], batch_size=1)
    worker.is_paused = True
    worker.is_cancelled = True
    finished: list[dict] = []
    worker.finished.connect(lambda results: finished.append(results))

    worker.run()

    assert finished == [{}]


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
