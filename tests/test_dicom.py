"""DICOM catalog tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sanikey.config import PersonConfig
from sanikey.dicom import catalog_dicom_studies
from sanikey.documents import scan_documents

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


def test_catalog_dicom_studies_links_manual_expansion(tmp_path: Path) -> None:
    """Verify ISO support links to manually expanded generated directory."""

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


def test_catalog_dicom_studies_warns_when_expansion_missing(tmp_path: Path) -> None:
    """Verify missing manual expansion is a warning, not deletion or failure."""

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Study.zip").write_bytes(b"zip")

    studies = catalog_dicom_studies(person, scan_documents(person))

    assert len(studies) == 1
    assert studies[0].support_kind == "dicom_zip"
    assert studies[0].extracted_path is None
    assert studies[0].warnings
