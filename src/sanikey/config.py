"""Configuration loading and validation for SaniKey."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from .errors import ConfigError

PATIENT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
REQUIRED_PERSON_FIELDS = (
    "id",
    "display_name",
    "source_documents",
    "metadata_directory",
    "local_build",
    "usb_uuid",
)
UI_DENSITIES = frozenset({"compact", "comfortable"})
UI_TABS = frozenset({"documents", "timeline", "summary"})
UI_TIMELINE_ORDERS = frozenset({"asc", "desc"})
UI_DOCUMENT_LINK_MODES = frozenset({"usb-relative"})
UI_FIELDS = frozenset(
    {
        "accent_color",
        "density",
        "default_tab",
        "timeline_order",
        "document_link_mode",
        "subtitle",
    }
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
class UiConfig:
    """Frontend consultation UI configuration.

    Parameters
    ----------
    accent_color : str
        Hexadecimal accent color used by the generated frontend.
    density : str
        Layout density, either ``compact`` or ``comfortable``.
    default_tab : str
        Initial consultation tab.
    timeline_order : str
        Timeline sort order, either ``desc`` or ``asc``.
    document_link_mode : str
        Document link strategy. Currently only ``usb-relative`` is supported.
    subtitle : str
        Optional short subtitle rendered below the patient name.
    """

    accent_color: str = "#2563eb"
    density: str = "comfortable"
    default_tab: str = "documents"
    timeline_order: str = "desc"
    document_link_mode: str = "usb-relative"
    subtitle: str = "Archivio sanitario personale"


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
        Directory containing original source documents.
    metadata_directory : pathlib.Path
        Directory containing curated metadata.
    local_build : pathlib.Path
        Directory for generated artefacts.
    usb_uuid : str
        Expected filesystem UUID for deployment.
    enabled : bool
        Whether the patient should be included in builds.
    ui : UiConfig
        Resolved frontend UI configuration for this patient.
    """

    id: str
    display_name: str
    source_documents: Path
    metadata_directory: Path
    local_build: Path
    usb_uuid: str
    enabled: bool = True
    ui: UiConfig = field(default_factory=UiConfig)


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
    ui : UiConfig
        Global frontend UI defaults.
    """

    config_version: int
    people: tuple[PersonConfig, ...]
    path: Path
    ui: UiConfig = field(default_factory=UiConfig)

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

    resolved = path.expanduser().resolve(strict=False)
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

    base_dir = _path_base(path)
    global_ui = _parse_ui_config(global_section.get("ui", {}), context="[global.ui]")
    people = tuple(
        _parse_person(item, index=index, base_dir=base_dir, global_ui=global_ui)
        for index, item in enumerate(people_items)
    )
    _validate_unique_ids(people)
    return AccountsConfig(
        config_version=version, people=people, path=path, ui=global_ui
    )


def _parse_person(
    item: Any,
    *,
    index: int,
    base_dir: Path,
    global_ui: UiConfig,
) -> PersonConfig:
    """Parse one ``[[person]]`` entry.

    Parameters
    ----------
    item : Any
        Raw TOML table.
    index : int
        Zero-based person index for diagnostics.
    base_dir : pathlib.Path
        Base directory for relative paths.
    global_ui : UiConfig
        Global UI defaults to merge with per-person overrides.

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
    ui = _parse_ui_config(
        item.get("ui", {}),
        context=f"[[person]] entry {index} ui",
        base=global_ui,
    )

    return PersonConfig(
        id=person_id,
        display_name=_require_string(item, "display_name", index=index),
        source_documents=_require_path(
            item, "source_documents", index=index, base_dir=base_dir
        ),
        metadata_directory=_require_path(
            item, "metadata_directory", index=index, base_dir=base_dir
        ),
        local_build=_require_path(item, "local_build", index=index, base_dir=base_dir),
        usb_uuid=_require_string(item, "usb_uuid", index=index),
        enabled=enabled,
        ui=ui,
    )


def _parse_ui_config(
    value: Any,
    *,
    context: str,
    base: UiConfig | None = None,
) -> UiConfig:
    """Parse and validate a UI configuration table.

    Parameters
    ----------
    value : Any
        Raw TOML value.
    context : str
        Diagnostic context.
    base : UiConfig | None, optional
        Base configuration used for override merging.

    Returns
    -------
    UiConfig
        Validated UI configuration.

    Raises
    ------
    ConfigError
        If the table or any field is invalid.
    """

    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    unknown = sorted(set(value) - UI_FIELDS)
    if unknown:
        _fail(f"{context} unknown fields: {', '.join(unknown)}")
    source = UiConfig() if base is None else base
    return UiConfig(
        accent_color=_optional_color(
            value, "accent_color", context=context, default=source.accent_color
        ),
        density=_optional_choice(
            value,
            "density",
            context=context,
            choices=UI_DENSITIES,
            default=source.density,
        ),
        default_tab=_optional_choice(
            value,
            "default_tab",
            context=context,
            choices=UI_TABS,
            default=source.default_tab,
        ),
        timeline_order=_optional_choice(
            value,
            "timeline_order",
            context=context,
            choices=UI_TIMELINE_ORDERS,
            default=source.timeline_order,
        ),
        document_link_mode=_optional_choice(
            value,
            "document_link_mode",
            context=context,
            choices=UI_DOCUMENT_LINK_MODES,
            default=source.document_link_mode,
        ),
        subtitle=_optional_short_string(
            value, "subtitle", context=context, default=source.subtitle
        ),
    )


def _optional_color(
    item: dict[str, Any],
    field_name: str,
    *,
    context: str,
    default: str,
) -> str:
    """Return an optional hexadecimal color field.

    Parameters
    ----------
    item : dict[str, Any]
        UI configuration table.
    field_name : str
        Field to read.
    context : str
        Diagnostic context.
    default : str
        Default value when the field is omitted.

    Returns
    -------
    str
        Validated color.

    Raises
    ------
    ConfigError
        If the value is not a ``#rrggbb`` color.
    """

    value = item.get(field_name, default)
    if not isinstance(value, str) or COLOR_RE.fullmatch(value) is None:
        _fail(f"{context} field {field_name} must be a #rrggbb color")
    return cast("str", value).lower()


def _optional_choice(
    item: dict[str, Any],
    field_name: str,
    *,
    context: str,
    choices: frozenset[str],
    default: str,
) -> str:
    """Return an optional closed-set string field.

    Parameters
    ----------
    item : dict[str, Any]
        UI configuration table.
    field_name : str
        Field to read.
    context : str
        Diagnostic context.
    choices : frozenset[str]
        Accepted values.
    default : str
        Default value when the field is omitted.

    Returns
    -------
    str
        Validated choice.

    Raises
    ------
    ConfigError
        If the value is not one of ``choices``.
    """

    value = item.get(field_name, default)
    if not isinstance(value, str) or value not in choices:
        accepted = ", ".join(sorted(choices))
        _fail(f"{context} field {field_name} must be one of: {accepted}")
    return cast("str", value)


def _optional_short_string(
    item: dict[str, Any],
    field_name: str,
    *,
    context: str,
    default: str,
) -> str:
    """Return an optional short string field.

    Parameters
    ----------
    item : dict[str, Any]
        UI configuration table.
    field_name : str
        Field to read.
    context : str
        Diagnostic context.
    default : str
        Default value when the field is omitted.

    Returns
    -------
    str
        Stripped string value.

    Raises
    ------
    ConfigError
        If the value is not a string or is too long.
    """

    value = item.get(field_name, default)
    if not isinstance(value, str):
        _fail(f"{context} field {field_name} must be a string")
    rendered = cast("str", value).strip()
    if len(rendered) > 120:
        _fail(f"{context} field {field_name} must be at most 120 characters")
    return rendered


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


def _path_base(config_path: Path) -> Path:
    """Return the base directory used for relative paths.

    Parameters
    ----------
    config_path : pathlib.Path
        Accounts configuration path.

    Returns
    -------
    pathlib.Path
        Repository root for ``config/accounts.toml``, otherwise config parent.
    """

    parent = config_path.expanduser().resolve(strict=False).parent
    if parent.name == "config":
        return parent.parent
    return parent


def _require_path(
    item: dict[str, Any], field: str, *, index: int, base_dir: Path
) -> Path:
    """Return a path field resolved against the configuration base.

    Parameters
    ----------
    item : dict[str, Any]
        Person table.
    field : str
        Field name to read.
    index : int
        Person index for diagnostics.
    base_dir : pathlib.Path
        Base directory for relative paths.

    Returns
    -------
    pathlib.Path
        Expanded path. Relative values are resolved against ``base_dir``.

    Raises
    ------
    ConfigError
        If the field is missing or non-string.
    """

    value = _require_string(item, field, index=index)
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return base_dir / path


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
