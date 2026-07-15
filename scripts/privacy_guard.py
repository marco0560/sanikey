#!/usr/bin/env python3
"""Validate that commit-candidate repository content does not leak private paths."""

from __future__ import annotations

from pathlib import Path

from sanikey.errors import PrivacyError
from sanikey.privacy import validate_tracked_privacy

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Run the tracked-content privacy guard.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Zero when tracked content satisfies privacy invariants, otherwise one.
    """

    try:
        validate_tracked_privacy(repo_root=REPO_ROOT)
    except PrivacyError as exc:
        print(f"ERRORE: {exc}")
        return 1
    print("privacy=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
