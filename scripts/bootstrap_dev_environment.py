#!/usr/bin/env python3
"""Bootstrap the repository-local development environment.

This maintenance script prepares a fresh clone for local development by
synchronizing the uv-managed environment, applying repository-local Git
configuration, and optionally running the standard validation surface.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REQUIRED_REPO_MARKERS = (
    ".git",
    ".githooks",
    ".gitmessage",
    "pyproject.toml",
)


@dataclass(frozen=True)
class CommandSpec:
    """Represent a bootstrap subprocess invocation."""

    description: str
    argv: tuple[str, ...]
    cwd: Path


@dataclass(frozen=True)
class BootstrapOptions:
    """Hold bootstrap execution options."""

    with_docs: bool
    run_validation: bool


def fail(msg: str, *, exit_code: int = 1) -> None:
    """Print an error message and terminate the program."""

    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(exit_code)


def resolve_executable(name: str) -> str:
    """Resolve an executable to an absolute path."""

    resolved = shutil.which(name)
    if resolved is None:
        fail(f"Required executable not found in PATH: {name}")
    return resolved


def detect_repo_root(repo_root: Path | None = None) -> Path:
    """Resolve and validate the repository root directory."""

    candidate = (
        repo_root.resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[1]
    )
    missing = [
        marker for marker in REQUIRED_REPO_MARKERS if not (candidate / marker).exists()
    ]
    if missing:
        fail(
            "Repository root validation failed. Missing expected entries: "
            + ", ".join(missing)
        )
    return candidate


def uv_sync_command(*, with_docs: bool) -> tuple[str, ...]:
    """Build the uv sync command for the repository environment."""

    command = ["uv", "sync", "--extra", "dev"]
    if with_docs:
        command.extend(["--extra", "docs"])
    return tuple(command)


def build_bootstrap_commands(
    *, repo_root: Path, options: BootstrapOptions
) -> list[CommandSpec]:
    """Build the ordered bootstrap command plan."""

    commands = [
        CommandSpec(
            "Synchronize uv-managed development environment",
            uv_sync_command(with_docs=options.with_docs),
            repo_root,
        ),
        CommandSpec(
            "Verify installed package requirements",
            ("uv", "pip", "check"),
            repo_root,
        ),
        CommandSpec(
            "Install repo-local Git configuration",
            ("uv", "run", "python", "scripts/install_repo_git_config.py"),
            repo_root,
        ),
    ]
    if options.run_validation:
        commands.append(
            CommandSpec(
                "Run repository validation",
                ("uv", "run", "python", "scripts/validate_repo.py"),
                repo_root,
            )
        )
    return commands


def render_command(command: CommandSpec) -> str:
    """Render a command plan entry for user-readable output."""

    return " ".join(shlex.quote(arg) for arg in command.argv)


def run_plan(commands: list[CommandSpec], *, dry_run: bool) -> None:
    """Execute or print the bootstrap plan."""

    for command in commands:
        print(f"==> {command.description}")
        print(f"    {render_command(command)}")
        if dry_run:
            continue
        try:
            subprocess.run(command.argv, cwd=command.cwd, check=True)
        except subprocess.CalledProcessError as exc:
            fail(
                f"Bootstrap step failed with exit code {exc.returncode}: "
                f"{render_command(command)}"
            )


def main(argv: list[str] | None = None) -> int:
    """Bootstrap the local repository development environment."""

    parser = argparse.ArgumentParser(
        description="Install dependencies and configure local Git state.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root to bootstrap (default: infer from script location)",
    )
    parser.add_argument(
        "--with-docs",
        action="store_true",
        help="Install documentation dependencies in addition to dev dependencies",
    )
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    resolve_executable("uv")
    repo_root = detect_repo_root(args.repo_root)
    commands = build_bootstrap_commands(
        repo_root=repo_root,
        options=BootstrapOptions(
            with_docs=args.with_docs,
            run_validation=not args.skip_validation,
        ),
    )
    run_plan(commands, dry_run=args.dry_run)

    print("\nBootstrap completed successfully.")
    if args.skip_validation:
        print("Validation was skipped by request.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
