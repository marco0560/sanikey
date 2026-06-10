"""CLI smoke tests."""

from __future__ import annotations

import subprocess
import sys

MODULE = "sanikey"


def test_module_help_runs() -> None:
    """Verify the module help exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", MODULE, "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "sanikey" in result.stdout


def test_info_subcommand_runs() -> None:
    """Verify the example info subcommand exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", MODULE, "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "project=sanikey" in result.stdout
