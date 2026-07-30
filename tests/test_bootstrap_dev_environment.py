"""Behaviour contract for the development bootstrap script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_bootstrap_module() -> object:
    """Load the bootstrap script as an importable module.

    Returns
    -------
    object
        Loaded bootstrap module.
    """

    path = REPO_ROOT / "scripts" / "bootstrap_dev_environment.py"
    spec = importlib.util.spec_from_file_location("bootstrap_dev_environment", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_system_dependency_commands_install_missing_fedora_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Fedora installs only the missing declared host tools.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    bootstrap = load_bootstrap_module()
    available = {"dnf": "/usr/bin/dnf", "sudo": "/usr/bin/sudo"}
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: available.get(name),
    )

    commands = bootstrap.system_dependency_commands(repo_root=REPO_ROOT)

    assert len(commands) == 1
    assert commands[0].argv == (
        "sudo",
        "dnf",
        "install",
        "--assumeyes",
        "uv",
        "pandoc",
    )


def test_system_dependency_commands_are_empty_when_tools_are_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a prepared host does not receive another system install.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    bootstrap = load_bootstrap_module()
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: "/usr/bin/tool")

    assert bootstrap.system_dependency_commands(repo_root=REPO_ROOT) == []


def test_bootstrap_plan_installs_managed_python_before_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Python 3.13 is ensured before uv synchronizes dependencies.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    bootstrap = load_bootstrap_module()
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: "/usr/bin/tool")
    commands = bootstrap.build_bootstrap_commands(
        repo_root=REPO_ROOT,
        options=bootstrap.BootstrapOptions(with_docs=True, run_validation=False),
    )

    assert commands[0].argv == ("uv", "python", "install", "3.13")
    assert commands[1].argv == ("uv", "sync", "--group", "dev", "--extra", "docs")
