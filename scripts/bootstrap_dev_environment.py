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
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from collections.abc import Callable

REQUIRED_REPO_MARKERS = (
    ".git",
    ".githooks",
    ".gitmessage",
    "pyproject.toml",
)
BOOTSTRAP_CONFIG_PATH = ("tool", "sanikey", "bootstrap")


@dataclass(frozen=True)
class CommandSpec:
    """Represent a bootstrap subprocess invocation.

    Parameters
    ----------
    description : str
        User-facing description printed before execution.
    argv : tuple[str, ...]
        Command argument vector.
    cwd : pathlib.Path
        Working directory for the command.
    """

    description: str
    argv: tuple[str, ...]
    cwd: Path


@dataclass(frozen=True)
class BootstrapOptions:
    """Hold bootstrap execution options.

    Parameters
    ----------
    with_docs : bool
        Whether documentation dependencies should be installed.
    run_validation : bool
        Whether the validation command should run after bootstrap.
    """

    with_docs: bool
    run_validation: bool


def load_system_dependencies(repo_root: Path) -> dict[str, tuple[str, ...]]:
    """Load declared system dependencies from ``pyproject.toml``.

    Parameters
    ----------
    repo_root : pathlib.Path
        Validated repository root containing ``pyproject.toml``.

    Returns
    -------
    dict[str, tuple[str, ...]]
        Package-manager names mapped to their required package names.

    Raises
    ------
    SystemExit
        If the bootstrap system-dependency configuration is malformed.
    """

    with (repo_root / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    configuration: object = data
    for key in BOOTSTRAP_CONFIG_PATH:
        if not isinstance(configuration, dict):
            fail("configurazione bootstrap non valida in pyproject.toml")
        configuration = configuration.get(key)
    if not isinstance(configuration, dict):
        fail("configurazione bootstrap mancante in pyproject.toml")
    dependencies = configuration.get("system-dependencies")
    if not isinstance(dependencies, dict):
        fail("dipendenze di sistema bootstrap mancanti in pyproject.toml")

    result: dict[str, tuple[str, ...]] = {}
    for manager, packages in dependencies.items():
        if (
            not isinstance(manager, str)
            or not isinstance(packages, list)
            or not packages
            or not all(isinstance(package, str) and package for package in packages)
        ):
            fail("dipendenze di sistema bootstrap non valide in pyproject.toml")
        result[manager] = tuple(packages)
    return result


def system_dependency_commands(
    *,
    repo_root: Path,
    executable_lookup: Callable[[str], str | None] | None = None,
) -> list[CommandSpec]:
    """Build commands that install missing host tools declared by the project.

    Parameters
    ----------
    repo_root : pathlib.Path
        Validated repository root.
    executable_lookup : collections.abc.Callable[[str], str | None], optional
        Executable resolver, injectable for tests.

    Returns
    -------
    list[CommandSpec]
        Empty when all declared host tools are already available.

    Raises
    ------
    SystemExit
        If tools are missing and no declared package manager is available.
    """

    resolver = shutil.which if executable_lookup is None else executable_lookup
    dependencies = load_system_dependencies(repo_root)
    for manager, packages in dependencies.items():
        missing = [package for package in packages if resolver(package) is None]
        if not missing:
            continue
        if resolver(manager) is None:
            continue
        if resolver("sudo") is None:
            fail("sudo non trovato: impossibile installare " + ", ".join(missing))
        return [
            CommandSpec(
                "Installa prerequisiti di sistema mancanti",
                ("sudo", manager, "install", "--assumeyes", *missing),
                repo_root,
            )
        ]

    missing_tools = sorted(
        {
            package
            for packages in dependencies.values()
            for package in packages
            if resolver(package) is None
        }
    )
    if missing_tools:
        fail(
            "Prerequisiti di sistema mancanti: "
            + ", ".join(missing_tools)
            + ". Nessun gestore pacchetti dichiarato e disponibile puo' installarli."
        )
    return []


def fail(msg: str, *, exit_code: int = 1) -> NoReturn:
    """Print an error message and terminate the program.

    Parameters
    ----------
    msg : str
        Error message to print.
    exit_code : int, optional
        Process status used for termination.

    Returns
    -------
    typing.NoReturn
        This function never returns.

    Raises
    ------
    SystemExit
        Always raised with ``exit_code``.
    """

    print(f"ERRORE: {msg}", file=sys.stderr)
    raise SystemExit(exit_code)


def detect_repo_root(repo_root: Path | None = None) -> Path:
    """Resolve and validate the repository root directory.

    Parameters
    ----------
    repo_root : pathlib.Path | None, optional
        Explicit repository root. When omitted, infer it from this script.

    Returns
    -------
    pathlib.Path
        Validated repository root.
    """

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
            "Validazione radice repository non riuscita. Voci attese mancanti: "
            + ", ".join(missing)
        )
    return candidate


def uv_sync_command(*, with_docs: bool) -> tuple[str, ...]:
    """Build the uv sync command for the repository environment.

    Parameters
    ----------
    with_docs : bool
        Whether documentation dependencies should be included.

    Returns
    -------
    tuple[str, ...]
        Command argument vector.
    """

    command = ["uv", "sync", "--group", "dev"]
    if with_docs:
        command.extend(["--extra", "docs"])
    return tuple(command)


def build_bootstrap_commands(
    *, repo_root: Path, options: BootstrapOptions
) -> list[CommandSpec]:
    """Build the ordered bootstrap command plan.

    Parameters
    ----------
    repo_root : pathlib.Path
        Repository root used as command working directory.
    options : BootstrapOptions
        Bootstrap execution options.

    Returns
    -------
    list[CommandSpec]
        Ordered command plan.
    """

    commands = [
        *system_dependency_commands(repo_root=repo_root),
        CommandSpec(
            "Assicura l'interprete Python 3.13 gestito da uv",
            ("uv", "python", "install", "3.13"),
            repo_root,
        ),
        CommandSpec(
            "Sincronizza ambiente di sviluppo gestito da uv",
            uv_sync_command(with_docs=options.with_docs),
            repo_root,
        ),
        CommandSpec(
            "Verifica requisiti pacchetti installati",
            ("uv", "pip", "check"),
            repo_root,
        ),
        CommandSpec(
            "Installa configurazione Git locale al repository",
            ("uv", "run", "python", "scripts/install_repo_git_config.py"),
            repo_root,
        ),
    ]
    if options.run_validation:
        commands.append(
            CommandSpec(
                "Esegue validazione repository",
                ("uv", "run", "python", "scripts/validate_repo.py"),
                repo_root,
            )
        )
    return commands


def render_command(command: CommandSpec) -> str:
    """Render a command plan entry for user-readable output.

    Parameters
    ----------
    command : CommandSpec
        Command to render.

    Returns
    -------
    str
        Shell-quoted command line.
    """

    return " ".join(shlex.quote(arg) for arg in command.argv)


def run_plan(commands: list[CommandSpec], *, dry_run: bool) -> None:
    """Execute or print the bootstrap plan.

    Parameters
    ----------
    commands : list[CommandSpec]
        Ordered command plan.
    dry_run : bool
        Whether commands should be printed without execution.

    Returns
    -------
    None
    """

    for command in commands:
        print(f"==> {command.description}")
        print(f"    {render_command(command)}")
        if dry_run:
            continue
        try:
            subprocess.run(command.argv, cwd=command.cwd, check=True)
        except subprocess.CalledProcessError as exc:
            fail(
                f"Passaggio bootstrap non riuscito con codice {exc.returncode}: "
                f"{render_command(command)}"
            )


def main(argv: list[str] | None = None) -> int:
    """Bootstrap the local repository development environment.

    Parameters
    ----------
    argv : list[str] | None, optional
        Command-line arguments. When omitted, use ``sys.argv``.

    Returns
    -------
    int
        Process exit status.
    """

    parser = argparse.ArgumentParser(
        description="Installa dipendenze e configura lo stato Git locale.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Radice repository da inizializzare (default: inferita dallo script)",
    )
    parser.add_argument(
        "--with-docs",
        action="store_true",
        help="Installa dipendenze documentazione oltre a quelle dev",
    )
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = detect_repo_root(args.repo_root)
    commands = build_bootstrap_commands(
        repo_root=repo_root,
        options=BootstrapOptions(
            with_docs=args.with_docs,
            run_validation=not args.skip_validation,
        ),
    )
    run_plan(commands, dry_run=args.dry_run)

    print("\nBootstrap completato correttamente.")
    if args.skip_validation:
        print("Validazione saltata su richiesta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
