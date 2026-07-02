"""CLI smoke tests."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from sanikey import __version__

MODULE = "sanikey"


def test_module_help_runs() -> None:
    """Verify the module help exits successfully.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    result = subprocess.run(
        [sys.executable, "-m", MODULE, "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "sanikey" in result.stdout


def test_short_version_flag_runs() -> None:
    """Verify the short version flag exits successfully.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    result = subprocess.run(
        [sys.executable, "-m", MODULE, "-V"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"sanikey {__version__}"


def test_info_subcommand_runs() -> None:
    """Verify the example info subcommand exits successfully.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    result = subprocess.run(
        [sys.executable, "-m", MODULE, "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "project=sanikey" in result.stdout


def test_validate_config_subcommand_runs(tmp_path: Path) -> None:
    """Verify validate-config accepts synthetic local data paths.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
    """Verify list-patients renders configured patient ids.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
    """Verify scan-documents renders only a summary by default.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
    assert "Report" not in result.stdout


def test_scan_documents_verbose_renders_readable_inventory(tmp_path: Path) -> None:
    """Verify verbose scan-documents renders a readable inventory table.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
            "--verbose",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "patient=patient-a ingested_documents=1" in result.stdout
    assert "02/01/2026" in result.stdout
    assert "laboratory/20260102 Report.txt" in result.stdout


def test_scan_documents_writes_text_output(tmp_path: Path) -> None:
    """Verify scan-documents writes legacy text output on request.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    source = tmp_path / "source" / "laboratory"
    source.mkdir(parents=True)
    document_path = source / "20260102 Report.txt"
    document_path.write_text("synthetic", encoding="utf-8")
    config_path = tmp_path / "accounts.toml"
    output_path = tmp_path / "scan.txt"
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
            "--output",
            str(output_path),
            "--format",
            "text",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    fields = output_path.read_text(encoding="utf-8").strip().split("\t")
    assert result.returncode == 0
    assert "Report" not in result.stdout
    assert fields[:5] == ["patient-a", "text", "laboratory", "2026-01-02", "Report"]
    assert fields[6] == str(document_path)


def test_scan_documents_writes_csv_output(tmp_path: Path) -> None:
    """Verify scan-documents writes CSV output on request.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    source = tmp_path / "source" / "laboratory"
    source.mkdir(parents=True)
    document_path = source / "20260102 Report.txt"
    document_path.write_text("synthetic", encoding="utf-8")
    config_path = tmp_path / "accounts.toml"
    output_path = tmp_path / "scan.csv"
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
            "--output",
            str(output_path),
            "--format",
            "csv",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    rows = list(csv.reader(output_path.read_text(encoding="utf-8").splitlines()))
    assert result.returncode == 0
    assert rows[0] == [
        "patient_id",
        "kind",
        "category",
        "date",
        "title",
        "sha256",
        "path",
    ]
    assert rows[1][:5] == ["patient-a", "text", "laboratory", "2026-01-02", "Report"]
    assert rows[1][6] == str(document_path)


def test_scan_documents_rejects_format_without_output(tmp_path: Path) -> None:
    """Verify --format is accepted only with --output.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
            "--format",
            "text",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "--format is valid only with --output" in result.stdout


def test_scan_documents_duplicate_warning_uses_three_lines(tmp_path: Path) -> None:
    """Verify duplicate warnings are readable in scan-documents output.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    source = tmp_path / "source"
    source.mkdir()
    (source / "20260102 A.txt").write_text("same", encoding="utf-8")
    (source / "20260103 B.txt").write_text("same", encoding="utf-8")
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
            "scan-documents",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    warning_lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("WARNING:") or line.endswith(".txt")
    ]
    assert result.returncode == 0
    assert warning_lines[0].startswith(
        "WARNING: duplicate document content skipped. "
        "The following files are identical (sha256="
    )
    assert warning_lines[1].endswith("20260102 A.txt")
    assert warning_lines[2].endswith("20260103 B.txt")


def test_process_dicom_subcommand_runs(tmp_path: Path) -> None:
    """Verify process-dicom catalogs original DICOM supports.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
    """Verify build-database creates a per-patient SQLite archive.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
    """Verify build-patient runs the local build pipeline.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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


def test_build_patient_subcommand_emits_duplicate_warning(tmp_path: Path) -> None:
    """Verify duplicate-content files are reported in build output.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    source = tmp_path / "source"
    source.mkdir(parents=True)
    (source / "20260102 A.txt").write_text("same", encoding="utf-8")
    (source / "20260103 B.txt").write_text("same", encoding="utf-8")
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
    assert '"documents": 1' in result.stdout
    assert '"duplicates": 1' in result.stdout
    assert "duplicate document content skipped" in result.stdout
    assert "20260103 B.txt" in result.stdout
    assert "20260102 A.txt" in result.stdout


def test_build_patient_subcommand_hides_unexpected_tracebacks(tmp_path: Path) -> None:
    """Verify runtime failures are reported without stack dumps.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    source = tmp_path / "source"
    source.mkdir(parents=True)
    (source / "20260102 Report.txt").write_text("synthetic", encoding="utf-8")
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "therapies.toml").write_text(
        """
[[therapy]]
id = "therapy-a"
medication_id = "missing-drug"
""",
        encoding="utf-8",
    )
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

    assert result.returncode == 1
    assert "ERROR:" in result.stdout
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_generate_proposals_subcommand_runs(tmp_path: Path) -> None:
    """Verify generate-proposals writes proposal storage.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
    """Verify generate-exports writes frontend JSON data.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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


def test_build_web_subcommand_runs(tmp_path: Path) -> None:
    """Verify build-web writes static frontend files.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
            "build-web",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "web=" in result.stdout
    assert (tmp_path / "generated" / "web" / "index.html").is_file()


def test_deploy_usb_subcommand_runs(tmp_path: Path) -> None:
    """Verify deploy-usb builds and exports a simulated USB layout.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    source = tmp_path / "source"
    source.mkdir()
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
    target = tmp_path / "usb"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "deploy-usb",
            "--config",
            str(config_path),
            str(target),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "usb=" in result.stdout
    assert (target / "START-HERE-Patient-A.html").is_file()
    assert (tmp_path / "exports" / "usb-image" / "START-HERE-Patient-A.html").is_file()


def test_list_patients_wrapper_script_runs(tmp_path: Path) -> None:
    """Verify compatibility scripts delegate to the package CLI.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
            "scripts/list_patients.py",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "patient-a" in result.stdout
