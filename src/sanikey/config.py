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
)
UI_DENSITIES = frozenset({"compact", "comfortable"})
UI_TABS = frozenset({"advanced", "documents", "timeline", "summary"})
UI_TIMELINE_ORDERS = frozenset({"asc", "desc"})
UI_DOCUMENT_LINK_MODES = frozenset({"usb-relative"})
UI_FIELDS = frozenset(
    {
        "accent_color",
        "background_image",
        "background_opacity",
        "density",
        "default_tab",
        "timeline_order",
        "document_link_mode",
        "subtitle",
    }
)
SEARCH_FIELDS = frozenset({"advanced_index_warning_mb", "dictionary"})
INGESTION_FIELDS = frozenset({"exclude_patterns"})
USB_COPY_STRATEGIES = frozenset({"python", "rsync-preferred"})
USB_FIELDS = frozenset(
    {
        "copy_strategy",
        "min_free_space_mb",
        "usb_uuid",
        "require_exfat",
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
    background_image : pathlib.Path | None, optional
        Optional image copied into the generated frontend background assets.
    background_opacity : float
        Background image opacity between 0 and 1.
    """

    accent_color: str = "#2563eb"
    density: str = "comfortable"
    default_tab: str = "documents"
    timeline_order: str = "desc"
    document_link_mode: str = "usb-relative"
    subtitle: str = "Archivio sanitario personale"
    background_image: Path | None = None
    background_opacity: float = 0.1


@dataclass(frozen=True)
class SearchDictionary:
    """Configurable search term expansions.

    Parameters
    ----------
    terms : dict[str, tuple[str, ...]]
        Search synonyms keyed by canonical term.
    months : dict[str, tuple[str, ...]]
        Month expansions keyed by month name or number.
    """

    terms: dict[str, tuple[str, ...]] = field(default_factory=dict)
    months: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchConfig:
    """Advanced search configuration.

    Parameters
    ----------
    dictionary : pathlib.Path | None, optional
        Optional TOML dictionary path.
    dictionary_data : SearchDictionary
        Parsed dictionary content.
    advanced_index_warning_mb : int
        Warning threshold for the generated advanced-search index.
    """

    dictionary: Path | None = None
    dictionary_data: SearchDictionary = field(default_factory=SearchDictionary)
    advanced_index_warning_mb: int = 25


@dataclass(frozen=True)
class IngestionConfig:
    """Document ingestion configuration.

    Parameters
    ----------
    exclude_patterns : tuple[str, ...]
        Glob patterns excluded before hashing, staging, and extraction.
    """

    exclude_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class UsbConfig:
    """USB deployment configuration.

    Parameters
    ----------
    usb_uuid : str | None, optional
        Expected filesystem UUID for physical targets.
    require_exfat : bool
        Whether physical targets must be mounted as exFAT.
    min_free_space_mb : int
        Extra free-space margin required before copying.
    copy_strategy : str
        Copy strategy, either ``python`` or ``rsync-preferred``.
    """

    usb_uuid: str | None = None
    require_exfat: bool = False
    min_free_space_mb: int = 256
    copy_strategy: str = "rsync-preferred"


@dataclass(frozen=True)
class _PathFieldOptions:
    """Validation options for optional path fields.

    Parameters
    ----------
    context : str
        Diagnostic context.
    base_dir : pathlib.Path
        Base directory for relative paths.
    default : pathlib.Path | None
        Default path when the field is omitted.
    must_exist : bool
        Whether the resolved path must exist.
    """

    context: str
    base_dir: Path
    default: Path | None
    must_exist: bool


@dataclass(frozen=True)
class _FloatFieldOptions:
    """Validation options for optional float fields.

    Parameters
    ----------
    context : str
        Diagnostic context.
    default : float
        Default value when the field is omitted.
    minimum : float
        Inclusive minimum value.
    maximum : float
        Inclusive maximum value.
    """

    context: str
    default: float
    minimum: float
    maximum: float


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
        Expected filesystem UUID for deployment, resolved from the per-patient
        value or ``[global.usb].usb_uuid``.
    enabled : bool
        Whether the patient should be included in builds.
    ui : UiConfig
        Resolved frontend UI configuration for this patient.
    search : SearchConfig
        Resolved advanced search configuration for this patient.
    ingestion : IngestionConfig
        Resolved ingestion filtering configuration for this patient.
    """

    id: str
    display_name: str
    source_documents: Path
    metadata_directory: Path
    local_build: Path
    usb_uuid: str
    enabled: bool = True
    ui: UiConfig = field(default_factory=UiConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)


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
    search : SearchConfig
        Global advanced search defaults.
    ingestion : IngestionConfig
        Global ingestion defaults.
    usb : UsbConfig
        Global USB deployment defaults.
    """

    config_version: int
    people: tuple[PersonConfig, ...]
    path: Path
    ui: UiConfig = field(default_factory=UiConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    usb: UsbConfig = field(default_factory=UsbConfig)

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
    global_ui = _parse_ui_config(
        global_section.get("ui", {}),
        context="[global.ui]",
        base_dir=base_dir,
    )
    global_search = _parse_search_config(
        global_section.get("search", {}),
        context="[global.search]",
        base_dir=base_dir,
    )
    global_ingestion = _parse_ingestion_config(
        global_section.get("ingestion", {}),
        context="[global.ingestion]",
    )
    global_usb = _parse_usb_config(
        global_section.get("usb", {}),
        context="[global.usb]",
    )
    people = tuple(
        _parse_person(
            item,
            index=index,
            base_dir=base_dir,
            global_ui=global_ui,
            global_search=global_search,
            global_ingestion=global_ingestion,
            global_usb=global_usb,
        )
        for index, item in enumerate(people_items)
    )
    _validate_unique_ids(people)
    _validate_enabled_usb_uuid(people, global_usb)
    return AccountsConfig(
        config_version=version,
        people=people,
        path=path,
        ui=global_ui,
        search=global_search,
        ingestion=global_ingestion,
        usb=global_usb,
    )


def _parse_person(  # noqa: PLR0913
    item: Any,
    *,
    index: int,
    base_dir: Path,
    global_ui: UiConfig,
    global_search: SearchConfig,
    global_ingestion: IngestionConfig,
    global_usb: UsbConfig,
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
    global_search : SearchConfig
        Global search defaults to merge with per-person overrides.
    global_ingestion : IngestionConfig
        Global ingestion defaults to merge with per-person overrides.
    global_usb : UsbConfig
        Global USB defaults used to resolve the per-person UUID.

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
        base_dir=base_dir,
        base=global_ui,
    )
    search = _parse_search_config(
        item.get("search", {}),
        context=f"[[person]] entry {index} search",
        base_dir=base_dir,
        base=global_search,
    )
    ingestion = _parse_ingestion_config(
        item.get("ingestion", {}),
        context=f"[[person]] entry {index} ingestion",
        base=global_ingestion,
    )
    usb_uuid = _optional_nullable_string(
        item,
        "usb_uuid",
        context=f"[[person]] entry {index}",
        default=None,
    )
    if usb_uuid is None:
        global_usb_uuid = global_usb.usb_uuid
        if global_usb_uuid is None:
            _fail(
                f"[[person]] entry {index} missing fields: usb_uuid "
                "or [global.usb].usb_uuid",
            )
        usb_uuid = global_usb_uuid
    assert usb_uuid is not None

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
        usb_uuid=usb_uuid,
        enabled=enabled,
        ui=ui,
        search=search,
        ingestion=ingestion,
    )


def _parse_ui_config(
    value: Any,
    *,
    context: str,
    base_dir: Path,
    base: UiConfig | None = None,
) -> UiConfig:
    """Parse and validate a UI configuration table.

    Parameters
    ----------
    value : Any
        Raw TOML value.
    context : str
        Diagnostic context.
    base_dir : pathlib.Path
        Base directory for relative paths.
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
        background_image=_optional_path(
            value,
            "background_image",
            _PathFieldOptions(
                context=context,
                base_dir=base_dir,
                default=source.background_image,
                must_exist=True,
            ),
        ),
        background_opacity=_optional_float(
            value,
            "background_opacity",
            _FloatFieldOptions(
                context=context,
                default=source.background_opacity,
                minimum=0.0,
                maximum=1.0,
            ),
        ),
    )


def _parse_search_config(
    value: Any,
    *,
    context: str,
    base_dir: Path,
    base: SearchConfig | None = None,
) -> SearchConfig:
    """Parse and validate an advanced search configuration table.

    Parameters
    ----------
    value : Any
        Raw TOML value.
    context : str
        Diagnostic context.
    base_dir : pathlib.Path
        Base directory for relative paths.
    base : SearchConfig | None, optional
        Base configuration used for override merging.

    Returns
    -------
    SearchConfig
        Validated search configuration.

    Raises
    ------
    ConfigError
        If the table or any field is invalid.
    """

    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    unknown = sorted(set(value) - SEARCH_FIELDS)
    if unknown:
        _fail(f"{context} unknown fields: {', '.join(unknown)}")
    source = SearchConfig() if base is None else base
    dictionary = _optional_path(
        value,
        "dictionary",
        _PathFieldOptions(
            context=context,
            base_dir=base_dir,
            default=source.dictionary,
            must_exist=True,
        ),
    )
    return SearchConfig(
        dictionary=dictionary,
        dictionary_data=(
            source.dictionary_data
            if dictionary == source.dictionary
            else _load_search_dictionary(dictionary, context=context)
        ),
        advanced_index_warning_mb=_optional_positive_int(
            value,
            "advanced_index_warning_mb",
            context=context,
            default=source.advanced_index_warning_mb,
        ),
    )


def _parse_ingestion_config(
    value: Any,
    *,
    context: str,
    base: IngestionConfig | None = None,
) -> IngestionConfig:
    """Parse and validate an ingestion configuration table.

    Parameters
    ----------
    value : Any
        Raw TOML value.
    context : str
        Diagnostic context.
    base : IngestionConfig | None, optional
        Base configuration used for additive per-person overrides.

    Returns
    -------
    IngestionConfig
        Validated ingestion configuration.

    Raises
    ------
    ConfigError
        If the table or any field is invalid.
    """

    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    unknown = sorted(set(value) - INGESTION_FIELDS)
    if unknown:
        _fail(f"{context} unknown fields: {', '.join(unknown)}")
    source = IngestionConfig() if base is None else base
    return IngestionConfig(
        exclude_patterns=(
            *source.exclude_patterns,
            *_optional_string_list(
                value,
                "exclude_patterns",
                context=context,
                default=(),
            ),
        ),
    )


def _parse_usb_config(value: Any, *, context: str) -> UsbConfig:
    """Parse and validate a USB deployment configuration table.

    Parameters
    ----------
    value : Any
        Raw TOML value.
    context : str
        Diagnostic context.

    Returns
    -------
    UsbConfig
        Validated USB configuration.

    Raises
    ------
    ConfigError
        If the table or any field is invalid.
    """

    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    unknown = sorted(set(value) - USB_FIELDS)
    if unknown:
        _fail(f"{context} unknown fields: {', '.join(unknown)}")
    source = UsbConfig()
    return UsbConfig(
        usb_uuid=_optional_nullable_string(
            value,
            "usb_uuid",
            context=context,
            default=source.usb_uuid,
        ),
        require_exfat=_optional_bool(
            value,
            "require_exfat",
            context=context,
            default=source.require_exfat,
        ),
        min_free_space_mb=_optional_positive_int(
            value,
            "min_free_space_mb",
            context=context,
            default=source.min_free_space_mb,
        ),
        copy_strategy=_optional_choice(
            value,
            "copy_strategy",
            context=context,
            choices=USB_COPY_STRATEGIES,
            default=source.copy_strategy,
        ),
    )


def _optional_string_list(
    item: dict[str, Any],
    field_name: str,
    *,
    context: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    """Return an optional list of non-empty strings.

    Parameters
    ----------
    item : dict[str, Any]
        Configuration table.
    field_name : str
        Field to read.
    context : str
        Diagnostic context.
    default : tuple[str, ...]
        Default value when the field is omitted.

    Returns
    -------
    tuple[str, ...]
        Validated string tuple.

    Raises
    ------
    ConfigError
        If the value is not a list of non-empty strings.
    """

    value = item.get(field_name)
    if value is None:
        return default
    if not isinstance(value, list):
        _fail(f"{context} field {field_name} must be a list of strings")
    parsed = []
    for raw_value in value:
        if not isinstance(raw_value, str) or not raw_value.strip():
            _fail(f"{context} field {field_name} must contain only non-empty strings")
        parsed.append(raw_value.strip())
    return tuple(parsed)


def _optional_nullable_string(
    item: dict[str, Any],
    field_name: str,
    *,
    context: str,
    default: str | None,
) -> str | None:
    """Return an optional nullable string field.

    Parameters
    ----------
    item : dict[str, Any]
        Configuration table.
    field_name : str
        Field to read.
    context : str
        Diagnostic context.
    default : str | None
        Default value when the field is omitted.

    Returns
    -------
    str | None
        Stripped string or ``None``.

    Raises
    ------
    ConfigError
        If the value is not null or a non-empty string.
    """

    value = item.get(field_name, default)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        _fail(f"{context} field {field_name} must be a non-empty string")
    return value.strip()


def _optional_bool(
    item: dict[str, Any],
    field_name: str,
    *,
    context: str,
    default: bool,
) -> bool:
    """Return an optional boolean field.

    Parameters
    ----------
    item : dict[str, Any]
        Configuration table.
    field_name : str
        Field to read.
    context : str
        Diagnostic context.
    default : bool
        Default value when the field is omitted.

    Returns
    -------
    bool
        Validated boolean.

    Raises
    ------
    ConfigError
        If the value is not boolean.
    """

    value = item.get(field_name, default)
    if not isinstance(value, bool):
        _fail(f"{context} field {field_name} must be boolean")
    return cast("bool", value)


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


def _optional_path(
    item: dict[str, Any],
    field_name: str,
    options: _PathFieldOptions,
) -> Path | None:
    """Return an optional path field resolved against the configuration base.

    Parameters
    ----------
    item : dict[str, Any]
        Configuration table.
    field_name : str
        Field to read.
    options : _PathFieldOptions
        Validation options.

    Returns
    -------
    pathlib.Path | None
        Resolved optional path.

    Raises
    ------
    ConfigError
        If the value is not a string or the required path is missing.
    """

    value = item.get(field_name)
    if value is None:
        return options.default
    if not isinstance(value, str) or not value.strip():
        _fail(f"{options.context} field {field_name} must be a non-empty string")
    path = Path(cast("str", value).strip()).expanduser()
    resolved = path if path.is_absolute() else options.base_dir / path
    if options.must_exist and not resolved.exists():
        _fail(f"{options.context} field {field_name} path does not exist: {resolved}")
    return resolved


def _optional_float(
    item: dict[str, Any],
    field_name: str,
    options: _FloatFieldOptions,
) -> float:
    """Return an optional bounded float field.

    Parameters
    ----------
    item : dict[str, Any]
        Configuration table.
    field_name : str
        Field to read.
    options : _FloatFieldOptions
        Validation options.

    Returns
    -------
    float
        Validated float value.

    Raises
    ------
    ConfigError
        If the value is not numeric or is outside the accepted range.
    """

    value = item.get(field_name, options.default)
    if not isinstance(value, int | float) or isinstance(value, bool):
        _fail(f"{options.context} field {field_name} must be a number")
    rendered = float(value)
    if rendered < options.minimum or rendered > options.maximum:
        _fail(
            f"{options.context} field {field_name} must be between "
            f"{options.minimum} and {options.maximum}"
        )
    return rendered


def _optional_positive_int(
    item: dict[str, Any],
    field_name: str,
    *,
    context: str,
    default: int,
) -> int:
    """Return an optional positive integer field.

    Parameters
    ----------
    item : dict[str, Any]
        Configuration table.
    field_name : str
        Field to read.
    context : str
        Diagnostic context.
    default : int
        Default value when the field is omitted.

    Returns
    -------
    int
        Validated positive integer.

    Raises
    ------
    ConfigError
        If the value is not a positive integer.
    """

    value = item.get(field_name, default)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _fail(f"{context} field {field_name} must be a positive integer")
    return cast("int", value)


def _load_search_dictionary(path: Path | None, *, context: str) -> SearchDictionary:
    """Load an optional search dictionary TOML file.

    Parameters
    ----------
    path : pathlib.Path | None
        Dictionary path.
    context : str
        Diagnostic context.

    Returns
    -------
    SearchDictionary
        Parsed dictionary content.

    Raises
    ------
    ConfigError
        If the file is malformed.
    """

    if path is None:
        return SearchDictionary()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        message = f"invalid TOML in {path}: {exc}"
        raise ConfigError(message) from exc
    terms = _parse_dictionary_section(data.get("terms", {}), context=f"{context}.terms")
    months = _parse_dictionary_section(
        data.get("months", {}), context=f"{context}.months"
    )
    unknown = sorted(set(data) - {"terms", "months"})
    if unknown:
        _fail(f"{context} dictionary unknown sections: {', '.join(unknown)}")
    return SearchDictionary(terms=terms, months=months)


def _parse_dictionary_section(
    value: Any, *, context: str
) -> dict[str, tuple[str, ...]]:
    """Parse one search dictionary section.

    Parameters
    ----------
    value : Any
        Raw section value.
    context : str
        Diagnostic context.

    Returns
    -------
    dict[str, tuple[str, ...]]
        Validated dictionary section.

    Raises
    ------
    ConfigError
        If the section is malformed.
    """

    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    parsed: dict[str, tuple[str, ...]] = {}
    for key, raw_values in value.items():
        if not isinstance(key, str) or not key.strip():
            _fail(f"{context} keys must be non-empty strings")
        if not isinstance(raw_values, list) or not raw_values:
            _fail(f"{context}.{key} must be a non-empty list of strings")
        values = []
        for raw_value in raw_values:
            if not isinstance(raw_value, str) or not raw_value.strip():
                _fail(f"{context}.{key} must contain only non-empty strings")
            values.append(raw_value.strip())
        parsed[key.strip()] = tuple(values)
    return parsed


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


def _validate_enabled_usb_uuid(
    people: tuple[PersonConfig, ...],
    usb: UsbConfig,
) -> None:
    """Validate enabled patient USB UUID declarations.

    Parameters
    ----------
    people : tuple[PersonConfig, ...]
        Parsed patient entries.
    usb : UsbConfig
        Global USB configuration.

    Returns
    -------
    None

    Raises
    ------
    ConfigError
        If enabled patients require incompatible USB filesystems.
    """

    enabled_uuids = {
        person.usb_uuid.strip()
        for person in people
        if person.enabled and person.usb_uuid
    }
    if usb.usb_uuid is not None:
        mismatches = sorted(uuid for uuid in enabled_uuids if uuid != usb.usb_uuid)
        if mismatches:
            _fail(
                "[global.usb].usb_uuid conflicts with enabled "
                f"patient usb_uuid values: {', '.join(mismatches)}"
            )
        return
    if len(enabled_uuids) > 1:
        _fail(
            "enabled patients use different usb_uuid values; set one shared "
            "[global.usb].usb_uuid or align [[person]].usb_uuid"
        )
