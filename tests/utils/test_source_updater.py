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
        python_executable="C:/Python/python.exe",
        uv_executable="uv",
    )

    root_arg = source_updater.quote_command_arg(str(root))
    python_arg = source_updater.quote_command_arg("C:/Python/python.exe")
    uv_arg = source_updater.quote_command_arg("uv")
    assert command == (
        f"git -C {root_arg} pull --ff-only && "
        f"{uv_arg} pip install --python {python_arg} -e {root_arg}"
    )


def test_build_source_update_command_falls_back_to_python(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    command = source_updater.build_source_update_command(
        root,
        python_executable="python",
        uv_executable="",
    )

    root_arg = source_updater.quote_command_arg(str(root))
    python_arg = source_updater.quote_command_arg("python")
    assert command == (
        f"git -C {root_arg} pull --ff-only && "
        f"{python_arg} -m pip install -e {root_arg}"
    )


def test_build_source_update_command_quotes_shell_metacharacters(tmp_path):
    root = tmp_path / "R&D;repo"
    root.mkdir()

    command = source_updater.build_source_update_command(
        root,
        python_executable="/opt/python&tools/python",
        uv_executable="/opt/tools/u;v",
    )

    root_arg = source_updater.quote_command_arg(str(root))
    python_arg = source_updater.quote_command_arg("/opt/python&tools/python")
    uv_arg = source_updater.quote_command_arg("/opt/tools/u;v")
    assert command == (
        f"git -C {root_arg} pull --ff-only && "
        f"{uv_arg} pip install --python {python_arg} -e {root_arg}"
    )
    assert root_arg != str(root)
    assert python_arg != "/opt/python&tools/python"
    assert uv_arg != "/opt/tools/u;v"


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
        lambda command, **_kwargs: calls.append(command)
        or subprocess.CompletedProcess(command, 0, stdout=""),
    )

    result = source_updater.run_source_update(
        root,
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert result == 0
    assert calls == [
        [
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        ["git", "-C", str(root), "pull", "--ff-only"],
        [
            "uv",
            "pip",
            "install",
            "--python",
            source_updater.sys.executable,
            "-e",
            str(root),
        ],
    ]
    assert progress == [
        ("Checking source checkout", 5),
        ("Pulling latest source", 15),
        ("Reinstalling app", 70),
        ("Source update complete", 100),
    ]


def test_run_source_update_stops_when_checkout_has_local_changes(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "repo"
    root.mkdir()
    calls: list[list[str]] = []
    progress: list[tuple[str, int]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=" M README.md\n")

    monkeypatch.setattr(source_updater.subprocess, "run", fake_run)

    result = source_updater.run_source_update(
        root,
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert result == source_updater.SOURCE_UPDATE_DIRTY
    assert calls == [
        [
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ]
    ]
    assert progress == [("Checking source checkout", 5)]


def test_run_source_update_ignores_untracked_files(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        if command[:4] == ["git", "-C", str(root), "status"]:
            return subprocess.CompletedProcess(command, 0, stdout="")
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(source_updater.subprocess, "run", fake_run)
    monkeypatch.setattr(source_updater.shutil, "which", lambda _name: "")

    result = source_updater.run_source_update(root)

    assert result == source_updater.SOURCE_UPDATE_OK
    assert calls[0] == [
        "git",
        "-C",
        str(root),
        "status",
        "--porcelain",
        "--untracked-files=no",
    ]
    assert calls[1] == ["git", "-C", str(root), "pull", "--ff-only"]


def test_run_source_update_returns_command_failure(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    progress: list[tuple[str, int]] = []

    def fail(command, **_kwargs):
        raise subprocess.CalledProcessError(23, command)

    monkeypatch.setattr(source_updater.subprocess, "run", fail)

    result = source_updater.run_source_update(
        root,
        progress_callback=lambda status, value: progress.append((status, value)),
    )

    assert result == 23
    assert progress == [("Checking source checkout", 5)]
