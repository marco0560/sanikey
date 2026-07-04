"""Document inventory and text extraction."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .models import DocumentRecord

if TYPE_CHECKING:
    from .config import PersonConfig

DATE_PREFIX_RE = re.compile(r"^(?P<date>\d{8})[\s_-]+(?P<title>.+)$")
DICOM_EXTENSIONS = {".iso": "dicom_iso", ".zip": "dicom_zip"}
TEXT_EXTENSIONS = {".txt", ".md"}
ARCHIVE_EXTENSIONS = {".7z", ".rar", ".zip"}
DOCX_EXTENSIONS = {".docx"}
LEGACY_OFFICE_EXTENSIONS = {".doc", ".xls"}
ODF_EXTENSIONS = {".ods", ".odt"}
OFFICE_EXTENSIONS = DOCX_EXTENSIONS | LEGACY_OFFICE_EXTENSIONS | ODF_EXTENSIONS
XLSX_EXTENSIONS = {".xlsx"}
MIN_PDF_TEXT_CHARACTERS = 40


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
    if suffix in ARCHIVE_EXTENSIONS:
        return _extract_archive_text(document)
    if suffix in DOCX_EXTENSIONS:
        return _extract_docx_text(document)
    if suffix in XLSX_EXTENSIONS:
        return _extract_xlsx_text(document)
    if suffix in ODF_EXTENSIONS:
        return _extract_odf_text(document)
    if suffix in LEGACY_OFFICE_EXTENSIONS:
        return _extract_legacy_office_text(document)
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
    if suffix in ARCHIVE_EXTENSIONS:
        return "archive"
    if suffix in OFFICE_EXTENSIONS | XLSX_EXTENSIONS:
        return "office"
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
    if pymupdf_result is not None and _has_sufficient_pdf_text(pymupdf_result.text):
        return pymupdf_result
    ocrmypdf_result = _extract_pdf_text_with_ocrmypdf(document)
    if ocrmypdf_result is not None:
        if pymupdf_result is not None and pymupdf_result.warnings:
            return ExtractedText(
                document_id=document.document_id,
                text=ocrmypdf_result.text,
                warnings=(*pymupdf_result.warnings, *ocrmypdf_result.warnings),
            )
        return ocrmypdf_result
    if pymupdf_result is not None:
        if pymupdf_result.warnings:
            return pymupdf_result
        return ExtractedText(
            document_id=document.document_id,
            text=pymupdf_result.text,
            warnings=(
                "PyMuPDF extracted insufficient text and no OCR provider is available",
            ),
        )
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
    display_errors = bool(fitz.TOOLS.mupdf_display_errors())
    display_warnings = bool(fitz.TOOLS.mupdf_display_warnings())
    try:
        fitz.TOOLS.mupdf_display_errors(False)
        fitz.TOOLS.mupdf_display_warnings(False)
        with fitz.open(document.path) as pdf:
            text = "\n".join(page.get_text() for page in pdf)
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=(
                "PyMuPDF could not extract PDF text; falling back to OCRmyPDF "
                f"if available: {exc}",
            ),
        )
    finally:
        fitz.TOOLS.mupdf_display_errors(display_errors)
        fitz.TOOLS.mupdf_display_warnings(display_warnings)
    return ExtractedText(document_id=document.document_id, text=text)


def _has_sufficient_pdf_text(text: str) -> bool:
    """Return whether extracted PDF text is sufficient to skip OCR.

    Parameters
    ----------
    text : str
        Extracted text.

    Returns
    -------
    bool
        ``True`` when text has enough non-whitespace characters.
    """

    return sum(1 for character in text if not character.isspace()) >= (
        MIN_PDF_TEXT_CHARACTERS
    )


def _extract_archive_text(document: DocumentRecord) -> ExtractedText:
    """Extract an archive member inventory.

    Parameters
    ----------
    document : DocumentRecord
        Archive document.

    Returns
    -------
    ExtractedText
        Textual archive inventory or warning.
    """

    suffix = document.path.suffix.lower()
    if suffix == ".zip":
        return _extract_zip_inventory(document)
    if suffix == ".7z":
        return _extract_7z_inventory(document)
    if suffix == ".rar":
        return _extract_rar_inventory(document)
    return ExtractedText(
        document_id=document.document_id,
        text="",
        warnings=(f"unsupported archive format {suffix}",),
    )


def _extract_zip_inventory(document: DocumentRecord) -> ExtractedText:
    """Extract ZIP member names.

    Parameters
    ----------
    document : DocumentRecord
        ZIP document.

    Returns
    -------
    ExtractedText
        Textual inventory or warning.
    """

    try:
        with zipfile.ZipFile(document.path) as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile) as exc:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=(f"ZIP inventory extraction failed: {exc}",),
        )
    return ExtractedText(
        document_id=document.document_id,
        text=_archive_inventory_text("zip", names),
    )


def _extract_7z_inventory(document: DocumentRecord) -> ExtractedText:
    """Extract 7z member names.

    Parameters
    ----------
    document : DocumentRecord
        7z document.

    Returns
    -------
    ExtractedText
        Textual inventory or warning.
    """

    try:
        import py7zr

        with py7zr.SevenZipFile(document.path) as archive:
            names = archive.getnames()
    except (OSError, py7zr.Bad7zFile, py7zr.PasswordRequired) as exc:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=(f"7z inventory extraction failed: {exc}",),
        )
    return ExtractedText(
        document_id=document.document_id,
        text=_archive_inventory_text("7z", names),
    )


def _extract_rar_inventory(document: DocumentRecord) -> ExtractedText:
    """Extract RAR member names.

    Parameters
    ----------
    document : DocumentRecord
        RAR document.

    Returns
    -------
    ExtractedText
        Textual inventory or warning.
    """

    try:
        import rarfile

        with rarfile.RarFile(document.path) as archive:
            names = archive.namelist()
    except (OSError, rarfile.Error) as exc:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=(f"RAR inventory extraction failed: {exc}",),
        )
    return ExtractedText(
        document_id=document.document_id,
        text=_archive_inventory_text("rar", names),
    )


def _archive_inventory_text(kind: str, names: list[str]) -> str:
    """Render archive member names as text.

    Parameters
    ----------
    kind : str
        Archive kind.
    names : list[str]
        Member names.

    Returns
    -------
    str
        Textual inventory.
    """

    if not names:
        return f"{kind} archive is empty"
    return "\n".join((f"{kind} archive contents:", *sorted(names)))


def _extract_docx_text(document: DocumentRecord) -> ExtractedText:
    """Extract text from a DOCX document.

    Parameters
    ----------
    document : DocumentRecord
        DOCX document.

    Returns
    -------
    ExtractedText
        Extracted text or warning.
    """

    try:
        import docx
        from docx.opc.exceptions import PackageNotFoundError

        parsed = docx.Document(str(document.path))
        parts = [paragraph.text for paragraph in parsed.paragraphs if paragraph.text]
        for table in parsed.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row.cells if cell.text)
    except (OSError, PackageNotFoundError, ValueError, zipfile.BadZipFile) as exc:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=(f"DOCX text extraction failed: {exc}",),
        )
    return ExtractedText(document_id=document.document_id, text="\n".join(parts))


def _extract_xlsx_text(document: DocumentRecord) -> ExtractedText:
    """Extract text from an XLSX workbook.

    Parameters
    ----------
    document : DocumentRecord
        XLSX document.

    Returns
    -------
    ExtractedText
        Extracted cell text or warning.
    """

    try:
        import openpyxl
        from openpyxl.utils.exceptions import InvalidFileException

        workbook = openpyxl.load_workbook(
            document.path,
            read_only=True,
            data_only=True,
        )
        parts = []
        for worksheet in workbook.worksheets:
            parts.append(f"[{worksheet.title}]")
            for row in worksheet.iter_rows(values_only=True):
                values = [str(value) for value in row if value is not None]
                if values:
                    parts.append("\t".join(values))
        workbook.close()
    except (InvalidFileException, OSError, ValueError, zipfile.BadZipFile) as exc:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=(f"XLSX text extraction failed: {exc}",),
        )
    return ExtractedText(document_id=document.document_id, text="\n".join(parts))


def _extract_odf_text(document: DocumentRecord) -> ExtractedText:
    """Extract text from ODF documents.

    Parameters
    ----------
    document : DocumentRecord
        ODT or ODS document.

    Returns
    -------
    ExtractedText
        Extracted text or warning.
    """

    try:
        from odf import table as odf_table
        from odf.opendocument import load
        from odf.teletype import extractText

        parsed = load(str(document.path))
        if document.path.suffix.lower() == ".ods":
            parts = []
            for sheet in parsed.spreadsheet.getElementsByType(odf_table.Table):
                sheet_name = sheet.getAttribute("name")
                if sheet_name:
                    parts.append(f"[{sheet_name}]")
                for row in sheet.getElementsByType(odf_table.TableRow):
                    values = [
                        extractText(cell)
                        for cell in row.getElementsByType(odf_table.TableCell)
                    ]
                    values = [value for value in values if value]
                    if values:
                        parts.append("\t".join(values))
            text = "\n".join(parts)
        else:
            text = extractText(parsed.text)
    except (AttributeError, OSError, ValueError, zipfile.BadZipFile) as exc:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=(f"ODF text extraction failed: {exc}",),
        )
    return ExtractedText(document_id=document.document_id, text=text)


def _extract_legacy_office_text(document: DocumentRecord) -> ExtractedText:
    """Extract text from legacy Office documents through LibreOffice.

    Parameters
    ----------
    document : DocumentRecord
        Legacy ``.doc`` or ``.xls`` document.

    Returns
    -------
    ExtractedText
        Extracted text or warning.
    """

    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if executable is None:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=("LibreOffice not installed; legacy Office extraction skipped",),
        )
    suffix = document.path.suffix.lower()
    output_filter = "csv" if suffix == ".xls" else "txt:Text"
    with tempfile.TemporaryDirectory(prefix="sanikey-office-") as directory:
        output_dir = Path(directory)
        try:
            completed = subprocess.run(
                [
                    executable,
                    "--headless",
                    "--convert-to",
                    output_filter,
                    "--outdir",
                    str(output_dir),
                    str(document.path),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return ExtractedText(
                document_id=document.document_id,
                text="",
                warnings=("LibreOffice extraction timed out",),
            )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            return ExtractedText(
                document_id=document.document_id,
                text="",
                warnings=(f"LibreOffice extraction failed: {detail}",),
            )
        outputs = sorted(path for path in output_dir.iterdir() if path.is_file())
        if not outputs:
            return ExtractedText(
                document_id=document.document_id,
                text="",
                warnings=("LibreOffice did not produce extracted text",),
            )
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace") for path in outputs
        )
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
