import subprocess

from markitdowngui.utils import source_updater


def test_find_source_root_finds_git_checkout(tmp_path):
    root = tmp_path / "repo"
    package_dir = root / "markitdowngui" / "utils"
    package_dir.mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    start = package_dir / "source_updater.py"
    start.write_text("", encoding="utf-8")

    assert source_updater.find_source_root(start) == root


def test_build_source_update_command_prefers_uv(tmp_path):
    root = tmp_path / "repo with spaces"
    root.mkdir()

    command = source_updater.build_source_update_command(
        root,
        python_executable="python",
        uv_executable="uv",
    )

    assert command == (
        f'git -C "{root}" pull --ff-only && uv pip install -e "{root}"'
    )


def test_build_source_update_command_falls_back_to_python(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    command = source_updater.build_source_update_command(
        root,
        python_executable="python",
        uv_executable="",
    )

    assert command == (
        f"git -C {root} pull --ff-only && "
        f"python -m pip install -e {root}"
    )


def test_run_source_update_reports_progress_with_uv(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    calls: list[list[str]] = []
    progress: list[tuple[str, int]] = []

    monkeypatch.setattr(
        source_updater.shutil,
        "which",
        lambda name: "uv" if name == "uv" else None,
    )
    monkeypatch.setattr(
        source_updater.subprocess,
        "run",
        lambda command, check: calls.append(command),
    )

    result = source_updater.run_source_update(
        root,
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert result == 0
    assert calls == [
        ["git", "-C", str(root), "pull", "--ff-only"],
        ["uv", "pip", "install", "-e", str(root)],
    ]
    assert progress == [
        ("Pulling latest source", 15),
        ("Reinstalling app", 70),
        ("Source update complete", 100),
    ]


def test_run_source_update_returns_command_failure(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    progress: list[tuple[str, int]] = []

    def fail(command, check):
        raise subprocess.CalledProcessError(23, command)

    monkeypatch.setattr(source_updater.subprocess, "run", fail)

    result = source_updater.run_source_update(
        root,
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert result == 23
    assert progress == [("Pulling latest source", 15)]
