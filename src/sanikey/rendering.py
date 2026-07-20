"""Create browser-openable representations for consultation exports."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .documents import (
    LEGACY_OFFICE_EXTENSIONS,
    PANDOC_EXTENSIONS,
    SPREADSHEET_EXTENSIONS,
    _known_suffix,
)

if TYPE_CHECKING:
    from .config import PersonConfig
    from .models import DocumentRecord


@dataclass(frozen=True)
class ConsultationRenderResult:
    """Result of preparing browser-openable document representations.

    Parameters
    ----------
    rendered_document_ids : tuple[str, ...]
        Identifiers for documents rendered or copied into the build.
    warning_messages : tuple[str, ...]
        Non-fatal rendering failures, one per document when applicable.

    Returns
    -------
    None
    """

    rendered_document_ids: tuple[str, ...]
    warning_messages: tuple[str, ...] = ()


_BROWSER_SUFFIXES = {".pdf", ".txt", ".md", ".htm", ".html", ".jpg", ".jpeg", ".png"}


def prepare_consultation_documents(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
) -> ConsultationRenderResult:
    """Prepare local representations for documents lacking a direct web link.

    Parameters
    ----------
    person : sanikey.config.PersonConfig
        Patient configuration that owns the generated build directory.
    documents : tuple[sanikey.models.DocumentRecord, ...]
        Source and container-derived document records.

    Returns
    -------
    ConsultationRenderResult
        Rendered identifiers and user-actionable warnings.

    Notes
    -----
    HTML members extracted from containers are viewer assets rather than
    independent clinical documents and are not rendered for consultation.
    """

    root = person.local_build / "rendered-documents"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    rendered: list[str] = []
    warnings: list[str] = []
    for document in documents:
        if document.kind.startswith("dicom_") or document.kind in {"archive", "binary"}:
            continue
        if document.origin == "container" and _known_suffix(document.path) in {
            ".htm",
            ".html",
        }:
            continue
        suffix = _known_suffix(document.path)
        target = root / document.document_id / _rendered_name(document, suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        if suffix in _BROWSER_SUFFIXES:
            if document.origin == "container":
                shutil.copy2(document.path, target)
                rendered.append(document.document_id)
            continue
        if document.kind != "office":
            continue
        warning = _render_office_document(document.path, target, suffix)
        if warning is None:
            rendered.append(document.document_id)
        else:
            warnings.append(f"{document.path}: {warning}")
    return ConsultationRenderResult(tuple(rendered), tuple(warnings))


def rendered_document_href(
    person: PersonConfig, document: DocumentRecord
) -> str | None:
    """Return the consultation href for one rendered or native document.

    Parameters
    ----------
    person : sanikey.config.PersonConfig
        Patient configuration that owns the generated build directory.
    document : sanikey.models.DocumentRecord
        Candidate document.

    Returns
    -------
    str | None
        Relative URL from ``web/index.html`` or ``None`` when unavailable.
    """

    rendered = person.local_build / "rendered-documents" / document.document_id
    files = sorted(path for path in rendered.glob("*") if path.is_file())
    if files:
        return f"../rendered-documents/{document.document_id}/{files[0].name}"
    if (
        document.origin != "source"
        or _known_suffix(document.path) not in _BROWSER_SUFFIXES
    ):
        return None
    try:
        relative = document.path.relative_to(person.source_documents)
    except ValueError:
        return None
    return f"../documents/{relative.as_posix()}"


def _rendered_name(document: DocumentRecord, suffix: str) -> str:
    """Return a stable file name for one generated representation.

    Parameters
    ----------
    document : sanikey.models.DocumentRecord
        Source document record.
    suffix : str
        Normalized logical suffix.

    Returns
    -------
    str
        Output file name.

    Notes
    -----
    Files that are already browser-openable retain their normalized suffix.
    The ``document.pdf`` name is reserved for a successful Office conversion.
    """

    if suffix in _BROWSER_SUFFIXES:
        return f"original{suffix}"
    if document.kind == "office":
        return "document.pdf"
    return f"original{suffix or '.bin'}"


def _render_office_document(path: Path, target: Path, suffix: str) -> str | None:
    """Render one Office document to a local PDF.

    Parameters
    ----------
    path : pathlib.Path
        Office input path.
    target : pathlib.Path
        PDF output path.
    suffix : str
        Normalized logical input suffix.

    Returns
    -------
    str | None
        Failure reason, or ``None`` when a PDF was produced.
    """

    if suffix in PANDOC_EXTENSIONS:
        executable = shutil.which("pandoc")
        if executable is None:
            return "Pandoc non installato; conversione PDF saltata"
        completed = subprocess.run(
            [executable, str(path), "--output", str(target)],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode == 0 and target.is_file():
            return None
        message = (
            completed.stderr or completed.stdout or "conversione Pandoc non riuscita"
        ).strip()
        return f"conversione PDF Pandoc non riuscita: {message}"
    if suffix in LEGACY_OFFICE_EXTENSIONS | SPREADSHEET_EXTENSIONS:
        executable = shutil.which("libreoffice") or shutil.which("soffice")
        if executable is None:
            return "LibreOffice non installato; conversione PDF saltata"
        with tempfile.TemporaryDirectory(prefix="sanikey-render-") as directory:
            completed = subprocess.run(
                [
                    executable,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    directory,
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
            rendered = Path(directory) / f"{path.stem}.pdf"
            if completed.returncode == 0 and rendered.is_file():
                shutil.copy2(rendered, target)
                return None
        message = (
            completed.stderr
            or completed.stdout
            or "conversione LibreOffice non riuscita"
        ).strip()
        return f"conversione PDF LibreOffice non riuscita: {message}"
    return "formato Office non supportato per la conversione PDF"
