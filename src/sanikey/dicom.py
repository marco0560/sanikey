"""DICOM support cataloging for SaniKey v1."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

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
        Original DICOM support.
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
        if _is_dicom_support(document)
    ]
    return tuple(sorted(studies, key=lambda study: str(study.support_path)))


def _study_from_document(person: PersonConfig, document: DocumentRecord) -> DicomStudy:
    """Build a DICOM study from one original support document.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        DICOM support document.

    Returns
    -------
    DicomStudy
        Catalog entry.
    """

    extracted = _manual_extracted_path(person, document)
    viewers = _viewer_paths(extracted) if extracted is not None else ()
    warnings: tuple[str, ...] = ()
    support_kind = _dicom_support_kind(document)
    if extracted is None and support_kind in {
        "dicom_7z",
        "dicom_iso",
        "dicom_rar",
        "dicom_zip",
    }:
        warnings = ("manual DICOM expansion directory not found",)
    return DicomStudy(
        study_id=document.document_id,
        patient_id=document.patient_id,
        support_path=document.path,
        support_kind=support_kind,
        extracted_path=extracted,
        viewer_paths=viewers,
        warnings=warnings,
    )


def _is_dicom_support(document: DocumentRecord) -> bool:
    """Return whether a document represents DICOM support content.

    Parameters
    ----------
    document : DocumentRecord
        Document to inspect.

    Returns
    -------
    bool
        ``True`` for direct DICOM files, ISO supports, or archives with DICOM
        content.
    """

    if document.kind in {"dicom_file", "dicom_iso"}:
        return True
    if document.kind != "archive":
        return False
    return _archive_contains_dicom(document)


def _dicom_support_kind(document: DocumentRecord) -> str:
    """Return the DICOM support kind for cataloging.

    Parameters
    ----------
    document : DocumentRecord
        DICOM support document.

    Returns
    -------
    str
        Original or promoted DICOM support kind.
    """

    suffix = document.path.suffix.lower()
    if document.kind == "archive" and suffix in {".7z", ".rar", ".zip"}:
        return f"dicom_{suffix[1:]}"
    return document.kind


def _archive_contains_dicom(document: DocumentRecord) -> bool:
    """Return whether an archive appears to contain DICOM data.

    Parameters
    ----------
    document : DocumentRecord
        Archive document.

    Returns
    -------
    bool
        ``True`` when names, path structure, or readable magic bytes indicate
        DICOM content.
    """

    suffix = document.path.suffix.lower()
    if suffix == ".zip":
        return _zip_contains_dicom(document.path)
    if suffix == ".rar":
        return _rar_contains_dicom(document.path)
    if suffix == ".7z":
        return _seven_zip_contains_dicom(document.path)
    return False


def _zip_contains_dicom(path: Path) -> bool:
    """Return whether a ZIP archive contains DICOM content.

    Parameters
    ----------
    path : pathlib.Path
        ZIP archive path.

    Returns
    -------
    bool
        ``True`` when member names or magic bytes indicate DICOM content.
    """

    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if any(_looks_like_dicom_member_name(name) for name in names):
                return True
            for name in names:
                info = archive.getinfo(name)
                if info.is_dir():
                    continue
                with archive.open(info) as handle:
                    if name.lower().endswith(".zip") and _nested_zip_contains_dicom(
                        handle.read()
                    ):
                        return True
                    if _stream_has_dicom_magic(handle):
                        return True
    except (OSError, zipfile.BadZipFile):
        return False
    return False


def _rar_contains_dicom(path: Path) -> bool:
    """Return whether a RAR archive contains DICOM content.

    Parameters
    ----------
    path : pathlib.Path
        RAR archive path.

    Returns
    -------
    bool
        ``True`` when member names or magic bytes indicate DICOM content.
    """

    try:
        import rarfile

        with rarfile.RarFile(path) as archive:
            infos = archive.infolist()
            if any(_looks_like_dicom_member_name(info.filename) for info in infos):
                return True
            for info in infos:
                if info.isdir():
                    continue
                with archive.open(info) as handle:
                    if _stream_has_dicom_magic(handle):
                        return True
    except (OSError, rarfile.Error):
        return False
    return False


def _seven_zip_contains_dicom(path: Path) -> bool:
    """Return whether a 7z archive contains DICOM content by member names.

    Parameters
    ----------
    path : pathlib.Path
        7z archive path.

    Returns
    -------
    bool
        ``True`` when member names indicate DICOM content.
    """

    try:
        import py7zr

        with py7zr.SevenZipFile(path) as archive:
            return any(
                _looks_like_dicom_member_name(name) for name in archive.getnames()
            )
    except (OSError, py7zr.Bad7zFile, py7zr.PasswordRequired):
        return False


def _looks_like_dicom_member_name(name: str) -> bool:
    """Return whether an archive member name indicates DICOM content.

    Parameters
    ----------
    name : str
        Archive member name.

    Returns
    -------
    bool
        ``True`` for DICOMDIR, DICOM files, disk-image supports, or DICOM path
        segments.
    """

    path = PurePosixPath(name)
    parts = tuple(part.lower() for part in path.parts)
    return (
        path.name.lower() == "dicomdir"
        or path.suffix.lower() in {".dcm", ".img", ".iso"}
        or "dicom" in parts
    )


def _nested_zip_contains_dicom(data: bytes) -> bool:
    """Return whether a nested ZIP payload contains DICOM content.

    Parameters
    ----------
    data : bytes
        Nested ZIP bytes.

    Returns
    -------
    bool
        ``True`` when nested member names indicate DICOM content.
    """

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return any(
                _looks_like_dicom_member_name(name) for name in archive.namelist()
            )
    except (OSError, zipfile.BadZipFile):
        return False


def _stream_has_dicom_magic(handle: Any) -> bool:
    """Return whether a binary stream contains the DICOM magic marker.

    Parameters
    ----------
    handle : object
        Binary file-like object.

    Returns
    -------
    bool
        ``True`` when bytes 128-131 are ``DICM``.
    """

    try:
        handle.seek(128)
        return bool(handle.read(4) == b"DICM")
    except (AttributeError, OSError):
        return False


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

    candidates = (
        person.local_build / "dicom" / document.path.stem,
        person.local_build / "staging" / "containers" / document.document_id,
    )
    for candidate in candidates:
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
