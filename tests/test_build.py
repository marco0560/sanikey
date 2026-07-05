"""Local build pipeline tests."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from typing import TYPE_CHECKING

from sanikey.build import build_all, build_patient
from sanikey.config import AccountsConfig, PersonConfig

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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
    assert result.derived_documents == 0
    assert result.dicom_instances == 0
    assert result.total_records == 1
    assert result.database.is_file()
    assert result.manifest.is_file()
    assert result.report.is_file()
    assert result.checksums.is_file()
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    report = json.loads(result.report.read_text(encoding="utf-8"))
    assert manifest["patient_id"] == "patient-a"
    assert report["documents"] == 1
    assert report["derived_documents"] == 0
    assert report["dicom_instances"] == 0
    assert report["total_records"] == 1
    assert "database/medical_archive.db" in result.checksums.read_text(encoding="utf-8")


def test_build_patient_defaults_to_incremental_mode(tmp_path: Path) -> None:
    """Verify the programmatic build default is incremental.

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

    result = build_patient(person)

    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert manifest["build_mode"] == "incremental"


def test_repeated_incremental_build_preserves_manifest_and_checksums(
    tmp_path: Path,
) -> None:
    """Verify repeated unchanged builds keep stable manifest/checksum content.

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

    first = build_patient(person)
    first_manifest = json.loads(first.manifest.read_text(encoding="utf-8"))
    first_checksums = first.checksums.read_text(encoding="utf-8")
    second = build_patient(person)
    second_manifest = json.loads(second.manifest.read_text(encoding="utf-8"))
    second_checksums = second.checksums.read_text(encoding="utf-8")

    assert second_manifest == first_manifest
    assert second_checksums == first_checksums


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


def test_build_patient_skips_duplicate_content_with_warning(tmp_path: Path) -> None:
    """Verify duplicate-content files do not collide in the database.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    reports = person.source_documents / "reports"
    reports.mkdir(parents=True)
    (reports / "20260102 A.txt").write_text("same", encoding="utf-8")
    (reports / "20260103 B.txt").write_text("same", encoding="utf-8")

    result = build_patient(person, mode="full")
    report = json.loads(result.report.read_text(encoding="utf-8"))

    assert result.documents == 1
    assert result.duplicates == 1
    assert result.warnings == 1
    assert "20260103 B.txt" in result.warning_messages[0]
    assert "20260102 A.txt" in result.warning_messages[0]
    assert report["documents"] == 1
    assert report["duplicates"] == 1
    assert report["warning_messages"] == list(result.warning_messages)


def test_build_patient_reports_image_ocr_provider_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify image OCR provider warnings are reported once.

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
    person.source_documents.mkdir(parents=True)
    (person.source_documents / "20260102 Photo.jpg").write_bytes(b"photo")
    monkeypatch.setattr("sanikey.documents.shutil.which", lambda _: None)

    result = build_patient(person, mode="full")

    assert result.warnings == 1
    assert len(result.warning_messages) == 1
    assert "Tesseract not installed; image OCR skipped" in result.warning_messages[0]


def test_build_patient_stages_container_members_with_provenance(
    tmp_path: Path,
) -> None:
    """Verify container members are staged and recorded as derived documents.

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
    bundle = person.source_documents / "20260102 Bundle.zip"
    dicom_bytes = b"\0" * 128 + b"DICM" + b"synthetic"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("reports/20260103 Inner.txt", "inner text")
        archive.writestr("dicom/image.dcm", dicom_bytes)

    result = build_patient(person, mode="full")

    staging_manifest = person.local_build / "manifests" / "container_staging.json"
    staging_payload = json.loads(staging_manifest.read_text(encoding="utf-8"))
    with sqlite3.connect(result.database) as connection:
        rows = connection.execute(
            """
            SELECT kind, origin, container_id, internal_path
            FROM documents
            ORDER BY internal_path IS NULL, internal_path
            """
        ).fetchall()
        dicom_count = connection.execute(
            "SELECT count(*) FROM dicom_studies"
        ).fetchone()[0]

    assert result.documents == 1
    assert result.derived_documents == 2
    assert result.dicom_instances == 1
    assert result.total_records == 3
    assert result.warnings == 0
    assert len(staging_payload["members"]) == 2
    assert "staging/containers" in result.checksums.read_text(encoding="utf-8")
    assert any(row[0] == "text" and row[1] == "container" for row in rows)
    assert any(row[0] == "dicom_file" and row[1] == "container" for row in rows)
    assert all(row[2] is not None for row in rows if row[1] == "container")
    assert {row[3] for row in rows if row[1] == "container"} == {
        "dicom/image.dcm",
        "reports/20260103 Inner.txt",
    }
    assert dicom_count == 2
    assert not any(
        "manual DICOM expansion directory not found" in warning
        for warning in result.warning_messages
    )
