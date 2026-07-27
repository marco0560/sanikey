#!/usr/bin/env python3
"""Check the local SaniKey version and release-tooling wiring."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEMVER_TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+$")
GIT_EXE = shutil.which("git") or "git"


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
    """Verify deterministic local release controls.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Zero when all checked release controls are coherent, otherwise one.
    """
    print("== Autoverifica sistema di rilascio ==")
    failed = False

    print("[1] Controllo hooks path...")
    if output(["git", "config", "core.hooksPath"]) != ".githooks":
        print("ERRORE: hooksPath non e' .githooks")
        failed = True

    print("[2] Controllo strumenti obbligatori...")
    for path in (
        Path("scripts/release_audit.py"),
        Path("scripts/release_rel.py"),
        Path("scripts/release_system_selfcheck.py"),
        Path("scripts/privacy_guard.py"),
        Path("scripts/tag_guard.sh"),
        Path("scripts/changelog_guard.sh"),
        Path(".githooks/pre-push"),
    ):
        if not (REPO_ROOT / path).is_file():
            print(f"ERRORE: file mancante {path}")
            failed = True

    print("[3] Controllo alias di rilascio...")
    for alias in ("release-audit", "release-check", "rel"):
        if subprocess.run(
            [GIT_EXE, "config", f"alias.{alias}"], cwd=REPO_ROOT, check=False
        ).returncode:
            print(f"ERRORE: alias.{alias} mancante")
            failed = True

    print("[4] Controllo versione derivata dai tag...")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if (
        'dynamic = ["version"]' not in pyproject
        or "[tool.setuptools_scm]" not in pyproject
    ):
        print("ERRORE: setuptools-scm non configura una versione dinamica")
        failed = True

    print("[5] Controllo hook pre-push...")
    pre_push = (REPO_ROOT / ".githooks" / "pre-push").read_text(encoding="utf-8")
    for marker in ("ALLOW_MAIN_PUSH", "git rel", "privacy_guard.py"):
        if marker not in pre_push:
            print(f"ERRORE: controllo pre-push mancante: {marker}")
            failed = True

    print("[6] Controllo integrita' dei tag...")
    tags = [
        tag
        for tag in output(["git", "tag", "--sort=v:refname"]).splitlines()
        if SEMVER_TAG.fullmatch(tag)
    ]
    if (
        tags
        and subprocess.run(
            [GIT_EXE, "merge-base", "--is-ancestor", tags[0], "HEAD"],
            cwd=REPO_ROOT,
            check=False,
        ).returncode
    ):
        print("ERRORE: storia riscritta dopo la prima release")
        failed = True

    if failed:
        print("ERRORE: sistema di rilascio incoerente")
        return 1
    print("OK: sistema di rilascio coerente")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
