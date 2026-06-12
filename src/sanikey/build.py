"""Local build pipeline for SaniKey."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .database import build_database
from .dicom import catalog_dicom_studies
from .documents import extract_text, find_duplicate_documents, scan_documents
from .metadata import load_curated_metadata

if TYPE_CHECKING:
    from pathlib import Path

    from .config import AccountsConfig, PersonConfig


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
        Scanned document count.
    duplicates : int
        Duplicate digest count.
    warnings : int
        Non-fatal warning count.
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
    duplicates: int
    warnings: int
    database: Path
    manifest: Path
    checksums: Path
    report: Path


def build_patient(
    person: PersonConfig, *, mode: str = "incremental"
) -> PatientBuildResult:
    """Build generated artefacts for one patient.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    mode : str, optional
        Build mode: ``full``, ``incremental``, or ``validation``.

    Returns
    -------
    PatientBuildResult
        Build result.
    """

    if mode not in {"full", "incremental", "validation"}:
        msg = f"unsupported build mode: {mode}"
        raise ValueError(msg)
    build_root = person.local_build
    build_root.mkdir(parents=True, exist_ok=True)
    documents = scan_documents(person)
    metadata = load_curated_metadata(person.metadata_directory)
    dicom_studies = catalog_dicom_studies(person, documents)
    extracted = tuple(extract_text(document) for document in documents)
    duplicates = find_duplicate_documents(documents)
    warnings = sum(len(item.warnings) for item in extracted) + sum(
        len(study.warnings) for study in dicom_studies
    )
    db_result = build_database(person, documents, metadata, dicom_studies)
    manifest_path = _write_manifest(
        person,
        build_root=build_root,
        mode=mode,
        documents=len(documents),
        warnings=warnings,
    )
    report_path = _write_report(
        person,
        build_root=build_root,
        documents=len(documents),
        duplicates=len(duplicates),
        warnings=warnings,
    )
    checksums_path = _write_checksums(build_root)
    return PatientBuildResult(
        patient_id=person.id,
        build_root=build_root,
        documents=len(documents),
        duplicates=len(duplicates),
        warnings=warnings,
        database=db_result.path,
        manifest=manifest_path,
        checksums=checksums_path,
        report=report_path,
    )


def build_all(
    config: AccountsConfig,
    *,
    mode: str = "incremental",
) -> tuple[PatientBuildResult, ...]:
    """Build all enabled patients.

    Parameters
    ----------
    config : AccountsConfig
        Loaded accounts configuration.
    mode : str, optional
        Build mode.

    Returns
    -------
    tuple[PatientBuildResult, ...]
        Build results in patient order.
    """

    return tuple(build_patient(person, mode=mode) for person in config.enabled_people())


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
    payload = {
        "schema_version": 1,
        "patient_id": person.id,
        "build_mode": mode,
        "generated_at": datetime.now(UTC).isoformat(),
        "documents": documents,
        "warnings": warnings,
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target


def _write_report(
    person: PersonConfig,
    *,
    build_root: Path,
    documents: int,
    duplicates: int,
    warnings: int,
) -> Path:
    """Write a compact JSON build report.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    build_root : pathlib.Path
        Build root.
    documents : int
        Document count.
    duplicates : int
        Duplicate count.
    warnings : int
        Warning count.

    Returns
    -------
    pathlib.Path
        Report path.
    """

    target = build_root / "reports" / "build_report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "patient_id": person.id,
        "documents": documents,
        "duplicates": duplicates,
        "warnings": warnings,
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
