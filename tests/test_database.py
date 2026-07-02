"""SQLite archive generation tests."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from sanikey.config import PersonConfig
from sanikey.database import build_database, database_path
from sanikey.dicom import catalog_dicom_studies
from sanikey.documents import scan_documents
from sanikey.metadata import load_curated_metadata
from sanikey.models import CuratedMetadata, TherapyEpisode

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


def test_build_database_inserts_documents_metadata_and_dicom(tmp_path: Path) -> None:
    """Verify database build creates per-patient SQLite archive.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    documents_dir = person.source_documents / "laboratory"
    documents_dir.mkdir(parents=True)
    (documents_dir / "20260102 Blood Test.txt").write_text(
        "Synthetic text",
        encoding="utf-8",
    )
    (person.source_documents / "20260103 Study.iso").write_bytes(b"iso")
    person.metadata_directory.mkdir(parents=True)
    (person.metadata_directory / "problems.toml").write_text(
        """
[[problem]]
id = "problem-a"
title = "Problem A"
status = "active"
""",
        encoding="utf-8",
    )
    documents = scan_documents(person)
    result = build_database(
        person,
        documents,
        load_curated_metadata(person.metadata_directory),
        catalog_dicom_studies(person, documents),
    )

    assert result.path == database_path(person)
    with sqlite3.connect(result.path) as connection:
        document_count = connection.execute(
            "SELECT count(*) FROM documents"
        ).fetchone()[0]
        problem_count = connection.execute("SELECT count(*) FROM problems").fetchone()[
            0
        ]
        dicom_count = connection.execute(
            "SELECT count(*) FROM dicom_studies"
        ).fetchone()[0]
        fts_count = connection.execute(
            "SELECT count(*) FROM document_fts WHERE document_fts MATCH 'Blood'"
        ).fetchone()[0]
    assert document_count == 2
    assert problem_count == 1
    assert dicom_count == 1
    assert fts_count == 1


def test_build_database_rejects_invalid_therapy_reference(tmp_path: Path) -> None:
    """Verify SQLite foreign keys reject therapies without medications.

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
    (person.source_documents / "20260102 Report.txt").write_text(
        "Synthetic text",
        encoding="utf-8",
    )
    documents = scan_documents(person)
    metadata = CuratedMetadata(
        therapies=(TherapyEpisode(id="therapy-a", medication_id="missing-drug"),)
    )

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        build_database(person, documents, metadata, ())
