from markitdowngui.ui.home_state import next_state_after_queue_change


def test_queue_change_clears_results_to_empty_state_when_no_files_remain():
    assert next_state_after_queue_change(has_results=True, has_files=False) == "empty"


def test_queue_change_returns_to_queue_when_results_are_invalidated():
    assert next_state_after_queue_change(has_results=True, has_files=True) == "queue"


def test_queue_change_keeps_current_state_when_results_are_already_clear():
    assert next_state_after_queue_change(has_results=False, has_files=True) is None
