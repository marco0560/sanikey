#!/usr/bin/env python3
"""Run the guarded SaniKey release push path used by ``git rel``."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, env: dict[str, str] | None = None) -> int:
    """Run one command from the repository and return its status.

    Parameters
    ----------
    command : list[str]
        Command argument vector to execute.
    env : dict[str, str] | None, optional
        Optional child-process environment overrides.

    Returns
    -------
    int
        Child-process exit status.
    """
    return subprocess.run(command, cwd=REPO_ROOT, check=False, env=env).returncode


def output(command: list[str]) -> str:
    """Run one command from the repository and return its standard output.

    Parameters
    ----------
    command : list[str]
        Command argument vector to execute.

    Returns
    -------
    str
        Decoded standard output with no surrounding whitespace.
    """
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    """Push ``main`` through the guarded SaniKey release workflow.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Zero on successful guarded push, otherwise a failing child-process
        status.
    """
    if any(argument in {"-h", "--help"} for argument in sys.argv[1:]):
        print("Usage: python -m scripts.release_rel [-h|--help]")
        return 0
    if output(["git", "rev-parse", "--abbrev-ref", "HEAD"]) != "main":
        print("ERRORE: git rel puo' essere eseguito soltanto su main")
        return 1

    print("== Percorso di rilascio SaniKey ==")
    for label, command in (
        ("[1] Aggiornamento dal remoto...", ["git", "fetch"]),
        ("[1] Aggiornamento dal remoto...", ["git", "pull", "--ff-only"]),
        (
            "[2] Audit di rilascio...",
            [sys.executable, "-m", "scripts.release_audit"],
        ),
    ):
        print(label)
        status = run(command)
        if status:
            return status

    environment = dict(os.environ)
    environment["SKIP_RELEASE_AUDIT"] = "1"
    environment["ALLOW_MAIN_PUSH"] = "1"
    print("[3] Invio branch a GitHub...")
    status = run(["git", "push"], env=environment)
    if status:
        return status

    print("[4] Attendere il workflow Release di GitHub.")
    print("[5] Al termine: git pull --ff-only && uv sync && uv run sanikey -V")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
