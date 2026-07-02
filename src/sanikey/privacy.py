"""Privacy guardrails for local real-data paths."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .errors import PrivacyError

if TYPE_CHECKING:
    from .config import AccountsConfig, PersonConfig

LOCAL_DATA_DIRS = ("config", "patients", "generated", "exports", "logs", "local-data")
GIT_EXE = shutil.which("git")


def _fail(message: str) -> None:
    """Raise a privacy error.

    Parameters
    ----------
    message : str
        Diagnostic message.

    Returns
    -------
    None

    Raises
    ------
    PrivacyError
        Always raised.
    """

    raise PrivacyError(message)


def validate_privacy(config: AccountsConfig, *, repo_root: Path) -> None:
    """Validate repository privacy invariants for real-data paths.

    Parameters
    ----------
    config : AccountsConfig
        Loaded accounts configuration.
    repo_root : pathlib.Path
        Repository root.

    Returns
    -------
    None

    Raises
    ------
    PrivacyError
        If real-data paths are tracked or unsafe.
    """

    resolved_root = repo_root.resolve()
    _validate_local_data_dirs_ignored(resolved_root)
    for person in config.people:
        _validate_person_paths(person, repo_root=resolved_root)


def _validate_local_data_dirs_ignored(repo_root: Path) -> None:
    """Validate local real-data directories are not tracked.

    Parameters
    ----------
    repo_root : pathlib.Path
        Repository root.

    Returns
    -------
    None

    Raises
    ------
    PrivacyError
        If Git reports local real-data directories as tracked.
    """

    tracked = _tracked_paths(repo_root)
    violations = sorted(
        path for path in tracked if path.parts and path.parts[0] in LOCAL_DATA_DIRS
    )
    if violations:
        rendered = ", ".join(str(path) for path in violations[:10])
        _fail(f"real-data paths are tracked by Git: {rendered}")


def _validate_person_paths(person: PersonConfig, *, repo_root: Path) -> None:
    """Validate one patient's configured real-data paths.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    repo_root : pathlib.Path
        Repository root.

    Returns
    -------
    None

    Raises
    ------
    PrivacyError
        If configured real-data paths point into versioned repository content.
    """

    for field_name, path in (
        ("source_documents", person.source_documents),
        ("metadata_directory", person.metadata_directory),
        ("local_build", person.local_build),
    ):
        resolved = path.resolve(strict=False)
        if _is_inside(resolved, repo_root):
            relative = resolved.relative_to(repo_root)
            if not relative.parts or relative.parts[0] not in LOCAL_DATA_DIRS:
                _fail(
                    f"{person.id}.{field_name} points inside versioned repository "
                    f"content: {resolved}",
                )


def _tracked_paths(repo_root: Path) -> set[Path]:
    """Return Git-tracked paths relative to the repository root.

    Parameters
    ----------
    repo_root : pathlib.Path
        Repository root.

    Returns
    -------
    set[pathlib.Path]
        Tracked paths.

    Raises
    ------
    PrivacyError
        If Git is unavailable or fails.
    """

    if GIT_EXE is None:
        _fail("git executable not found")
    git_exe = cast("str", GIT_EXE)
    completed = subprocess.run(
        [git_exe, "ls-files"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        _fail(completed.stderr.strip() or "git ls-files failed")
    return {Path(line) for line in completed.stdout.splitlines() if line}


def _is_inside(path: Path, parent: Path) -> bool:
    """Return whether a path resolves inside a parent directory.

    Parameters
    ----------
    path : pathlib.Path
        Candidate path.
    parent : pathlib.Path
        Parent directory.

    Returns
    -------
    bool
        ``True`` when ``path`` is equal to or inside ``parent``.
    """

    return path == parent or parent in path.parents
