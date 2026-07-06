"""Local build pipeline for SaniKey."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from .containers import stage_container_documents
from .database import build_database
from .dicom import catalog_dicom_studies
from .documents import ExtractedText, extract_text
from .exports import generate_exports
from .frontend import build_frontend
from .inspection import (
    extraction_warning_messages,
    inspect_patient_documents,
    static_document_warning_messages,
)
from .metadata import load_curated_metadata

if TYPE_CHECKING:
    from pathlib import Path

    from .config import AccountsConfig, PersonConfig
    from .models import DocumentRecord
    from .progress import ProgressReporter


@dataclass(frozen=True)
class BuildCounts:
    """Build document counters.

    Parameters
    ----------
    documents : int
        Source document count.
    derived_documents : int
        Derived document count.
    dicom_instances : int
        DICOM instance count.
    total_records : int
        Total source and derived document records.
    extracted_documents : int
        Documents processed by extraction in this build.
    cached_documents : int
        Documents reused from the extraction cache in this build.
    """

    documents: int
    derived_documents: int
    dicom_instances: int
    total_records: int
    extracted_documents: int = 0
    cached_documents: int = 0


@dataclass(frozen=True)
class PatientBuildResult:
    """Build result for one patient.

    Parameters
    ----------
    patient_id : str
        Built patient id.
    build_root : pathlib.Path
        Patient build root.
    documents : int
        Source document count.
    derived_documents : int
        Derived document count.
    dicom_instances : int
        DICOM instance count.
    total_records : int
        Total source and derived document records.
    extracted_documents : int
        Documents processed by extraction in this build.
    cached_documents : int
        Documents reused from the extraction cache in this build.
    duplicates : int
        Duplicate digest count.
    warnings : int
        Non-fatal warning count.
    warning_messages : tuple[str, ...]
        Non-fatal warning messages.
    database : pathlib.Path
        Generated database path.
    manifest : pathlib.Path
        Generated manifest path.
    checksums : pathlib.Path
        Generated checksum path.
    report : pathlib.Path
        Generated report path.
    """

    patient_id: str
    build_root: Path
    documents: int
    derived_documents: int
    dicom_instances: int
    total_records: int
    extracted_documents: int
    cached_documents: int
    duplicates: int
    warnings: int
    warning_messages: tuple[str, ...]
    database: Path
    manifest: Path
    checksums: Path
    report: Path


@dataclass(frozen=True)
class ExtractDocumentsResult:
    """Result of build-time document text extraction.

    Parameters
    ----------
    items : tuple[ExtractedText, ...]
        Extracted text records for database persistence.
    extracted : int
        Documents processed by extraction in this build.
    cached : int
        Documents reused from cache in this build.
    """

    items: tuple[ExtractedText, ...]
    extracted: int
    cached: int


def build_patient(
    person: PersonConfig,
    *,
    mode: str = "incremental",
    progress: ProgressReporter | None = None,
) -> PatientBuildResult:
    """Build generated artefacts for one patient.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    mode : str, optional
        Build mode: ``full``, ``incremental``, or ``validation``.
    progress : ProgressReporter | None, optional
        Progress reporter for long build steps.

    Returns
    -------
    PatientBuildResult
        Build result.

    Raises
    ------
    ValueError
        If ``mode`` is unsupported.
    """

    if mode not in {"full", "incremental", "validation"}:
        msg = f"unsupported build mode: {mode}"
        raise ValueError(msg)
    build_root = person.local_build
    build_root.mkdir(parents=True, exist_ok=True)
    inspection = inspect_patient_documents(person, progress=progress)
    staging = stage_container_documents(
        person,
        inspection.documents,
        progress=progress,
        progress_label=f"stage-containers {person.id}",
    )
    documents = (*inspection.documents, *staging.documents)
    dicom_studies = catalog_dicom_studies(person, documents)
    metadata = load_curated_metadata(person.metadata_directory)
    extraction_documents = tuple(
        document for document in documents if not document.kind.startswith("dicom_")
    )
    extracted_result = _extract_documents(
        person,
        extraction_documents,
        mode=mode,
        progress=progress,
    )
    extracted = extracted_result.items
    inspection_warnings = tuple(
        warning
        for warning in inspection.warning_messages
        if "manual DICOM expansion directory not found" not in warning
    )
    dicom_warnings = tuple(
        f"{study.support_path}: {warning}"
        for study in dicom_studies
        for warning in study.warnings
    )
    warning_messages = (
        *inspection_warnings,
        *static_document_warning_messages(staging.documents),
        *dicom_warnings,
        *staging.warning_messages,
        *extraction_warning_messages(extraction_documents, extracted),
    )
    warnings = len(warning_messages)
    counts = BuildCounts(
        documents=len(inspection.documents),
        derived_documents=len(staging.documents),
        dicom_instances=sum(
            1 for document in documents if document.kind == "dicom_file"
        ),
        total_records=len(documents),
        extracted_documents=extracted_result.extracted,
        cached_documents=extracted_result.cached,
    )
    db_result = build_database(person, documents, metadata, dicom_studies, extracted)
    manifest_path = _write_manifest(
        person,
        build_root=build_root,
        mode=mode,
        documents=counts.documents,
        warnings=warnings,
    )
    report_path = _write_report(
        person,
        build_root=build_root,
        counts=counts,
        duplicates=len(inspection.duplicates),
        warning_messages=warning_messages,
    )
    generate_exports(person, documents, metadata)
    build_frontend(person)
    checksums_path = _write_checksums(build_root)
    return PatientBuildResult(
        patient_id=person.id,
        build_root=build_root,
        documents=counts.documents,
        derived_documents=counts.derived_documents,
        dicom_instances=counts.dicom_instances,
        total_records=counts.total_records,
        extracted_documents=counts.extracted_documents,
        cached_documents=counts.cached_documents,
        duplicates=len(inspection.duplicates),
        warnings=warnings,
        warning_messages=warning_messages,
        database=db_result.path,
        manifest=manifest_path,
        checksums=checksums_path,
        report=report_path,
    )


def build_all(
    config: AccountsConfig,
    *,
    mode: str = "incremental",
    progress: ProgressReporter | None = None,
) -> tuple[PatientBuildResult, ...]:
    """Build all enabled patients.

    Parameters
    ----------
    config : AccountsConfig
        Loaded accounts configuration.
    mode : str, optional
        Build mode.
    progress : ProgressReporter | None, optional
        Progress reporter for long build steps.

    Returns
    -------
    tuple[PatientBuildResult, ...]
        Build results in patient order.
    """

    return tuple(
        build_patient(person, mode=mode, progress=progress)
        for person in config.enabled_people()
    )


def _extract_documents(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
    *,
    mode: str,
    progress: ProgressReporter | None,
) -> ExtractDocumentsResult:
    """Extract document text using the incremental cache when enabled.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    documents : tuple[DocumentRecord, ...]
        Documents eligible for text extraction.
    mode : str
        Build mode.
    progress : ProgressReporter | None
        Progress reporter for extraction.

    Returns
    -------
    ExtractDocumentsResult
        Extracted text rows and cache counters.
    """

    cache_path = _extraction_cache_path(person)
    cache = _read_extraction_cache(cache_path) if mode == "incremental" else {}
    next_cache: dict[str, dict[str, object]] = {}
    extracted_items = []
    extracted_count = 0
    cached_count = 0
    if progress is not None:
        progress.begin(f"extract-text {person.id}", total=len(documents))
    for index, document in enumerate(documents, start=1):
        cached = _cached_extracted_text(cache, document)
        if cached is None:
            item = extract_text(document)
            extracted_count += 1
        else:
            item = cached
            cached_count += 1
        extracted_items.append(item)
        next_cache[document.document_id] = _extraction_cache_entry(document, item)
        if progress is not None:
            progress.advance(index, total=len(documents))
    if progress is not None:
        progress.done(
            f"done documents={len(documents)} "
            f"extracted={extracted_count} cached={cached_count}"
        )
    _write_extraction_cache(cache_path, next_cache)
    return ExtractDocumentsResult(
        items=tuple(extracted_items),
        extracted=extracted_count,
        cached=cached_count,
    )


def _extraction_cache_path(person: PersonConfig) -> Path:
    """Return the patient extraction cache path.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    pathlib.Path
        Extraction cache path.
    """

    return person.local_build / "cache" / "extracted_text.json"


def _read_extraction_cache(target: Path) -> dict[str, dict[str, object]]:
    """Read a persisted extraction cache.

    Parameters
    ----------
    target : pathlib.Path
        Cache path.

    Returns
    -------
    dict[str, dict[str, object]]
        Cache entries keyed by document id.
    """

    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return {}
    entries = payload.get("documents")
    if not isinstance(entries, dict):
        return {}
    return {
        key: value
        for key, value in entries.items()
        if isinstance(key, str) and isinstance(value, dict)
    }


def _write_extraction_cache(
    target: Path,
    entries: dict[str, dict[str, object]],
) -> None:
    """Write the extraction cache.

    Parameters
    ----------
    target : pathlib.Path
        Cache path.
    entries : dict[str, dict[str, object]]
        Cache entries keyed by document id.

    Returns
    -------
    None
    """

    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "documents": entries,
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _cached_extracted_text(
    cache: dict[str, dict[str, object]],
    document: DocumentRecord,
) -> ExtractedText | None:
    """Return cached extracted text when a document entry still matches.

    Parameters
    ----------
    cache : dict[str, dict[str, object]]
        Cache entries keyed by document id.
    document : DocumentRecord
        Current document record.

    Returns
    -------
    ExtractedText | None
        Cached extraction result, or ``None`` when the document must be
        processed again.
    """

    entry = cache.get(document.document_id)
    if entry is None:
        return None
    expected = _document_cache_identity(document)
    if any(entry.get(key) != value for key, value in expected.items()):
        return None
    text = entry.get("text")
    warnings = entry.get("warnings")
    if not isinstance(text, str) or not isinstance(warnings, list):
        return None
    if not all(isinstance(warning, str) for warning in warnings):
        return None
    return ExtractedText(
        document_id=document.document_id,
        text=text,
        warnings=tuple(warnings),
    )


def _extraction_cache_entry(
    document: DocumentRecord,
    extracted: ExtractedText,
) -> dict[str, object]:
    """Build a cache entry for one extracted document.

    Parameters
    ----------
    document : DocumentRecord
        Document record.
    extracted : ExtractedText
        Extracted text result.

    Returns
    -------
    dict[str, object]
        JSON-serializable cache entry.
    """

    return {
        **_document_cache_identity(document),
        "text": extracted.text,
        "warnings": list(extracted.warnings),
    }


def _document_cache_identity(document: DocumentRecord) -> dict[str, object]:
    """Return fields that make an extraction cache entry valid.

    Parameters
    ----------
    document : DocumentRecord
        Document record.

    Returns
    -------
    dict[str, object]
        Stable document identity fields for extraction reuse.
    """

    return {
        "document_id": document.document_id,
        "path": str(document.path),
        "kind": document.kind,
        "sha256": document.sha256,
        "origin": document.origin,
        "container_id": document.container_id,
        "internal_path": document.internal_path,
    }


def _write_manifest(
    person: PersonConfig,
    *,
    build_root: Path,
    mode: str,
    documents: int,
    warnings: int,
) -> Path:
    """Write a patient build manifest.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    build_root : pathlib.Path
        Build root.
    mode : str
        Build mode.
    documents : int
        Document count.
    warnings : int
        Warning count.

    Returns
    -------
    pathlib.Path
        Manifest path.
    """

    target = build_root / "manifests" / "manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    base_payload = {
        "schema_version": 1,
        "patient_id": person.id,
        "build_mode": mode,
        "documents": documents,
        "warnings": warnings,
    }
    payload = {
        **base_payload,
        "generated_at": _manifest_generated_at(target, base_payload),
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target


def _manifest_generated_at(target: Path, base_payload: dict[str, object]) -> str:
    """Return a stable manifest generation timestamp.

    Parameters
    ----------
    target : pathlib.Path
        Manifest path.
    base_payload : dict[str, object]
        Manifest content excluding ``generated_at``.

    Returns
    -------
    str
        Existing timestamp for unchanged manifests, otherwise current UTC time.
    """

    if target.is_file():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        if (
            isinstance(existing, dict)
            and all(existing.get(key) == value for key, value in base_payload.items())
            and isinstance(existing.get("generated_at"), str)
        ):
            return cast("str", existing["generated_at"])
    return datetime.now(UTC).isoformat()


def _write_report(
    person: PersonConfig,
    *,
    build_root: Path,
    counts: BuildCounts,
    duplicates: int,
    warning_messages: tuple[str, ...],
) -> Path:
    """Write a compact JSON build report.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    build_root : pathlib.Path
        Build root.
    counts : BuildCounts
        Build document counters.
    duplicates : int
        Duplicate count.
    warning_messages : tuple[str, ...]
        Non-fatal warning messages.

    Returns
    -------
    pathlib.Path
        Report path.
    """

    target = build_root / "reports" / "build_report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "patient_id": person.id,
        "documents": counts.documents,
        "derived_documents": counts.derived_documents,
        "dicom_instances": counts.dicom_instances,
        "total_records": counts.total_records,
        "duplicates": duplicates,
        "warnings": len(warning_messages),
        "warning_messages": list(warning_messages),
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target


def _write_checksums(build_root: Path) -> Path:
    """Write SHA256 checksums for generated files.

    Parameters
    ----------
    build_root : pathlib.Path
        Build root.

    Returns
    -------
    pathlib.Path
        Checksum file path.
    """

    target = build_root / "checksums.sha256"
    rows = []
    for path in sorted(item for item in build_root.rglob("*") if item.is_file()):
        if path == target:
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(build_root)}")
    target.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return target


def _sha256(path: Path) -> str:
    """Compute a file SHA256 digest.

    Parameters
    ----------
    path : pathlib.Path
        File to hash.

    Returns
    -------
    str
        Hex digest.
    """

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def result_to_json(result: PatientBuildResult) -> str:
    """Serialize a build result for CLI output.

    Parameters
    ----------
    result : PatientBuildResult
        Build result.

    Returns
    -------
    str
        JSON line.
    """

    payload = asdict(result)
    for key in ("build_root", "database", "manifest", "checksums", "report"):
        payload[key] = str(payload[key])
    return json.dumps(payload, sort_keys=True)
