"""CLI helpers for sanikey."""

from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
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
    return parser


def run_info(_args: argparse.Namespace) -> int:
    """Print a minimal project information summary."""
    print("project=sanikey")
    print("package=sanikey")
    print("cli=sanikey")
    return 0
