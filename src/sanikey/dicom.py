"""DICOM support cataloging for SaniKey v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .config import PersonConfig
    from .models import DocumentRecord


@dataclass(frozen=True)
class DicomStudy:
    """Catalog entry for one diagnostic study.

    Parameters
    ----------
    study_id : str
        Stable study identifier.
    patient_id : str
        Owning patient id.
    support_path : pathlib.Path
        Original ISO or ZIP support.
    support_kind : str
        Original support kind.
    extracted_path : pathlib.Path | None
        Manually expanded directory when available.
    viewer_paths : tuple[pathlib.Path, ...]
        Detected viewer executables or launch files.
    warnings : tuple[str, ...]
        Non-fatal cataloging warnings.
    """

    study_id: str
    patient_id: str
    support_path: Path
    support_kind: str
    extracted_path: Path | None = None
    viewer_paths: tuple[Path, ...] = ()
    warnings: tuple[str, ...] = ()


def catalog_dicom_studies(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
) -> tuple[DicomStudy, ...]:
    """Catalog DICOM supports for one patient.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    documents : tuple[DocumentRecord, ...]
        Scanned document records.

    Returns
    -------
    tuple[DicomStudy, ...]
        Cataloged DICOM studies sorted by support path.
    """

    studies = [
        _study_from_document(person, document)
        for document in documents
        if document.kind in {"dicom_iso", "dicom_zip"}
    ]
    return tuple(sorted(studies, key=lambda study: str(study.support_path)))


def _study_from_document(person: PersonConfig, document: DocumentRecord) -> DicomStudy:
    """Build a DICOM study from one original support document.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        ISO or ZIP support document.

    Returns
    -------
    DicomStudy
        Catalog entry.
    """

    extracted = _manual_extracted_path(person, document)
    viewers = _viewer_paths(extracted) if extracted is not None else ()
    warnings: tuple[str, ...] = ()
    if extracted is None:
        warnings = ("manual DICOM expansion directory not found",)
    return DicomStudy(
        study_id=document.document_id,
        patient_id=document.patient_id,
        support_path=document.path,
        support_kind=document.kind,
        extracted_path=extracted,
        viewer_paths=viewers,
        warnings=warnings,
    )


def _manual_extracted_path(
    person: PersonConfig,
    document: DocumentRecord,
) -> Path | None:
    """Return the expected manual DICOM extraction directory.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        DICOM support document.

    Returns
    -------
    pathlib.Path | None
        Existing extraction directory, if any.
    """

    candidate = person.local_build / "dicom" / document.path.stem
    if candidate.is_dir():
        return candidate
    return None


def _viewer_paths(extracted_path: Path) -> tuple[Path, ...]:
    """Find likely DICOM viewer launch files in an extracted directory.

    Parameters
    ----------
    extracted_path : pathlib.Path
        Manually expanded study directory.

    Returns
    -------
    tuple[pathlib.Path, ...]
        Viewer-like paths sorted for deterministic output.
    """

    candidates = []
    for path in extracted_path.rglob("*"):
        if path.is_file() and path.name.lower() in {
            "viewer.exe",
            "start.exe",
            "autorun.inf",
            "index.html",
        }:
            candidates.append(path)
    return tuple(sorted(candidates))
