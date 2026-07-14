"""Observation import pipeline from tabular source files."""

from __future__ import annotations

import csv
import hashlib
import re
import tomllib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Never, cast

from python_calamine import CalamineError, load_workbook

from .errors import ConfigError

if TYPE_CHECKING:
    from .config import PersonConfig

SPREADSHEET_SUFFIXES = {".ods", ".xls", ".xlsb", ".xlsm", ".xlsx"}
CSV_SUFFIXES = {".csv"}
STATE_FILE = "import_state.toml"
SERIES_FILE = "series.toml"


@dataclass(frozen=True)
class ObservationImportResult:
    """Represent the result of one observation import run.

    Parameters
    ----------
    patient_id : str
        Patient identifier.
    series : int
        Imported series count.
    points : int
        Imported point count.
    warnings : tuple[str, ...]
        Non-fatal import warnings.
    """

    patient_id: str
    series: int
    points: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _SeriesSpec:
    """Represent one series declared in the import manifest.

    Parameters
    ----------
    id : str
        Series identifier.
    name : str
        Human-readable series name.
    value_type : str
        Value type.
    unit : str | None
        Measurement unit.
    description : str | None
        Optional description.
    warn_duplicate_same_day : bool
        Whether same-day duplicates produce warnings.
    """

    id: str
    name: str
    value_type: str
    unit: str | None
    description: str | None
    warn_duplicate_same_day: bool


@dataclass(frozen=True)
class _SourceSpec:
    """Represent one tabular source declared in the import manifest.

    Parameters
    ----------
    path : Path
        Resolved source path.
    raw_path : str
        Manifest path value.
    series_id : str
        Target series id.
    columns : dict[str, str]
        Logical field to source column mapping.
    sheet : str | None
        Optional worksheet name.
    source_reference : str
        Source reference written into points.
    """

    path: Path
    raw_path: str
    series_id: str
    columns: dict[str, str]
    sheet: str | None
    source_reference: str


@dataclass(frozen=True)
class _Manifest:
    """Represent a parsed import manifest.

    Parameters
    ----------
    series : tuple[_SeriesSpec, ...]
        Declared observation series.
    sources : tuple[_SourceSpec, ...]
        Declared tabular sources.
    manifest_hash : str
        Hash of manifest bytes.
    source_hashes : dict[str, str]
        Source hashes keyed by manifest path.
    """

    series: tuple[_SeriesSpec, ...]
    sources: tuple[_SourceSpec, ...]
    manifest_hash: str
    source_hashes: dict[str, str]


def import_observations(person: PersonConfig) -> ObservationImportResult:
    """Import longitudinal observations for one patient.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    ObservationImportResult
        Import counters and warnings.

    Raises
    ------
    ConfigError
        If the manifest or a source file is invalid.
    """

    manifest_path = person.metadata_directory / "observation_imports.toml"
    if not manifest_path.exists():
        return ObservationImportResult(patient_id=person.id, series=0, points=0)
    manifest = _load_manifest(person, manifest_path)
    output_dir = person.metadata_directory / "observations"
    output_dir.mkdir(parents=True, exist_ok=True)
    points_by_series: dict[str, list[dict[str, Any]]] = {
        series.id: [] for series in manifest.series
    }
    warnings: list[str] = []
    for source_index, source in enumerate(manifest.sources):
        rows = _read_table(source)
        points = _points_from_rows(source, rows, source_index)
        points_by_series[source.series_id].extend(points)
    for series in manifest.series:
        series_points = sorted(
            points_by_series[series.id],
            key=lambda item: (item["observation_date"], item["id"]),
        )
        if series.warn_duplicate_same_day:
            warnings.extend(_duplicate_day_warnings(series, series_points))
        _write_points(output_dir / f"{_slug(series.id)}.toml", series_points)
    _write_series(output_dir / SERIES_FILE, manifest.series)
    _write_state(output_dir / STATE_FILE, manifest)
    return ObservationImportResult(
        patient_id=person.id,
        series=len(manifest.series),
        points=sum(len(points) for points in points_by_series.values()),
        warnings=tuple(warnings),
    )


def ensure_observation_imports_current(person: PersonConfig) -> None:
    """Fail when normalized observations are stale.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    None

    Raises
    ------
    ConfigError
        If generated observation artifacts are missing or stale.
    """

    manifest_path = person.metadata_directory / "observation_imports.toml"
    if not manifest_path.exists():
        return
    manifest = _load_manifest(person, manifest_path)
    state_path = person.metadata_directory / "observations" / STATE_FILE
    if not state_path.exists():
        _fail_stale(person)
    try:
        state = tomllib.loads(state_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        message = f"TOML non valido in {state_path}: {exc}"
        raise ConfigError(message) from exc
    if state.get("manifest_hash") != manifest.manifest_hash:
        _fail_stale(person)
    if state.get("source_hashes") != manifest.source_hashes:
        _fail_stale(person)


def _load_manifest(person: PersonConfig, path: Path) -> _Manifest:
    """Load an observation import manifest.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    path : pathlib.Path
        Manifest path.

    Returns
    -------
    _Manifest
        Parsed manifest.
    """

    try:
        raw_text = path.read_text(encoding="utf-8")
        data = tomllib.loads(raw_text)
    except tomllib.TOMLDecodeError as exc:
        message = f"TOML non valido in {path}: {exc}"
        raise ConfigError(message) from exc
    series = tuple(
        _series_from_table(_table(item, path, "series", index), path, index)
        for index, item in enumerate(_array(data, "series", path))
    )
    sources = tuple(
        _source_from_table(person, _table(item, path, "source", index), path, index)
        for index, item in enumerate(_array(data, "source", path))
    )
    series_ids = {item.id for item in series}
    if len(series_ids) != len(series):
        _fail(f"{path}: id serie osservazioni duplicato")
    for source in sources:
        if source.series_id not in series_ids:
            _fail(
                f"{path}: source {source.raw_path} referenzia series_id sconosciuto "
                f"{source.series_id}"
            )
        if not source.path.exists():
            _fail(f"{path}: sorgente osservazioni non trovata: {source.path}")
    source_hashes = {source.raw_path: _sha256(source.path) for source in sources}
    return _Manifest(
        series=series,
        sources=sources,
        manifest_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        source_hashes=source_hashes,
    )


def _series_from_table(item: dict[str, Any], path: Path, index: int) -> _SeriesSpec:
    """Parse one series table.

    Parameters
    ----------
    item : dict[str, Any]
        Raw manifest table.
    path : pathlib.Path
        Manifest path.
    index : int
        Table index.

    Returns
    -------
    _SeriesSpec
        Parsed series.
    """

    return _SeriesSpec(
        id=_required_string(item, "id", path, index),
        name=_required_string(item, "name", path, index),
        value_type=_required_string(item, "value_type", path, index),
        unit=_optional_string(item, "unit"),
        description=_optional_string(item, "description"),
        warn_duplicate_same_day=_optional_bool(
            item,
            "warn_duplicate_same_day",
            default=True,
            path=path,
            index=index,
        ),
    )


def _source_from_table(
    person: PersonConfig,
    item: dict[str, Any],
    path: Path,
    index: int,
) -> _SourceSpec:
    """Parse one source table.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.
    item : dict[str, Any]
        Raw manifest table.
    path : pathlib.Path
        Manifest path.
    index : int
        Table index.

    Returns
    -------
    _SourceSpec
        Parsed source.
    """

    raw_path = _required_string(item, "path", path, index)
    source_path = Path(raw_path)
    if not source_path.is_absolute():
        source_path = person.source_documents / source_path
    columns = item.get("columns")
    if not isinstance(columns, dict):
        _fail(f"{path}: source {index} deve contenere [source.columns]")
    return _SourceSpec(
        path=source_path,
        raw_path=raw_path,
        series_id=_required_string(item, "series_id", path, index),
        columns={str(key): str(value) for key, value in columns.items()},
        sheet=_optional_string(item, "sheet"),
        source_reference=_optional_string(item, "source_reference") or raw_path,
    )


def _read_table(source: _SourceSpec) -> list[dict[str, Any]]:
    """Read one tabular source into row dictionaries.

    Parameters
    ----------
    source : _SourceSpec
        Source specification.

    Returns
    -------
    list[dict[str, Any]]
        Rows keyed by header.
    """

    suffix = source.path.suffix.lower()
    if suffix in CSV_SUFFIXES:
        with source.path.open(encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if suffix not in SPREADSHEET_SUFFIXES:
        _fail(f"formato osservazioni non supportato: {source.path}")
    try:
        workbook = load_workbook(source.path)
        try:
            sheet_name = source.sheet or workbook.sheet_names[0]
            sheet = workbook.get_sheet_by_name(sheet_name)
            rows = sheet.to_python(skip_empty_area=False)
        finally:
            workbook.close()
    except (CalamineError, OSError, ValueError) as exc:
        message = f"lettura osservazioni non riuscita per {source.path}: {exc}"
        raise ConfigError(message) from exc
    if not rows:
        return []
    headers = [str(value).strip() for value in rows[0]]
    return [
        {
            header: row[index] if index < len(row) else None
            for index, header in enumerate(headers)
            if header
        }
        for row in rows[1:]
    ]


def _points_from_rows(
    source: _SourceSpec,
    rows: list[dict[str, Any]],
    source_index: int,
) -> list[dict[str, Any]]:
    """Build normalized points from table rows.

    Parameters
    ----------
    source : _SourceSpec
        Source specification.
    rows : list[dict[str, Any]]
        Source rows.
    source_index : int
        Source index in the manifest.

    Returns
    -------
    list[dict[str, Any]]
        Normalized points.
    """

    points: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows, start=2):
        observation_date = _date_value(_mapped_value(source, row, "date"))
        if observation_date is None:
            continue
        point: dict[str, Any] = {
            "id": f"{_slug(source.series_id)}-{observation_date}-{source_index + 1}-{row_index}",
            "series_id": source.series_id,
            "observation_date": observation_date,
            "source_type": "spreadsheet",
            "source_reference": source.source_reference,
        }
        for field in ("numeric_value", "systolic", "diastolic", "pulse"):
            value = _number_value(_mapped_value(source, row, field))
            if value is not None:
                point[field] = value
        text_value = _text_value(
            _mapped_value(source, row, "text_value")
            or _mapped_value(source, row, "value")
        )
        if text_value is not None:
            point["text_value"] = text_value
        note = _text_value(_mapped_value(source, row, "note"))
        if note is not None:
            point["note"] = note
        points.append(point)
    return points


def _mapped_value(source: _SourceSpec, row: dict[str, Any], field: str) -> Any:
    """Return a mapped row value.

    Parameters
    ----------
    source : _SourceSpec
        Source specification.
    row : dict[str, Any]
        Source row.
    field : str
        Logical field name.

    Returns
    -------
    Any
        Mapped value or ``None``.
    """

    column = source.columns.get(field)
    if column is None:
        return None
    return row.get(column)


def _write_series(path: Path, series: tuple[_SeriesSpec, ...]) -> None:
    """Write normalized series TOML.

    Parameters
    ----------
    path : pathlib.Path
        Output path.
    series : tuple[_SeriesSpec, ...]
        Series to write.

    Returns
    -------
    None
    """

    lines: list[str] = []
    for item in series:
        lines.extend(
            [
                "[[series]]",
                f"id = {_toml_string(item.id)}",
                f"name = {_toml_string(item.name)}",
                f"value_type = {_toml_string(item.value_type)}",
                f"warn_duplicate_same_day = {_toml_bool(item.warn_duplicate_same_day)}",
            ]
        )
        if item.unit is not None:
            lines.append(f"unit = {_toml_string(item.unit)}")
        if item.description is not None:
            lines.append(f"description = {_toml_string(item.description)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_points(path: Path, points: list[dict[str, Any]]) -> None:
    """Write normalized point TOML.

    Parameters
    ----------
    path : pathlib.Path
        Output path.
    points : list[dict[str, Any]]
        Points to write.

    Returns
    -------
    None
    """

    lines: list[str] = []
    for point in points:
        lines.append("[[point]]")
        for key, value in point.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_state(path: Path, manifest: _Manifest) -> None:
    """Write import state TOML.

    Parameters
    ----------
    path : pathlib.Path
        Output path.
    manifest : _Manifest
        Parsed manifest.

    Returns
    -------
    None
    """

    lines = [
        f"manifest_hash = {_toml_string(manifest.manifest_hash)}",
        "",
        "[source_hashes]",
    ]
    for source, digest in sorted(manifest.source_hashes.items()):
        lines.append(f"{_toml_key(source)} = {_toml_string(digest)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _duplicate_day_warnings(
    series: _SeriesSpec,
    points: list[dict[str, Any]],
) -> tuple[str, ...]:
    """Return duplicate same-day warnings for one series.

    Parameters
    ----------
    series : _SeriesSpec
        Series specification.
    points : list[dict[str, Any]]
        Normalized points.

    Returns
    -------
    tuple[str, ...]
        Warning messages.
    """

    counts: dict[str, int] = {}
    for point in points:
        key = cast("str", point["observation_date"])
        counts[key] = counts.get(key, 0) + 1
    return tuple(
        f"serie {series.id}: {count} misurazioni nella stessa data {day}"
        for day, count in sorted(counts.items())
        if count > 1
    )


def _array(data: dict[str, Any], key: str, path: Path) -> list[Any]:
    """Return a TOML array value.

    Parameters
    ----------
    data : dict[str, Any]
        TOML data.
    key : str
        Array key.
    path : pathlib.Path
        Source path.

    Returns
    -------
    list[Any]
        Array value.
    """

    value = data.get(key, [])
    if not isinstance(value, list):
        _fail(f"{path}: {key} deve essere un array di tabelle")
    return value


def _table(item: Any, path: Path, key: str, index: int) -> dict[str, Any]:
    """Return a TOML table value.

    Parameters
    ----------
    item : Any
        Raw value.
    path : pathlib.Path
        Source path.
    key : str
        Parent array key.
    index : int
        Item index.

    Returns
    -------
    dict[str, Any]
        Table value.
    """

    if not isinstance(item, dict):
        _fail(f"{path}: {key}[{index}] deve essere una tabella")
    return cast("dict[str, Any]", item)


def _required_string(item: dict[str, Any], field: str, path: Path, index: int) -> str:
    """Return a required non-empty string.

    Parameters
    ----------
    item : dict[str, Any]
        TOML table.
    field : str
        Field name.
    path : pathlib.Path
        Source path.
    index : int
        Table index.

    Returns
    -------
    str
        Parsed string.
    """

    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        _fail(f"{path}: elemento {index} campo {field} deve essere stringa")
    return value.strip()


def _optional_string(item: dict[str, Any], field: str) -> str | None:
    """Return an optional string.

    Parameters
    ----------
    item : dict[str, Any]
        TOML table.
    field : str
        Field name.

    Returns
    -------
    str | None
        Parsed string.
    """

    value = item.get(field)
    if value is None:
        return None
    return str(value).strip() or None


def _optional_bool(
    item: dict[str, Any],
    field: str,
    *,
    default: bool,
    path: Path,
    index: int,
) -> bool:
    """Return an optional boolean.

    Parameters
    ----------
    item : dict[str, Any]
        TOML table.
    field : str
        Field name.
    default : bool
        Default value.
    path : pathlib.Path
        Source path.
    index : int
        Table index.

    Returns
    -------
    bool
        Parsed boolean.
    """

    value = item.get(field)
    if value is None:
        return default
    if not isinstance(value, bool):
        _fail(f"{path}: elemento {index} campo {field} deve essere booleano")
    return value


def _date_value(value: Any) -> str | None:
    """Return an ISO date string from a cell value.

    Parameters
    ----------
    value : Any
        Raw cell value.

    Returns
    -------
    str | None
        ISO date string.
    """

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    _fail(f"data osservazione non valida: {text}")
    return None


def _number_value(value: Any) -> float | None:
    """Return a float from a cell value.

    Parameters
    ----------
    value : Any
        Raw cell value.

    Returns
    -------
    float | None
        Parsed float.
    """

    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    return float(text)


def _text_value(value: Any) -> str | None:
    """Return text from a cell value.

    Parameters
    ----------
    value : Any
        Raw cell value.

    Returns
    -------
    str | None
        Parsed text.
    """

    if value in (None, ""):
        return None
    if isinstance(value, datetime | date | time | timedelta):
        return str(value)
    text = str(value).strip()
    return text or None


def _sha256(path: Path) -> str:
    """Return the SHA256 digest of a file.

    Parameters
    ----------
    path : pathlib.Path
        File path.

    Returns
    -------
    str
        Hex digest.
    """

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug(value: str) -> str:
    """Return a filesystem-safe slug.

    Parameters
    ----------
    value : str
        Raw value.

    Returns
    -------
    str
        Slug value.
    """

    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "osservazione"


def _toml_value(value: Any) -> str:
    """Render a simple TOML value.

    Parameters
    ----------
    value : Any
        Python value.

    Returns
    -------
    str
        TOML literal.
    """

    if isinstance(value, bool):
        return _toml_bool(value)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return str(value)
    return _toml_string(str(value))


def _toml_string(value: str) -> str:
    """Render a TOML basic string.

    Parameters
    ----------
    value : str
        Raw value.

    Returns
    -------
    str
        TOML string.
    """

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_bool(value: bool) -> str:
    """Render a TOML boolean.

    Parameters
    ----------
    value : bool
        Boolean value.

    Returns
    -------
    str
        TOML boolean.
    """

    return "true" if value else "false"


def _toml_key(value: str) -> str:
    """Render a TOML quoted key.

    Parameters
    ----------
    value : str
        Raw key.

    Returns
    -------
    str
        TOML key.
    """

    return _toml_string(value)


def _fail_stale(person: PersonConfig) -> None:
    """Raise a stale import error for one patient.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    None

    Raises
    ------
    ConfigError
        Always raised.
    """

    _fail(
        f"osservazioni importate non aggiornate per {person.id}: "
        "eseguire `sanikey import-observations`"
    )


def _fail(message: str) -> Never:
    """Raise a configuration error.

    Parameters
    ----------
    message : str
        Error message.

    Returns
    -------
    Never
        This function always raises.

    Raises
    ------
    ConfigError
        Always raised.
    """

    raise ConfigError(message)
