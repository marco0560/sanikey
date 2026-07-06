"""Source document integrity snapshots."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .config import PersonConfig


@dataclass(frozen=True)
class SourceIntegrityResult:
    """Result of a source document integrity operation.

    Parameters
    ----------
    patient_id : str
        Patient identifier.
    sha256_path : pathlib.Path
        SHA256 snapshot path.
    mtime_path : pathlib.Path
        Modification-time snapshot path.
    status : str
        Operation status.
    """

    patient_id: str
    sha256_path: Path
    mtime_path: Path
    status: str


def write_source_snapshot(
    person: PersonConfig,
    *,
    label: str,
    output_dir: Path,
) -> SourceIntegrityResult:
    """Write source document checksum and mtime snapshots.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    label : str
        Snapshot label, usually ``before`` or ``after``.
    output_dir : pathlib.Path
        Directory where snapshot files are written.

    Returns
    -------
    SourceIntegrityResult
        Written snapshot paths.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    sha256_path, mtime_path = source_snapshot_paths(
        person.id,
        label=label,
        output_dir=output_dir,
    )
    files = _source_files(person.source_documents)
    sha256_path.write_text(
        "".join(f"{_sha256(path)}  {_snapshot_path(path)}\n" for path in files),
        encoding="utf-8",
    )
    mtime_path.write_text(
        "".join(f"{_snapshot_path(path)}\t{path.stat().st_mtime}\n" for path in files),
        encoding="utf-8",
    )
    return SourceIntegrityResult(
        patient_id=person.id,
        sha256_path=sha256_path,
        mtime_path=mtime_path,
        status="written",
    )


def check_source_snapshots(
    person: PersonConfig,
    *,
    output_dir: Path,
) -> SourceIntegrityResult:
    """Compare before and after source document snapshots.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    output_dir : pathlib.Path
        Directory containing snapshot files.

    Returns
    -------
    SourceIntegrityResult
        Check result with status ``ok`` or ``changed``.

    Raises
    ------
    FileNotFoundError
        If any required snapshot file is missing.
    """

    before_sha256, before_mtime = source_snapshot_paths(
        person.id,
        label="before",
        output_dir=output_dir,
    )
    after_sha256, after_mtime = source_snapshot_paths(
        person.id,
        label="after",
        output_dir=output_dir,
    )
    _require_snapshot(before_sha256)
    _require_snapshot(before_mtime)
    _require_snapshot(after_sha256)
    _require_snapshot(after_mtime)
    status = (
        "ok"
        if before_sha256.read_text(encoding="utf-8")
        == after_sha256.read_text(encoding="utf-8")
        and before_mtime.read_text(encoding="utf-8")
        == after_mtime.read_text(encoding="utf-8")
        else "changed"
    )
    return SourceIntegrityResult(
        patient_id=person.id,
        sha256_path=after_sha256,
        mtime_path=after_mtime,
        status=status,
    )


def source_snapshot_paths(
    patient_id: str,
    *,
    label: str,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Return checksum and mtime snapshot paths.

    Parameters
    ----------
    patient_id : str
        Patient identifier.
    label : str
        Snapshot label.
    output_dir : pathlib.Path
        Snapshot directory.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path]
        SHA256 and mtime snapshot paths.
    """

    return (
        output_dir / f"{patient_id}-{label}.sha256",
        output_dir / f"{patient_id}-{label}-mtime.tsv",
    )


def _source_files(root: Path) -> tuple[Path, ...]:
    """Return sorted source document files.

    Parameters
    ----------
    root : pathlib.Path
        Source document root.

    Returns
    -------
    tuple[pathlib.Path, ...]
        Sorted file paths.
    """

    if not root.exists():
        return ()
    return tuple(sorted(path for path in root.rglob("*") if path.is_file()))


def _sha256(path: Path) -> str:
    """Compute a file SHA256 digest.

    Parameters
    ----------
    path : pathlib.Path
        File to hash.

    Returns
    -------
    str
        Hex digest.
    """

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_path(path: Path) -> str:
    """Return the path representation stored in snapshots.

    Parameters
    ----------
    path : pathlib.Path
        File path.

    Returns
    -------
    str
        POSIX-style path string.
    """

    return path.as_posix()


def _require_snapshot(path: Path) -> None:
    """Require a snapshot file to exist.

    Parameters
    ----------
    path : pathlib.Path
        Snapshot path.

    Returns
    -------
    None

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    """

    if not path.is_file():
        raise FileNotFoundError(path)
