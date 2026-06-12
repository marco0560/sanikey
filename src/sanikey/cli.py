"""CLI helpers for sanikey."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .config import default_accounts_path, load_accounts
from .errors import SaniKeyError
from .privacy import validate_privacy


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
