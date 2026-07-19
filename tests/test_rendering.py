"""Tests for browser-openable consultation document representations."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sanikey.config import PersonConfig
from sanikey.documents import DocumentRecordOrigin, document_record_for_path
from sanikey.exports import generate_exports
from sanikey.metadata import load_curated_metadata
from sanikey.rendering import prepare_consultation_documents

if TYPE_CHECKING:
    from pathlib import Path


def _person(tmp_path: Path) -> PersonConfig:
    """Build a synthetic patient configuration.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    sanikey.config.PersonConfig
        Isolated patient configuration.
    """

    return PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=tmp_path / "documents",
        metadata_directory=tmp_path / "metadata",
        local_build=tmp_path / "generated",
        usb_uuid="1A2B-3C4D",
    )


def test_prepare_consultation_documents_copies_container_pdf(tmp_path: Path) -> None:
    """Verify an extracted PDF becomes a local consultation document.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir()
    container = person.source_documents / "support.zip"
    container.write_bytes(b"archive")
    staged_root = tmp_path / "staging"
    staged_root.mkdir()
    pdf = staged_root / "referto.pdf"
    pdf.write_bytes(b"%PDF-synthetic")
    container_record = document_record_for_path(
        container, root=person.source_documents, patient_id=person.id
    )
    record = document_record_for_path(
        pdf,
        root=staged_root,
        patient_id=person.id,
        provenance=DocumentRecordOrigin(
            origin="container",
            container_id=container_record.document_id,
            internal_path="referto.pdf",
        ),
    )

    result = prepare_consultation_documents(person, (record,))
    exported = generate_exports(
        person, (record,), load_curated_metadata(person.metadata_directory)
    )
    documents = json.loads(exported.documents.read_text(encoding="utf-8"))

    assert result.rendered_document_ids == (record.document_id,)
    assert documents[0]["href"].startswith("../rendered-documents/")
    assert (person.local_build / documents[0]["href"][3:]).is_file()


def test_generate_exports_lists_non_openable_documents_by_extension(
    tmp_path: Path,
) -> None:
    """Verify non-openable records are removed from consultation and listed technically.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir()
    archive = person.source_documents / "archive.zip"
    archive.write_bytes(b"archive")
    binary = person.source_documents / "legacy.bin"
    binary.write_bytes(b"binary")
    records = tuple(
        document_record_for_path(
            path, root=person.source_documents, patient_id=person.id
        )
        for path in (archive, binary)
    )

    exported = generate_exports(
        person, records, load_curated_metadata(person.metadata_directory)
    )
    technical = (
        person.local_build / "technical" / "documenti-non-apribili.csv"
    ).read_text(encoding="utf-8")

    assert json.loads(exported.documents.read_text(encoding="utf-8")) == []
    assert technical.index('".bin"') < technical.index('".zip"')
    assert "legacy.bin" in technical
    assert "archive.zip" in technical
