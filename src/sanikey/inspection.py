"""Pre-build document inspection for SaniKey."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .containers import ContainerStagingResult, stage_container_documents
from .dicom import DicomStudy, catalog_dicom_studies
from .documents import (
    ExtractedText,
    duplicate_document_warnings,
    extract_text,
    find_duplicate_documents,
    scan_document_inventory,
    scan_documents,
)

if TYPE_CHECKING:
    from .config import PersonConfig
    from .models import DocumentRecord
    from .progress import ProgressReporter


@dataclass(frozen=True)
class PatientDocumentInspection:
    """Document inspection result for one patient.

    Parameters
    ----------
    inventory : tuple[DocumentRecord, ...]
        Full source document inventory, including duplicate content.
    documents : tuple[DocumentRecord, ...]
        Deduplicated document records.
    duplicates : dict[str, tuple[DocumentRecord, ...]]
        Duplicate documents grouped by SHA256.
    dicom_studies : tuple[DicomStudy, ...]
        Cataloged DICOM support records.
    warning_messages : tuple[str, ...]
        Fast diagnostic warnings from inventory and DICOM cataloging.
    preflight_warning_messages : tuple[str, ...]
        Optional deeper preflight warnings.
    container_staging : ContainerStagingResult | None
        Optional container staging result produced during inspection.
    """

    inventory: tuple[DocumentRecord, ...]
    documents: tuple[DocumentRecord, ...]
    duplicates: dict[str, tuple[DocumentRecord, ...]]
    dicom_studies: tuple[DicomStudy, ...]
    warning_messages: tuple[str, ...]
    preflight_warning_messages: tuple[str, ...] = ()
    container_staging: ContainerStagingResult | None = None


def inspect_patient_documents(
    person: PersonConfig,
    *,
    preflight: bool = False,
    stage_containers: bool = False,
    progress: ProgressReporter | None = None,
) -> PatientDocumentInspection:
    """Inspect a patient's documents before a full build.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    preflight : bool, optional
        Whether to run lightweight extraction checks for non-PDF containers and
        office documents.
    stage_containers : bool, optional
        Whether to stage supported containers for early manual inspection.
    progress : ProgressReporter | None, optional
        Progress reporter for long inspection steps.

    Returns
    -------
    PatientDocumentInspection
        Inspection result.
    """

    inventory = scan_document_inventory(
        person,
        progress=progress,
        progress_label=f"scan-documents {person.id}",
    )
    duplicates = find_duplicate_documents(inventory)
    documents = scan_documents(person)
    container_staging = None
    catalog_documents = documents
    if stage_containers:
        container_staging = stage_container_documents(
            person,
            documents,
            progress=progress,
            progress_label=f"stage-containers {person.id}",
        )
        catalog_documents = (*documents, *container_staging.documents)
    dicom_studies = catalog_dicom_studies(
        person,
        catalog_documents,
        progress=progress,
        progress_label=f"catalog-dicom {person.id}",
    )
    warning_messages = (
        *duplicate_document_warnings(duplicates),
        *(
            f"{study.support_path}: {warning}"
            for study in dicom_studies
            for warning in study.warnings
        ),
        *(static_document_warning_messages(documents)),
    )
    if container_staging is not None:
        warning_messages = (
            *warning_messages,
            *container_staging.warning_messages,
        )
    preflight_warning_messages = (
        _preflight_warning_messages(documents) if preflight else ()
    )
    return PatientDocumentInspection(
        inventory=inventory,
        documents=documents,
        duplicates=duplicates,
        dicom_studies=dicom_studies,
        warning_messages=warning_messages,
        preflight_warning_messages=preflight_warning_messages,
        container_staging=container_staging,
    )


def static_document_warning_messages(
    documents: tuple[DocumentRecord, ...],
) -> tuple[str, ...]:
    """Format static document warnings with source paths.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Documents to inspect.

    Returns
    -------
    tuple[str, ...]
        Static warning messages.
    """

    return tuple(
        f"{document.path}: {warning}"
        for document in documents
        for warning in _static_document_warnings(document)
    )


def _static_document_warnings(document: DocumentRecord) -> tuple[str, ...]:
    """Return warnings known without reading document content.

    Parameters
    ----------
    document : DocumentRecord
        Document record to inspect.

    Returns
    -------
    tuple[str, ...]
        Static warnings.
    """

    if document.kind == "binary":
        suffix = document.path.suffix.lower() or "extensionless file"
        return (f"unsupported text extraction for {suffix}",)
    return ()


def _preflight_warning_messages(
    documents: tuple[DocumentRecord, ...],
) -> tuple[str, ...]:
    """Run lightweight extraction checks before the full build.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Deduplicated document records to inspect.

    Returns
    -------
    tuple[str, ...]
        Preflight warning messages with source paths.
    """

    return tuple(
        f"{document.path}: {warning}"
        for document in documents
        for warning in _preflight_document_warnings(document)
    )


def _preflight_document_warnings(document: DocumentRecord) -> tuple[str, ...]:
    """Return preflight warnings for one document.

    Parameters
    ----------
    document : DocumentRecord
        Document record to inspect.

    Returns
    -------
    tuple[str, ...]
        Preflight warnings.
    """

    suffix = document.path.suffix.lower()
    if suffix == ".pdf" or document.kind.startswith("dicom_"):
        return ()
    if suffix in {".doc", ".xls"}:
        return ()
    if document.kind not in {"archive", "image", "office"}:
        return ()
    extracted = extract_text(document)
    return extracted.warnings


def extraction_warning_messages(
    documents: tuple[DocumentRecord, ...],
    extracted: tuple[ExtractedText, ...],
) -> tuple[str, ...]:
    """Format build extraction warnings without duplicating static warnings.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Documents passed to extraction.
    extracted : tuple[ExtractedText, ...]
        Extraction results corresponding to ``documents``.

    Returns
    -------
    tuple[str, ...]
        Extraction warnings with source paths.
    """

    return tuple(
        f"{document.path}: {warning}"
        for document, extracted_item in zip(documents, extracted, strict=True)
        for warning in extracted_item.warnings
        if warning not in _static_document_warnings(document)
    )
