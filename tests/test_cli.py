"""CLI smoke tests."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from sanikey import __version__, cli
from sanikey.cli import _config_path, build_parser
from sanikey.config import AccountsConfig, PersonConfig, default_accounts_path
from sanikey.documents import ExtractedText
from sanikey.errors import ConfigError
from sanikey.models import DocumentRecord

MODULE = "sanikey"


def _person(tmp_path: Path, patient_id: str = "patient-a") -> PersonConfig:
    """Build a synthetic patient config.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.
    patient_id : str, optional
        Patient identifier.

    Returns
    -------
    PersonConfig
        Patient configuration.
    """

    return PersonConfig(
        id=patient_id,
        display_name=f"Patient {patient_id}",
        source_documents=tmp_path / patient_id / "source",
        metadata_directory=tmp_path / patient_id / "metadata",
        local_build=tmp_path / patient_id / "generated",
        usb_uuid="1A2B-3C4D",
    )


def _accounts(tmp_path: Path, *people: PersonConfig) -> AccountsConfig:
    """Build a synthetic accounts config.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.
    *people : PersonConfig
        Patient configurations.

    Returns
    -------
    AccountsConfig
        Accounts configuration.
    """

    return AccountsConfig(
        path=tmp_path / "accounts.toml",
        config_version=1,
        people=people,
    )


def _document(path: Path, *, patient_id: str = "patient-a") -> DocumentRecord:
    """Build a synthetic document record.

    Parameters
    ----------
    path : pathlib.Path
        Document path.
    patient_id : str, optional
        Owning patient id.

    Returns
    -------
    DocumentRecord
        Document record.
    """

    return DocumentRecord(
        document_id="doc-1",
        patient_id=patient_id,
        path=path,
        title="Report",
        category="laboratorio",
        kind="txt",
        sha256="a" * 64,
        date="2026-01-02",
    )


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


def test_argparse_error_translation_handles_common_messages() -> None:
    """Verify common argparse diagnostics are localized.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    assert (
        cli._translate_argparse_error(
            "invalid choice: 'x' (choose from 'a'); expected one argument"
        )
        == "scelta non valida: 'x' (choose from 'a'); atteso un argomento"
    )


def test_italian_argument_parser_error_exits_in_italian(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify parser errors are emitted in Italian.

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    parser = cli.ItalianArgumentParser(prog="sanikey-test")

    with pytest.raises(SystemExit) as exc_info:
        parser.error("expected one argument")

    assert exc_info.value.code == 2
    assert "errore: atteso un argomento" in capsys.readouterr().err


def test_run_info_direct_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify run_info prints the localized project summary.

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    status = cli.run_info(argparse.Namespace())

    captured = capsys.readouterr()
    assert status == 0
    assert "progetto=sanikey" in captured.out
    assert f"versione={__version__}" in captured.out


def test_cli_config_and_selection_helpers(tmp_path: Path) -> None:
    """Verify shared CLI helper branches.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    patient_a = _person(tmp_path, "patient-a")
    patient_b = _person(tmp_path, "patient-b")
    config = _accounts(tmp_path, patient_a, patient_b)

    assert cli._config_path(argparse.Namespace(config_option=tmp_path / "x.toml")) == (
        tmp_path / "x.toml"
    )
    assert cli._config_path(argparse.Namespace()) == default_accounts_path()
    assert cli._selected_people(config, None) == (patient_a, patient_b)
    assert cli._selected_people(config, "patient-b") == (patient_b,)
    assert (
        cli._progress_from_args(argparse.Namespace(no_progress=True)).enabled is False
    )


def test_run_validate_config_direct_success_and_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify validate-config runner success and localized failure output.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    config = _accounts(tmp_path, _person(tmp_path))
    args = argparse.Namespace(config=tmp_path / "accounts.toml", repo_root=tmp_path)
    monkeypatch.setattr(cli, "load_accounts", lambda _path: config)
    monkeypatch.setattr(cli, "validate_privacy", lambda _config, *, repo_root: None)
    monkeypatch.setattr(cli, "load_curated_metadata", lambda _path: None)

    assert cli.run_validate_config(args) == 0
    captured = capsys.readouterr()
    assert "pazienti=1" in captured.out
    assert "stato=ok" in captured.out

    monkeypatch.setattr(
        cli,
        "load_accounts",
        lambda _path: (_ for _ in ()).throw(ConfigError("non valida")),
    )
    assert cli.run_validate_config(args) == 1
    assert "ERRORE: non valida" in capsys.readouterr().out


def test_run_list_patients_direct_includes_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify list-patients renders enabled and disabled patients.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    enabled = _person(tmp_path, "patient-a")
    disabled = PersonConfig(
        id="patient-b",
        display_name="Patient B",
        source_documents=tmp_path / "patient-b" / "source",
        metadata_directory=tmp_path / "patient-b" / "metadata",
        local_build=tmp_path / "patient-b" / "generated",
        usb_uuid="1A2B-3C4D",
        enabled=False,
    )
    monkeypatch.setattr(
        cli, "load_accounts", lambda _path: _accounts(tmp_path, enabled, disabled)
    )

    assert (
        cli.run_list_patients(
            argparse.Namespace(config=tmp_path / "accounts.toml", all=True)
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "patient-a" in output
    assert "abilitato" in output
    assert "patient-b" in output
    assert "disabilitato" in output


def test_run_scan_documents_direct_writes_output_and_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify scan-documents orchestration without subprocess coverage gaps.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    document = _document(person.source_documents / "20260102 Report.txt")
    output_path = tmp_path / "scan" / "documents.csv"
    config = _accounts(tmp_path, person)
    staging = SimpleNamespace(
        members=(SimpleNamespace(container_id="container-1"),),
        documents=(document,),
    )
    inspection = SimpleNamespace(
        inventory=(document.path,),
        documents=(document,),
        duplicates=(),
        excluded_files=(tmp_path / "skip.tmp",),
        warning_messages=("avviso inventario",),
        preflight_warning_messages=("avviso preflight",),
        container_staging=staging,
    )
    monkeypatch.setattr(cli, "load_accounts", lambda _path: config)
    monkeypatch.setattr(cli, "load_curated_metadata", lambda _path: None)
    monkeypatch.setattr(
        cli, "inspect_patient_documents", lambda *args, **kwargs: inspection
    )

    status = cli.run_scan_documents(
        argparse.Namespace(
            config=tmp_path / "accounts.toml",
            patient=None,
            output=output_path,
            format="csv",
            preflight=True,
            no_stage_containers=False,
            no_progress=True,
            verbose=True,
        )
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "archivi_preparati=1" in output
    assert "AVVISO: avviso inventario" in output
    assert "paziente=patient-a documenti_acquisiti=1" in output
    assert (
        output_path.read_text(encoding="utf-8")
        .splitlines()[0]
        .startswith("paziente,tipo,categoria")
    )


def test_run_scan_documents_direct_rejects_invalid_output_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify scan-documents direct error branches.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    assert cli.run_scan_documents(argparse.Namespace(output=None, format="csv")) == 1
    assert "--format e' valido solo con --output" in capsys.readouterr().out

    monkeypatch.setattr(
        cli, "load_accounts", lambda _path: _accounts(tmp_path, _person(tmp_path))
    )
    monkeypatch.setattr(cli, "load_curated_metadata", lambda _path: None)
    monkeypatch.setattr(
        cli,
        "inspect_patient_documents",
        lambda *args, **kwargs: SimpleNamespace(
            inventory=(),
            documents=(),
            duplicates=(),
            excluded_files=(),
            warning_messages=(),
            preflight_warning_messages=(),
            container_staging=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "_write_scan_output",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("permesso negato")),
    )

    status = cli.run_scan_documents(
        argparse.Namespace(
            config=tmp_path / "accounts.toml",
            patient=None,
            output=tmp_path / "blocked" / "out.txt",
            format="text",
            preflight=False,
            no_stage_containers=True,
            no_progress=True,
            verbose=False,
        )
    )

    assert status == 1
    assert "impossibile scrivere" in capsys.readouterr().out


def test_cli_formatting_helpers_cover_fallbacks(tmp_path: Path) -> None:
    """Verify pure CLI formatting helpers.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    in_source = _document(person.source_documents / "20260102 Report.txt")
    outside = _document(tmp_path / "outside.txt")
    text_path = tmp_path / "scan.txt"

    cli._write_scan_output(text_path, [(person, in_source)], output_format="text")

    assert (
        cli._format_scan_verbose(person, ())
        == "paziente=patient-a documenti_acquisiti=0"
    )
    assert "02/01/2026" in cli._format_scan_verbose(person, (in_source,))
    assert cli._format_display_date(None) == ""
    assert cli._format_display_date("20260102") == "20260102"
    assert cli._source_relative_path(person, in_source) == "20260102 Report.txt"
    assert cli._source_relative_path(person, outside) == str(outside.path)
    assert text_path.read_text(encoding="utf-8").startswith("patient-a\ttxt")


def test_run_document_integrity_direct_handles_write_and_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify document-integrity runner covers success and OSError paths.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    monkeypatch.setattr(cli, "load_accounts", lambda _path: _accounts(tmp_path, person))

    status = cli.run_document_integrity(
        argparse.Namespace(
            config=tmp_path / "accounts.toml",
            patient=None,
            action="before",
            output_dir=tmp_path / "snapshots",
        )
    )

    assert status == 0
    assert "stato=written" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "write_source_snapshot",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disco pieno")),
    )
    status = cli.run_document_integrity(
        argparse.Namespace(
            config=tmp_path / "accounts.toml",
            patient=None,
            action="after",
            output_dir=tmp_path / "snapshots",
        )
    )

    assert status == 1
    assert "disco pieno" in capsys.readouterr().out


def test_run_document_integrity_direct_reports_changed_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify document-integrity check returns non-zero on changed snapshots.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    monkeypatch.setattr(cli, "load_accounts", lambda _path: _accounts(tmp_path, person))
    monkeypatch.setattr(
        cli,
        "check_source_snapshots",
        lambda *args, **kwargs: SimpleNamespace(
            patient_id="patient-a",
            status="changed",
            sha256_path=tmp_path / "after.sha256",
            mtime_path=tmp_path / "after-mtime.tsv",
        ),
    )

    status = cli.run_document_integrity(
        argparse.Namespace(
            config=tmp_path / "accounts.toml",
            patient=None,
            action="check",
            output_dir=tmp_path / "snapshots",
        )
    )

    assert status == 1
    assert "stato=changed" in capsys.readouterr().out


def test_direct_content_runners_cover_success_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify direct CLI content runners without subprocess coverage gaps.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    document = _document(person.source_documents / "20260102 Report.txt")
    config = _accounts(tmp_path, person)
    args = argparse.Namespace(
        config=tmp_path / "accounts.toml",
        patient=None,
        mode="incremental",
        no_progress=True,
    )
    monkeypatch.setattr(cli, "load_accounts", lambda _path: config)
    monkeypatch.setattr(cli, "scan_documents", lambda _person: (document,))
    monkeypatch.setattr(
        cli,
        "extract_text",
        lambda _document: ExtractedText(
            document_id="doc-1",
            text="testo",
            warnings=("avviso testo",),
        ),
    )

    assert cli.run_extract_text(args) == 0
    assert "chars=5\tavvisi=1" in capsys.readouterr().out

    study = SimpleNamespace(
        patient_id="patient-a",
        support_kind="dicom_iso",
        support_path=tmp_path / "study.iso",
        extracted_path=tmp_path / "expanded",
        viewer_paths=(tmp_path / "viewer.exe",),
        warnings=("avviso dicom",),
        study_instance_uid="1.2.3",
        study_date="2026-01-02",
        study_description="Studio",
        instance_count=2,
    )
    monkeypatch.setattr(cli, "catalog_dicom_studies", lambda *_args: (study,))
    assert cli.run_process_dicom(args) == 0
    assert "studi_dicom=1" in capsys.readouterr().out

    monkeypatch.setattr(cli, "load_curated_metadata", lambda _path: object())
    monkeypatch.setattr(
        cli,
        "build_database",
        lambda *_args: SimpleNamespace(
            path=tmp_path / "medical_archive.db",
            documents=1,
            dicom_studies=1,
        ),
    )
    assert cli.run_build_database(args) == 0
    assert "documenti=1 studi_dicom=1" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "generate_manual_proposals",
        lambda _path: (SimpleNamespace(id="p1"),),
    )
    assert cli.run_generate_proposals(args) == 0
    assert "proposte=1" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "generate_exports",
        lambda *_args: SimpleNamespace(data_dir=tmp_path / "data"),
    )
    assert cli.run_generate_exports(args) == 0
    assert f"dati={tmp_path / 'data'}" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "build_frontend",
        lambda _person: SimpleNamespace(web_dir=tmp_path / "web"),
    )
    assert cli.run_build_web(args) == 0
    assert f"web={tmp_path / 'web'}" in capsys.readouterr().out


def test_direct_build_and_usb_runners_cover_success_and_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify direct CLI build and USB runners.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    config = _accounts(tmp_path, person)
    build_result = SimpleNamespace(
        patient_id="patient-a",
        build_root=tmp_path / "generated",
        documents=1,
        derived_documents=2,
        dicom_instances=3,
        total_records=4,
        extracted_documents=5,
        cached_documents=6,
        duplicates=1,
        warnings=2,
        warning_messages=(
            "contenuto documento duplicato saltato. a -> b",
            "PyMuPDF non ha potuto estrarre il testo PDF: report.pdf",
            "avviso nascosto",
        ),
        database=tmp_path / "db.sqlite",
        manifest=tmp_path / "manifest.json",
        checksums=tmp_path / "checksums.sha256",
        report=tmp_path / "report.json",
    )
    usb_result = SimpleNamespace(root=tmp_path / "usb", patients=1, files=2)
    monkeypatch.setattr(cli, "load_accounts", lambda _path: config)
    monkeypatch.setattr(cli, "build_patient", lambda *_args, **_kwargs: build_result)
    monkeypatch.setattr(cli, "build_all", lambda *_args, **_kwargs: (build_result,))
    monkeypatch.setattr(cli, "export_usb", lambda *_args, **_kwargs: usb_result)
    monkeypatch.setattr(cli, "validate_usb", lambda _target: True)

    patient_args = argparse.Namespace(
        config=tmp_path / "accounts.toml",
        patient="patient-a",
        mode="incremental",
        no_progress=True,
    )
    assert cli.run_build_patient(patient_args) == 0
    output = capsys.readouterr().out
    assert "documenti_derivati=2 istanze_dicom=3 record_totali=4" in output
    assert "AVVISO: contenuto documento duplicato" in output
    assert "avviso nascosto" not in output

    all_args = argparse.Namespace(
        config=tmp_path / "accounts.toml",
        mode="incremental",
        no_progress=True,
    )
    assert cli.run_build_all(all_args) == 0
    assert "paziente=patient-a stato=ok" in capsys.readouterr().out

    export_args = argparse.Namespace(
        config=tmp_path / "accounts.toml",
        target=tmp_path / "usb",
        no_progress=True,
    )
    assert cli.run_export_usb(export_args) == 0
    assert "pazienti=1 file=2" in capsys.readouterr().out
    assert cli.run_validate_usb(argparse.Namespace(target=tmp_path / "usb")) == 0
    assert "stato=ok" in capsys.readouterr().out

    assert cli.run_deploy_usb(export_args) == 0
    assert "pazienti=1 file=2" in capsys.readouterr().out

    monkeypatch.setattr(cli, "validate_usb", lambda _target: False)
    assert cli.run_validate_usb(argparse.Namespace(target=tmp_path / "usb")) == 1
    assert "stato=invalido" in capsys.readouterr().out
    assert cli.run_deploy_usb(export_args) == 1
    assert "validazione USB non riuscita" in capsys.readouterr().out


def test_direct_runner_error_branches_and_update_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify direct CLI error branches and update delegation.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    capsys : pytest.CaptureFixture[str]
        Pytest output capture fixture.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    config = _accounts(tmp_path, person)
    monkeypatch.setattr(cli, "load_accounts", lambda _path: config)

    assert (
        cli.run_build_patient(
            argparse.Namespace(
                config=tmp_path / "accounts.toml",
                patient="missing",
                mode="incremental",
                no_progress=True,
            )
        )
        == 1
    )
    assert "paziente non trovato" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "review_proposal",
        lambda *_args: SimpleNamespace(id="proposal-1", status="approved"),
    )
    assert (
        cli.run_review_proposal(
            argparse.Namespace(
                config=tmp_path / "accounts.toml",
                patient="patient-a",
                proposal_id="proposal-1",
                status="approved",
            )
        )
        == 0
    )
    assert "proposta=proposal-1 stato=approved" in capsys.readouterr().out
    assert (
        cli.run_review_proposal(
            argparse.Namespace(
                config=tmp_path / "accounts.toml",
                patient="missing",
                proposal_id="proposal-1",
                status="approved",
            )
        )
        == 1
    )
    assert "paziente non trovato" in capsys.readouterr().out

    calls: list[tuple[str, str | None]] = []

    def fake_build_all(args: argparse.Namespace) -> int:
        """Record build-all delegation.

        Parameters
        ----------
        args : argparse.Namespace
            Parsed command arguments.

        Returns
        -------
        int
            Synthetic exit status.
        """

        calls.append((args.mode, None))
        return 7

    def fake_build_patient(args: argparse.Namespace) -> int:
        """Record build-patient delegation.

        Parameters
        ----------
        args : argparse.Namespace
            Parsed command arguments.

        Returns
        -------
        int
            Synthetic exit status.
        """

        calls.append((args.mode, args.patient))
        return 8

    monkeypatch.setattr(cli, "run_build_all", fake_build_all)
    monkeypatch.setattr(cli, "run_build_patient", fake_build_patient)

    all_args = argparse.Namespace(patient=None)
    patient_args = argparse.Namespace(patient="patient-a")
    assert cli.run_update_archive(all_args) == 7
    assert cli.run_update_archive(patient_args) == 8
    assert calls == [("incremental", None), ("incremental", "patient-a")]


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
