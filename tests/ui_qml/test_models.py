from PySide6.QtCore import Qt

from markitdowngui.core.conversion import ConversionOutcome
from markitdowngui.ui_qml.models import QueueModel, ResultModel


def test_queue_model_adds_unique_sources_with_display_roles():
    model = QueueModel()

    added = model.add_sources([
        "C:/tmp/report.pdf",
        "https://example.com/article",
        "C:/tmp/report.pdf",
    ])

    assert added == 2
    assert model.rowCount() == 2
    assert model.data(model.index(0, 0), QueueModel.NameRole) == "report.pdf"
    assert model.data(model.index(1, 0), QueueModel.KindRole) == "URL"


def test_result_model_exposes_backend_and_failure_state():
    model = ResultModel()
    model.set_results(
        {
            "C:/tmp/report.pdf": ConversionOutcome(
                markdown="hello world",
                backend="native",
            )
        },
        {"C:/tmp/report.pdf"},
    )

    index = model.index(0, 0)
    assert model.rowCount() == 1
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "report.pdf"
    assert model.data(index, ResultModel.BackendRole) == "Native"
    assert model.data(index, ResultModel.FailedRole) is True
    assert model.data(index, ResultModel.WordCountRole) == 2


def test_result_model_labels_fast_pdf_results():
    model = ResultModel()
    model.add_result(
        "C:/tmp/report.pdf",
        ConversionOutcome(markdown="fast text", backend="pdf-inspector"),
    )

    assert model.data(model.index(0, 0), ResultModel.BackendRole) == "Fast PDF"


def test_result_model_add_result_preserves_existing_completed_items():
    model = ResultModel()
    model.add_result(
        "C:/tmp/first.pdf",
        ConversionOutcome(markdown="first", backend="native"),
    )
    model.add_result(
        "C:/tmp/second.pdf",
        ConversionOutcome(markdown="second", backend="http-ocr"),
        failed=True,
    )
    model.add_result(
        "C:/tmp/first.pdf",
        ConversionOutcome(markdown="first revised", backend="native"),
    )

    assert model.rowCount() == 2
    assert model.item_at(0).outcome.markdown == "first revised"
    assert model.item_at(1).failed is True
    assert model.data(model.index(1, 0), ResultModel.BackendRole) == "HTTP OCR"


def test_result_model_removes_only_sources_that_are_being_retried():
    model = ResultModel()
    model.set_results(
        {
            "C:/tmp/ok.pdf": ConversionOutcome("ok", backend="native"),
            "C:/tmp/broken.pdf": ConversionOutcome("failed", backend="native"),
        },
        {"C:/tmp/broken.pdf"},
    )

    model.remove_sources({"C:/tmp/broken.pdf"})

    assert model.rowCount() == 1
    assert model.item_at(0).source == "C:/tmp/ok.pdf"
