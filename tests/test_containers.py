"""Container staging tests."""

from __future__ import annotations

import subprocess
import zipfile
from typing import TYPE_CHECKING

import pytest

import sanikey.containers as containers_module
from sanikey.config import PersonConfig
from sanikey.containers import (
    _extract_container,
    _extract_with_7z,
    _safe_member_path,
    stage_container_documents,
)
from sanikey.documents import document_record_for_path

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


def _document(path: Path, root: Path):
    """Build a document record for tests.

    Parameters
    ----------
    path : pathlib.Path
        Document path.
    root : pathlib.Path
        Source root.

    Returns
    -------
    sanikey.models.DocumentRecord
        Document record.
    """

    return document_record_for_path(path, root=root, patient_id="patient-a")


def test_stage_container_documents_writes_empty_manifest_without_containers(
    tmp_path: Path,
) -> None:
    """Verify staging handles patients without containers.

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
    path = person.source_documents / "20260102 Report.txt"
    path.write_text("synthetic", encoding="utf-8")

    result = stage_container_documents(
        person, (_document(path, person.source_documents),)
    )

    assert result.documents == ()
    assert result.members == ()
    assert result.warning_messages == ()
    assert result.manifest.is_file()
    assert '"members": []' in result.manifest.read_text(encoding="utf-8")


def test_stage_container_documents_skips_already_processed_container(
    tmp_path: Path,
) -> None:
    """Verify duplicate queued containers are processed once.

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
    path = person.source_documents / "20260102 Archive.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("inner.txt", "synthetic")
    document = _document(path, person.source_documents)

    result = stage_container_documents(person, (document, document))

    assert len(result.documents) == 1
    assert len(result.members) == 1


def test_stage_container_documents_skips_zip_directories(tmp_path: Path) -> None:
    """Verify ZIP directory entries are ignored during staging.

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
    path = person.source_documents / "20260102 Archive.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("folder/", "")
        archive.writestr("folder/inner.txt", "synthetic")

    result = stage_container_documents(
        person,
        (_document(path, person.source_documents),),
    )

    assert [document.internal_path for document in result.documents] == [
        "folder/inner.txt"
    ]


def test_stage_container_documents_filters_technical_members(
    tmp_path: Path,
) -> None:
    """Verify extracted technical files stay out of document ingestion.

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
    path = person.source_documents / "20260102 Viewer.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("report.txt", "synthetic report")
        archive.writestr("Viewer-Windows/jre/bin/java.dll", b"binary")

    result = stage_container_documents(
        person,
        (_document(path, person.source_documents),),
    )

    assert [document.internal_path for document in result.documents] == ["report.txt"]
    assert [member.internal_path for member in result.members] == [
        "Viewer-Windows/jre/bin/java.dll",
        "report.txt",
    ]


def test_stage_container_documents_warns_for_unsafe_zip_member(
    tmp_path: Path,
) -> None:
    """Verify unsafe ZIP member paths become staging warnings.

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
    path = person.source_documents / "20260102 Archive.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../evil.txt", "synthetic")

    result = stage_container_documents(
        person,
        (_document(path, person.source_documents),),
    )

    assert result.documents == ()
    assert "unsafe container member path" in result.warning_messages[0]


def test_stage_container_documents_extracts_7z_archive(tmp_path: Path) -> None:
    """Verify 7z archives are staged.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    import py7zr

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    source_file = tmp_path / "inner.txt"
    source_file.write_text("synthetic", encoding="utf-8")
    path = person.source_documents / "20260102 Archive.7z"
    with py7zr.SevenZipFile(path, "w") as archive:
        archive.write(source_file, arcname="inner.txt")

    result = stage_container_documents(
        person,
        (_document(path, person.source_documents),),
    )

    assert result.warning_messages == ()
    assert result.documents[0].internal_path == "inner.txt"
    assert result.documents[0].path.read_text(encoding="utf-8") == "synthetic"


def test_stage_container_documents_warns_for_invalid_rar(tmp_path: Path) -> None:
    """Verify invalid RAR files become staging warnings.

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
    path = person.source_documents / "20260102 Archive.rar"
    path.write_bytes(b"not a rar archive")

    result = stage_container_documents(
        person,
        (_document(path, person.source_documents),),
    )

    assert result.documents == ()
    assert "container staging failed" in result.warning_messages[0]


def test_extract_with_7z_reports_missing_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ISO extraction reports a missing 7z command.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    monkeypatch.setattr(containers_module.shutil, "which", lambda _name: None)

    with pytest.raises(ValueError, match="7z command not installed"):
        _extract_with_7z(tmp_path / "image.iso", tmp_path / "target")


def test_extract_with_7z_reports_failed_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ISO extraction reports 7z failures.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    def fake_run(*_args, **_kwargs):
        """Return a failed subprocess result.

        Parameters
        ----------
        *_args : object
            Positional arguments ignored by the fake.
        **_kwargs : object
            Keyword arguments ignored by the fake.

        Returns
        -------
        subprocess.CompletedProcess[str]
            Failed command result.
        """

        return subprocess.CompletedProcess(
            args=("7z",),
            returncode=2,
            stdout="",
            stderr="synthetic 7z failure",
        )

    monkeypatch.setattr(containers_module.shutil, "which", lambda _name: "/usr/bin/7z")
    monkeypatch.setattr(containers_module.subprocess, "run", fake_run)

    with pytest.raises(ValueError, match="synthetic 7z failure"):
        _extract_with_7z(tmp_path / "image.iso", tmp_path / "target")


def test_extract_container_rejects_unsupported_suffix(tmp_path: Path) -> None:
    """Verify unsupported container suffixes are rejected.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    root = tmp_path / "documents"
    root.mkdir()
    path = root / "20260102 Archive.tar"
    path.write_bytes(b"tar")
    document = _document(path, root)

    with pytest.raises(ValueError, match="unsupported container format .tar"):
        _extract_container(document, tmp_path / "target")


def test_safe_member_path_rejects_absolute_paths(tmp_path: Path) -> None:
    """Verify absolute member paths are unsafe.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    with pytest.raises(ValueError, match="unsafe container member path"):
        _safe_member_path(tmp_path, "/absolute.txt")
