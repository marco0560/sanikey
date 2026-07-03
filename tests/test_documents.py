"""Document inventory and extraction tests."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

import sanikey.documents as documents_module
from sanikey.config import PersonConfig
from sanikey.documents import (
    duplicate_document_warnings,
    extract_text,
    find_duplicate_documents,
    scan_document_inventory,
    scan_documents,
)


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
    warning_lines = warnings[0].splitlines()
    assert len(warning_lines) == 3
    assert warning_lines[0].startswith(
        "duplicate document content skipped. The following files are identical (sha256="
    )
    assert warning_lines[1].endswith("20260102 A.txt")
    assert warning_lines[2].endswith("20260103 B.txt")


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


def test_extract_text_uses_ocrmypdf_when_pymupdf_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify system OCRmyPDF is a PDF extraction fallback.

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
    document_dir = person.source_documents
    document_dir.mkdir(parents=True)
    path = document_dir / "20260102 Report.pdf"
    path.write_bytes(b"%PDF synthetic")
    document = scan_documents(person)[0]

    def fake_run(command, **_kwargs):
        sidecar = Path(command[command.index("--sidecar") + 1])
        sidecar.write_text("ocr text", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(
        documents_module, "_extract_pdf_text_with_pymupdf", lambda _: None
    )
    monkeypatch.setattr(documents_module.shutil, "which", lambda _: "/usr/bin/ocrmypdf")
    monkeypatch.setattr(documents_module.subprocess, "run", fake_run)

    extracted = extract_text(document)

    assert extracted.text == "ocr text"
    assert extracted.warnings == ()


def test_extract_text_keeps_sufficient_pymupdf_text(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify sufficient PyMuPDF text avoids OCR.

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
    document_dir = person.source_documents
    document_dir.mkdir(parents=True)
    path = document_dir / "20260102 Report.pdf"
    path.write_bytes(b"%PDF synthetic")
    document = scan_documents(person)[0]

    monkeypatch.setattr(
        documents_module,
        "_extract_pdf_text_with_pymupdf",
        lambda item: documents_module.ExtractedText(
            document_id=item.document_id,
            text="This is enough extracted text from a digital PDF document.",
        ),
    )
    monkeypatch.setattr(documents_module.shutil, "which", lambda _: None)

    extracted = extract_text(document)

    assert extracted.text.startswith("This is enough")
    assert extracted.warnings == ()


def test_extract_text_uses_ocr_when_pymupdf_text_is_insufficient(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify weak PyMuPDF extraction falls back to OCRmyPDF.

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
    document_dir = person.source_documents
    document_dir.mkdir(parents=True)
    path = document_dir / "20260102 Report.pdf"
    path.write_bytes(b"%PDF synthetic")
    document = scan_documents(person)[0]

    def fake_run(command, **_kwargs):
        sidecar = Path(command[command.index("--sidecar") + 1])
        sidecar.write_text("ocr text after weak native extraction", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(
        documents_module,
        "_extract_pdf_text_with_pymupdf",
        lambda item: documents_module.ExtractedText(
            document_id=item.document_id,
            text="   \n",
        ),
    )
    monkeypatch.setattr(documents_module.shutil, "which", lambda _: "/usr/bin/ocrmypdf")
    monkeypatch.setattr(documents_module.subprocess, "run", fake_run)

    extracted = extract_text(document)

    assert extracted.text == "ocr text after weak native extraction"
    assert extracted.warnings == ()


def test_extract_text_warns_when_pymupdf_text_is_insufficient_without_ocr(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify weak PyMuPDF extraction warns when OCR is unavailable.

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
    document_dir = person.source_documents
    document_dir.mkdir(parents=True)
    path = document_dir / "20260102 Report.pdf"
    path.write_bytes(b"%PDF synthetic")
    document = scan_documents(person)[0]

    monkeypatch.setattr(
        documents_module,
        "_extract_pdf_text_with_pymupdf",
        lambda item: documents_module.ExtractedText(
            document_id=item.document_id,
            text="short",
        ),
    )
    monkeypatch.setattr(documents_module.shutil, "which", lambda _: None)

    extracted = extract_text(document)

    assert extracted.text == "short"
    assert extracted.warnings == (
        "PyMuPDF extracted insufficient text and no OCR provider is available",
    )


def test_extract_text_warns_when_no_pdf_provider_is_available(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify missing PDF providers produce a generic actionable warning.

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
    document_dir = person.source_documents
    document_dir.mkdir(parents=True)
    path = document_dir / "20260102 Report.pdf"
    path.write_bytes(b"%PDF synthetic")
    document = scan_documents(person)[0]

    monkeypatch.setattr(
        documents_module, "_extract_pdf_text_with_pymupdf", lambda _: None
    )
    monkeypatch.setattr(documents_module.shutil, "which", lambda _: None)

    extracted = extract_text(document)

    assert extracted.text == ""
    assert extracted.warnings == (
        "No PDF text extraction provider available; install PyMuPDF "
        "or configure OCRmyPDF",
    )


def test_extract_text_warns_when_ocrmypdf_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify OCRmyPDF failures are reported without hiding provider availability.

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
    document_dir = person.source_documents
    document_dir.mkdir(parents=True)
    path = document_dir / "20260102 Report.pdf"
    path.write_bytes(b"%PDF synthetic")
    document = scan_documents(person)[0]

    def fake_run(command, **_kwargs):
        return subprocess.CompletedProcess(command, 2, "", "ocr failed")

    monkeypatch.setattr(
        documents_module, "_extract_pdf_text_with_pymupdf", lambda _: None
    )
    monkeypatch.setattr(documents_module.shutil, "which", lambda _: "/usr/bin/ocrmypdf")
    monkeypatch.setattr(documents_module.subprocess, "run", fake_run)

    extracted = extract_text(document)

    assert extracted.text == ""
    assert extracted.warnings == (
        "OCRmyPDF failed; PDF text extraction skipped: ocr failed",
    )
