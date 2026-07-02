#!/usr/bin/env python3
"""Delegate compatibility scripts to the package CLI."""

from __future__ import annotations

import sys

from sanikey.__main__ import main

SCRIPT_COMMANDS = {
    "scan_documents.py": "scan-documents",
    "extract_text.py": "extract-text",
    "process_dicom.py": "process-dicom",
    "build_database.py": "build-database",
    "generate_embeddings.py": "generate-exports",
    "generate_timeline.py": "generate-exports",
    "generate_clinical_summary.py": "generate-proposals",
    "build_web.py": "build-web",
    "export_usb.py": "export-usb",
    "validate_usb.py": "validate-usb",
    "deploy_usb.py": "deploy-usb",
    "build_patient.py": "build-patient",
    "build_all.py": "build-all",
    "list_patients.py": "list-patients",
    "update_archive.py": "update-archive",
}


def main_for_script(script_name: str, argv: list[str]) -> int:
    """Run the CLI command mapped to a compatibility script.

    Parameters
    ----------
    script_name : str
        Script filename.
    argv : list[str]
        Script arguments.

    Returns
    -------
    int
        CLI exit status.
    """

    command = SCRIPT_COMMANDS[script_name]
    sys.argv = [script_name, command, *argv]
    return main()
