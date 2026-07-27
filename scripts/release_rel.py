#!/usr/bin/env python3
"""Run the guarded SaniKey release push path used by ``git rel``."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
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


def clean_build_artifacts() -> None:
    """Remove disposable package build artifacts before local verification.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    for path in (REPO_ROOT / "dist", REPO_ROOT / "build"):
        shutil.rmtree(path, ignore_errors=True)
    for path in REPO_ROOT.glob("*.egg-info"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def main() -> int:
    """Push ``main`` through the guarded SaniKey release workflow.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Zero on successful push and installed-wheel verification, otherwise a
        failing child-process status.
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
    print("[3] Invio branch e tag annotati...")
    status = run(["git", "push", "--follow-tags"], env=environment)
    if status:
        return status

    print("[4] Attesa propagazione CI/tag...")
    time.sleep(30)
    for command in (["git", "fetch", "-q"], ["git", "pull", "--ff-only", "-q"]):
        status = run(command)
        if status:
            return status

    print("[5] Verifica artefatto e versione installata...")
    clean_build_artifacts()
    if run([sys.executable, "-m", "build", "--wheel", "--no-isolation"]):
        return 1
    wheels = sorted(
        (REPO_ROOT / "dist").glob("*.whl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not wheels:
        print("ERRORE: nessuna wheel prodotta in dist/")
        return 1
    if run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "--force-reinstall",
            "--no-deps",
            "--quiet",
            str(wheels[0]),
        ]
    ):
        return 1
    return run([sys.executable, "-m", "sanikey", "-V"])


if __name__ == "__main__":
    raise SystemExit(main())
