"""Verify the repository-local SaniKey release safety contract."""

from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

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


def test_pre_push_runs_preview_only_for_guarded_main_pushes() -> None:
    """Ensure direct main pushes cannot bypass SaniKey privacy protection.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    hook = (REPO_ROOT / ".githooks" / "pre-push").read_text(encoding="utf-8")
    assert '[ "${ALLOW_MAIN_PUSH:-}" != "1" ]' in hook
    assert '[ "${ALLOW_MAIN_PUSH:-}" = "1" ]' in hook
    assert "release_preview.py" in hook
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
        "release_preview.py",
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
    release_configuration = json.loads(configuration)
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
    assert [
        "@semantic-release/release-notes-generator",
        {"preset": "conventionalcommits"},
    ] in release_configuration["plugins"]
    assert "CHANGELOG.md" in configuration
    assert "npx semantic-release" in workflow
    assert "contents: write" in workflow
    assert "issues: write" in workflow
    assert "pull-requests: write" in workflow
    assert "workflow_dispatch:" not in workflow
    assert "pypa/gh-action-pypi-publish" not in workflow
    assert "uv sync" not in workflow
    assert "uses: actions/setup-python@v6" in workflow
    assert "python scripts/privacy_guard.py" in workflow
    assert "PYTHONPATH: src" in workflow
    assert "uses: actions/setup-node@v6" in workflow
    assert workflow.index("python scripts/privacy_guard.py") < workflow.index(
        "npx semantic-release"
    )
    assert workflow.index("npm ci") < workflow.index("npx semantic-release")
    assert "--no-isolation" not in release_command
    assert 'run(["git", "push"], env=environment)' in release_command
    assert "uv run sanikey -V" in release_command


def test_release_preview_scopes_github_credentials_to_semantic_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure only the Semantic Release child receives the GitHub environment.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest facility used to observe child-process invocation.

    Returns
    -------
    None
    """
    spec = importlib.util.spec_from_file_location(
        "sanikey_release_preview", REPO_ROOT / "scripts" / "release_preview.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    commands: list[tuple[list[str], Path, bool]] = []

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> SimpleNamespace:
        """Record the exact preview invocation.

        Parameters
        ----------
        command : list[str]
            Child-process command vector.
        cwd : pathlib.Path
            Working directory for the child process.
        check : bool
            Whether subprocess should raise on failure.

        Returns
        -------
        types.SimpleNamespace
            Successful subprocess result.
        """
        commands.append((command, cwd, check))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.main() == 0
    assert commands == [
        (
            [
                "sops",
                "exec-env",
                str(module.GITHUB_ENV),
                "npx semantic-release --dry-run --config .releaserc.json",
            ],
            REPO_ROOT,
            False,
        )
    ]
