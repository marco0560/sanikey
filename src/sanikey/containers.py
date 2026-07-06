"""Container staging for archives and disk images."""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from .documents import DocumentRecordOrigin, document_record_for_path

if TYPE_CHECKING:
    from .config import PersonConfig
    from .models import DocumentRecord
    from .progress import ProgressReporter

CONTAINER_SUFFIXES = {".7z", ".img", ".iso", ".rar", ".zip"}
TECHNICAL_PATH_SEGMENTS = {"assets", "help", "jre", "manual", "viewer-windows"}


@dataclass(frozen=True)
class StagedContainerMember:
    """Represent one extracted container member.

    Parameters
    ----------
    container_id : str
        Parent container document id.
    document_id : str
        Derived member document id.
    internal_path : str
        Member path inside the parent container.
    path : str
        Generated staged file path.
    kind : str
        Derived document kind.
    sha256 : str
        Member SHA256.
    size : int
        Staged file size in bytes.
    mtime_ns : int
        Staged file modification time in nanoseconds.
    """

    container_id: str
    document_id: str
    internal_path: str
    path: str
    kind: str
    sha256: str
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class ContainerStagingResult:
    """Result of container staging.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Derived document records for staged members.
    members : tuple[StagedContainerMember, ...]
        Provenance records for staged members.
    warning_messages : tuple[str, ...]
        Non-fatal staging warnings.
    manifest : pathlib.Path
        Container staging manifest path.
    """

    documents: tuple[DocumentRecord, ...]
    members: tuple[StagedContainerMember, ...]
    warning_messages: tuple[str, ...]
    manifest: Path


def stage_container_documents(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
    *,
    progress: ProgressReporter | None = None,
    progress_label: str | None = None,
) -> ContainerStagingResult:
    """Extract supported containers into generated staging.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    documents : tuple[DocumentRecord, ...]
        Source and derived documents to inspect for containers.
    progress : ProgressReporter | None, optional
        Progress reporter for staged containers.
    progress_label : str | None, optional
        Label for the progress line.

    Returns
    -------
    ContainerStagingResult
        Staged member documents, provenance manifest, and warnings.
    """

    staging_root = person.local_build / "staging" / "containers"
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    queued = list(_container_documents(documents))
    if progress is not None and progress_label is not None:
        progress.begin(progress_label)
    processed: set[str] = set()
    staged_documents: list[DocumentRecord] = []
    members: list[StagedContainerMember] = []
    warnings: list[str] = []
    while queued:
        container = queued.pop(0)
        if container.document_id in processed:
            continue
        processed.add(container.document_id)
        container_result = _stage_one_container(person, container, staging_root)
        warnings.extend(container_result.warning_messages)
        staged_documents.extend(container_result.documents)
        members.extend(container_result.members)
        queued.extend(_container_documents(container_result.documents))
        if progress is not None:
            progress.advance(len(processed))
    if progress is not None and progress_label is not None:
        progress.done(
            f"done containers={len(processed)} derived={len(staged_documents)}"
        )
    manifest = _write_container_manifest(person, tuple(members), tuple(warnings))
    return ContainerStagingResult(
        documents=tuple(staged_documents),
        members=tuple(members),
        warning_messages=tuple(warnings),
        manifest=manifest,
    )


def _container_documents(
    documents: tuple[DocumentRecord, ...],
) -> tuple[DocumentRecord, ...]:
    """Return documents that can be staged as containers.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Documents to filter.

    Returns
    -------
    tuple[DocumentRecord, ...]
        Container documents.
    """

    return tuple(
        document
        for document in documents
        if document.path.suffix.lower() in CONTAINER_SUFFIXES
    )


def _stage_one_container(
    person: PersonConfig,
    container: DocumentRecord,
    staging_root: Path,
) -> ContainerStagingResult:
    """Stage one container document.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    container : DocumentRecord
        Container to extract.
    staging_root : pathlib.Path
        Root staging directory.

    Returns
    -------
    ContainerStagingResult
        Staged member records for this container.
    """

    target = staging_root / container.document_id
    target.mkdir(parents=True, exist_ok=True)
    try:
        _extract_container(container, target)
    except (OSError, subprocess.TimeoutExpired, ValueError, zipfile.BadZipFile) as exc:
        return ContainerStagingResult(
            documents=(),
            members=(),
            warning_messages=(f"{container.path}: container staging failed: {exc}",),
            manifest=person.local_build / "manifests" / "container_staging.json",
        )
    extracted_documents = tuple(
        document_record_for_path(
            path,
            root=target,
            patient_id=person.id,
            provenance=DocumentRecordOrigin(
                origin="container",
                container_id=container.document_id,
                internal_path=path.relative_to(target).as_posix(),
            ),
        )
        for path in sorted(item for item in target.rglob("*") if item.is_file())
    )
    documents = tuple(
        document
        for document in extracted_documents
        if _should_ingest_staged_document(document)
    )
    members = tuple(
        _member_record(container, document) for document in extracted_documents
    )
    return ContainerStagingResult(
        documents=documents,
        members=members,
        warning_messages=(),
        manifest=person.local_build / "manifests" / "container_staging.json",
    )


def _should_ingest_staged_document(document: DocumentRecord) -> bool:
    """Return whether a staged member should enter the document pipeline.

    Parameters
    ----------
    document : DocumentRecord
        Staged member document candidate.

    Returns
    -------
    bool
        ``True`` for clinically relevant document-like members.
    """

    if _is_technical_container_path(document.internal_path):
        return False
    return document.kind in {
        "dicom_file",
        "dicom_img",
        "dicom_iso",
        "office",
        "pdf",
        "text",
    }


def _is_technical_container_path(internal_path: str | None) -> bool:
    """Return whether a staged member belongs to known viewer/support paths.

    Parameters
    ----------
    internal_path : str | None
        Member path inside the container.

    Returns
    -------
    bool
        ``True`` when any path segment is a known technical support directory.
    """

    if internal_path is None:
        return False
    segments = (segment.lower() for segment in PurePosixPath(internal_path).parts)
    return any(
        segment in TECHNICAL_PATH_SEGMENTS or segment.startswith("manuale")
        for segment in segments
    )


def _extract_container(container: DocumentRecord, target: Path) -> None:
    """Extract one container into a target directory.

    Parameters
    ----------
    container : DocumentRecord
        Container to extract.
    target : pathlib.Path
        Extraction target directory.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the container suffix is unsupported or extraction fails.
    """

    suffix = container.path.suffix.lower()
    if suffix == ".zip":
        _extract_zip(container.path, target)
        return
    if suffix == ".7z":
        _extract_7z(container.path, target)
        return
    if suffix == ".rar":
        _extract_rar(container.path, target)
        return
    if suffix in {".img", ".iso"}:
        _extract_with_7z(container.path, target)
        return
    msg = f"unsupported container format {suffix}"
    raise ValueError(msg)


def _extract_zip(source: Path, target: Path) -> None:
    """Extract a ZIP archive with path traversal protection.

    Parameters
    ----------
    source : pathlib.Path
        ZIP archive.
    target : pathlib.Path
        Extraction target.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the archive cannot be read or requires a password.
    """

    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            output = _safe_member_path(target, member.filename)
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as input_file, output.open("wb") as output_file:
                shutil.copyfileobj(input_file, output_file)


def _extract_7z(source: Path, target: Path) -> None:
    """Extract a 7z archive with path traversal protection.

    Parameters
    ----------
    source : pathlib.Path
        7z archive.
    target : pathlib.Path
        Extraction target.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the archive cannot be read or extracted.
    """

    import py7zr

    try:
        with py7zr.SevenZipFile(source) as archive:
            for name in archive.getnames():
                _safe_member_path(target, name)
            archive.extractall(path=target)
    except (OSError, py7zr.Bad7zFile, py7zr.PasswordRequired) as exc:
        raise ValueError(exc) from exc


def _extract_rar(source: Path, target: Path) -> None:
    """Extract a RAR archive with path traversal protection.

    Parameters
    ----------
    source : pathlib.Path
        RAR archive.
    target : pathlib.Path
        Extraction target.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the archive cannot be read or extracted.
    """

    import rarfile

    try:
        with rarfile.RarFile(source) as archive:
            for name in archive.namelist():
                _safe_member_path(target, name)
            archive.extractall(path=target)
    except (OSError, rarfile.Error) as exc:
        raise ValueError(exc) from exc


def _extract_with_7z(source: Path, target: Path) -> None:
    """Extract a disk image through the system 7z command.

    Parameters
    ----------
    source : pathlib.Path
        Disk image.
    target : pathlib.Path
        Extraction target.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If ``7z`` is unavailable or the command fails.
    """

    seven_zip = shutil.which("7z")
    seven_zip_message = "7z command not installed"
    if seven_zip is not None:
        completed = subprocess.run(
            [seven_zip, "x", "-y", f"-o{target}", str(source)],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if completed.returncode == 0:
            return
        seven_zip_message = (
            completed.stderr or completed.stdout or "7z failed"
        ).strip()
    bsdtar = shutil.which("bsdtar")
    if bsdtar is None:
        msg = f"ISO staging skipped: {seven_zip_message}; bsdtar command not installed"
        raise ValueError(msg)
    completed = subprocess.run(
        [bsdtar, "-xf", str(source), "-C", str(target)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "bsdtar failed").strip()
        msg = f"ISO staging skipped: {seven_zip_message}; bsdtar failed: {message}"
        raise ValueError(msg)


def _safe_member_path(target: Path, member_name: str) -> Path:
    """Return a safe extraction path for one member.

    Parameters
    ----------
    target : pathlib.Path
        Extraction target.
    member_name : str
        Container member name.

    Returns
    -------
    pathlib.Path
        Safe member path.

    Raises
    ------
    ValueError
        If the member path is absolute or escapes the target directory.
    """

    normalized = PurePosixPath(member_name.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        msg = f"unsafe container member path: {member_name}"
        raise ValueError(msg)
    return target / Path(*normalized.parts)


def _member_record(
    container: DocumentRecord,
    document: DocumentRecord,
) -> StagedContainerMember:
    """Build one staged member provenance record.

    Parameters
    ----------
    container : DocumentRecord
        Parent container.
    document : DocumentRecord
        Derived member document.

    Returns
    -------
    StagedContainerMember
        Provenance record.
    """

    stat = document.path.stat()
    return StagedContainerMember(
        container_id=container.document_id,
        document_id=document.document_id,
        internal_path=document.internal_path or "",
        path=str(document.path),
        kind=document.kind,
        sha256=document.sha256,
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
    )


def _write_container_manifest(
    person: PersonConfig,
    members: tuple[StagedContainerMember, ...],
    warning_messages: tuple[str, ...],
) -> Path:
    """Write the container staging manifest.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    members : tuple[StagedContainerMember, ...]
        Staged members.
    warning_messages : tuple[str, ...]
        Staging warnings.

    Returns
    -------
    pathlib.Path
        Manifest path.
    """

    target = person.local_build / "manifests" / "container_staging.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "patient_id": person.id,
        "members": [asdict(member) for member in members],
        "warnings": list(warning_messages),
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target
