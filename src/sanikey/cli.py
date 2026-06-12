"""CLI helpers for sanikey."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__
from .config import default_accounts_path, load_accounts
from .dicom import catalog_dicom_studies
from .documents import extract_text, find_duplicate_documents, scan_documents
from .errors import SaniKeyError
from .privacy import validate_privacy

if TYPE_CHECKING:
    from .config import AccountsConfig, PersonConfig


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
    """Scan configured source documents and print inventory rows.

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
        duplicates = find_duplicate_documents(documents)
        print(
            f"patient={person.id} documents={len(documents)} duplicates={len(duplicates)}"
        )
        for document in documents:
            print(
                "\t".join(
                    (
                        document.patient_id,
                        document.kind,
                        document.category,
                        document.date or "",
                        document.title,
                        document.sha256,
                        str(document.path),
                    )
                )
            )
    return 0


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
