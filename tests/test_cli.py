"""CLI smoke tests."""

from __future__ import annotations

import csv
import subprocess
import sys
import zipfile
from pathlib import Path

from sanikey import __version__
from sanikey.cli import _config_path, build_parser
from sanikey.config import default_accounts_path

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
    assert "progetto=sanikey" in result.stdout


def test_config_path_uses_default_when_omitted() -> None:
    """Verify shared CLI config arguments preserve the default config path.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    parser = build_parser()

    default_args = parser.parse_args(["scan-documents", "--preflight"])
    explicit_args = parser.parse_args(["scan-documents", "custom.toml", "--preflight"])

    assert _config_path(default_args) == default_accounts_path()
    assert _config_path(explicit_args) == Path("custom.toml")


def test_scan_documents_rejects_config_flag_in_italian() -> None:
    """Verify scan-documents rejects non-ambiguous config flags in Italian.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = subprocess.run(
        [sys.executable, "-m", MODULE, "scan-documents", "--config", "custom.toml"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "errore: argomenti non riconosciuti: --config" in result.stderr


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
            str(config_path),
            "--repo-root",
            str(Path.cwd()),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "stato=ok" in result.stdout


def test_validate_config_rejects_invalid_metadata(tmp_path: Path) -> None:
    """Verify validate-config checks curated metadata invariants.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "therapies.toml").write_text(
        """
[[therapy]]
medication_id = "missing"
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
            "validate-config",
            str(config_path),
            "--repo-root",
            str(Path.cwd()),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "medication_id sconosciuto missing" in result.stdout


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
            str(config_path),
            "--no-progress",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "documenti=1" in result.stdout
    assert (
        "archivi_preparati=0 membri_in_archivi=0 documenti_derivati=0" in result.stdout
    )
    assert "Report" not in result.stdout
    assert result.stderr == ""


def test_scan_documents_rejects_invalid_metadata(tmp_path: Path) -> None:
    """Verify scan-documents fails before scanning invalid patient metadata.

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
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "medications.toml").write_text(
        """
[[medication]]
id = "drug-a"
name = "Drug A"
""",
        encoding="utf-8",
    )
    (metadata / "therapies.toml").write_text(
        """
[[therapy]]
id = "duplicate"
medication_id = "drug-a"

[[therapy]]
id = "duplicate"
medication_id = "drug-a"
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
            "scan-documents",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "id therapy duplicato: duplicate" in result.stdout


def test_scan_documents_stages_containers_by_default(tmp_path: Path) -> None:
    """Verify scan-documents materializes container staging for inspection.

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
    with zipfile.ZipFile(source / "20260102 Archive.zip", "w") as archive:
        archive.writestr("report.txt", "synthetic")
    config_path = tmp_path / "accounts.toml"
    build_root = tmp_path / "generated"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{source}"
metadata_directory = "{tmp_path / "metadata"}"
local_build = "{build_root}"
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
            str(config_path),
            "--no-progress",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert (
        "archivi_preparati=1 membri_in_archivi=1 documenti_derivati=1" in result.stdout
    )
    assert (build_root / "staging" / "containers").is_dir()
    assert (build_root / "manifests" / "container_staging.json").is_file()


def test_scan_documents_can_skip_container_staging(tmp_path: Path) -> None:
    """Verify scan-documents can run without materializing staging.

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
    with zipfile.ZipFile(source / "20260102 Archive.zip", "w") as archive:
        archive.writestr("report.txt", "synthetic")
    config_path = tmp_path / "accounts.toml"
    build_root = tmp_path / "generated"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{source}"
metadata_directory = "{tmp_path / "metadata"}"
local_build = "{build_root}"
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
            str(config_path),
            "--no-stage-containers",
            "--no-progress",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "archivi_preparati=" not in result.stdout
    assert not (build_root / "staging" / "containers").exists()


def test_document_integrity_creates_and_checks_patient_snapshots(
    tmp_path: Path,
) -> None:
    """Verify document-integrity uses configured patients for snapshots.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    source_a = tmp_path / "patient-a" / "documents"
    source_b = tmp_path / "patient-b" / "documents"
    source_a.mkdir(parents=True)
    source_b.mkdir(parents=True)
    (source_a / "20260102 A.txt").write_text("a", encoding="utf-8")
    (source_b / "20260102 B.txt").write_text("b", encoding="utf-8")
    snapshots = tmp_path / "snapshots"
    config_path = tmp_path / "accounts.toml"
    config_path.write_text(
        f"""
[global]
config_version = 1

[[person]]
id = "patient-a"
display_name = "Patient A"
source_documents = "{source_a}"
metadata_directory = "{tmp_path / "patient-a" / "metadata"}"
local_build = "{tmp_path / "generated" / "patient-a"}"
usb_uuid = "1A2B-3C4D"

[[person]]
id = "patient-b"
display_name = "Patient B"
source_documents = "{source_b}"
metadata_directory = "{tmp_path / "patient-b" / "metadata"}"
local_build = "{tmp_path / "generated" / "patient-b"}"
usb_uuid = "1A2B-3C4D"
""",
        encoding="utf-8",
    )

    for action in ("before", "after", "check"):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                MODULE,
                "document-integrity",
                action,
                "--config",
                str(config_path),
                "--output-dir",
                str(snapshots),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "paziente=patient-a" in result.stdout
        assert "paziente=patient-b" in result.stdout

    assert (snapshots / "patient-a-before.sha256").is_file()
    assert (snapshots / "patient-a-after-mtime.tsv").is_file()
    assert (snapshots / "patient-b-before.sha256").is_file()
    assert (snapshots / "patient-b-after-mtime.tsv").is_file()


def test_document_integrity_check_fails_when_sources_change(tmp_path: Path) -> None:
    """Verify document-integrity reports modified source documents.

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
    path = source / "20260102 Report.txt"
    path.write_text("before", encoding="utf-8")
    snapshots = tmp_path / "snapshots"
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
    before = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "document-integrity",
            "before",
            "--config",
            str(config_path),
            "--output-dir",
            str(snapshots),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert before.returncode == 0
    path.write_text("after", encoding="utf-8")
    after = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "document-integrity",
            "after",
            "--config",
            str(config_path),
            "--output-dir",
            str(snapshots),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert after.returncode == 0

    check = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "document-integrity",
            "check",
            "--config",
            str(config_path),
            "--output-dir",
            str(snapshots),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert check.returncode == 1
    assert "stato=changed" in check.stdout


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
            str(config_path),
            "--verbose",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "paziente=patient-a documenti_acquisiti=1" in result.stdout
    assert "02/01/2026" in result.stdout
    assert "laboratory/20260102 Report.txt" in result.stdout
    assert not any(line.endswith(" ") for line in result.stdout.splitlines())
    assert (
        "----------------------------------------------------------------"
        not in result.stdout
    )


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
        "paziente",
        "tipo",
        "categoria",
        "data",
        "titolo",
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
            str(config_path),
            "--format",
            "text",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "--format e' valido solo con --output" in result.stdout


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
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    warning_lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("AVVISO:") or line.endswith(".txt")
    ]
    assert result.returncode == 0
    assert warning_lines[0].startswith(
        "AVVISO: contenuto documento duplicato saltato. "
        "I file seguenti sono identici (sha256="
    )
    assert warning_lines[1].endswith("20260102 A.txt")
    assert warning_lines[2].endswith("20260103 B.txt")


def test_scan_documents_reports_static_problem_warnings(tmp_path: Path) -> None:
    """Verify scan-documents reports fast pre-build diagnostics.

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
    (source / "20260102 Photo.jpg").write_bytes(b"photo")
    with zipfile.ZipFile(source / "20260103 Study.zip", "w") as archive:
        archive.writestr("DICOMDIR", "synthetic")
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
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "documenti=2 duplicati=0 avvisi=0" in result.stdout
    assert (
        "archivi_preparati=1 membri_in_archivi=1 documenti_derivati=0" in result.stdout
    )
    assert "estrazione testo non supportata per .jpg" not in result.stdout
    assert "directory di espansione DICOM manuale non trovata" not in result.stdout


def test_scan_documents_preflight_reports_corrupt_office_file(
    tmp_path: Path,
) -> None:
    """Verify scan-documents preflight reports lightweight extraction warnings.

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
    (source / "20260102 Broken.docx").write_bytes(b"not a docx")
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
            str(config_path),
            "--preflight",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "documenti=1 duplicati=0 avvisi=1" in result.stdout
    assert "estrazione testo DOCX non riuscita" in result.stdout


def test_scan_documents_preflight_skips_legacy_office_conversion(
    tmp_path: Path,
) -> None:
    """Verify scan preflight does not convert legacy Office files.

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
    (source / "20260102 Legacy.doc").write_bytes(b"legacy")
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
            str(config_path),
            "--preflight",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "documenti=1 duplicati=0 avvisi=0" in result.stdout
    assert "LibreOffice" not in result.stdout


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
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "studi_dicom=1" in result.stdout
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
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "documenti=1" in result.stdout
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
            "--no-progress",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "paziente=patient-a stato=ok" in result.stdout
    assert "documenti=1 duplicati=0 avvisi=0" in result.stdout
    assert "documenti_derivati=0 istanze_dicom=0 record_totali=1" in result.stdout
    assert '"paziente": "patient-a"' not in result.stdout
    assert result.stderr == ""
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
    assert "documenti=1 duplicati=1" in result.stdout
    assert "contenuto documento duplicato saltato" in result.stdout
    assert "20260103 B.txt" in result.stdout
    assert "20260102 A.txt" in result.stdout
    assert "Avvisi=vedi report" in result.stdout


def test_build_patient_subcommand_prints_pymupdf_warning_path(
    tmp_path: Path,
) -> None:
    """Verify build output includes file paths for PyMuPDF warnings.

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
    pdf_path = source / "20260102 Malformed Report.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\nnot a valid page tree\n")
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

    combined_output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "MuPDF error" not in combined_output
    assert (
        f"AVVISO: {pdf_path}: PyMuPDF non ha potuto estrarre il testo PDF"
        in result.stdout
    )


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
    assert "ERRORE:" in result.stdout
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
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "proposte=1" in result.stdout
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
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "paziente=patient-a" in result.stdout
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
    assert (target / "index.html").is_file()
    assert (tmp_path / "exports" / "usb-image" / "index.html").is_file()


def test_export_usb_subcommand_accepts_no_progress(tmp_path: Path) -> None:
    """Verify export-usb supports disabling interactive progress.

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
    build_result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "build-patient",
            "patient-a",
            "--config",
            str(config_path),
            "--no-progress",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    target = tmp_path / "usb"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "export-usb",
            "--config",
            str(config_path),
            "--no-progress",
            str(target),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert build_result.returncode == 0
    assert result.returncode == 0
    assert "usb=" in result.stdout
    assert result.stderr == ""
    assert (target / "index.html").is_file()


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
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "patient-a" in result.stdout
