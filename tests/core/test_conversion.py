from markitdowngui.core import conversion


def test_convert_file_uses_markitdown_when_ocr_disabled(monkeypatch):
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


def test_convert_image_prefers_docintel_when_configured(monkeypatch):
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


def test_convert_image_falls_back_to_local_ocr(monkeypatch):
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


def test_convert_pdf_keeps_native_text_when_available(monkeypatch):
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


def test_convert_pdf_falls_back_to_docintel(monkeypatch):
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


def test_convert_pdf_falls_back_to_local_ocr_after_docintel_failure(monkeypatch):
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
