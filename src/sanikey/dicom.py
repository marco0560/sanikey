"""DICOM support cataloging for SaniKey v1."""

from __future__ import annotations

import hashlib
import io
import warnings
import zipfile
from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from .config import PersonConfig
    from .models import DocumentRecord
    from .progress import ProgressReporter


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
    html_viewer_path : pathlib.Path | None
        Preferred browser-openable viewer entrypoint when available.
    warnings : tuple[str, ...]
        Non-fatal cataloging warnings.
    study_instance_uid : str | None
        DICOM Study Instance UID when available.
    study_date : str | None
        DICOM study date when available.
    study_description : str | None
        DICOM study description when available.
    instance_count : int
        Number of DICOM instances grouped into the study.
    """

    study_id: str
    patient_id: str
    support_path: Path
    support_kind: str
    extracted_path: Path | None = None
    viewer_paths: tuple[Path, ...] = ()
    html_viewer_path: Path | None = None
    warnings: tuple[str, ...] = ()
    study_instance_uid: str | None = None
    study_date: str | None = None
    study_description: str | None = None
    instance_count: int = 1


@dataclass(frozen=True)
class DicomMetadata:
    """Relevant DICOM study metadata.

    Parameters
    ----------
    study_instance_uid : str | None
        Study Instance UID.
    study_date : str | None
        Study date normalized as ISO date when possible.
    study_description : str | None
        Study description.
    """

    study_instance_uid: str | None = None
    study_date: str | None = None
    study_description: str | None = None


def catalog_dicom_studies(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
    *,
    progress: ProgressReporter | None = None,
    progress_label: str | None = None,
) -> tuple[DicomStudy, ...]:
    """Catalog DICOM supports for one patient.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    documents : tuple[DocumentRecord, ...]
        Scanned document records.
    progress : ProgressReporter | None, optional
        Progress reporter for DICOM support checks.
    progress_label : str | None, optional
        Label for the progress line.

    Returns
    -------
    tuple[DicomStudy, ...]
        Cataloged DICOM studies sorted by support path.
    """

    if progress is not None and progress_label is not None:
        progress.begin(progress_label, total=len(documents))
    support_studies: list[DicomStudy] = []
    dicom_files: list[DocumentRecord] = []
    for index, document in enumerate(documents, start=1):
        if _is_dicom_support(document):
            if document.path.name.lower() == "dicomdir":
                studies_from_dicomdir = _studies_from_dicomdir(person, document)
                if studies_from_dicomdir:
                    support_studies.extend(studies_from_dicomdir)
                else:
                    dicom_files.append(document)
            elif document.kind == "dicom_file":
                dicom_files.append(document)
            else:
                support_studies.extend(_studies_from_document(person, document))
        if progress is not None:
            progress.advance(index, total=len(documents))
    studies = _coalesce_dicom_studies(
        (*support_studies, *_studies_from_dicom_files(person, tuple(dicom_files)))
    )
    if progress is not None and progress_label is not None:
        progress.done(f"done studies={len(studies)}")
    return tuple(sorted(studies, key=lambda study: str(study.support_path)))


def _studies_from_document(
    person: PersonConfig,
    document: DocumentRecord,
) -> tuple[DicomStudy, ...]:
    """Build DICOM studies from one support document.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        DICOM support document.

    Returns
    -------
    tuple[DicomStudy, ...]
        Catalog entries.
    """

    if document.path.name.lower() == "dicomdir":
        studies = _studies_from_dicomdir(person, document)
        if studies:
            return studies
    extracted = _manual_extracted_path(person, document)
    viewers = _viewer_paths(extracted) if extracted is not None else ()
    html_viewer = _html_viewer_path(extracted) if extracted is not None else None
    warnings: tuple[str, ...] = ()
    support_kind = _dicom_support_kind(document)
    if extracted is None and support_kind in {
        "dicom_7z",
        "dicom_img",
        "dicom_iso",
        "dicom_rar",
        "dicom_zip",
    }:
        warnings = ("directory di espansione DICOM manuale non trovata",)
    return (
        DicomStudy(
            study_id=document.document_id,
            patient_id=document.patient_id,
            support_path=document.path,
            support_kind=support_kind,
            extracted_path=extracted,
            viewer_paths=viewers,
            html_viewer_path=html_viewer,
            warnings=warnings,
        ),
    )


def _studies_from_dicom_files(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
) -> tuple[DicomStudy, ...]:
    """Group DICOM files by Study Instance UID.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    documents : tuple[DocumentRecord, ...]
        DICOM file documents.

    Returns
    -------
    tuple[DicomStudy, ...]
        Grouped DICOM studies.
    """

    grouped: dict[str, list[tuple[DocumentRecord, DicomMetadata]]] = {}
    fallback: list[DicomStudy] = []
    for document in documents:
        metadata = _read_dicom_metadata(document.path)
        if metadata is None or metadata.study_instance_uid is None:
            fallback.append(
                DicomStudy(
                    study_id=document.document_id,
                    patient_id=document.patient_id,
                    support_path=document.path,
                    support_kind=document.kind,
                )
            )
            continue
        grouped.setdefault(metadata.study_instance_uid, []).append((document, metadata))
    studies = []
    for study_uid, items in sorted(grouped.items()):
        first_document, first_metadata = sorted(
            items,
            key=lambda item: str(item[0].path),
        )[0]
        studies.append(
            DicomStudy(
                study_id=_study_id(person.id, study_uid),
                patient_id=person.id,
                support_path=first_document.path,
                support_kind="dicom_study",
                study_instance_uid=study_uid,
                study_date=first_metadata.study_date,
                study_description=first_metadata.study_description,
                instance_count=len(items),
            )
        )
    return (*tuple(studies), *tuple(fallback))


def _studies_from_dicomdir(
    person: PersonConfig,
    document: DocumentRecord,
) -> tuple[DicomStudy, ...]:
    """Build DICOM studies from a DICOMDIR file.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        DICOMDIR document.

    Returns
    -------
    tuple[DicomStudy, ...]
        Studies described by the DICOMDIR.
    """

    try:
        from pydicom import dcmread
    except ImportError:
        return ()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        try:
            dataset = dcmread(str(document.path), stop_before_pixels=True, force=True)
        except (OSError, ValueError):
            return ()
        records = getattr(dataset, "DirectoryRecordSequence", ())
        studies = []
        seen: set[str] = set()
        for record in records:
            if getattr(record, "DirectoryRecordType", None) != "STUDY":
                continue
            metadata = DicomMetadata(
                study_instance_uid=_clean_dicom_text(
                    getattr(record, "StudyInstanceUID", None)
                ),
                study_date=_normalize_dicom_date(getattr(record, "StudyDate", None)),
                study_description=_clean_dicom_text(
                    getattr(record, "StudyDescription", None)
                ),
            )
            if metadata.study_instance_uid is None:
                continue
            if metadata.study_instance_uid in seen:
                continue
            seen.add(metadata.study_instance_uid)
            studies.append(
                DicomStudy(
                    study_id=_study_id(person.id, metadata.study_instance_uid),
                    patient_id=person.id,
                    support_path=document.path,
                    support_kind="dicomdir_study",
                    extracted_path=document.path.parent,
                    study_instance_uid=metadata.study_instance_uid,
                    study_date=metadata.study_date,
                    study_description=metadata.study_description,
                    instance_count=0,
                )
            )
        return tuple(studies)


def _read_dicom_metadata(path: Path) -> DicomMetadata | None:
    """Read DICOM study metadata from one file.

    Parameters
    ----------
    path : pathlib.Path
        DICOM file path.

    Returns
    -------
    DicomMetadata | None
        Study metadata, or ``None`` when the file is not readable as DICOM.
    """

    try:
        from pydicom import dcmread
    except ImportError:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        try:
            dataset = dcmread(
                str(path),
                stop_before_pixels=True,
                specific_tags=[
                    "StudyInstanceUID",
                    "StudyDate",
                    "StudyDescription",
                ],
                force=True,
            )
        except (OSError, ValueError):
            return None
        return DicomMetadata(
            study_instance_uid=_clean_dicom_text(
                getattr(dataset, "StudyInstanceUID", None)
            ),
            study_date=_normalize_dicom_date(getattr(dataset, "StudyDate", None)),
            study_description=_clean_dicom_text(
                getattr(dataset, "StudyDescription", None)
            ),
        )


def _coalesce_dicom_studies(studies: tuple[DicomStudy, ...]) -> tuple[DicomStudy, ...]:
    """Merge duplicate study records before persistence.

    Parameters
    ----------
    studies : tuple[DicomStudy, ...]
        Candidate DICOM studies.

    Returns
    -------
    tuple[DicomStudy, ...]
        DICOM studies with unique identifiers.
    """

    merged: dict[str, DicomStudy] = {}
    for study in sorted(studies, key=_study_merge_sort_key):
        existing = merged.get(study.study_id)
        if existing is None:
            merged[study.study_id] = study
            continue
        merged[study.study_id] = replace(
            existing,
            extracted_path=existing.extracted_path or study.extracted_path,
            viewer_paths=_deduplicate_paths(
                (*existing.viewer_paths, *study.viewer_paths)
            ),
            html_viewer_path=existing.html_viewer_path or study.html_viewer_path,
            warnings=_deduplicate_text((*existing.warnings, *study.warnings)),
            study_instance_uid=existing.study_instance_uid or study.study_instance_uid,
            study_date=existing.study_date or study.study_date,
            study_description=(existing.study_description or study.study_description),
            instance_count=max(existing.instance_count, study.instance_count),
        )
    return tuple(merged.values())


def _study_merge_sort_key(study: DicomStudy) -> tuple[int, str]:
    """Return the deterministic merge preference for one DICOM study.

    Parameters
    ----------
    study : DicomStudy
        DICOM study candidate.

    Returns
    -------
    tuple[int, str]
        Sort key that prefers instance-backed records over DICOMDIR-only
        records while keeping deterministic path order.
    """

    return (0 if study.instance_count > 0 else 1, str(study.support_path))


def _deduplicate_paths(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    """Deduplicate paths preserving first occurrence order.

    Parameters
    ----------
    paths : tuple[pathlib.Path, ...]
        Paths to deduplicate.

    Returns
    -------
    tuple[pathlib.Path, ...]
        Unique paths.
    """

    return tuple(dict.fromkeys(paths))


def _deduplicate_text(values: tuple[str, ...]) -> tuple[str, ...]:
    """Deduplicate text values preserving first occurrence order.

    Parameters
    ----------
    values : tuple[str, ...]
        Text values to deduplicate.

    Returns
    -------
    tuple[str, ...]
        Unique text values.
    """

    return tuple(dict.fromkeys(values))


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

    if document.kind in {"dicom_file", "dicom_img", "dicom_iso"}:
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


def _study_id(patient_id: str, study_instance_uid: str) -> str:
    """Build a stable DICOM study identifier.

    Parameters
    ----------
    patient_id : str
        Patient identifier.
    study_instance_uid : str
        DICOM Study Instance UID.

    Returns
    -------
    str
        Stable SHA256 study id.
    """

    identity = "\0".join(("dicom-study", patient_id, study_instance_uid))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _clean_dicom_text(value: object) -> str | None:
    """Return a stripped DICOM text value.

    Parameters
    ----------
    value : object
        DICOM value.

    Returns
    -------
    str | None
        Stripped text, or ``None`` when empty.
    """

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_dicom_date(value: object) -> str | None:
    """Normalize a DICOM DA value to ISO date.

    Parameters
    ----------
    value : object
        DICOM date value.

    Returns
    -------
    str | None
        ISO date when possible, otherwise the original non-empty value.
    """

    text = _clean_dicom_text(value)
    if text is None:
        return None
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


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
            "index.htm",
        }:
            candidates.append(path)
    return tuple(sorted(candidates))


def _html_viewer_path(extracted_path: Path) -> Path | None:
    """Return the preferred HTML viewer entrypoint in an extracted support.

    Parameters
    ----------
    extracted_path : pathlib.Path
        Manually expanded or staged DICOM support directory.

    Returns
    -------
    pathlib.Path | None
        Browser-openable entrypoint, preferring IHE PDI study pages when
        available.
    """

    candidates = tuple(path for path in extracted_path.rglob("*") if path.is_file())
    ihe_studies = _html_candidates_under(candidates, ("ihe_pdi", "pages", "studies"))
    if ihe_studies:
        return ihe_studies[0]
    ihe_pages = _html_candidates_under(candidates, ("ihe_pdi", "pages"))
    if ihe_pages:
        return ihe_pages[0]
    named = [
        path
        for path in candidates
        if path.name.lower() in {"index.html", "index.htm", "default.htm", "start.htm"}
    ]
    if named:
        return tuple(sorted(named))[0]
    return None


def _html_candidates_under(
    paths: tuple[Path, ...],
    segments: tuple[str, ...],
) -> tuple[Path, ...]:
    """Return HTML files whose path contains an ordered segment sequence.

    Parameters
    ----------
    paths : tuple[pathlib.Path, ...]
        Candidate files.
    segments : tuple[str, ...]
        Lowercase path segment sequence to match.

    Returns
    -------
    tuple[pathlib.Path, ...]
        Matching HTML files in deterministic order.
    """

    matches = []
    for path in paths:
        if path.suffix.lower() not in {".html", ".htm"}:
            continue
        parts = tuple(part.lower() for part in path.parts)
        if _contains_ordered_segments(parts, segments):
            matches.append(path)
    return tuple(sorted(matches))


def _contains_ordered_segments(
    parts: tuple[str, ...],
    segments: tuple[str, ...],
) -> bool:
    """Return whether path parts contain a contiguous segment sequence.

    Parameters
    ----------
    parts : tuple[str, ...]
        Lowercase path parts.
    segments : tuple[str, ...]
        Segment sequence to find.

    Returns
    -------
    bool
        ``True`` when the sequence is present.
    """

    if len(parts) < len(segments):
        return False
    return any(
        parts[index : index + len(segments)] == segments
        for index in range(len(parts) - len(segments) + 1)
    )
