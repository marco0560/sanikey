"""Document inventory and extraction tests."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from sanikey.config import PersonConfig
from sanikey.documents import (
    duplicate_document_warnings,
    extract_text,
    find_duplicate_documents,
    scan_document_inventory,
    scan_documents,
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


def test_scan_documents_builds_stable_records(tmp_path: Path) -> None:
    """Verify scanner derives category, date, title, kind, and digest.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    document_dir = person.source_documents / "laboratory"
    document_dir.mkdir(parents=True)
    (document_dir / "20260102 Blood Test.txt").write_text(
        "Synthetic text",
        encoding="utf-8",
    )

    documents = scan_documents(person)

    assert len(documents) == 1
    assert documents[0].patient_id == "patient-a"
    assert documents[0].category == "laboratory"
    assert documents[0].date == "2026-01-02"
    assert documents[0].title == "Blood Test"
    assert documents[0].kind == "text"
    assert len(documents[0].sha256) == 64


def test_duplicate_detection_skips_duplicate_content_with_warning(
    tmp_path: Path,
) -> None:
    """Verify duplicate content is reported and skipped for ingestion.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    document_dir = person.source_documents / "reports"
    document_dir.mkdir(parents=True)
    (document_dir / "20260102 A.txt").write_text("same", encoding="utf-8")
    (document_dir / "20260103 B.txt").write_text("same", encoding="utf-8")

    inventory = scan_document_inventory(person)
    documents = scan_documents(person)
    duplicates = find_duplicate_documents(inventory)
    warnings = duplicate_document_warnings(duplicates)

    assert len(inventory) == 2
    assert len(documents) == 1
    assert documents[0].path.name == "20260102 A.txt"
    assert len(duplicates) == 1
    assert len(next(iter(duplicates.values()))) == 2
    assert "20260103 B.txt" in warnings[0]
    assert "20260102 A.txt" in warnings[0]


def test_extract_text_reads_text_files(tmp_path: Path) -> None:
    """Verify supported text files are extracted directly.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    document_dir = person.source_documents
    document_dir.mkdir(parents=True)
    path = document_dir / "note.txt"
    path.write_text("hello", encoding="utf-8")
    document = scan_documents(person)[0]

    extracted = extract_text(document)

    assert extracted.text == "hello"
    assert extracted.warnings == ()


def test_extract_text_warns_for_dicom_support(tmp_path: Path) -> None:
    """Verify DICOM support files are catalog-only in v1.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    document_dir = person.source_documents
    document_dir.mkdir(parents=True)
    path = document_dir / "20260102 Study.iso"
    path.write_bytes(b"not a real iso")
    document = scan_documents(person)[0]

    extracted = extract_text(replace(document, path=path))

    assert extracted.text == ""
    assert extracted.warnings
