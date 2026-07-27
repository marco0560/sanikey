"""Verify the repository-local SaniKey release safety contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_git_config_module() -> object:
    """Load the standalone Git configuration installer for inspection.

    Parameters
    ----------
    None

    Returns
    -------
    object
        Loaded module object exposing the alias inventory.
    """
    path = REPO_ROOT / "scripts" / "install_repo_git_config.py"
    spec = importlib.util.spec_from_file_location("sanikey_git_config", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_aliases_use_guarded_python_entrypoints() -> None:
    """Ensure bootstrap installs the guarded release aliases.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    module = load_git_config_module()
    aliases = dict(module.git_alias_entries())
    assert aliases["alias.release-audit"] == "!uv run python -m scripts.release_audit"
    assert (
        aliases["alias.release-check"]
        == "!uv run python -m scripts.release_system_selfcheck"
    )
    assert aliases["alias.rel"] == "!uv run python -m scripts.release_rel"


def test_pre_push_blocks_main_and_runs_privacy_guard() -> None:
    """Ensure direct main pushes cannot bypass SaniKey privacy protection.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    hook = (REPO_ROOT / ".githooks" / "pre-push").read_text(encoding="utf-8")
    assert "ALLOW_MAIN_PUSH" in hook
    assert "git rel" in hook
    assert "privacy_guard.py" in hook
    assert "scripts.release_audit" in hook


def test_release_tools_exist() -> None:
    """Ensure the guarded release commands remain available.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    for script in (
        "release_audit.py",
        "release_rel.py",
        "release_system_selfcheck.py",
    ):
        assert (REPO_ROOT / "scripts" / script).is_file()
