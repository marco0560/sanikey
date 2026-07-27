#!/usr/bin/env python3
"""Run conservative, privacy-aware release-readiness checks."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEMVER_TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+$")


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

    Raises
    ------
    subprocess.CalledProcessError
        If the command exits unsuccessfully.
    """
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def run(command: list[str]) -> int:
    """Run one command from the repository and return its status.

    Parameters
    ----------
    command : list[str]
        Command argument vector to execute.

    Returns
    -------
    int
        Child-process exit status.
    """
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


def latest_reachable_tag() -> str:
    """Return the latest reachable semantic-version tag.

    Parameters
    ----------
    None

    Returns
    -------
    str
        Latest ``vX.Y.Z`` tag reachable from ``HEAD``, or an empty string.
    """
    tags = [
        tag
        for tag in output(
            ["git", "tag", "--merged", "HEAD", "--sort=v:refname"]
        ).splitlines()
        if SEMVER_TAG.fullmatch(tag)
    ]
    return tags[-1] if tags else ""


def main() -> int:
    """Run the SaniKey release-readiness audit.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Zero when release prerequisites are satisfied, otherwise one.
    """
    if any(argument in {"-h", "--help"} for argument in sys.argv[1:]):
        print("Usage: python -m scripts.release_audit [-h|--help]")
        return 0
    if os.environ.get("SKIP_RELEASE_AUDIT") == "1":
        return 0

    print("== Audit di rilascio ==")
    print("[1] Controllo privacy dei contenuti candidati al commit...")
    if run([sys.executable, "scripts/privacy_guard.py"]):
        return 1

    print("[2] Controllo working tree pulito...")
    if run(["git", "diff", "--quiet"]) or run(["git", "diff", "--cached", "--quiet"]):
        print("ERRORE: working tree sporco")
        return 1

    print("[3] Controllo allineamento branch...")
    local = output(["git", "rev-parse", "@"])
    try:
        remote = output(["git", "rev-parse", "@{u}"])
    except subprocess.CalledProcessError:
        remote = ""
    if not remote:
        print("OK: nessun upstream configurato")
    else:
        base = output(["git", "merge-base", "@", "@{u}"])
        if local == remote:
            print("OK: branch allineata")
        elif local == base:
            print("ERRORE: branch indietro rispetto al remoto")
            return 1
        elif remote == base:
            print("OK: branch avanti rispetto al remoto")
        else:
            print("ERRORE: branch divergente")
            return 1

    branch = output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch != "main":
        print(f"Audit di rilascio non applicabile alla branch {branch}")
        return 0

    print("[4] Controllo ancestry dell'ultimo tag...")
    latest_tag = latest_reachable_tag()
    if not latest_tag:
        print("AVVISO: nessun tag semantico raggiungibile da HEAD")
    elif run(["bash", "scripts/tag_guard.sh", latest_tag]):
        return 1
    elif run(["git", "merge-base", "--is-ancestor", latest_tag, "HEAD"]):
        print("ERRORE: l'ultimo tag non e' un antenato di HEAD")
        return 1
    else:
        print(f"OK: ultimo tag coerente ({latest_tag})")

    print("[5] Controllo changelog...")
    if run(["bash", "scripts/changelog_guard.sh"]):
        return 1

    commits = output(
        ["git", "rev-list", f"{latest_tag}..HEAD" if latest_tag else "HEAD", "--count"]
    )
    print(f"Commit dalla precedente release raggiungibile: {commits}")
    print("OK: baseline di rilascio valida")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
