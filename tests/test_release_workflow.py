import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


@pytest.fixture
def workflow():
    # BaseLoader retains the GitHub Actions `on` key instead of YAML 1.1's boolean.
    return yaml.load(Path(".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader)


def step(workflow, name):
    return next(item for item in workflow["jobs"]["build"]["steps"] if item.get("name") == name)


def test_validation_builds_keep_release_permissions_behind_tag_push_guard(workflow):
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["on"]["push"]["branches"] == ["codex/package-validation-*"]
    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert workflow["jobs"]["release"]["if"] == (
        "github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')"
    )
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["env"]["UV_PYTHON"] == "3.10"
    assert workflow["jobs"]["build"]["strategy"]["matrix"]["os"] == [
        "ubuntu-latest", "macos-latest", "windows-latest",
    ]


@pytest.mark.parametrize(
    ("event", "ref", "expected"),
    [
        ("push", "refs/tags/v1.2.3", "1.2.3"),
        ("push", "refs/tags/v.1.2.3", "1.2.3"),
        ("push", "refs/heads/codex/package-validation-test", None),
        ("workflow_dispatch", "refs/tags/v9.9.9", None),
    ],
)
def test_build_version_uses_tag_only_for_tag_pushes(workflow, tmp_path, event, ref, expected):
    script = step(workflow, "Set build version")["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    package = tmp_path / "markitdowngui"
    package.mkdir()
    init = package / "__init__.py"
    init.write_text('__version__ = "0.0.0"\n')
    environment_file = tmp_path / "github-env"
    environment = {
        **os.environ,
        "GITHUB_REF": ref,
        "GITHUB_EVENT_NAME": event,
        "GITHUB_ENV": str(environment_file),
    }

    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, env=environment,
        capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    expected = expected or importlib.metadata.version("markitdowngui")
    assert environment_file.read_text() == f"BUILD_VERSION={expected}\n"
    assert init.read_text() == f'__version__ = "{expected}"\n'


def test_build_version_rejects_invalid_tag_before_writing_files(workflow, tmp_path):
    script = step(workflow, "Set build version")["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    package = tmp_path / "markitdowngui"
    package.mkdir()
    init = package / "__init__.py"
    init.write_text('__version__ = "0.0.0"\n')
    environment_file = tmp_path / "github-env"

    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path,
        env={
            **os.environ,
            "GITHUB_REF": "refs/tags/v../../escape",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_ENV": str(environment_file),
        },
        capture_output=True, text=True,
    )

    assert result.returncode != 0
    assert not environment_file.exists()
    assert init.read_text() == '__version__ = "0.0.0"\n'


def test_installed_artifacts_are_checked_before_upload_with_failure_reports(workflow):
    names = [item.get("name") for item in workflow["jobs"]["build"]["steps"]]
    assert names.index("Build Windows installer") < names.index("Check installed Windows app") < names.index("Upload artifact")
    assert names.index("Build Linux AppImage") < names.index("Check extracted Linux AppImage") < names.index("Upload artifact")
    windows = step(workflow, "Check installed Windows app")["run"]
    linux = step(workflow, "Check extracted Linux AppImage")["run"]
    assert "Start-Process" in windows and "-Wait -PassThru" in windows
    assert "$process.ExitCode -ne 0" in windows
    assert "$LASTEXITCODE -ne 0" in windows
    assert "--executable $installedApp" in windows
    assert "windows-installed-backends.json" in windows
    assert "--appimage-extract" in linux
    assert '"$extract_dir/squashfs-root/AppRun"' in linux
    assert "xvfb-run -a" in linux and "--qt-platform xcb" in linux
    assert "linux-appimage-backends.json" in linux
    reports = step(workflow, "Upload package check reports")
    assert reports["if"] == "always()"
    assert reports["with"]["path"] == "package-check-reports/"
    assert int(reports["with"]["retention-days"]) > 0
