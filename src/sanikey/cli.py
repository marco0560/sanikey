"""CLI helpers for sanikey."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__
from .build import PatientBuildResult, build_all, build_patient
from .config import default_accounts_path, load_accounts
from .database import build_database
from .dicom import catalog_dicom_studies
from .documents import (
    extract_text,
    scan_documents,
)
from .errors import SaniKeyError
from .exports import generate_exports
from .frontend import build_frontend
from .inspection import inspect_patient_documents
from .metadata import load_curated_metadata
from .privacy import validate_privacy
from .proposals import generate_manual_proposals, review_proposal
from .usb import export_usb, validate_usb

if TYPE_CHECKING:
    from .config import AccountsConfig, PersonConfig
    from .models import DocumentRecord


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser.

    Parameters
    ----------
    None

    Returns
    -------
    argparse.ArgumentParser
        Configured parser for the SaniKey command line.
    """

    parser = argparse.ArgumentParser(
        prog="sanikey",
        description="Medical documents on a USB key",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    info_parser = subparsers.add_parser("info", help="Show project information")
    info_parser.set_defaults(func=run_info)

    validate_parser = subparsers.add_parser(
        "validate-config",
        help="Validate local accounts configuration and privacy invariants",
    )
    _add_config_arguments(validate_parser)
    validate_parser.set_defaults(func=run_validate_config)

    list_parser = subparsers.add_parser(
        "list-patients",
        help="List configured patients",
    )
    _add_config_arguments(list_parser)
    list_parser.add_argument(
        "--all",
        action="store_true",
        help="Include disabled patients",
    )
    list_parser.set_defaults(func=run_list_patients)

    scan_parser = subparsers.add_parser(
        "scan-documents",
        help="Scan configured source documents",
    )
    _add_config_arguments(scan_parser)
    scan_parser.add_argument("--patient", help="Only scan one patient id")
    scan_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print a human-readable ingested document list",
    )
    scan_parser.add_argument(
        "--output",
        type=Path,
        help="Write the ingested document list to a file",
    )
    scan_parser.add_argument(
        "--format",
        choices=("text", "csv"),
        default=None,
        help="Output file format, valid only with --output",
    )
    scan_parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run lightweight pre-build checks for archives and office documents",
    )
    scan_parser.set_defaults(func=run_scan_documents)

    extract_parser = subparsers.add_parser(
        "extract-text",
        help="Extract supported text from configured source documents",
    )
    _add_config_arguments(extract_parser)
    extract_parser.add_argument("--patient", help="Only process one patient id")
    extract_parser.set_defaults(func=run_extract_text)

    dicom_parser = subparsers.add_parser(
        "process-dicom",
        help="Catalog DICOM supports and manual expansion directories",
    )
    _add_config_arguments(dicom_parser)
    dicom_parser.add_argument("--patient", help="Only process one patient id")
    dicom_parser.set_defaults(func=run_process_dicom)

    database_parser = subparsers.add_parser(
        "build-database",
        help="Build per-patient SQLite archive databases",
    )
    _add_config_arguments(database_parser)
    database_parser.add_argument("--patient", help="Only build one patient id")
    database_parser.set_defaults(func=run_build_database)

    build_patient_parser = subparsers.add_parser(
        "build-patient",
        help="Run the local build pipeline for one patient",
    )
    _add_config_arguments(build_patient_parser)
    build_patient_parser.add_argument("patient")
    build_patient_parser.add_argument(
        "--mode", choices=("full", "incremental", "validation"), default="incremental"
    )
    build_patient_parser.set_defaults(func=run_build_patient)

    build_all_parser = subparsers.add_parser(
        "build-all",
        help="Run the local build pipeline for all enabled patients",
    )
    _add_config_arguments(build_all_parser)
    build_all_parser.add_argument(
        "--mode", choices=("full", "incremental", "validation"), default="incremental"
    )
    build_all_parser.set_defaults(func=run_build_all)

    update_parser = subparsers.add_parser(
        "update-archive",
        help="Run the default incremental archive update",
    )
    _add_config_arguments(update_parser)
    update_parser.add_argument("--patient", help="Only update one patient id")
    update_parser.set_defaults(func=run_update_archive)

    proposals_parser = subparsers.add_parser(
        "generate-proposals",
        help="Generate deterministic manual-review proposals",
    )
    _add_config_arguments(proposals_parser)
    proposals_parser.add_argument("--patient", help="Only process one patient id")
    proposals_parser.set_defaults(func=run_generate_proposals)

    review_parser = subparsers.add_parser(
        "review-proposal",
        help="Approve or reject a stored proposal",
    )
    _add_config_arguments(review_parser)
    review_parser.add_argument("patient")
    review_parser.add_argument("proposal_id")
    review_parser.add_argument("status", choices=("approved", "rejected"))
    review_parser.set_defaults(func=run_review_proposal)

    exports_parser = subparsers.add_parser(
        "generate-exports",
        help="Generate static JSON frontend/search/timeline exports",
    )
    _add_config_arguments(exports_parser)
    exports_parser.add_argument("--patient", help="Only process one patient id")
    exports_parser.set_defaults(func=run_generate_exports)

    web_parser = subparsers.add_parser(
        "build-web",
        help="Generate static frontend files",
    )
    _add_config_arguments(web_parser)
    web_parser.add_argument("--patient", help="Only process one patient id")
    web_parser.set_defaults(func=run_build_web)

    export_parser = subparsers.add_parser(
        "export-usb",
        help="Export generated artefacts to a USB layout directory",
    )
    _add_config_arguments(export_parser)
    export_parser.add_argument("target", type=Path)
    export_parser.set_defaults(func=run_export_usb)

    validate_usb_parser = subparsers.add_parser(
        "validate-usb",
        help="Validate a generated USB layout directory",
    )
    validate_usb_parser.add_argument("target", type=Path)
    validate_usb_parser.set_defaults(func=run_validate_usb)

    deploy_parser = subparsers.add_parser(
        "deploy-usb",
        help="Build all enabled patients and export them to a USB layout directory",
    )
    _add_config_arguments(deploy_parser)
    deploy_parser.add_argument("target", type=Path)
    deploy_parser.set_defaults(func=run_deploy_usb)
    return parser


def run_info(_args: argparse.Namespace) -> int:
    """Print a minimal project information summary.

    Parameters
    ----------
    _args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    print("project=sanikey")
    print("package=sanikey")
    print("cli=sanikey")
    return 0


def run_validate_config(args: argparse.Namespace) -> int:
    """Validate accounts configuration and privacy constraints.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
        validate_privacy(config, repo_root=args.repo_root)
        for person in config.enabled_people():
            load_curated_metadata(person.metadata_directory)
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    enabled = len(config.enabled_people())
    total = len(config.people)
    print(f"config={config.path}")
    print(f"patients={total}")
    print(f"enabled={enabled}")
    print("status=ok")
    return 0


def run_list_patients(args: argparse.Namespace) -> int:
    """List configured patient identifiers.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    selected = config.people if args.all else config.enabled_people()
    for person in selected:
        state = "enabled" if person.enabled else "disabled"
        print(f"{person.id}\t{state}\t{person.display_name}")
    return 0


def run_scan_documents(args: argparse.Namespace) -> int:
    """Scan configured source documents and optionally print inventory rows.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    if args.output is None and args.format is not None:
        print("ERROR: --format is valid only with --output")
        return 1
    try:
        config = load_accounts(args.config)
        selected_people = _selected_people(config, args.patient)
        for person in selected_people:
            load_curated_metadata(person.metadata_directory)
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    output_rows: list[tuple[PersonConfig, DocumentRecord]] = []
    for person in selected_people:
        inspection = inspect_patient_documents(person, preflight=args.preflight)
        warning_messages = (
            *inspection.warning_messages,
            *inspection.preflight_warning_messages,
        )
        print(
            f"patient={person.id} files={len(inspection.inventory)} "
            f"documents={len(inspection.documents)} "
            f"duplicates={len(inspection.duplicates)} warnings={len(warning_messages)}"
        )
        for warning in warning_messages:
            print(f"WARNING: {warning}")
        if args.verbose:
            print(_format_scan_verbose(person, inspection.documents))
        output_rows.extend((person, document) for document in inspection.documents)
    if args.output is not None:
        try:
            _write_scan_output(
                args.output,
                output_rows,
                output_format=args.format or "text",
            )
        except OSError as exc:
            print(f"ERROR: cannot write scan output: {exc}")
            return 1
    return 0


def _format_scan_verbose(
    person: PersonConfig,
    documents: tuple[DocumentRecord, ...],
) -> str:
    """Render a readable scan inventory table for stdout.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    documents : tuple[DocumentRecord, ...]
        Deduplicated document records.

    Returns
    -------
    str
        Human-readable table.
    """

    if not documents:
        return f"patient={person.id} ingested_documents=0"
    rows = [
        (
            "patient",
            "kind",
            "date",
            "category",
            "sha256",
            "file",
        ),
        *(
            (
                document.patient_id,
                document.kind,
                _format_display_date(document.date),
                document.category,
                document.sha256[:12],
                _source_relative_path(person, document),
            )
            for document in documents
        ),
    ]
    widths = tuple(
        max(len(row[index]) for row in rows) for index in range(len(rows[0]))
    )
    rendered = [f"patient={person.id} ingested_documents={len(documents)}"]
    for row_index, row in enumerate(rows):
        rendered.append(_format_table_row(row, widths))
        if row_index == 0:
            rendered.append(_format_scan_separator(row, widths))
    return "\n".join(rendered)


def _format_table_row(row: tuple[str, ...], widths: tuple[int, ...]) -> str:
    """Render one table row without padding the final column.

    Parameters
    ----------
    row : tuple[str, ...]
        Table row values.
    widths : tuple[int, ...]
        Column widths.

    Returns
    -------
    str
        Rendered row.
    """

    padded = [value.ljust(widths[index]) for index, value in enumerate(row[:-1])]
    return "  ".join((*padded, row[-1])).rstrip()


def _format_scan_separator(row: tuple[str, ...], widths: tuple[int, ...]) -> str:
    """Render the scan table separator.

    Parameters
    ----------
    row : tuple[str, ...]
        Header row.
    widths : tuple[int, ...]
        Column widths.

    Returns
    -------
    str
        Separator row.
    """

    separator = tuple(
        "-" * (4 if index == len(row) - 1 else min(widths[index], 20))
        for index in range(len(row))
    )
    return _format_table_row(separator, widths)


def _write_scan_output(
    output_path: Path,
    rows: list[tuple[PersonConfig, DocumentRecord]],
    *,
    output_format: str,
) -> None:
    """Write scan inventory rows to a user-selected file.

    Parameters
    ----------
    output_path : pathlib.Path
        Destination file path.
    rows : list[tuple[PersonConfig, DocumentRecord]]
        Patient and document rows.
    output_format : str
        Output format, either ``text`` or ``csv``.

    Returns
    -------
    None
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "csv":
        _write_scan_csv(output_path, rows)
        return
    _write_scan_text(output_path, rows)


def _write_scan_csv(
    output_path: Path,
    rows: list[tuple[PersonConfig, DocumentRecord]],
) -> None:
    """Write scan inventory rows as CSV.

    Parameters
    ----------
    output_path : pathlib.Path
        Destination file path.
    rows : list[tuple[PersonConfig, DocumentRecord]]
        Patient and document rows.

    Returns
    -------
    None
    """

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ("patient_id", "kind", "category", "date", "title", "sha256", "path")
        )
        for _person, document in rows:
            writer.writerow(_scan_legacy_row(document))


def _write_scan_text(
    output_path: Path,
    rows: list[tuple[PersonConfig, DocumentRecord]],
) -> None:
    """Write scan inventory rows in legacy tab-separated text format.

    Parameters
    ----------
    output_path : pathlib.Path
        Destination file path.
    rows : list[tuple[PersonConfig, DocumentRecord]]
        Patient and document rows.

    Returns
    -------
    None
    """

    lines = ["\t".join(_scan_legacy_row(document)) for _person, document in rows]
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _scan_legacy_row(document: DocumentRecord) -> tuple[str, ...]:
    """Return the legacy scan inventory row.

    Parameters
    ----------
    document : DocumentRecord
        Document record.

    Returns
    -------
    tuple[str, ...]
        Legacy row fields.
    """

    return (
        document.patient_id,
        document.kind,
        document.category,
        document.date or "",
        document.title,
        document.sha256,
        str(document.path),
    )


def _format_display_date(value: str | None) -> str:
    """Format an ISO date for display.

    Parameters
    ----------
    value : str | None
        ISO date or missing value.

    Returns
    -------
    str
        Italian display date or empty string.
    """

    if value is None:
        return ""
    match = value.split("-")
    if len(match) == 3 and all(part.isdigit() for part in match):
        return f"{match[2]}/{match[1]}/{match[0]}"
    return value


def _source_relative_path(person: PersonConfig, document: DocumentRecord) -> str:
    """Return a document path relative to the source root when possible.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    document : DocumentRecord
        Document record.

    Returns
    -------
    str
        Relative path or absolute path fallback.
    """

    try:
        return document.path.relative_to(person.source_documents).as_posix()
    except ValueError:
        return str(document.path)


def run_extract_text(args: argparse.Namespace) -> int:
    """Extract text from configured source documents.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    for person in _selected_people(config, args.patient):
        for document in scan_documents(person):
            extracted = extract_text(document)
            print(
                f"{person.id}\t{document.sha256}\tchars={len(extracted.text)}"
                f"\twarnings={len(extracted.warnings)}"
            )
            for warning in extracted.warnings:
                print(f"WARNING: {document.path}: {warning}")
    return 0


def run_process_dicom(args: argparse.Namespace) -> int:
    """Catalog DICOM supports for configured patients.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    for person in _selected_people(config, args.patient):
        studies = catalog_dicom_studies(person, scan_documents(person))
        print(f"patient={person.id} dicom_studies={len(studies)}")
        for study in studies:
            extracted = (
                "" if study.extracted_path is None else str(study.extracted_path)
            )
            print(
                "\t".join(
                    (
                        study.patient_id,
                        study.support_kind,
                        str(study.support_path),
                        extracted,
                        str(len(study.viewer_paths)),
                        str(len(study.warnings)),
                    )
                )
            )
            for warning in study.warnings:
                print(f"WARNING: {study.support_path}: {warning}")
    return 0


def run_build_database(args: argparse.Namespace) -> int:
    """Build SQLite databases for configured patients.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    for person in _selected_people(config, args.patient):
        documents = scan_documents(person)
        metadata = load_curated_metadata(person.metadata_directory)
        dicom_studies = catalog_dicom_studies(person, documents)
        result = build_database(person, documents, metadata, dicom_studies)
        print(
            f"patient={person.id} database={result.path} "
            f"documents={result.documents} dicom_studies={result.dicom_studies}"
        )
    return 0


def run_build_patient(args: argparse.Namespace) -> int:
    """Run the local build pipeline for one patient.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
        selected = _selected_people(config, args.patient)
        if not selected:
            print(f"ERROR: patient not found or disabled: {args.patient}")
            return 1
        _print_build_result(build_patient(selected[0], mode=args.mode))
    except (SaniKeyError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


def run_build_all(args: argparse.Namespace) -> int:
    """Run the local build pipeline for all enabled patients.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
        for result in build_all(config, mode=args.mode):
            _print_build_result(result)
    except (SaniKeyError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


def run_update_archive(args: argparse.Namespace) -> int:
    """Run the default incremental archive update.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    if args.patient is None:
        args.mode = "incremental"
        return run_build_all(args)
    args.mode = "incremental"
    args.patient = str(args.patient)
    return run_build_patient(args)


def run_generate_proposals(args: argparse.Namespace) -> int:
    """Generate deterministic manual-review proposals.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
        for person in _selected_people(config, args.patient):
            proposals = generate_manual_proposals(person.metadata_directory)
            print(f"patient={person.id} proposals={len(proposals)}")
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


def run_review_proposal(args: argparse.Namespace) -> int:
    """Approve or reject one stored proposal.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
        selected = _selected_people(config, args.patient)
        if not selected:
            print(f"ERROR: patient not found or disabled: {args.patient}")
            return 1
        updated = review_proposal(
            selected[0].metadata_directory,
            args.proposal_id,
            args.status,
        )
        print(f"proposal={updated.id} status={updated.status}")
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


def run_generate_exports(args: argparse.Namespace) -> int:
    """Generate static JSON exports.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
        for person in _selected_people(config, args.patient):
            metadata = load_curated_metadata(person.metadata_directory)
            result = generate_exports(person, scan_documents(person), metadata)
            print(f"patient={person.id} data={result.data_dir}")
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


def run_build_web(args: argparse.Namespace) -> int:
    """Generate static frontend files.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
        for person in _selected_people(config, args.patient):
            result = build_frontend(person)
            print(f"patient={person.id} web={result.web_dir}")
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


def run_export_usb(args: argparse.Namespace) -> int:
    """Export generated artefacts to a USB layout.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
        result = export_usb(config, args.target)
        print(f"usb={result.root} patients={result.patients} files={result.files}")
    except SaniKeyError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


def run_validate_usb(args: argparse.Namespace) -> int:
    """Validate a generated USB layout.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    if validate_usb(args.target):
        print("status=ok")
        return 0
    print("status=invalid")
    return 1


def run_deploy_usb(args: argparse.Namespace) -> int:
    """Build all enabled patients and export them to a USB layout.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    int
        Process exit status.
    """

    try:
        config = load_accounts(args.config)
        for result in build_all(config, mode="incremental"):
            _print_build_result(result)
        export = export_usb(config, args.target)
        print(f"usb={export.root} patients={export.patients} files={export.files}")
        if not validate_usb(args.target):
            print("ERROR: USB validation failed")
            return 1
    except (SaniKeyError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


def _print_build_result(result: PatientBuildResult) -> None:
    """Print a human-readable patient build result.

    Parameters
    ----------
    result : PatientBuildResult
        Build result.

    Returns
    -------
    None
    """

    print(f"patient={result.patient_id} status=ok")
    print(
        f"documents={result.documents} duplicates={result.duplicates} "
        f"warnings={result.warnings}"
    )
    print(f"build_root={result.build_root}")
    print(f"database={result.database}")
    print(f"manifest={result.manifest}")
    print(f"checksums={result.checksums}")
    print(f"report={result.report}")
    for warning in result.warning_messages:
        if _should_print_build_warning(warning):
            print(f"WARNING: {warning}")
    if result.warnings:
        print("warning_messages=see report")


def _should_print_build_warning(warning: str) -> bool:
    """Return whether a build warning should be visible on stdout.

    Parameters
    ----------
    warning : str
        Warning message.

    Returns
    -------
    bool
        ``True`` for warnings that need immediate operator attention.
    """

    return warning.startswith("duplicate document content skipped.") or (
        "PyMuPDF could not extract PDF text" in warning
    )


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared configuration arguments to a subparser.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser to mutate.

    Returns
    -------
    None
    """

    parser.add_argument(
        "--config",
        type=Path,
        default=default_accounts_path(),
        help="Path to config/accounts.toml",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root used for privacy checks",
    )


def _selected_people(
    config: AccountsConfig,
    patient_id: str | None,
) -> tuple[PersonConfig, ...]:
    """Return enabled people, optionally filtered by id.

    Parameters
    ----------
    config : AccountsConfig
        Accounts configuration object.
    patient_id : str | None
        Optional patient id.

    Returns
    -------
    tuple[PersonConfig, ...]
        Selected patient configs.
    """

    people = config.enabled_people()
    if patient_id is None:
        return people
    return tuple(person for person in people if person.id == patient_id)
