"""USB export tests."""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pytest

from sanikey.build import build_patient
from sanikey.config import AccountsConfig, IngestionConfig, PersonConfig
from sanikey.usb import export_usb, usb_image_root, validate_usb


def _person(tmp_path: Path, patient_id: str, display_name: str) -> PersonConfig:
    """Build a synthetic patient config.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.
    patient_id : str
        Patient identifier.
    display_name : str
        Patient display name.

    Returns
    -------
    PersonConfig
        Patient configuration.
    """

    return PersonConfig(
        id=patient_id,
        display_name=display_name,
        source_documents=tmp_path / patient_id / "documents",
        metadata_directory=tmp_path / patient_id / "metadata",
        local_build=tmp_path / patient_id / "generated",
        usb_uuid=f"UUID-{patient_id}",
    )


def _write_document(person: PersonConfig, filename: str, text: str) -> None:
    """Write one synthetic source document.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    filename : str
        Source document filename.
    text : str
        Document content.

    Returns
    -------
    None
    """

    person.source_documents.mkdir(parents=True)
    (person.source_documents / filename).write_text(text, encoding="utf-8")


class ProgressRecorder:
    """Record progress labels emitted by USB export.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    def __init__(self) -> None:
        """Initialize the recorder.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.labels: list[str] = []

    def begin(
        self,
        label: str,
        *,
        total: int | None = None,
        interval: int | None = None,
    ) -> None:
        """Record a progress line label.

        Parameters
        ----------
        label : str
            Progress label.
        total : int | None, optional
            Expected item count.
        interval : int | None, optional
            Dot interval override.

        Returns
        -------
        None
        """

        self.labels.append(label)

    def advance(self, completed: int, *, total: int | None = None) -> None:
        """Ignore progress advancement.

        Parameters
        ----------
        completed : int
            Completed item count.
        total : int | None, optional
            Expected item count.

        Returns
        -------
        None
        """

    def done(self, summary: str = "done") -> None:
        """Ignore progress completion.

        Parameters
        ----------
        summary : str, optional
            Completion summary.

        Returns
        -------
        None
        """


def test_export_usb_writes_chapter_three_layout(tmp_path: Path) -> None:
    """Verify simulated USB export layout and validation.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path, "patient-a", "Patient A")
    _write_document(person, "20260102 Report.txt", "synthetic")
    build_patient(person, mode="full")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )

    result = export_usb(config, tmp_path / "usb")

    assert result.patients == 1
    assert (result.root / "START-HERE-Patient-A.html").is_file()
    assert (result.root / "patients" / "patient-a" / "medical_archive.db").is_file()
    assert (result.root / "patients" / "patient-a" / "web" / "index.html").is_file()
    assert (result.root / "patients" / "patient-a" / "web" / "data.js").is_file()
    data_script = (
        result.root / "patients" / "patient-a" / "web" / "data.js"
    ).read_text(encoding="utf-8")
    assert '"href": "../documents/20260102 Report.txt"' in data_script
    assert str(person.source_documents) not in data_script
    assert (usb_image_root(config) / "START-HERE-Patient-A.html").is_file()
    assert usb_image_root(config) != result.root
    assert validate_usb(result.root)


def test_export_usb_reports_progress_phases(tmp_path: Path) -> None:
    """Verify USB export emits progress labels for long-running phases.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path, "patient-a", "Patient A")
    _write_document(person, "20260102 Report.txt", "synthetic")
    build_patient(person, mode="full")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )
    progress = ProgressRecorder()

    export_usb(config, tmp_path / "usb", progress=progress)

    assert progress.labels == [
        "export-usb prepare",
        "export-usb image",
        "export-usb manifest",
        "export-usb target",
    ]


def test_export_usb_applies_source_document_exclusions(tmp_path: Path) -> None:
    """Verify USB export does not copy source files excluded from ingestion.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    base = _person(tmp_path, "patient-a", "Patient A")
    person = PersonConfig(
        id=base.id,
        display_name=base.display_name,
        source_documents=base.source_documents,
        metadata_directory=base.metadata_directory,
        local_build=base.local_build,
        usb_uuid=base.usb_uuid,
        ingestion=IngestionConfig(exclude_patterns=("Help/**", "*.tmp")),
    )
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Report.txt").write_text(
        "synthetic",
        encoding="utf-8",
    )
    help_dir = person.source_documents / "Help"
    help_dir.mkdir()
    (help_dir / "manual.txt").write_text("exclude", encoding="utf-8")
    (person.source_documents / "scratch.tmp").write_text("exclude", encoding="utf-8")
    build_patient(person, mode="full")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )

    result = export_usb(config, tmp_path / "usb")
    documents = result.root / "patients" / "patient-a" / "documents"

    assert (documents / "20260102 Report.txt").is_file()
    assert not (documents / "Help" / "manual.txt").exists()
    assert not (documents / "scratch.tmp").exists()
    assert validate_usb(result.root)


def test_export_usb_copies_dicom_html_viewer_and_validates_link(
    tmp_path: Path,
) -> None:
    """Verify USB export links staged DICOM HTML viewers with relative hrefs.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path, "patient-a", "Patient A")
    person.source_documents.mkdir(parents=True)
    archive = person.source_documents / "20260102 TAC.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("DICOMDIR", b"")
        bundle.writestr("IHE_PDI/PAGES/STUDIES/STUDY1.HTM", "<html>viewer</html>")
        bundle.writestr("IHE_PDI/PAGES/IMAGES/IMG1.jpeg", b"jpeg")
    build_patient(person, mode="full")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )

    result = export_usb(config, tmp_path / "usb")
    data_script = (
        result.root / "patients" / "patient-a" / "web" / "data.js"
    ).read_text(encoding="utf-8")
    payload = json.loads(
        data_script.removeprefix("window.SANIKEY_DATA = ").removesuffix(";\n")
    )
    viewer_href = payload["clinical"]["dicom_studies"][0]["viewer_href"]

    assert "../dicom-viewers/" in data_script
    assert "IHE_PDI/PAGES/STUDIES/STUDY1.HTM" in data_script
    assert (result.root / "patients" / "patient-a" / "web" / viewer_href).is_file()
    assert "/home/" not in data_script
    assert "file://" not in data_script
    assert validate_usb(result.root)


def test_export_usb_isolates_enabled_patients(tmp_path: Path) -> None:
    """Verify USB export keeps enabled patient archives independent.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    patient_a = _person(tmp_path, "patient-a", "Patient A")
    patient_b = _person(tmp_path, "patient-b", "Patient B")
    disabled = _person(tmp_path, "patient-disabled", "Patient Disabled")
    disabled = PersonConfig(
        id=disabled.id,
        display_name=disabled.display_name,
        source_documents=disabled.source_documents,
        metadata_directory=disabled.metadata_directory,
        local_build=disabled.local_build,
        usb_uuid=disabled.usb_uuid,
        enabled=False,
    )
    _write_document(patient_a, "20260102 Report A.txt", "alpha")
    _write_document(patient_b, "20260103 Report B.txt", "beta")
    _write_document(disabled, "20260104 Disabled.txt", "disabled")
    build_patient(patient_a, mode="full")
    build_patient(patient_b, mode="full")
    build_patient(disabled, mode="full")
    config = AccountsConfig(
        config_version=1,
        people=(patient_a, patient_b, disabled),
        path=tmp_path / "accounts.toml",
    )

    result = export_usb(config, tmp_path / "usb")
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))

    assert result.patients == 2
    assert {patient["id"] for patient in manifest["patients"]} == {
        "patient-a",
        "patient-b",
    }
    assert (result.root / "patients" / "patient-a" / "documents").is_dir()
    assert (result.root / "patients" / "patient-b" / "documents").is_dir()
    assert not (result.root / "patients" / "patient-disabled").exists()
    assert not (
        result.root / "patients" / "patient-a" / "documents" / "20260103 Report B.txt"
    ).exists()
    assert not (
        result.root / "patients" / "patient-b" / "documents" / "20260102 Report A.txt"
    ).exists()
    assert validate_usb(result.root)


def test_validate_usb_rejects_tampered_checksum(tmp_path: Path) -> None:
    """Verify checksum validation fails after export tampering.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path, "patient-a", "Patient A")
    _write_document(person, "20260102 Report.txt", "synthetic")
    build_patient(person, mode="full")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )
    result = export_usb(config, tmp_path / "usb")

    (
        result.root / "patients" / "patient-a" / "documents" / "20260102 Report.txt"
    ).write_text(
        "tampered",
        encoding="utf-8",
    )

    assert not validate_usb(result.root)


def test_export_usb_keeps_office_hrefs_relative_and_resolvable(
    tmp_path: Path,
) -> None:
    """Verify Office original links point to exported USB files.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path, "patient-a", "Patient A")
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Workbook.xlsx").write_bytes(b"xlsx")
    (person.source_documents / "20260103 Letter.doc").write_bytes(b"doc")
    build_patient(person, mode="full")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )

    result = export_usb(config, tmp_path / "usb")
    data_script = (
        result.root / "patients" / "patient-a" / "web" / "data.js"
    ).read_text(encoding="utf-8")

    assert '"href": "../documents/20260102 Workbook.xlsx"' in data_script
    assert '"href": "../documents/20260103 Letter.doc"' in data_script
    assert (
        result.root / "patients" / "patient-a" / "documents" / "20260102 Workbook.xlsx"
    ).is_file()
    assert (
        result.root / "patients" / "patient-a" / "documents" / "20260103 Letter.doc"
    ).is_file()
    assert "/home/" not in data_script
    assert "file://" not in data_script
    assert validate_usb(result.root)


def test_validate_usb_rejects_absolute_frontend_hrefs(tmp_path: Path) -> None:
    """Verify USB validation fails on host-local frontend links.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path, "patient-a", "Patient A")
    _write_document(person, "20260102 Report.txt", "synthetic")
    build_patient(person, mode="full")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )
    result = export_usb(config, tmp_path / "usb")
    data_script = result.root / "patients" / "patient-a" / "web" / "data.js"
    data_script.write_text(
        data_script.read_text(encoding="utf-8").replace(
            "../documents/20260102 Report.txt",
            "/home/marco/private/20260102 Report.txt",
        ),
        encoding="utf-8",
    )

    assert not validate_usb(result.root)


def test_export_usb_excludes_generated_cache_logs_and_temp(tmp_path: Path) -> None:
    """Verify non-exportable generated artefacts stay off the USB image.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path, "patient-a", "Patient A")
    _write_document(person, "20260102 Report.txt", "synthetic")
    build_patient(person, mode="full")
    for relative in (
        "cache/internal.tmp",
        "logs/build.log",
        "tmp/scratch.tmp",
    ):
        path = person.local_build / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not exportable", encoding="utf-8")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )

    result = export_usb(config, tmp_path / "usb")
    exported_files = {
        path.relative_to(result.root).as_posix()
        for path in result.root.rglob("*")
        if path.is_file()
    }

    assert not any("cache/" in path for path in exported_files)
    assert not any("logs/" in path for path in exported_files)
    assert not any("tmp/" in path for path in exported_files)


def test_export_usb_removes_obsolete_target_files(tmp_path: Path) -> None:
    """Verify mirroring the canonical image removes stale target files.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path, "patient-a", "Patient A")
    _write_document(person, "20260102 Report.txt", "synthetic")
    build_patient(person, mode="full")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )
    target = tmp_path / "usb"
    stale = target / "stale.txt"
    stale.parent.mkdir()
    stale.write_text("remove me", encoding="utf-8")
    target_inode = target.stat().st_ino

    result = export_usb(config, target)

    assert target.stat().st_ino == target_inode
    assert not stale.exists()
    assert validate_usb(result.root)


def test_export_usb_optional_real_filesystem_target(tmp_path: Path) -> None:
    """Verify export against an explicitly configured real target.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    target_value = os.environ.get("SANIKEY_USB_INTEGRATION_TARGET")
    if target_value is None:
        pytest.skip("SANIKEY_USB_INTEGRATION_TARGET is not set")
    target = Path(target_value)
    person = _person(tmp_path, "patient-a", "Patient A")
    _write_document(person, "20260102 Report.txt", "synthetic")
    build_patient(person, mode="full")
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )

    result = export_usb(config, target)

    assert validate_usb(result.root)
