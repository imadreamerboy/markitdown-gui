from pathlib import Path
import shutil
import types

from markitdowngui.core import pdf_pipeline


class _FakeRect:
    def __init__(self, *args):
        if len(args) == 1:
            x0, y0, x1, y1 = args[0]
        else:
            x0, y0, x1, y1 = args
        self.x0 = float(x0)
        self.y0 = float(y0)
        self.x1 = float(x1)
        self.y1 = float(y1)

    def intersects(self, other) -> bool:
        return not (
            self.x1 <= other.x0
            or other.x1 <= self.x0
            or self.y1 <= other.y0
            or other.y1 <= self.y0
        )


class _FakeLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, message: str) -> None:
        self.infos.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def test_extract_pdf_markdown_merges_text_and_tables(monkeypatch):
    class FakeTable:
        bbox = (0, 40, 100, 90)

        def extract(self):
            return [["A", "B"], ["1", "2"]]

    class FakePage:
        def find_tables(self):
            return types.SimpleNamespace(tables=[FakeTable()])

        def get_text(self, kind, sort=True):
            assert kind == "dict"
            assert sort is True
            return {
                "blocks": [
                    {
                        "bbox": (0, 0, 100, 20),
                        "lines": [{"spans": [{"text": "Intro"}]}],
                    },
                    {
                        "bbox": (0, 45, 100, 80),
                        "lines": [{"spans": [{"text": "inside table"}]}],
                    },
                    {
                        "bbox": (0, 100, 100, 120),
                        "lines": [{"spans": [{"text": "Outro"}]}],
                    },
                ]
            }

    class FakeDocument:
        def __iter__(self):
            return iter([FakePage()])

        def close(self):
            pass

    fake_pymupdf = types.SimpleNamespace(
        open=lambda _path: FakeDocument(),
        Rect=_FakeRect,
    )
    monkeypatch.setattr(pdf_pipeline, "_import_pymupdf", lambda *_args, **_kwargs: fake_pymupdf)

    markdown = pdf_pipeline.extract_pdf_markdown("scan.pdf")

    assert "Intro" in markdown
    assert "|A|B|" in markdown
    assert "inside table" not in markdown
    assert "Outro" in markdown


def test_extract_pdf_image_assets_deduplicates_identical_images(monkeypatch):
    temp_dirs = set()
    logger = _FakeLogger()

    class FakePage:
        def get_images(self, full=True):
            assert full is True
            return [(11,), (22,)]

    class FakeDocument:
        def __iter__(self):
            return iter([FakePage()])

        def extract_image(self, xref):
            return {
                "image": b"a" * 4096,
                "width": 128,
                "height": 128,
                "ext": "png",
            }

        def close(self):
            pass

    fake_pymupdf = types.SimpleNamespace(
        open=lambda _path: FakeDocument(),
        Rect=_FakeRect,
        Matrix=lambda x, y: (x, y),
    )
    monkeypatch.setattr(pdf_pipeline, "_import_pymupdf", lambda *_args, **_kwargs: fake_pymupdf)

    assets = pdf_pipeline.extract_pdf_image_assets(
        "scan.pdf",
        min_width=64,
        min_height=64,
        min_bytes=2048,
        logger=logger,
    )
    temp_dirs.update({str(Path(asset.temp_path).parent) for asset in assets})

    try:
        assert len(assets) == 2
        assert assets[0].temp_path == assets[1].temp_path
        assert any("Deduplicated PDF image" in message for message in logger.infos)
    finally:
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_extract_pdf_image_assets_filters_small_images(monkeypatch):
    logger = _FakeLogger()

    class FakePage:
        def get_images(self, full=True):
            return [(11,)]

    class FakeDocument:
        def __iter__(self):
            return iter([FakePage()])

        def extract_image(self, xref):
            return {
                "image": b"a" * 4096,
                "width": 32,
                "height": 32,
                "ext": "png",
            }

        def close(self):
            pass

    fake_pymupdf = types.SimpleNamespace(
        open=lambda _path: FakeDocument(),
        Rect=_FakeRect,
        Matrix=lambda x, y: (x, y),
    )
    monkeypatch.setattr(pdf_pipeline, "_import_pymupdf", lambda *_args, **_kwargs: fake_pymupdf)

    assets = pdf_pipeline.extract_pdf_image_assets(
        "scan.pdf",
        min_width=64,
        min_height=64,
        min_bytes=2048,
        logger=logger,
    )

    assert assets == ()
    assert any("Filtered PDF image" in message for message in logger.infos)


def test_extract_pdf_image_assets_ignores_failed_objects_and_keeps_successful_ones(
    monkeypatch,
):
    temp_dirs = set()
    logger = _FakeLogger()

    class FakePage:
        def get_images(self, full=True):
            return [(11,), (22,)]

    class FakeDocument:
        def __iter__(self):
            return iter([FakePage()])

        def extract_image(self, xref):
            if xref == 11:
                raise RuntimeError("bad image")
            return {
                "image": b"a" * 4096,
                "width": 128,
                "height": 128,
                "ext": "png",
            }

        def close(self):
            pass

    fake_pymupdf = types.SimpleNamespace(
        open=lambda _path: FakeDocument(),
        Rect=_FakeRect,
        Matrix=lambda x, y: (x, y),
    )
    monkeypatch.setattr(pdf_pipeline, "_import_pymupdf", lambda *_args, **_kwargs: fake_pymupdf)

    assets = pdf_pipeline.extract_pdf_image_assets(
        "scan.pdf",
        min_width=64,
        min_height=64,
        min_bytes=2048,
        logger=logger,
    )
    temp_dirs.update({str(Path(asset.temp_path).parent) for asset in assets})

    try:
        assert len(assets) == 1
        assert assets[0].page_number == 1
        assert assets[0].image_number == 2
        assert any("Skipping PDF image" in message for message in logger.warnings)
    finally:
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
