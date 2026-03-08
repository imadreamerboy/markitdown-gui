import importlib
import sys
import types

import pytest


class _FakeSignal:
    def __init__(self, *_args, **_kwargs):
        pass

    def connect(self, _callback):
        pass

    def emit(self, *_args, **_kwargs):
        pass


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


def test_test_azure_ocr_connection_uses_api_key_credential(monkeypatch, conversion):
    captured = {}

    class FakeAzureKeyCredential:
        def __init__(self, key):
            self.key = key

    class FakeClient:
        def __init__(self, *, endpoint, credential):
            captured["endpoint"] = endpoint
            captured["credential"] = credential
            captured["closed"] = False

        def get_resource_details(self):
            captured["tested"] = True
            return object()

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
    assert captured["tested"] is True
    assert captured["closed"] is True


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
