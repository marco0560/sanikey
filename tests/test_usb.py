"""USB export tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sanikey.build import build_patient
from sanikey.config import AccountsConfig, PersonConfig
from sanikey.usb import export_usb, validate_usb

if TYPE_CHECKING:
    from pathlib import Path


def test_export_usb_writes_chapter_three_layout(tmp_path: Path) -> None:
    """Verify simulated USB export layout and validation."""

    person = PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=tmp_path / "documents",
        metadata_directory=tmp_path / "metadata",
        local_build=tmp_path / "generated",
        usb_uuid="1A2B-3C4D",
    )
    person.source_documents.mkdir()
    (person.source_documents / "20260102 Report.txt").write_text(
        "synthetic",
        encoding="utf-8",
    )
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
