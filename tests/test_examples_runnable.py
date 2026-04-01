"""
Smoke test: every example script exits cleanly.

Runs each examples/*/main.py as a subprocess and asserts exit code 0
with no tracebacks in stderr.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

_example_dirs = sorted(d for d in EXAMPLES_DIR.iterdir() if d.is_dir() and (d / "main.py").exists())


@pytest.mark.parametrize(
    "example_dir",
    _example_dirs,
    ids=[d.name for d in _example_dirs],
)
def test_example_runs_cleanly(example_dir: Path) -> None:
    main_py = example_dir / "main.py"
    result = subprocess.run(
        [sys.executable, str(main_py)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"{example_dir.name}/main.py exited with code {result.returncode}\n"
        f"stdout:\n{result.stdout[-500:]}\n"
        f"stderr:\n{result.stderr[-500:]}"
    )
    assert "Traceback" not in result.stderr, (
        f"{example_dir.name}/main.py had a traceback in stderr:\n{result.stderr[-500:]}"
    )
