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
from .documents import extract_text
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
    """

    documents: int
    derived_documents: int
    dicom_instances: int
    total_records: int


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
    duplicates: int
    warnings: int
    warning_messages: tuple[str, ...]
    database: Path
    manifest: Path
    checksums: Path
    report: Path


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
    if progress is not None:
        progress.begin(f"stage-containers {person.id}")
    staging = stage_container_documents(person, inspection.documents)
    if progress is not None:
        progress.done(f"done derived={len(staging.documents)}")
    documents = (*inspection.documents, *staging.documents)
    dicom_studies = catalog_dicom_studies(person, documents)
    metadata = load_curated_metadata(person.metadata_directory)
    extraction_documents = tuple(
        document for document in documents if not document.kind.startswith("dicom_")
    )
    if progress is not None:
        progress.begin(f"extract-text {person.id}", total=len(extraction_documents))
    extracted_items = []
    for index, document in enumerate(extraction_documents, start=1):
        extracted_items.append(extract_text(document))
        if progress is not None:
            progress.advance(index, total=len(extraction_documents))
    if progress is not None:
        progress.done(f"done documents={len(extraction_documents)}")
    extracted = tuple(extracted_items)
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
    )
    db_result = build_database(person, documents, metadata, dicom_studies)
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
