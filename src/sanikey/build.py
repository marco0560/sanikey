"""Local build pipeline for SaniKey."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from .database import build_database
from .documents import extract_text
from .exports import generate_exports
from .frontend import build_frontend
from .inspection import extraction_warning_messages, inspect_patient_documents
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
    duplicates: int
    warnings: int
    warning_messages: tuple[str, ...]
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
    inspection = inspect_patient_documents(person)
    documents = inspection.documents
    metadata = load_curated_metadata(person.metadata_directory)
    extracted = tuple(extract_text(document) for document in documents)
    warning_messages = (
        *inspection.warning_messages,
        *extraction_warning_messages(documents, extracted),
    )
    warnings = len(warning_messages)
    db_result = build_database(person, documents, metadata, inspection.dicom_studies)
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
        duplicates=len(inspection.duplicates),
        warning_messages=warning_messages,
    )
    generate_exports(person, documents, metadata)
    build_frontend(person)
    checksums_path = _write_checksums(build_root)
    return PatientBuildResult(
        patient_id=person.id,
        build_root=build_root,
        documents=len(documents),
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
    documents: int,
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
    documents : int
        Document count.
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
        "documents": documents,
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
