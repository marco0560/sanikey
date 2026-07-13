"""Source integrity snapshot tests."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from sanikey.config import PersonConfig
from sanikey.integrity import (
    _require_snapshot,
    _snapshot_path,
    _source_files,
    check_source_snapshots,
    source_snapshot_paths,
    write_source_snapshot,
)

if TYPE_CHECKING:
    from pathlib import Path


def _person(tmp_path: Path) -> PersonConfig:
    """Build a synthetic patient config.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    PersonConfig
        Patient configuration.
    """

    return PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=tmp_path / "documents",
        metadata_directory=tmp_path / "metadata",
        local_build=tmp_path / "generated",
        usb_uuid="1A2B-3C4D",
    )


def test_source_snapshot_paths_are_deterministic(tmp_path: Path) -> None:
    """Verify source snapshot filenames are derived from patient and label.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    sha256_path, mtime_path = source_snapshot_paths(
        "patient-a",
        label="before",
        output_dir=tmp_path,
    )

    assert sha256_path == tmp_path / "patient-a-before.sha256"
    assert mtime_path == tmp_path / "patient-a-before-mtime.tsv"


def test_write_source_snapshot_records_sorted_files_and_digests(
    tmp_path: Path,
) -> None:
    """Verify snapshot files contain sorted paths, mtimes, and digests.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    nested = person.source_documents / "z"
    nested.mkdir(parents=True)
    first = person.source_documents / "a.txt"
    second = nested / "b.txt"
    first.write_text("alpha", encoding="utf-8")
    second.write_text("beta", encoding="utf-8")

    result = write_source_snapshot(person, label="before", output_dir=tmp_path)

    expected_first = hashlib.sha256(b"alpha").hexdigest()
    expected_second = hashlib.sha256(b"beta").hexdigest()
    assert result.status == "written"
    assert result.sha256_path.read_text(encoding="utf-8").splitlines() == [
        f"{expected_first}  {first.as_posix()}",
        f"{expected_second}  {second.as_posix()}",
    ]
    assert result.mtime_path.read_text(encoding="utf-8").splitlines() == [
        f"{first.as_posix()}\t{first.stat().st_mtime}",
        f"{second.as_posix()}\t{second.stat().st_mtime}",
    ]


def test_check_source_snapshots_reports_ok_and_changed(tmp_path: Path) -> None:
    """Verify integrity checks compare both checksum and mtime snapshots.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    source = person.source_documents / "report.txt"
    source.write_text("before", encoding="utf-8")
    write_source_snapshot(person, label="before", output_dir=tmp_path)
    write_source_snapshot(person, label="after", output_dir=tmp_path)

    ok = check_source_snapshots(person, output_dir=tmp_path)

    source.write_text("after", encoding="utf-8")
    write_source_snapshot(person, label="after", output_dir=tmp_path)
    changed = check_source_snapshots(person, output_dir=tmp_path)

    assert ok.status == "ok"
    assert changed.status == "changed"


def test_source_files_handles_missing_root_and_snapshot_requirement(
    tmp_path: Path,
) -> None:
    """Verify missing source roots and missing snapshots are explicit.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    missing = tmp_path / "missing"

    assert _source_files(missing) == ()
    assert _snapshot_path(missing / "nested" / "file.txt").endswith(
        "missing/nested/file.txt"
    )
    with pytest.raises(FileNotFoundError):
        _require_snapshot(missing / "patient-before.sha256")


def test_check_source_snapshots_requires_existing_files(tmp_path: Path) -> None:
    """Verify integrity checks fail when a required snapshot is absent.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)

    with pytest.raises(FileNotFoundError):
        check_source_snapshots(person, output_dir=tmp_path)
