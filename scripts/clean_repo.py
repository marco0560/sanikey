#!/usr/bin/env python3
"""Remove ignored build and cache artifacts from the repository."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

GIT_EXE = shutil.which("git")
PROTECTED_PATHS = {".venv", ".vscode", "node_modules"}


def git_ignored_paths() -> Iterable[Path]:
    """Yield ignored paths that currently exist in the working tree."""
    if GIT_EXE is None:
        msg = "git executable not found"
        raise RuntimeError(msg)
    result = subprocess.run(
        [GIT_EXE, "status", "--ignored", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("!! "):
            yield Path(line[3:])


def remove_path(path: Path, dry_run: bool) -> None:
    """Remove a filesystem path or print the planned removal."""
    if dry_run:
        print(f"[DRY-RUN] Would remove: {path}")
        return
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def main() -> int:
    """Clean ignored artifacts from the repository root."""
    parser = argparse.ArgumentParser(description="Clean ignored repository artifacts.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path.cwd()
    ignored = [
        path
        for path in git_ignored_paths()
        if path.parts and path.parts[0] not in PROTECTED_PATHS
    ]
    if not ignored:
        print("Nothing to clean.")
        return 0
    for path in ignored:
        remove_path(repo_root / path, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
