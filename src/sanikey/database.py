"""SQLite archive generation for SaniKey."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .config import PersonConfig
    from .dicom import DicomStudy
    from .models import CuratedMetadata, DocumentRecord


@dataclass(frozen=True)
class DatabaseBuildResult:
    """Result of a database build.

    Parameters
    ----------
    path : pathlib.Path
        Generated SQLite database path.
    documents : int
        Number of inserted documents.
    timeline_events : int
        Number of inserted timeline events.
    dicom_studies : int
        Number of inserted DICOM studies.
    """

    path: Path
    documents: int
    timeline_events: int
    dicom_studies: int


def database_path(person: PersonConfig) -> Path:
    """Return the generated database path for a patient.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    pathlib.Path
        Database path under ``local_build``.
    """

    return person.local_build / "database" / "medical_archive.db"


def build_database(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
    metadata: CuratedMetadata,
    dicom_studies: tuple[DicomStudy, ...],
) -> DatabaseBuildResult:
    """Build a complete per-patient SQLite database.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    documents : tuple[DocumentRecord, ...]
        Scanned source documents.
    metadata : CuratedMetadata
        Curated metadata.
    dicom_studies : tuple[DicomStudy, ...]
        Cataloged DICOM studies.

    Returns
    -------
    DatabaseBuildResult
        Build result.
    """

    path = database_path(person)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _create_schema(connection)
        _insert_documents(connection, documents)
        _insert_metadata(connection, metadata)
        _insert_dicom(connection, dicom_studies)
        connection.commit()
    return DatabaseBuildResult(
        path=path,
        documents=len(documents),
        timeline_events=len(metadata.timeline_events),
        dicom_studies=len(dicom_studies),
    )


def _create_schema(connection: sqlite3.Connection) -> None:
    """Create the SaniKey SQLite schema.

    Parameters
    ----------
    connection : sqlite3.Connection
        Open database connection.

    Returns
    -------
    None
    """

    connection.executescript(
        """
        CREATE TABLE documents (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            path TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            kind TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            document_date TEXT,
            series TEXT
        );

        CREATE VIRTUAL TABLE document_fts USING fts5(
            title,
            category,
            tags,
            content='documents',
            content_rowid='rowid'
        );

        CREATE TABLE problems (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE medications (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            active_ingredient TEXT,
            form TEXT,
            strength_per_unit TEXT
        );

        CREATE TABLE therapies (
            id TEXT PRIMARY KEY,
            medication_id TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            dosage TEXT,
            schedule TEXT NOT NULL,
            instructions TEXT,
            FOREIGN KEY (medication_id) REFERENCES medications(id)
        );

        CREATE TABLE procedures (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            procedure_date TEXT,
            status TEXT NOT NULL
        );

        CREATE TABLE observations (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            value TEXT NOT NULL,
            observation_date TEXT
        );

        CREATE TABLE timeline_events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            source TEXT NOT NULL,
            links TEXT NOT NULL
        );

        CREATE TABLE dicom_studies (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            support_path TEXT NOT NULL,
            support_kind TEXT NOT NULL,
            extracted_path TEXT,
            viewer_count INTEGER NOT NULL,
            warning_count INTEGER NOT NULL
        );
        """
    )


def _insert_documents(
    connection: sqlite3.Connection,
    documents: tuple[DocumentRecord, ...],
) -> None:
    """Insert documents and lexical index rows.

    Parameters
    ----------
    connection : sqlite3.Connection
        Open database connection.
    documents : tuple[DocumentRecord, ...]
        Documents to insert.

    Returns
    -------
    None
    """

    for document in documents:
        connection.execute(
            """
            INSERT INTO documents (
                id, patient_id, path, title, category, kind, sha256,
                document_date, series
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.document_id,
                document.patient_id,
                str(document.path),
                document.title,
                document.category,
                document.kind,
                document.sha256,
                document.date,
                document.series,
            ),
        )
        connection.execute(
            "INSERT INTO document_fts(rowid, title, category, tags) "
            "VALUES (last_insert_rowid(), ?, ?, ?)",
            (document.title, document.category, " ".join(document.tags)),
        )


def _insert_metadata(connection: sqlite3.Connection, metadata: CuratedMetadata) -> None:
    """Insert curated metadata.

    Parameters
    ----------
    connection : sqlite3.Connection
        Open database connection.
    metadata : CuratedMetadata
        Metadata to insert.

    Returns
    -------
    None
    """

    connection.executemany(
        "INSERT INTO problems(id, title, status) VALUES (?, ?, ?)",
        ((item.id, item.title, item.status) for item in metadata.problems),
    )
    connection.executemany(
        """
        INSERT INTO medications(id, name, active_ingredient, form, strength_per_unit)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            (
                item.id,
                item.name,
                item.active_ingredient,
                item.form,
                item.strength_per_unit,
            )
            for item in metadata.medications
        ),
    )
    connection.executemany(
        """
        INSERT INTO therapies(
            id, medication_id, start_date, end_date, dosage, schedule, instructions
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                item.id,
                item.medication_id,
                item.start_date,
                item.end_date,
                item.dosage,
                ",".join(item.schedule),
                item.instructions,
            )
            for item in metadata.therapies
        ),
    )
    connection.executemany(
        "INSERT INTO procedures(id, title, procedure_date, status) VALUES (?, ?, ?, ?)",
        ((item.id, item.title, item.date, item.status) for item in metadata.procedures),
    )
    connection.executemany(
        "INSERT INTO observations(id, kind, value, observation_date) VALUES (?, ?, ?, ?)",
        ((item.id, item.kind, item.value, item.date) for item in metadata.observations),
    )
    connection.executemany(
        """
        INSERT INTO timeline_events(id, title, start_date, end_date, source, links)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            (
                item.id,
                item.title,
                item.start_date,
                item.end_date,
                item.source,
                ",".join(item.links),
            )
            for item in metadata.timeline_events
        ),
    )


def _insert_dicom(
    connection: sqlite3.Connection,
    studies: tuple[DicomStudy, ...],
) -> None:
    """Insert DICOM catalog rows.

    Parameters
    ----------
    connection : sqlite3.Connection
        Open database connection.
    studies : tuple[DicomStudy, ...]
        DICOM studies.

    Returns
    -------
    None
    """

    connection.executemany(
        """
        INSERT INTO dicom_studies(
            id, patient_id, support_path, support_kind, extracted_path,
            viewer_count, warning_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                study.study_id,
                study.patient_id,
                str(study.support_path),
                study.support_kind,
                None if study.extracted_path is None else str(study.extracted_path),
                len(study.viewer_paths),
                len(study.warnings),
            )
            for study in studies
        ),
    )
