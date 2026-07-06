"""Document inventory and text extraction."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .models import DocumentRecord

if TYPE_CHECKING:
    from .config import PersonConfig
    from .progress import ProgressReporter

DATE_PREFIX_RE = re.compile(r"^(?P<date>\d{8})[\s_-]+(?P<title>.+)$")
DICOM_EXTENSIONS = {".dcm": "dicom_file", ".img": "dicom_img", ".iso": "dicom_iso"}
TEXT_EXTENSIONS = {".txt", ".md"}
IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png"}
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


@dataclass(frozen=True)
class DocumentRecordOrigin:
    """Provenance fields for a document record.

    Parameters
    ----------
    origin : str
        Document origin, either ``source`` or ``container``.
    container_id : str | None, optional
        Parent container document id.
    internal_path : str | None, optional
        Member path inside the parent container.
    """

    origin: str = "source"
    container_id: str | None = None
    internal_path: str | None = None


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


def scan_document_inventory(
    person: PersonConfig,
    *,
    progress: ProgressReporter | None = None,
    progress_label: str | None = None,
) -> tuple[DocumentRecord, ...]:
    """Scan every file in a patient's source document directory.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    progress : ProgressReporter | None, optional
        Progress reporter for scanned files.
    progress_label : str | None, optional
        Label for the progress line.

    Returns
    -------
    tuple[DocumentRecord, ...]
        Deterministically sorted document records, including duplicate content.
    """

    root = person.source_documents
    if not root.exists():
        return ()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if progress is not None and progress_label is not None:
        progress.begin(progress_label, total=len(files), interval=20)
    records = []
    for index, path in enumerate(files, start=1):
        records.append(document_record_for_path(path, root=root, patient_id=person.id))
        if progress is not None:
            progress.advance(index, total=len(files))
    if progress is not None and progress_label is not None:
        progress.done(f"done files={len(files)}")
    return tuple(records)


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
    if suffix in IMAGE_EXTENSIONS:
        return _extract_image_text(document)
    if document.kind.startswith("dicom_"):
        return ExtractedText(
            document_id=document.document_id,
            text="",
        )
    return ExtractedText(
        document_id=document.document_id,
        text="",
        warnings=(f"unsupported text extraction for {suffix or 'extensionless file'}",),
    )


def document_record_for_path(
    path: Path,
    *,
    root: Path,
    patient_id: str,
    provenance: DocumentRecordOrigin | None = None,
) -> DocumentRecord:
    """Build a document record for one file.

    Parameters
    ----------
    path : pathlib.Path
        Source file.
    root : pathlib.Path
        Source document root.
    patient_id : str
        Owning patient id.
    provenance : DocumentRecordOrigin | None, optional
        Optional provenance fields.

    Returns
    -------
    DocumentRecord
        Document record.
    """

    digest = _sha256(path)
    record_origin = provenance or DocumentRecordOrigin()
    relative = path.relative_to(root)
    category = relative.parts[0] if len(relative.parts) > 1 else "uncategorized"
    date, title = _title_from_name(path.stem)
    kind = _document_kind(path)
    document_id = digest
    if record_origin.origin != "source":
        identity = "\0".join(
            (
                record_origin.origin,
                record_origin.container_id or "",
                record_origin.internal_path or "",
                digest,
            )
        )
        document_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return DocumentRecord(
        document_id=document_id,
        patient_id=patient_id,
        path=path,
        title=title,
        category=category,
        kind=kind,
        sha256=digest,
        date=date,
        origin=record_origin.origin,
        container_id=record_origin.container_id,
        internal_path=record_origin.internal_path,
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
    if _has_dicom_magic(path):
        return "dicom_file"
    if suffix in DICOM_EXTENSIONS:
        return DICOM_EXTENSIONS[suffix]
    if suffix == ".pdf":
        return "pdf"
    if suffix in TEXT_EXTENSIONS:
        return "text"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in ARCHIVE_EXTENSIONS:
        return "archive"
    if suffix in OFFICE_EXTENSIONS | XLSX_EXTENSIONS:
        return "office"
    return "binary"


def _has_dicom_magic(path: Path) -> bool:
    """Return whether a file contains the standard DICOM magic marker.

    Parameters
    ----------
    path : pathlib.Path
        File to inspect.

    Returns
    -------
    bool
        ``True`` when bytes 128-131 are ``DICM``.
    """

    try:
        with path.open("rb") as handle:
            handle.seek(128)
            return handle.read(4) == b"DICM"
    except OSError:
        return False


def _extract_image_text(document: DocumentRecord) -> ExtractedText:
    """Extract text from an image using the system Tesseract CLI.

    Parameters
    ----------
    document : DocumentRecord
        Image document.

    Returns
    -------
    ExtractedText
        Extracted OCR text or warning.
    """

    executable = shutil.which("tesseract")
    if executable is None:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=("Tesseract not installed; image OCR skipped",),
        )
    command = [
        executable,
        str(document.path),
        "stdout",
        *_tesseract_language_arguments(executable),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=(f"Tesseract failed; image OCR skipped: {exc}",),
        )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        return ExtractedText(
            document_id=document.document_id,
            text="",
            warnings=(f"Tesseract failed; image OCR skipped: {detail}",),
        )
    return ExtractedText(document_id=document.document_id, text=result.stdout.strip())


def _tesseract_language_arguments(executable: str) -> tuple[str, ...]:
    """Return preferred Tesseract language arguments when available.

    Parameters
    ----------
    executable : str
        Tesseract executable path.

    Returns
    -------
    tuple[str, ...]
        ``("-l", "ita+eng")`` when both languages are available, otherwise empty.
    """

    try:
        result = subprocess.run(
            [executable, "--list-langs"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()
    available = {
        line.strip()
        for line in (*result.stdout.splitlines(), *result.stderr.splitlines())
        if line.strip() and not line.startswith("List of available languages")
    }
    if {"ita", "eng"}.issubset(available):
        return ("-l", "ita+eng")
    return ()


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

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
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
    warning_messages = tuple(
        dict.fromkeys(
            "XLSX text extracted; workbook compatibility feature not preserved: "
            f"{item.message}"
            for item in caught
        )
    )
    return ExtractedText(
        document_id=document.document_id,
        text="\n".join(parts),
        warnings=warning_messages,
    )


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
        completed = _run_ocrmypdf(
            executable,
            document.path,
            sidecar,
            output_pdf,
        )
        if completed.returncode != 0 and _should_retry_ocrmypdf_without_optimize(
            completed
        ):
            sidecar.unlink(missing_ok=True)
            output_pdf.unlink(missing_ok=True)
            retry = _run_ocrmypdf(
                executable,
                document.path,
                sidecar,
                output_pdf,
                optimize=False,
            )
            if retry.returncode == 0:
                completed = retry
            else:
                detail = _summarize_command_failure(completed)
                retry_detail = _summarize_command_failure(retry)
                return ExtractedText(
                    document_id=document.document_id,
                    text="",
                    warnings=(
                        "OCRmyPDF failed; PDF text extraction skipped: "
                        f"{detail}; retry with --optimize 0 failed: {retry_detail}",
                    ),
                )
        if completed.returncode != 0:
            detail = _summarize_command_failure(completed)
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


def _run_ocrmypdf(
    executable: str,
    source: Path,
    sidecar: Path,
    output_pdf: Path,
    *,
    optimize: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run OCRmyPDF for one PDF document.

    Parameters
    ----------
    executable : str
        OCRmyPDF executable path.
    source : pathlib.Path
        Source PDF.
    sidecar : pathlib.Path
        Text sidecar output path.
    output_pdf : pathlib.Path
        Temporary OCR PDF output path.
    optimize : bool, optional
        Whether OCRmyPDF should run its PDF optimization phase.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed OCRmyPDF process.
    """

    command = [executable, "--skip-text"]
    if not optimize:
        command.extend(("--optimize", "0"))
    command.extend(("--sidecar", str(sidecar), str(source), str(output_pdf)))
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


def _should_retry_ocrmypdf_without_optimize(
    completed: subprocess.CompletedProcess[str],
) -> bool:
    """Return whether OCRmyPDF should be retried without optimization.

    Parameters
    ----------
    completed : subprocess.CompletedProcess[str]
        Failed OCRmyPDF process.

    Returns
    -------
    bool
        ``True`` when the failure appears to happen after OCR during PDF
        optimization or image transcoding.
    """

    output = f"{completed.stderr}\n{completed.stdout}".lower()
    return any(
        marker in output
        for marker in (
            "optimize_pdf",
            "optimize.py",
            "transcode_jpegs",
            "image file is truncated",
        )
    )


def _summarize_command_failure(completed: subprocess.CompletedProcess[str]) -> str:
    """Summarize a failed external command without dumping full logs.

    Parameters
    ----------
    completed : subprocess.CompletedProcess[str]
        Failed command result.

    Returns
    -------
    str
        Short failure detail suitable for user-facing reports.
    """

    lines = [
        line.strip()
        for text in (completed.stderr, completed.stdout)
        for line in text.splitlines()
        if line.strip()
    ]
    for line in reversed(lines):
        if any(marker in line for marker in ("Error", "Exception", "OSError")):
            return line
    if lines:
        return lines[-1]
    return f"exit status {completed.returncode}"
