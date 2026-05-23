from markitdowngui.ui_qml.controller import AppController


def test_controller_add_url_rejects_invalid_url():
    controller = AppController()
    messages: list[tuple[str, str]] = []
    controller.toastRequested.connect(lambda kind, message: messages.append((kind, message)))

    controller.addUrl("not a url")

    assert controller.queue_model.rowCount() == 0
    assert messages == [("error", "Enter a valid http:// or https:// URL.")]


def test_controller_add_url_queues_valid_url():
    controller = AppController()

    controller.addUrl("https://example.com/article")

    assert controller.queue_model.sources() == ["https://example.com/article"]
    assert controller.hasQueue is True

