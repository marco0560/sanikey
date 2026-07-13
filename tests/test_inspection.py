"""Document inspection tests."""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

from sanikey.config import PersonConfig
from sanikey.documents import ExtractedText, scan_documents
from sanikey.inspection import (
    extraction_warning_messages,
    inspect_patient_documents,
)

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
    assert "estrazione testo DOCX non riuscita" in result.preflight_warning_messages[0]


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


def test_inspect_patient_documents_preflight_reports_image_ocr_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify preflight reports missing image OCR providers.

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
    path = person.source_documents / "20260102 Photo.jpg"
    path.write_bytes(b"image")
    monkeypatch.setattr("sanikey.documents.shutil.which", lambda _: None)

    result = inspect_patient_documents(person, preflight=True)

    assert result.preflight_warning_messages == (
        f"{path}: Tesseract non installato; OCR immagine saltato",
    )


def test_inspect_patient_documents_can_stage_containers(tmp_path: Path) -> None:
    """Verify inspection optionally stages containers for manual review.

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

    result = inspect_patient_documents(person, stage_containers=True)

    assert result.container_staging is not None
    assert len(result.container_staging.members) == 1
    assert result.container_staging.documents[0].internal_path == "report.txt"


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
    path = person.source_documents / "20260102 Blob.bin"
    path.write_bytes(b"binary")
    document = scan_documents(person)[0]
    extracted = ExtractedText(
        document_id=document.document_id,
        text="",
        warnings=(
            "estrazione testo non supportata per .bin",
            "custom extraction warning",
        ),
    )

    warnings = extraction_warning_messages((document,), (extracted,))

    assert warnings == (f"{path}: custom extraction warning",)
