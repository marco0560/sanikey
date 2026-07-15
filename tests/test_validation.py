"""Repository validation command tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


def _load_validate_repo_module() -> ModuleType:
    """Load ``scripts/validate_repo.py`` as a test module.

    Parameters
    ----------
    None

    Returns
    -------
    types.ModuleType
        Loaded validation script module.
    """

    script = Path(__file__).resolve().parents[1] / "scripts" / "validate_repo.py"
    spec = importlib.util.spec_from_file_location("validate_repo", script)
    if spec is None or spec.loader is None:
        message = "impossibile caricare scripts/validate_repo.py"
        raise AssertionError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_repo_includes_privacy_guard() -> None:
    """Verify standard validation runs the tracked-content privacy guard.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    validate_repo = _load_validate_repo_module()
    commands = validate_repo.build_validation_commands(python="python")

    assert commands[0][-1] == "scripts/privacy_guard.py"
