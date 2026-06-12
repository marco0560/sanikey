"""Public example acceptance tests."""

from __future__ import annotations

from pathlib import Path

from sanikey.build import build_patient
from sanikey.config import AccountsConfig, PersonConfig
from sanikey.usb import export_usb, validate_usb


def test_public_examples_build_and_export_demo_usb(tmp_path: Path) -> None:
    """Verify public synthetic examples can produce a demo USB export."""

    repo_root = Path.cwd()
    person = PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=repo_root
        / "docs"
        / "patients-example"
        / "patient-a"
        / "documents",
        metadata_directory=repo_root
        / "docs"
        / "patients-example"
        / "patient-a"
        / "metadata",
        local_build=tmp_path / "generated" / "patient-a",
        usb_uuid="1A2B-3C4D",
    )
    config = AccountsConfig(
        config_version=1, people=(person,), path=tmp_path / "accounts.toml"
    )

    build_patient(person, mode="full")
    export = export_usb(config, tmp_path / "usb")

    assert validate_usb(export.root)
    assert (export.root / "START-HERE-Patient-A.html").is_file()
