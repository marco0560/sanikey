#!/usr/bin/env python3
"""Install deterministic repo-local Git configuration."""

from __future__ import annotations

import shutil
import subprocess

GIT_EXE = shutil.which("git")


def git_alias_entries() -> list[tuple[str, str]]:
    """Return repo-local Git config entries to install."""
    return [
        ("core.hooksPath", ".githooks"),
        ("commit.template", ".gitmessage"),
        ("pull.ff", "only"),
        ("pull.rebase", "false"),
        ("rebase.autostash", "true"),
        ("alias.check", "!uv run python scripts/validate_repo.py"),
        (
            "alias.fix",
            "!uv run python scripts/run_repo_tool.py ruff check . --fix && uv run python scripts/run_repo_tool.py ruff format .",
        ),
        ("alias.clean-repo", "!uv run python scripts/clean_repo.py"),
        ("alias.new-decision", "!uv run python scripts/new_decision.py"),
        ("alias.gen-cheatsheet", "!uv run python scripts/generate_cheatsheet.py"),
        ("alias.docs-build", "!uv run mkdocs build --strict"),
        ("alias.docs-serve", "!uv run mkdocs serve"),
        ("alias.release-audit", "!bash scripts/release_audit.sh"),
        ("alias.safe-push", "!git fetch && git pull --ff-only && git push"),
        (
            "alias.release",
            "!bash scripts/release_audit.sh && git push --follow-tags",
        ),
    ]


def main() -> int:
    """Apply the repo-local Git configuration entries."""
    if GIT_EXE is None:
        msg = "git executable not found"
        raise RuntimeError(msg)
    for key, value in git_alias_entries():
        subprocess.run([GIT_EXE, "config", "--local", key, value], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
