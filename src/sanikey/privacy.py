"""Privacy guardrails for local real-data paths."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .errors import PrivacyError

if TYPE_CHECKING:
    from .config import AccountsConfig, PersonConfig

LOCAL_DATA_DIRS = ("config", "patients", "generated", "exports", "logs", "local-data")
GIT_EXE = shutil.which("git")
MAX_PRIVACY_SCAN_BYTES = 2 * 1024 * 1024
PRIVATE_PATH_RE = re.compile(
    r"""
    file:///(?:home|Users)/[^\s|"'`<>)\]]+
    |/(?:home|Users)/[^\s|"'`<>)\]]+
    |[A-Za-z]:\\Users\\[^\s|"'`<>)\]]+
    |\$(?:HOME|\{HOME\})/[^\s|"'`<>)\]]+
    """,
    re.VERBOSE,
)


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


def validate_tracked_privacy(*, repo_root: Path) -> None:
    """Validate privacy invariants for content that could enter a commit.

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
        If commit-candidate content includes private data directories or
        host-local path literals.
    """

    resolved_root = repo_root.resolve()
    _validate_local_data_dirs_ignored(resolved_root)
    _validate_tracked_private_literals(resolved_root)


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

    tracked = _commit_candidate_paths(repo_root)
    violations = sorted(
        path for path in tracked if path.parts and path.parts[0] in LOCAL_DATA_DIRS
    )
    if violations:
        rendered = ", ".join(str(path) for path in violations[:10])
        _fail(f"percorsi dati reali tracciati da Git: {rendered}")


def _validate_tracked_private_literals(repo_root: Path) -> None:
    """Validate commit-candidate files do not contain host-local path literals.

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
        If a commit-candidate text file contains a path literal tied to a user
        host.
    """

    violations: list[str] = []
    for relative in sorted(_commit_candidate_paths(repo_root)):
        path = repo_root / relative
        if not path.is_file():
            continue
        content = _read_privacy_scan_text(path)
        if content is None:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            match = PRIVATE_PATH_RE.search(line)
            if match is not None:
                violations.append(f"{relative}:{line_number}: {match.group(0)}")
                break

    if violations:
        rendered = "; ".join(violations[:10])
        _fail(f"riferimenti privati in file tracciati: {rendered}")


def _read_privacy_scan_text(path: Path) -> str | None:
    """Read a file when it is suitable for textual privacy scanning.

    Parameters
    ----------
    path : pathlib.Path
        Candidate file.

    Returns
    -------
    str | None
        Text content, or ``None`` for binary or oversized files.
    """

    try:
        stat = path.stat()
    except OSError:
        return None
    if stat.st_size > MAX_PRIVACY_SCAN_BYTES:
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    return raw.decode("utf-8", errors="replace")


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
                    f"{person.id}.{field_name} punta dentro contenuto versionato "
                    f"del repository: {resolved}",
                )


def _commit_candidate_paths(repo_root: Path) -> set[Path]:
    """Return tracked and unignored paths relative to the repository root.

    Parameters
    ----------
    repo_root : pathlib.Path
        Repository root.

    Returns
    -------
    set[pathlib.Path]
        Paths that are tracked already or visible to Git as unignored new files.

    Raises
    ------
    PrivacyError
        If Git is unavailable or fails.
    """

    if GIT_EXE is None:
        _fail("eseguibile git non trovato")
    git_exe = cast("str", GIT_EXE)
    completed = subprocess.run(
        [git_exe, "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        _fail(completed.stderr.strip() or "git ls-files non riuscito")
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
