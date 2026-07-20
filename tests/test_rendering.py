"""Tests for browser-openable consultation document representations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from sanikey import rendering
from sanikey.config import PersonConfig
from sanikey.documents import DocumentRecordOrigin, document_record_for_path
from sanikey.exports import generate_exports
from sanikey.metadata import load_curated_metadata
from sanikey.rendering import prepare_consultation_documents

if TYPE_CHECKING:
    import pytest


def _person(tmp_path: Path) -> PersonConfig:
    """Build a synthetic patient configuration.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    sanikey.config.PersonConfig
        Isolated patient configuration.
    """

    return PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=tmp_path / "documents",
        metadata_directory=tmp_path / "metadata",
        local_build=tmp_path / "generated",
        usb_uuid="1A2B-3C4D",
    )


def test_prepare_consultation_documents_copies_container_pdf(tmp_path: Path) -> None:
    """Verify an extracted PDF becomes a local consultation document.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir()
    container = person.source_documents / "support.zip"
    container.write_bytes(b"archive")
    staged_root = tmp_path / "staging"
    staged_root.mkdir()
    pdf = staged_root / "referto.pdf"
    pdf.write_bytes(b"%PDF-synthetic")
    container_record = document_record_for_path(
        container, root=person.source_documents, patient_id=person.id
    )
    record = document_record_for_path(
        pdf,
        root=staged_root,
        patient_id=person.id,
        provenance=DocumentRecordOrigin(
            origin="container",
            container_id=container_record.document_id,
            internal_path="referto.pdf",
        ),
    )

    result = prepare_consultation_documents(person, (record,))
    exported = generate_exports(
        person, (record,), load_curated_metadata(person.metadata_directory)
    )
    documents = json.loads(exported.documents.read_text(encoding="utf-8"))

    assert result.rendered_document_ids == (record.document_id,)
    assert documents[0]["href"].startswith("../rendered-documents/")
    assert (person.local_build / documents[0]["href"][3:]).is_file()


def test_prepare_consultation_documents_excludes_container_html(
    tmp_path: Path,
) -> None:
    """Verify container HTML stays out of clinical consultation documents.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir()
    container = person.source_documents / "support.zip"
    container.write_bytes(b"archive")
    staged_root = tmp_path / "staging"
    staged_root.mkdir()
    page = staged_root / "INDEX.HTM"
    page.write_text("<html>viewer</html>", encoding="utf-8")
    container_record = document_record_for_path(
        container, root=person.source_documents, patient_id=person.id
    )
    record = document_record_for_path(
        page,
        root=staged_root,
        patient_id=person.id,
        provenance=DocumentRecordOrigin(
            origin="container",
            container_id=container_record.document_id,
            internal_path="INDEX.HTM",
        ),
    )

    result = prepare_consultation_documents(person, (record,))
    exported = generate_exports(
        person, (record,), load_curated_metadata(person.metadata_directory)
    )

    assert result.rendered_document_ids == ()
    assert json.loads(exported.documents.read_text(encoding="utf-8")) == []
    assert not (person.local_build / "rendered-documents" / record.document_id).exists()


def test_rendered_name_preserves_browser_openable_suffix(tmp_path: Path) -> None:
    """Verify browser-openable files cannot be renamed as converted PDFs.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    page = tmp_path / "viewer.html"
    page.write_text("<html>viewer</html>", encoding="utf-8")
    record = document_record_for_path(page, root=tmp_path, patient_id="patient-a")

    assert rendering._rendered_name(record, ".html") == "original.html"


def test_generate_exports_lists_non_openable_documents_by_extension(
    tmp_path: Path,
) -> None:
    """Verify non-openable records are removed from consultation and listed technically.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir()
    archive = person.source_documents / "archive.zip"
    archive.write_bytes(b"archive")
    binary = person.source_documents / "legacy.bin"
    binary.write_bytes(b"binary")
    records = tuple(
        document_record_for_path(
            path, root=person.source_documents, patient_id=person.id
        )
        for path in (archive, binary)
    )

    exported = generate_exports(
        person, records, load_curated_metadata(person.metadata_directory)
    )
    technical = (
        person.local_build / "technical" / "documenti-non-apribili.csv"
    ).read_text(encoding="utf-8")

    assert json.loads(exported.documents.read_text(encoding="utf-8")) == []
    assert technical.index('".bin"') < technical.index('".zip"')
    assert "legacy.bin" in technical
    assert "archive.zip" in technical


def test_render_office_document_covers_converter_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Office conversion handles missing, failing, and working tools.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    source = tmp_path / "letter.docx"
    source.write_text("synthetic", encoding="utf-8")
    target = tmp_path / "letter.pdf"
    monkeypatch.setattr(rendering.shutil, "which", lambda _name: None)
    assert "Pandoc non installato" in rendering._render_office_document(
        source, target, ".docx"
    )
    assert "LibreOffice non installato" in rendering._render_office_document(
        source, target, ".doc"
    )
    assert rendering._render_office_document(source, target, ".bin") == (
        "formato Office non supportato per la conversione PDF"
    )

    monkeypatch.setattr(rendering.shutil, "which", lambda _name: "/usr/bin/pandoc")
    monkeypatch.setattr(
        rendering.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess((), 1, stderr="errore"),
    )
    assert (
        rendering._render_office_document(source, target, ".docx")
        == "conversione PDF Pandoc non riuscita: errore"
    )

    def successful_pandoc(arguments: list[str], **_kwargs: object) -> object:
        """Write the requested synthetic Pandoc PDF.

        Parameters
        ----------
        arguments : list[str]
            Pandoc command arguments.
        _kwargs : object
            Ignored subprocess keyword arguments.

        Returns
        -------
        object
            Successful process result.
        """

        Path(arguments[arguments.index("--output") + 1]).write_bytes(b"%PDF-test")
        return subprocess.CompletedProcess(arguments, 0)

    monkeypatch.setattr(rendering.subprocess, "run", successful_pandoc)
    assert rendering._render_office_document(source, target, ".docx") is None
    assert target.read_bytes() == b"%PDF-test"

    def successful_libreoffice(arguments: list[str], **_kwargs: object) -> object:
        """Write the synthetic PDF emitted by LibreOffice.

        Parameters
        ----------
        arguments : list[str]
            LibreOffice command arguments.
        _kwargs : object
            Ignored subprocess keyword arguments.

        Returns
        -------
        object
            Successful process result.
        """

        output_directory = Path(arguments[arguments.index("--outdir") + 1])
        (output_directory / f"{source.stem}.pdf").write_bytes(b"%PDF-office")
        return subprocess.CompletedProcess(arguments, 0)

    monkeypatch.setattr(rendering.subprocess, "run", successful_libreoffice)
    assert rendering._render_office_document(source, target, ".doc") is None
    assert target.read_bytes() == b"%PDF-office"


def test_prepare_documents_renders_office_and_resolves_source_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Office render results and safe native-document fallback links.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir()
    office = person.source_documents / "letter.docx"
    text = person.source_documents / "note.txt"
    foreign = tmp_path / "foreign.txt"
    office.write_text("synthetic office", encoding="utf-8")
    text.write_text("synthetic text", encoding="utf-8")
    foreign.write_text("synthetic foreign", encoding="utf-8")
    office_record = document_record_for_path(
        office, root=person.source_documents, patient_id=person.id
    )
    text_record = document_record_for_path(
        text, root=person.source_documents, patient_id=person.id
    )
    foreign_record = document_record_for_path(
        foreign, root=tmp_path, patient_id=person.id
    )

    def render_office(_source: Path, target: Path, _suffix: str) -> None:
        """Write a synthetic rendered PDF.

        Parameters
        ----------
        _source : pathlib.Path
            Ignored Office source document.
        target : pathlib.Path
            Rendered PDF destination.
        _suffix : str
            Ignored source suffix.

        Returns
        -------
        None
        """

        target.write_bytes(b"%PDF-rendered")

    monkeypatch.setattr(rendering, "_render_office_document", render_office)
    result = prepare_consultation_documents(person, (office_record, text_record))

    assert result.rendered_document_ids == (office_record.document_id,)
    assert rendering.rendered_document_href(person, office_record).endswith(
        "document.pdf"
    )
    assert (
        rendering.rendered_document_href(person, text_record) == "../documents/note.txt"
    )
    assert rendering.rendered_document_href(person, foreign_record) is None
