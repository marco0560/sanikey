"""Local build pipeline tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sanikey.build import build_patient
from sanikey.config import PersonConfig

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
