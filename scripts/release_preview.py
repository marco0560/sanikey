#!/usr/bin/env python3
"""Preview the guarded Semantic Release operation with scoped credentials."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GITHUB_ENV = Path.home() / "credentials/personal-secrets/secrets/github.env"
SEMANTIC_RELEASE_COMMAND = "npx semantic-release --dry-run --config .releaserc.json"


def build_preview_command() -> list[str]:
    """Build the SOPS-scoped Semantic Release preview command.

    Parameters
    ----------
    None

    Returns
    -------
    list[str]
        Command vector that gives GitHub credentials only to Semantic Release.
    """
    return ["sops", "exec-env", str(GITHUB_ENV), SEMANTIC_RELEASE_COMMAND]


def main() -> int:
    """Run the non-publishing Semantic Release preview.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Semantic Release child-process exit status.
    """
    print("Esecuzione anteprima Semantic Release controllata...")
    return subprocess.run(
        build_preview_command(), cwd=REPO_ROOT, check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
