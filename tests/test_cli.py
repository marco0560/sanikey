"""CLI smoke tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MODULE = "sanikey"


def test_module_help_runs() -> None:
    """Verify the module help exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", MODULE, "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "sanikey" in result.stdout


def test_info_subcommand_runs() -> None:
    """Verify the example info subcommand exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", MODULE, "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "project=sanikey" in result.stdout


def test_validate_config_subcommand_runs(tmp_path: Path) -> None:
    """Verify validate-config accepts synthetic local data paths."""

    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{tmp_path / "source"}"
metadata_directory = "{tmp_path / "metadata"}"
local_build = "{tmp_path / "generated"}"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "validate-config",
            "--config",
            str(config_path),
            "--repo-root",
            str(Path.cwd()),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "status=ok" in result.stdout


def test_list_patients_subcommand_runs(tmp_path: Path) -> None:
    """Verify list-patients renders configured patient ids."""

    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{tmp_path / "source"}"
metadata_directory = "{tmp_path / "metadata"}"
local_build = "{tmp_path / "generated"}"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "list-patients",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "patient-a" in result.stdout


def test_scan_documents_subcommand_runs(tmp_path: Path) -> None:
    """Verify scan-documents renders an inventory from configured paths."""

    source = tmp_path / "source" / "laboratory"
    source.mkdir(parents=True)
    (source / "20260102 Report.txt").write_text("synthetic", encoding="utf-8")
    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{tmp_path / "source"}"
metadata_directory = "{tmp_path / "metadata"}"
local_build = "{tmp_path / "generated"}"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "scan-documents",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "documents=1" in result.stdout
    assert "Report" in result.stdout


def test_process_dicom_subcommand_runs(tmp_path: Path) -> None:
    """Verify process-dicom catalogs original DICOM supports."""

    source = tmp_path / "source"
    source.mkdir(parents=True)
    (source / "20260102 Study.iso").write_bytes(b"iso")
    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{source}"
metadata_directory = "{tmp_path / "metadata"}"
local_build = "{tmp_path / "generated"}"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "process-dicom",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "dicom_studies=1" in result.stdout
    assert "dicom_iso" in result.stdout


def test_build_database_subcommand_runs(tmp_path: Path) -> None:
    """Verify build-database creates a per-patient SQLite archive."""

    source = tmp_path / "source"
    source.mkdir(parents=True)
    (source / "20260102 Report.txt").write_text("synthetic", encoding="utf-8")
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{source}"
metadata_directory = "{metadata}"
local_build = "{tmp_path / "generated"}"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "build-database",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "documents=1" in result.stdout
    assert (tmp_path / "generated" / "database" / "medical_archive.db").is_file()


def test_build_patient_subcommand_runs(tmp_path: Path) -> None:
    """Verify build-patient runs the local build pipeline."""

    source = tmp_path / "source"
    source.mkdir(parents=True)
    (source / "20260102 Report.txt").write_text("synthetic", encoding="utf-8")
    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{source}"
metadata_directory = "{tmp_path / "metadata"}"
local_build = "{tmp_path / "generated"}"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "build-patient",
            "patient-a",
            "--config",
            str(config_path),
            "--mode",
            "full",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert '"patient_id": "patient-a"' in result.stdout
    assert (tmp_path / "generated" / "manifests" / "manifest.json").is_file()


def test_generate_proposals_subcommand_runs(tmp_path: Path) -> None:
    """Verify generate-proposals writes proposal storage."""

    metadata = tmp_path / "metadata"
    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{tmp_path / "source"}"
metadata_directory = "{metadata}"
local_build = "{tmp_path / "generated"}"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "generate-proposals",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "proposals=1" in result.stdout
    assert (metadata / "proposed" / "proposals.toml").is_file()


def test_generate_exports_subcommand_runs(tmp_path: Path) -> None:
    """Verify generate-exports writes frontend JSON data."""

    source = tmp_path / "source"
    source.mkdir(parents=True)
    (source / "20260102 Report.txt").write_text("synthetic", encoding="utf-8")
    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{source}"
metadata_directory = "{tmp_path / "metadata"}"
local_build = "{tmp_path / "generated"}"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "generate-exports",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "patient=patient-a" in result.stdout
    assert (tmp_path / "generated" / "web" / "data" / "summary.json").is_file()
