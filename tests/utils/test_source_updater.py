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


def test_build_source_update_command_uses_the_shared_updater(tmp_path):
    root = tmp_path / "repo with spaces"
    command = source_updater.build_source_update_command(
        root,
        python_executable="C:/Python/python.exe",
        uv_executable="uv",
    )
    arguments = [
        "C:/Python/python.exe", "-m", "markitdowngui.utils.source_updater",
        "--source-root", str(root), "--uv-executable", "uv",
    ]
    assert command == " ".join(source_updater.quote_command_arg(arg) for arg in arguments)


def test_build_source_update_command_preserves_explicit_pip_selection(tmp_path):
    command = source_updater.build_source_update_command(
        tmp_path, python_executable="python", uv_executable="",
    )
    assert command.endswith("--uv-executable " + source_updater.quote_command_arg(""))


def test_build_source_update_command_quotes_shell_metacharacters(tmp_path):
    root = tmp_path / "R&D;repo"
    command = source_updater.build_source_update_command(
        root,
        python_executable="/opt/python&tools/python",
        uv_executable="/opt/tools/u;v",
    )
    arguments = [
        "/opt/python&tools/python", "-m", "markitdowngui.utils.source_updater",
        "--source-root", str(root), "--uv-executable", "/opt/tools/u;v",
    ]
    assert command == " ".join(source_updater.quote_command_arg(arg) for arg in arguments)
    assert source_updater.quote_command_arg(str(root)) != str(root)


def test_run_source_update_reports_progress_with_uv(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "requirements.txt").write_text("pyjwt==2.15.1\n", encoding="utf-8")
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
            "--no-deps",
            "-r",
            str(root / "requirements.txt"),
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
    (root / "requirements.txt").write_text("pyjwt==2.15.1\n", encoding="utf-8")
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
    assert calls[2] == [
        source_updater.sys.executable,
        "-m",
        "pip",
        "install",
        "--no-deps",
        "-r",
        str(root / "requirements.txt"),
        "-e",
        str(root),
    ]


def test_run_source_update_rejects_missing_requirements_before_pull(
    monkeypatch, tmp_path, capsys,
):
    root = tmp_path / "repo"
    root.mkdir()
    calls: list[list[str]] = []
    monkeypatch.setattr(
        source_updater.subprocess,
        "run",
        lambda command, **_kwargs: calls.append(command)
        or subprocess.CompletedProcess(command, 0, stdout=""),
    )

    assert source_updater.run_source_update(root) == source_updater.SOURCE_UPDATE_FAILED
    assert len(calls) == 1
    assert calls[0][:4] == ["git", "-C", str(root), "status"]
    assert str(root / "requirements.txt") in capsys.readouterr().err


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


def test_qt_migration_removes_shared_essentials_before_pinned_install(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "requirements.txt").write_text("pyside6-essentials==6.12.0\n", encoding="utf-8")
    monkeypatch.setattr(source_updater, "_installed_version", lambda _name: "6.9.1")
    calls = []
    monkeypatch.setattr(source_updater.subprocess, "run", lambda command, **kwargs:
        calls.append(command) or subprocess.CompletedProcess(command, 0, stdout=""))

    assert source_updater.run_source_update(root, uv_executable="uv") == 0
    assert calls[2] == ["uv", "pip", "uninstall", "--python", source_updater.sys.executable,
                        "PySide6", "PySide6-Addons", "PySide6-Essentials"]
    assert calls[3][:5] == ["uv", "pip", "install", "--python", source_updater.sys.executable]
    assert "--no-deps" in calls[3]


def test_qt_migration_uses_pip_in_the_active_interpreter(monkeypatch, tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pyside6-essentials==6.12.0\n", encoding="utf-8")
    monkeypatch.setattr(source_updater, "_installed_version", lambda name:
        "6.9.1" if name in {"PySide6-Addons", "PySide6-Essentials"} else None)
    calls = []
    monkeypatch.setattr(source_updater.subprocess, "run", lambda command, **kwargs: calls.append(command))
    source_updater._migrate_legacy_qt(requirements, "")
    assert calls == [[source_updater.sys.executable, "-m", "pip", "uninstall", "--yes",
                      "PySide6-Addons", "PySide6-Essentials"]]


def test_qt_migration_skips_an_essentials_only_environment(monkeypatch, tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pyside6-essentials==6.12.0\n", encoding="utf-8")
    monkeypatch.setattr(source_updater, "_installed_version", lambda name:
        "6.12.0" if name == "PySide6-Essentials" else None)
    calls = []
    monkeypatch.setattr(source_updater.subprocess, "run", lambda command, **kwargs: calls.append(command))
    source_updater._migrate_legacy_qt(requirements, "uv")
    assert calls == []


def test_qt_migration_does_not_remove_full_qt_when_target_still_requires_it(monkeypatch, tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pyside6==6.12.0\npyside6-essentials==6.12.0\n", encoding="utf-8")
    monkeypatch.setattr(source_updater, "_installed_version", lambda _name: "6.9.1")
    calls = []
    monkeypatch.setattr(source_updater.subprocess, "run", lambda command, **kwargs: calls.append(command))
    source_updater._migrate_legacy_qt(requirements, "uv")
    assert calls == []


def test_qt_migration_stops_on_uninstall_failure(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "requirements.txt").write_text("pyside6-essentials==6.12.0\n", encoding="utf-8")
    monkeypatch.setattr(source_updater, "_installed_version", lambda _name: "6.9.1")
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        if "uninstall" in command:
            raise subprocess.CalledProcessError(19, command)
        return subprocess.CompletedProcess(command, 0, stdout="")
    monkeypatch.setattr(source_updater.subprocess, "run", run)
    assert source_updater.run_source_update(root, uv_executable="uv") == 19
    assert len(calls) == 3
    assert "uninstall" in calls[-1]


def test_qt_migration_retains_compatible_full_qt_distributions(monkeypatch, tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pyside6-essentials==6.12.0\n", encoding="utf-8")
    # Compatible Addons may be required by a separately installed WebEngine.
    monkeypatch.setattr(source_updater, "_installed_version", lambda _name: "6.12.0")
    calls = []
    monkeypatch.setattr(source_updater.subprocess, "run", lambda command, **kwargs: calls.append(command))
    source_updater._migrate_legacy_qt(requirements, "uv")
    assert calls == []
