"""Document inspection tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sanikey.config import PersonConfig
from sanikey.documents import ExtractedText, scan_documents
from sanikey.inspection import (
    extraction_warning_messages,
    inspect_patient_documents,
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


def test_inspect_patient_documents_preflight_reports_office_warnings(
    tmp_path: Path,
) -> None:
    """Verify preflight reports lightweight extraction warnings.

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
    path = person.source_documents / "20260102 Broken.docx"
    path.write_bytes(b"not a docx")

    result = inspect_patient_documents(person, preflight=True)

    assert result.preflight_warning_messages
    assert str(path) in result.preflight_warning_messages[0]
    assert "DOCX text extraction failed" in result.preflight_warning_messages[0]


def test_inspect_patient_documents_preflight_skips_non_lightweight_files(
    tmp_path: Path,
) -> None:
    """Verify preflight skips files that require build-time extraction.

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
    (person.source_documents / "20260102 Report.pdf").write_bytes(b"%PDF-1.7\n")
    (person.source_documents / "20260103 Legacy.doc").write_bytes(b"legacy")
    (person.source_documents / "20260104 Notes.txt").write_text(
        "notes",
        encoding="utf-8",
    )

    result = inspect_patient_documents(person, preflight=True)

    assert result.preflight_warning_messages == ()


def test_extraction_warning_messages_filters_static_warnings(tmp_path: Path) -> None:
    """Verify extraction warnings do not duplicate static warnings.

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
    path = person.source_documents / "20260102 Photo.jpg"
    path.write_bytes(b"image")
    document = scan_documents(person)[0]
    extracted = ExtractedText(
        document_id=document.document_id,
        text="",
        warnings=(
            "unsupported text extraction for .jpg",
            "custom extraction warning",
        ),
    )

    warnings = extraction_warning_messages((document,), (extracted,))

    assert warnings == (f"{path}: custom extraction warning",)
