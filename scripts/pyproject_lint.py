#!/usr/bin/env python3
"""
Deterministic structural lint for pyproject.toml.

Hard-fail validator for:
- PEP 621 metadata consistency
- setuptools compatibility (PEP 639 license rules)
- dependency format sanity
- tool configuration presence

No heuristics. No silent fixes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:  # pragma: no cover
    print("ERRORE: Python 3.11+ richiesto (tomllib mancante)", file=sys.stderr)
    raise SystemExit(2) from None


class LintError(Exception):
    """Hard failure in pyproject structure."""


def fail(msg: str) -> None:
    """Raise a hard-failure lint error after reporting it.

    Parameters
    ----------
    msg : str
        Error message describing the structural lint failure.

    Returns
    -------
    None

    Raises
    ------
    LintError
        Always raised after the message is emitted.
    """

    print(f"[ERR ] {msg}", file=sys.stderr)
    raise LintError(msg)


def ok(msg: str) -> None:
    """Emit a success message for a completed lint check.

    Parameters
    ----------
    msg : str
        Success message describing the completed check.

    Returns
    -------
    None
    """

    print(f"[OK  ] {msg}")


def check_project_table(data: dict[str, Any]) -> None:
    """Validate the required PEP 621 project metadata table.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed ``pyproject.toml`` content.

    Returns
    -------
    None

    Raises
    ------
    LintError
        Raised when the project table or required fields are missing.
    """

    project = data.get("project")
    if not isinstance(project, dict):
        fail("Tabella [project] mancante")

    required = ["name", "requires-python"]
    for field in required:
        if field not in project:
            fail(f"[project] campo obbligatorio mancante: {field}")

    ok("[project] campi obbligatori presenti")


def check_license_rules(data: dict[str, Any]) -> None:
    """Validate mutually exclusive license metadata rules.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed ``pyproject.toml`` content.

    Returns
    -------
    None

    Raises
    ------
    LintError
        Raised when license metadata violates the enforced policy.
    """

    project = data["project"]

    license_field = project.get("license")
    classifiers = project.get("classifiers", [])

    if license_field and any(item.startswith("License ::") for item in classifiers):
        fail(
            "License classifiers are forbidden when 'license' is set "
            "(PEP 639). Remove License :: classifiers."
        )

    ok("license configuration valid")


def check_dependencies(data: dict[str, Any]) -> None:
    """Validate the main dependency list structure and uniqueness.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed ``pyproject.toml`` content.

    Returns
    -------
    None

    Raises
    ------
    LintError
        Raised when dependency entries are malformed or duplicated.
    """

    project = data["project"]
    deps = project.get("dependencies", [])
    if not isinstance(deps, list):
        fail("[project.dependencies] deve essere una lista")

    seen: set[str] = set()
    for dep in deps:
        if not isinstance(dep, str):
            fail(f"Voce dipendenza non valida (non stringa): {dep}")

        name = dep.split(">=")[0].split("==")[0]
        if name in seen:
            fail(f"Dipendenza duplicata: {name}")
        seen.add(name)

    ok("dipendenze valide")


def check_optional_dependencies(data: dict[str, Any]) -> None:
    """Validate optional dependency groups and entry types.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed ``pyproject.toml`` content.

    Returns
    -------
    None

    Raises
    ------
    LintError
        Raised when optional dependency groups are malformed.
    """

    project = data["project"]
    optional = project.get("optional-dependencies", {})

    if not isinstance(optional, dict):
        fail("[project.optional-dependencies] deve essere una tabella")

    for group, deps in optional.items():
        if not isinstance(deps, list):
            fail(f"Gruppo opzionale '{group}' deve essere una lista")

        for dep in deps:
            if not isinstance(dep, str):
                fail(f"Dipendenza non valida in [{group}]: {dep}")

    ok("dipendenze opzionali valide")


def check_build_system(data: dict[str, Any]) -> None:
    """Validate the build-system table and required keys.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed ``pyproject.toml`` content.

    Returns
    -------
    None

    Raises
    ------
    LintError
        Raised when build-system configuration is missing or invalid.
    """

    build = data.get("build-system")
    if not isinstance(build, dict):
        fail("[build-system] mancante")

    requires = build.get("requires")
    backend = build.get("build-backend")

    if not requires or not isinstance(requires, list):
        fail("[build-system.requires] deve essere una lista")

    if not backend or not isinstance(backend, str):
        fail("[build-system.build-backend] mancante o non valido")

    ok("build-system valido")


def check_tooling(data: dict[str, Any]) -> None:
    """Validate presence of required tool configuration blocks.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed ``pyproject.toml`` content.

    Returns
    -------
    None

    Raises
    ------
    LintError
        Raised when required tool sections are missing.
    """

    tool = data.get("tool", {})

    if "ruff" not in tool:
        fail("Configurazione [tool.ruff] mancante")

    if "mypy" not in tool:
        fail("Configurazione [tool.mypy] mancante")

    ok("configurazione tooling presente")


def main() -> int:
    """Run the deterministic structural lint for ``pyproject.toml``.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Process exit status code for the lint run.

    Raises
    ------
    LintError
        Raised when the target file is missing or validation fails.
    """

    path = Path("pyproject.toml")
    if not path.exists():
        fail("pyproject.toml non trovato")

    with path.open("rb") as handle:
        data = tomllib.load(handle)

    check_project_table(data)
    check_license_rules(data)
    check_dependencies(data)
    check_optional_dependencies(data)
    check_build_system(data)
    check_tooling(data)

    ok("pyproject.toml structural lint PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LintError:
        raise SystemExit(1) from None
