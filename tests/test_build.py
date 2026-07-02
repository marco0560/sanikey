"""Local build pipeline tests."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from sanikey.build import build_all, build_patient
from sanikey.config import AccountsConfig, PersonConfig

if TYPE_CHECKING:
    from pathlib import Path


def _person(tmp_path: Path) -> PersonConfig:
    """Build a synthetic patient config.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    PersonConfig
        Patient configuration.
    """

    return PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=tmp_path / "documents",
        metadata_directory=tmp_path / "metadata",
        local_build=tmp_path / "generated",
        usb_uuid="1A2B-3C4D",
    )


def test_build_patient_writes_manifest_report_checksums(tmp_path: Path) -> None:
    """Verify a patient build produces verifiable artefacts.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Report.txt").write_text(
        "synthetic",
        encoding="utf-8",
    )

    result = build_patient(person, mode="full")

    assert result.documents == 1
    assert result.database.is_file()
    assert result.manifest.is_file()
    assert result.report.is_file()
    assert result.checksums.is_file()
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert manifest["patient_id"] == "patient-a"
    assert "database/medical_archive.db" in result.checksums.read_text(encoding="utf-8")


def test_build_all_skips_disabled_patients_and_isolates_outputs(
    tmp_path: Path,
) -> None:
    """Verify multi-patient builds write only enabled patient artefacts.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    patient_a = _person(tmp_path / "patient-a")
    patient_b = PersonConfig(
        id="patient-b",
        display_name="Patient B",
        source_documents=tmp_path / "patient-b" / "documents",
        metadata_directory=tmp_path / "patient-b" / "metadata",
        local_build=tmp_path / "patient-b" / "generated",
        usb_uuid="1A2B-3C4D",
    )
    disabled = PersonConfig(
        id="patient-disabled",
        display_name="Patient Disabled",
        source_documents=tmp_path / "disabled" / "documents",
        metadata_directory=tmp_path / "disabled" / "metadata",
        local_build=tmp_path / "disabled" / "generated",
        usb_uuid="1A2B-3C4D",
        enabled=False,
    )
    patient_a.source_documents.mkdir(parents=True)
    patient_b.source_documents.mkdir(parents=True)
    disabled.source_documents.mkdir(parents=True)
    (patient_a.source_documents / "20260102 Report A.txt").write_text(
        "alpha",
        encoding="utf-8",
    )
    (patient_b.source_documents / "20260103 Report B.txt").write_text(
        "beta",
        encoding="utf-8",
    )
    (disabled.source_documents / "20260104 Disabled.txt").write_text(
        "disabled",
        encoding="utf-8",
    )
    config = AccountsConfig(
        config_version=1,
        people=(patient_a, patient_b, disabled),
        path=tmp_path / "accounts.toml",
    )

    results = build_all(config, mode="full")

    assert [result.patient_id for result in results] == ["patient-a", "patient-b"]
    assert (patient_a.local_build / "database" / "medical_archive.db").is_file()
    assert (patient_b.local_build / "database" / "medical_archive.db").is_file()
    assert (patient_a.local_build / "web" / "index.html").is_file()
    assert (patient_b.local_build / "web" / "index.html").is_file()
    assert not disabled.local_build.exists()


def test_build_patient_preserves_original_document_bytes_and_mtime(
    tmp_path: Path,
) -> None:
    """Verify build does not mutate authoritative source documents.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    source = person.source_documents / "20260102 Report.txt"
    source.write_text("synthetic", encoding="utf-8")
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    original_mtime_ns = source.stat().st_mtime_ns

    build_patient(person, mode="full")

    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    assert source.stat().st_mtime_ns == original_mtime_ns
