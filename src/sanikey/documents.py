"""Document inventory and text extraction."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .models import DocumentRecord

if TYPE_CHECKING:
    from .config import PersonConfig

DATE_PREFIX_RE = re.compile(r"^(?P<date>\d{8})[\s_-]+(?P<title>.+)$")
DICOM_EXTENSIONS = {".iso": "dicom_iso", ".zip": "dicom_zip"}
TEXT_EXTENSIONS = {".txt", ".md"}


@dataclass(frozen=True)
class ExtractedText:
    """Text extracted from one document.

    Parameters
    ----------
    document_id : str
        Source document id.
    text : str
        Extracted text content.
    warnings : tuple[str, ...]
        Non-fatal extraction warnings.
    """

    document_id: str
    text: str
    warnings: tuple[str, ...] = ()


def scan_documents(person: PersonConfig) -> tuple[DocumentRecord, ...]:
    """Scan a patient's source document directory.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    tuple[DocumentRecord, ...]
        Deterministically sorted document records.
    """

    return _deduplicate_documents(scan_document_inventory(person))


def scan_document_inventory(person: PersonConfig) -> tuple[DocumentRecord, ...]:
    """Scan every file in a patient's source document directory.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    tuple[DocumentRecord, ...]
        Deterministically sorted document records, including duplicate content.
    """

    root = person.source_documents
    if not root.exists():
        return ()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    return tuple(
        _record_for_path(path, root=root, patient_id=person.id) for path in files
    )


def find_duplicate_documents(
    documents: tuple[DocumentRecord, ...],
) -> dict[str, tuple[DocumentRecord, ...]]:
    """Find technical duplicate documents by digest.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Document records to inspect.

    Returns
    -------
    dict[str, tuple[DocumentRecord, ...]]
        SHA256 digests with more than one document.
    """

    grouped: dict[str, list[DocumentRecord]] = {}
    for document in documents:
        grouped.setdefault(document.sha256, []).append(document)
    return {digest: tuple(items) for digest, items in grouped.items() if len(items) > 1}


def duplicate_document_warnings(
    duplicates: dict[str, tuple[DocumentRecord, ...]],
) -> tuple[str, ...]:
    """Build warnings for duplicate-content documents.

    Parameters
    ----------
    duplicates : dict[str, tuple[DocumentRecord, ...]]
        Duplicate digest groups.

    Returns
    -------
    tuple[str, ...]
        Human-readable warnings naming the identical files.
    """

    warnings: list[str] = []
    for digest, documents in sorted(duplicates.items()):
        retained = documents[0]
        for skipped in documents[1:]:
            warnings.append(
                "duplicate document content skipped. "
                "The following files are identical "
                f"(sha256={digest}): \n{retained.path}\n{skipped.path}"
            )
    return tuple(warnings)


def extract_text(document: DocumentRecord) -> ExtractedText:
    """Extract text from a document when supported.

    Parameters
    ----------
    document : DocumentRecord
        Source document.

    Returns
    -------
    ExtractedText
        Extracted text and non-fatal warnings.
    """

    suffix = document.path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return ExtractedText(
            document_id=document.document_id,
            text=document.path.read_text(encoding="utf-8", errors="replace"),
        )
    if suffix == ".pdf":
        return _extract_pdf_text(document)
    if document.kind.startswith("dicom_"):
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=("DICOM supports are cataloged but not OCR-extracted",),
        )
    return ExtractedText(
        document_id=document.document_id,
        text="",
        warnings=(f"unsupported text extraction for {suffix or 'extensionless file'}",),
    )


def _record_for_path(path: Path, *, root: Path, patient_id: str) -> DocumentRecord:
    """Build a document record for one file.

    Parameters
    ----------
    path : pathlib.Path
        Source file.
    root : pathlib.Path
        Source document root.
    patient_id : str
        Owning patient id.

    Returns
    -------
    DocumentRecord
        Document record.
    """

    digest = _sha256(path)
    relative = path.relative_to(root)
    category = relative.parts[0] if len(relative.parts) > 1 else "uncategorized"
    date, title = _title_from_name(path.stem)
    kind = _document_kind(path)
    return DocumentRecord(
        document_id=digest,
        patient_id=patient_id,
        path=path,
        title=title,
        category=category,
        kind=kind,
        sha256=digest,
        date=date,
    )


def _deduplicate_documents(
    documents: tuple[DocumentRecord, ...],
) -> tuple[DocumentRecord, ...]:
    """Keep only the first document for each content digest.

    Parameters
    ----------
    documents : tuple[DocumentRecord, ...]
        Scanned document records in deterministic order.
    Returns
    -------
    tuple[DocumentRecord, ...]
        First document for each SHA256 digest.
    """

    seen: set[str] = set()
    retained: list[DocumentRecord] = []
    for document in documents:
        if document.sha256 in seen:
            continue
        seen.add(document.sha256)
        retained.append(document)
    return tuple(retained)


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


def _title_from_name(stem: str) -> tuple[str | None, str]:
    """Extract optional date and title from a filename stem.

    Parameters
    ----------
    stem : str
        Filename stem.

    Returns
    -------
    tuple[str | None, str]
        ISO date when present and a readable title.
    """

    match = DATE_PREFIX_RE.match(stem)
    if match is None:
        return None, stem.replace("_", " ").strip()
    raw_date = match.group("date")
    date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    return date, match.group("title").replace("_", " ").strip()


def _document_kind(path: Path) -> str:
    """Return document kind from extension.

    Parameters
    ----------
    path : pathlib.Path
        Source file.

    Returns
    -------
    str
        Document kind.
    """

    suffix = path.suffix.lower()
    if suffix in DICOM_EXTENSIONS:
        return DICOM_EXTENSIONS[suffix]
    if suffix == ".pdf":
        return "pdf"
    if suffix in TEXT_EXTENSIONS:
        return "text"
    return "binary"


def _extract_pdf_text(document: DocumentRecord) -> ExtractedText:
    """Extract PDF text through the first available provider.

    Parameters
    ----------
    document : DocumentRecord
        PDF document.

    Returns
    -------
    ExtractedText
        Extracted text or warning when no provider is available.
    """

    pymupdf_result = _extract_pdf_text_with_pymupdf(document)
    if pymupdf_result is not None:
        return pymupdf_result
    ocrmypdf_result = _extract_pdf_text_with_ocrmypdf(document)
    if ocrmypdf_result is not None:
        return ocrmypdf_result
    return ExtractedText(
        document_id=document.document_id,
        text="",
        warnings=(
            "No PDF text extraction provider available; install PyMuPDF "
            "or configure OCRmyPDF",
        ),
    )


def _extract_pdf_text_with_pymupdf(document: DocumentRecord) -> ExtractedText | None:
    """Extract PDF text with PyMuPDF when installed.

    Parameters
    ----------
    document : DocumentRecord
        PDF document.

    Returns
    -------
    ExtractedText | None
        Extracted text, or ``None`` when PyMuPDF is unavailable.
    """

    try:
        import fitz
    except ImportError:
        return None
    with fitz.open(document.path) as pdf:
        text = "\n".join(page.get_text() for page in pdf)
    return ExtractedText(document_id=document.document_id, text=text)


def _extract_pdf_text_with_ocrmypdf(document: DocumentRecord) -> ExtractedText | None:
    """Extract PDF text with system OCRmyPDF sidecar output when available.

    Parameters
    ----------
    document : DocumentRecord
        PDF document.

    Returns
    -------
    ExtractedText | None
        Extracted text, warning from OCRmyPDF, or ``None`` when unavailable.
    """

    executable = shutil.which("ocrmypdf")
    if executable is None:
        return None
    with tempfile.TemporaryDirectory(prefix="sanikey-ocr-") as directory:
        temp_root = Path(directory)
        sidecar = temp_root / "document.txt"
        output_pdf = temp_root / "document.pdf"
        completed = subprocess.run(
            [
                executable,
                "--skip-text",
                "--sidecar",
                str(sidecar),
                str(document.path),
                str(output_pdf),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            if not detail:
                detail = f"exit status {completed.returncode}"
            return ExtractedText(
                document_id=document.document_id,
                text="",
                warnings=(f"OCRmyPDF failed; PDF text extraction skipped: {detail}",),
            )
        if not sidecar.is_file():
            return ExtractedText(
                document_id=document.document_id,
                text="",
                warnings=("OCRmyPDF did not produce text sidecar",),
            )
        return ExtractedText(
            document_id=document.document_id,
            text=sidecar.read_text(encoding="utf-8", errors="replace"),
        )
