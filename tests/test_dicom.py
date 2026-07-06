"""DICOM catalog tests."""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import sanikey.dicom as dicom_module
from sanikey.config import PersonConfig
from sanikey.dicom import catalog_dicom_studies
from sanikey.documents import scan_documents

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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


def test_catalog_dicom_studies_links_manual_expansion(tmp_path: Path) -> None:
    """Verify ISO support links to manually expanded generated directory.

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
    (person.source_documents / "20260102 Study.iso").write_bytes(b"iso")
    extracted = person.local_build / "dicom" / "20260102 Study"
    extracted.mkdir(parents=True)
    (extracted / "index.html").write_text("<html></html>", encoding="utf-8")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_iso"
    assert studies[0].extracted_path == extracted
    assert studies[0].viewer_paths == (extracted / "index.html",)
    assert studies[0].warnings == ()


def test_catalog_dicom_studies_accepts_img_disk_images(tmp_path: Path) -> None:
    """Verify IMG disk images are cataloged as DICOM supports.

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
    (person.source_documents / "20260102 Study.img").write_bytes(b"img")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_img"


def test_catalog_dicom_studies_warns_when_expansion_missing(tmp_path: Path) -> None:
    """Verify missing manual expansion is a warning, not deletion or failure.

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
    path = person.source_documents / "20260102 Study.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("DICOMDIR", "synthetic")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_zip"
    assert studies[0].extracted_path is None
    assert studies[0].warnings


def test_catalog_dicom_studies_ignores_regular_zip_archives(tmp_path: Path) -> None:
    """Verify regular ZIP archives are not DICOM supports by extension alone.

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
        archive.writestr("report.txt", "synthetic")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert studies == ()


def test_catalog_dicom_studies_detects_dicom_zip_by_magic(tmp_path: Path) -> None:
    """Verify ZIP members with DICOM magic are cataloged as DICOM support.

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
    path = person.source_documents / "20260102 Study.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("IM000001", (b"\0" * 128) + b"DICM")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_zip"


def test_catalog_dicom_studies_detects_dicom_7z_disk_image(tmp_path: Path) -> None:
    """Verify 7z archives with ISO members are cataloged as DICOM support.

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
    source_file = tmp_path / "Study.iso"
    source_file.write_text("synthetic", encoding="utf-8")
    path = person.source_documents / "20260102 Study.7z"
    with py7zr.SevenZipFile(path, "w") as archive:
        archive.write(source_file, arcname="Study.iso")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_7z"


def test_catalog_dicom_studies_detects_nested_dicom_zip(tmp_path: Path) -> None:
    """Verify ZIP archives with nested DICOM ZIP members are cataloged.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    import io

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    nested_bytes = io.BytesIO()
    with zipfile.ZipFile(nested_bytes, "w") as nested:
        nested.writestr("Study/Slice0001.dcm", "synthetic")
    path = person.source_documents / "20260102 Nested Study.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("payload/study.zip", nested_bytes.getvalue())

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_zip"


def test_catalog_dicom_studies_detects_dicom_rar_by_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify RAR archives can be promoted to DICOM support.

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

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Study.rar").write_bytes(b"rar")
    monkeypatch.setattr(dicom_module, "_rar_contains_dicom", lambda _path: True)

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_rar"
