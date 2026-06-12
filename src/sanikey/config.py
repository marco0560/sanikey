"""Configuration loading and validation for SaniKey."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .errors import ConfigError

PATIENT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED_PERSON_FIELDS = (
    "id",
    "display_name",
    "source_documents",
    "metadata_directory",
    "local_build",
    "usb_uuid",
)


def _fail(message: str) -> None:
    """Raise a configuration error.

    Parameters
    ----------
    message : str
        Diagnostic message.

    Returns
    -------
    None

    Raises
    ------
    ConfigError
        Always raised.
    """

    raise ConfigError(message)


@dataclass(frozen=True)
class PersonConfig:
    """Per-patient configuration.

    Parameters
    ----------
    id : str
        Stable technical patient identifier.
    display_name : str
        Human-readable name shown in generated artefacts.
    source_documents : pathlib.Path
        Absolute directory containing original source documents.
    metadata_directory : pathlib.Path
        Absolute directory containing curated metadata.
    local_build : pathlib.Path
        Absolute directory for generated artefacts.
    usb_uuid : str
        Expected filesystem UUID for deployment.
    enabled : bool
        Whether the patient should be included in builds.
    """

    id: str
    display_name: str
    source_documents: Path
    metadata_directory: Path
    local_build: Path
    usb_uuid: str
    enabled: bool = True


@dataclass(frozen=True)
class AccountsConfig:
    """Loaded ``config/accounts.toml`` content.

    Parameters
    ----------
    config_version : int
        Configuration schema version.
    people : tuple[PersonConfig, ...]
        Patient entries in deterministic file order.
    path : pathlib.Path
        Path of the loaded configuration file.
    """

    config_version: int
    people: tuple[PersonConfig, ...]
    path: Path

    def enabled_people(self) -> tuple[PersonConfig, ...]:
        """Return enabled patient entries.

        Parameters
        ----------
        None

        Returns
        -------
        tuple[PersonConfig, ...]
            Enabled patients in configuration order.
        """

        return tuple(person for person in self.people if person.enabled)


def default_accounts_path(repo_root: Path | None = None) -> Path:
    """Return the conventional local accounts configuration path.

    Parameters
    ----------
    repo_root : pathlib.Path | None, optional
        Repository root. When omitted, the current working directory is used.

    Returns
    -------
    pathlib.Path
        ``config/accounts.toml`` under ``repo_root``.
    """

    root = Path.cwd() if repo_root is None else repo_root
    return root / "config" / "accounts.toml"


def load_accounts(path: Path) -> AccountsConfig:
    """Load and validate an accounts configuration file.

    Parameters
    ----------
    path : pathlib.Path
        Path to ``accounts.toml``.

    Returns
    -------
    AccountsConfig
        Parsed and validated configuration.

    Raises
    ------
    ConfigError
        If the file is missing, malformed, or semantically invalid.
    """

    resolved = path.expanduser()
    if not resolved.is_file():
        _fail(f"accounts configuration not found: {resolved}")
    try:
        data = tomllib.loads(resolved.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        message = f"invalid TOML in {resolved}: {exc}"
        raise ConfigError(message) from exc
    return parse_accounts_data(data, path=resolved)


def parse_accounts_data(data: dict[str, Any], *, path: Path) -> AccountsConfig:
    """Validate parsed accounts TOML data.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed TOML mapping.
    path : pathlib.Path
        Configuration path used in diagnostics.

    Returns
    -------
    AccountsConfig
        Validated accounts configuration.

    Raises
    ------
    ConfigError
        If required fields are missing or invalid.
    """

    global_section = data.get("global", {})
    if not isinstance(global_section, dict):
        _fail("[global] must be a table")
    version = global_section.get(
        "config_version",
        global_section.get("repository_version"),
    )
    if version is None:
        _fail("[global].config_version is required")
    if not isinstance(version, int):
        _fail("[global].config_version must be an integer")

    people_data = data.get("person")
    if not isinstance(people_data, list) or not people_data:
        _fail("at least one [[person]] entry is required")
    people_items = cast("list[Any]", people_data)

    people = tuple(
        _parse_person(item, index=index) for index, item in enumerate(people_items)
    )
    _validate_unique_ids(people)
    return AccountsConfig(config_version=version, people=people, path=path)


def _parse_person(item: Any, *, index: int) -> PersonConfig:
    """Parse one ``[[person]]`` entry.

    Parameters
    ----------
    item : Any
        Raw TOML table.
    index : int
        Zero-based person index for diagnostics.

    Returns
    -------
    PersonConfig
        Validated person configuration.

    Raises
    ------
    ConfigError
        If the table is incomplete or invalid.
    """

    if not isinstance(item, dict):
        _fail(f"[[person]] entry {index} must be a table")
    missing = [field for field in REQUIRED_PERSON_FIELDS if field not in item]
    if missing:
        _fail(f"[[person]] entry {index} missing fields: {', '.join(missing)}")

    person_id = _require_string(item, "id", index=index)
    if PATIENT_ID_RE.fullmatch(person_id) is None:
        _fail(
            f"[[person]] entry {index} has invalid id {person_id!r}; "
            "use lowercase letters, digits, and hyphens",
        )

    enabled = item.get("enabled", True)
    if not isinstance(enabled, bool):
        _fail(f"[[person]] entry {index} field enabled must be boolean")

    return PersonConfig(
        id=person_id,
        display_name=_require_string(item, "display_name", index=index),
        source_documents=_require_absolute_path(item, "source_documents", index=index),
        metadata_directory=_require_absolute_path(
            item, "metadata_directory", index=index
        ),
        local_build=_require_absolute_path(item, "local_build", index=index),
        usb_uuid=_require_string(item, "usb_uuid", index=index),
        enabled=enabled,
    )


def _require_string(item: dict[str, Any], field: str, *, index: int) -> str:
    """Return a non-empty string field.

    Parameters
    ----------
    item : dict[str, Any]
        Person table.
    field : str
        Field name to read.
    index : int
        Person index for diagnostics.

    Returns
    -------
    str
        Non-empty string value.

    Raises
    ------
    ConfigError
        If the field is not a non-empty string.
    """

    value = item[field]
    if not isinstance(value, str) or not value.strip():
        _fail(
            f"[[person]] entry {index} field {field} must be a non-empty string",
        )
    return cast("str", value.strip())


def _require_absolute_path(item: dict[str, Any], field: str, *, index: int) -> Path:
    """Return an absolute path field.

    Parameters
    ----------
    item : dict[str, Any]
        Person table.
    field : str
        Field name to read.
    index : int
        Person index for diagnostics.

    Returns
    -------
    pathlib.Path
        Absolute expanded path.

    Raises
    ------
    ConfigError
        If the field is missing, non-string, or relative.
    """

    value = _require_string(item, field, index=index)
    path = Path(value).expanduser()
    if not path.is_absolute():
        _fail(f"[[person]] entry {index} field {field} must be absolute")
    return path


def _validate_unique_ids(people: tuple[PersonConfig, ...]) -> None:
    """Validate patient id uniqueness.

    Parameters
    ----------
    people : tuple[PersonConfig, ...]
        Parsed patient entries.

    Returns
    -------
    None

    Raises
    ------
    ConfigError
        If a duplicate id exists.
    """

    seen: set[str] = set()
    for person in people:
        if person.id in seen:
            _fail(f"duplicate patient id: {person.id}")
        seen.add(person.id)
