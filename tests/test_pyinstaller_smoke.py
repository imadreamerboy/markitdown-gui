import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.packaging]


@pytest.mark.skipif(
    os.environ.get("MARKITDOWNGUI_RUN_PYINSTALLER_SMOKE") != "1",
    reason="Set MARKITDOWNGUI_RUN_PYINSTALLER_SMOKE=1 to run the packaging smoke test.",
)
def test_pyinstaller_builds_markitdown_bundle(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    dist_path = tmp_path / "dist"
    build_path = tmp_path / "build"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "MarkItDown.spec",
            "--clean",
            "--noconfirm",
            "--distpath",
            str(dist_path),
            "--workpath",
            str(build_path),
        ],
        cwd=project_root,
        check=True,
    )

    executable_name = "MarkItDown.exe" if os.name == "nt" else "MarkItDown"
    executable_path = dist_path / "MarkItDown" / executable_name
    assert executable_path.exists()
