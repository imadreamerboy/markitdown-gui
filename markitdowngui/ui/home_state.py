def next_state_after_queue_change(*, has_results: bool, has_files: bool) -> str | None:
    if not has_files:
        return "empty"
    if has_results:
        return "queue"
    return None
