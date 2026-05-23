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

