"""USB export tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sanikey.build import build_patient
from sanikey.config import AccountsConfig, PersonConfig
from sanikey.usb import export_usb, validate_usb

if TYPE_CHECKING:
    from pathlib import Path


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
