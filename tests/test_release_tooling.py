"""Verify the repository-local SaniKey release safety contract."""

from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_RELEASE_PACKAGES = {
    "@semantic-release/changelog",
    "@semantic-release/commit-analyzer",
    "@semantic-release/git",
    "@semantic-release/github",
    "@semantic-release/release-notes-generator",
    "conventional-changelog-conventionalcommits",
    "semantic-release",
}


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


def test_release_build_dependencies_and_tooling_are_pinned() -> None:
    """Ensure local release checks have a wheel builder and pinned tooling.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert "wheel>=0.45,<1" in pyproject["dependency-groups"]["dev"]

    package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    dependencies = package["devDependencies"]
    assert dependencies.keys() >= SEMANTIC_RELEASE_PACKAGES
    assert all(dependencies[name][0].isdigit() for name in SEMANTIC_RELEASE_PACKAGES)


def test_semantic_release_creates_versioned_changelog_releases() -> None:
    """Ensure GitHub owns tags, release numbers, and changelog updates.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    configuration = (REPO_ROOT / ".releaserc.json").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    release_command = (REPO_ROOT / "scripts" / "release_rel.py").read_text(
        encoding="utf-8"
    )

    assert '"branches": ["main"]' in configuration
    assert '"tagFormat": "v${version}"' in configuration
    assert '"type": "feat", "release": "minor"' in configuration
    assert '"type": "fix", "release": "patch"' in configuration
    assert "CHANGELOG.md" in configuration
    assert "npx semantic-release" in workflow
    assert "contents: write" in workflow
    semantic_release_job = workflow.split("  build-manual:", maxsplit=1)[0]
    assert (
        'git describe --tags --exact-match --match "v[0-9]*"'
        not in semantic_release_job
    )
    assert "npx semantic-release" in semantic_release_job
    assert "--no-isolation" not in release_command
    assert 'run(["git", "push"], env=environment)' in release_command
    assert "uv run sanikey -V" in release_command
