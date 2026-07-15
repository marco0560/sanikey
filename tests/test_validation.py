"""Repository validation command tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


def _load_script_module(script_name: str, module_name: str) -> ModuleType:
    """Load a repository script as a test module.

    Parameters
    ----------
    script_name : str
        Script file name under ``scripts/``.
    module_name : str
        Synthetic module name used for the import.

    Returns
    -------
    types.ModuleType
        Loaded script module.

    Raises
    ------
    AssertionError
        If the script import specification cannot be created.
    """

    script = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        message = f"impossibile caricare scripts/{script_name}"
        raise AssertionError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_repo_includes_privacy_guard() -> None:
    """Verify standard validation starts with privacy and Codira checks.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    validate_repo = _load_script_module("validate_repo.py", "validate_repo")
    commands = validate_repo.build_validation_commands(python="python")

    assert commands[0][-1] == "scripts/privacy_guard.py"
    assert commands[1][-2:] == ("codira", "index")
    assert commands[2][-2:] == ("codira", "audit")


def test_run_repo_tool_supports_codira_console_script(tmp_path: Path) -> None:
    """Verify the repository tool wrapper can invoke Codira.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    run_repo_tool = _load_script_module("run_repo_tool.py", "run_repo_tool")
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    python = bin_dir / "python"
    codira = bin_dir / "codira"
    python.write_text("", encoding="utf-8")
    codira.write_text("", encoding="utf-8")

    argv = run_repo_tool.build_tool_argv(
        "codira",
        ("audit",),
        state_root=tmp_path,
        python=str(python),
    )

    assert argv == (str(codira), "audit")
