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
    extracts : tuple[_ExtractSpec, ...]
        Target point extractions.
    sheet : str | None
        Optional worksheet name.
    header_rows : tuple[int, ...]
        One-based row indexes used to build column headers.
    data_start_row : int | None
        One-based first data row. Defaults after the last header row.
    fill_down : tuple[str, ...]
        Logical fields whose previous non-empty value is reused.
    layout : str
        Source layout strategy.
    matrix : dict[str, Any]
        Matrix layout options for ``repeating_matrix`` sources.
    """

    path: Path
    raw_path: str
    extracts: tuple[_ExtractSpec, ...]
    sheet: str | None
    header_rows: tuple[int, ...]
    data_start_row: int | None
    fill_down: tuple[str, ...]
    layout: str
    matrix: dict[str, Any]


@dataclass(frozen=True)
class _ExtractSpec:
    """Represent one point extraction declared for a source.

    Parameters
    ----------
    series_id : str
        Target series id.
    columns : dict[str, str]
        Logical field to source column mapping.
    source_reference : str
        Source reference written into points.
    note_columns : tuple[str, ...]
        Additional source columns appended to the point note.
    note_join : str
        Separator used when composing multiple note fragments.
    static_note : str | None
        Optional note fragment appended to every point.
    date_policy : str
        Date normalization policy.
    skip_invalid_dates : bool
        Whether rows with invalid dates are skipped.
    compound_column : str | None
        Column containing a compound textual value.
    compound_pattern : str | None
        Regular expression with named groups extracted from the compound value.
    """

    series_id: str
    columns: dict[str, str]
    source_reference: str
    note_columns: tuple[str, ...]
    note_join: str
    static_note: str | None
    date_policy: str
    skip_invalid_dates: bool
    compound_column: str | None
    compound_pattern: str | None


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


@dataclass(frozen=True)
class _ExtractState:
    """Represent per-extract row state during point construction.

    Parameters
    ----------
    previous_values : dict[tuple[int, str], Any]
        Previous field values used for fill-down.
    extract_index : int
        Extraction index in the source.
    """

    previous_values: dict[tuple[int, str], Any]
    extract_index: int


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
        for point in points:
            points_by_series[cast("str", point["series_id"])].append(point)
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

    Raises
    ------
    ConfigError
        If the manifest is invalid or references missing sources.
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
        for extract in source.extracts:
            if extract.series_id not in series_ids:
                _fail(
                    f"{path}: source {source.raw_path} referenzia "
                    f"series_id sconosciuto {extract.series_id}"
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
    extracts = _extracts_from_table(item, path, index)
    header_rows = _header_rows_from_table(item, path, index)
    return _SourceSpec(
        path=source_path,
        raw_path=raw_path,
        extracts=extracts,
        sheet=_optional_string(item, "sheet"),
        header_rows=header_rows,
        data_start_row=_optional_int(item, "data_start_row", path, index),
        fill_down=_optional_string_tuple(item, "fill_down", path, index),
        layout=_optional_string(item, "layout") or "table",
        matrix=_optional_table(item, "matrix", path, index),
    )


def _extracts_from_table(
    item: dict[str, Any],
    path: Path,
    index: int,
) -> tuple[_ExtractSpec, ...]:
    """Parse source extraction tables.

    Parameters
    ----------
    item : dict[str, Any]
        Raw source table.
    path : pathlib.Path
        Manifest path.
    index : int
        Source table index.

    Returns
    -------
    tuple[_ExtractSpec, ...]
        Parsed extraction specs.
    """

    raw_extracts = item.get("extract")
    if raw_extracts is None:
        return (_legacy_extract_from_table(item, path, index),)
    if not isinstance(raw_extracts, list):
        _fail(f"{path}: source {index} campo extract deve essere un array")
    return tuple(
        _extract_from_table(
            _table(raw, path, "source.extract", offset), item, path, index
        )
        for offset, raw in enumerate(raw_extracts)
    )


def _legacy_extract_from_table(
    item: dict[str, Any],
    path: Path,
    index: int,
) -> _ExtractSpec:
    """Parse a legacy source as one extraction.

    Parameters
    ----------
    item : dict[str, Any]
        Raw source table.
    path : pathlib.Path
        Manifest path.
    index : int
        Source table index.

    Returns
    -------
    _ExtractSpec
        Parsed extraction spec.
    """

    return _extract_from_table(item, item, path, index)


def _extract_from_table(
    item: dict[str, Any],
    source_item: dict[str, Any],
    path: Path,
    index: int,
) -> _ExtractSpec:
    """Parse one source extraction table.

    Parameters
    ----------
    item : dict[str, Any]
        Raw extraction table.
    source_item : dict[str, Any]
        Parent source table.
    path : pathlib.Path
        Manifest path.
    index : int
        Source table index.

    Returns
    -------
    _ExtractSpec
        Parsed extraction spec.
    """

    columns = item.get("columns")
    if not isinstance(columns, dict):
        _fail(f"{path}: source {index} deve contenere [source.columns]")
    compound = _optional_table(item, "compound_value", path, index)
    return _ExtractSpec(
        series_id=_required_string(item, "series_id", path, index),
        columns={str(key): str(value) for key, value in columns.items()},
        source_reference=(
            _optional_string(item, "source_reference")
            or _optional_string(source_item, "source_reference")
            or _required_string(source_item, "path", path, index)
        ),
        note_columns=_optional_string_tuple(item, "note_columns", path, index),
        note_join=_optional_string(item, "note_join") or "; ",
        static_note=_optional_string(item, "static_note"),
        date_policy=_optional_string(item, "date_policy") or "exact",
        skip_invalid_dates=_optional_bool(
            item,
            "skip_invalid_dates",
            default=False,
            path=path,
            index=index,
        ),
        compound_column=_optional_string(compound, "column"),
        compound_pattern=_optional_string(compound, "pattern"),
    )


def _header_rows_from_table(
    item: dict[str, Any],
    path: Path,
    index: int,
) -> tuple[int, ...]:
    """Return configured one-based header rows.

    Parameters
    ----------
    item : dict[str, Any]
        Raw source table.
    path : pathlib.Path
        Manifest path.
    index : int
        Source table index.

    Returns
    -------
    tuple[int, ...]
        Header row indexes.
    """

    raw_rows = item.get("header_rows")
    if raw_rows is not None:
        if not isinstance(raw_rows, list) or not raw_rows:
            _fail(f"{path}: source {index} campo header_rows non valido")
        return tuple(
            _positive_int(value, path, "header_rows", index) for value in raw_rows
        )
    header_row = _optional_int(item, "header_row", path, index)
    return (header_row or 1,)


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

    Raises
    ------
    ConfigError
        If the source format is unsupported or cannot be read.
    """

    suffix = source.path.suffix.lower()
    if suffix in CSV_SUFFIXES:
        with source.path.open(encoding="utf-8", newline="") as handle:
            raw_rows = [row for row in csv.reader(handle)]
        return _rows_to_dicts(source, raw_rows)
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
    return _rows_to_dicts(source, rows)


def _rows_to_dicts(source: _SourceSpec, rows: list[list[Any]]) -> list[dict[str, Any]]:
    """Convert raw table rows to dictionaries.

    Parameters
    ----------
    source : _SourceSpec
        Source specification.
    rows : list[list[Any]]
        Raw table rows.

    Returns
    -------
    list[dict[str, Any]]
        Rows keyed by header.
    """

    if source.layout == "repeating_matrix":
        return _read_repeating_matrix(source, rows)
    if source.layout != "table":
        _fail(f"layout osservazioni non supportato: {source.layout}")
    if not rows:
        return []
    headers = _headers_from_rows(rows, source.header_rows)
    start_row = source.data_start_row or max(source.header_rows) + 1
    return [
        {
            header: row[index] if index < len(row) else None
            for index, header in enumerate(headers)
            if header
        }
        for row in rows[start_row - 1 :]
    ]


def _headers_from_rows(
    rows: list[list[Any]], header_rows: tuple[int, ...]
) -> list[str]:
    """Build column headers from one or more worksheet rows.

    Parameters
    ----------
    rows : list[list[Any]]
        Raw worksheet rows.
    header_rows : tuple[int, ...]
        One-based header row indexes.

    Returns
    -------
    list[str]
        Header names by column.
    """

    max_index = max(header_rows) - 1
    if max_index >= len(rows):
        return []
    width = max((len(rows[row - 1]) for row in header_rows), default=0)
    carried_rows: list[list[str]] = []
    for row_number in header_rows:
        raw = rows[row_number - 1] if row_number - 1 < len(rows) else []
        carried: list[str] = []
        previous = ""
        for column in range(width):
            text = _text_value(raw[column] if column < len(raw) else None) or ""
            if text:
                previous = text
            carried.append(previous)
        carried_rows.append(carried)
    headers: list[str] = []
    for column in range(width):
        parts: list[str] = []
        for carried in carried_rows:
            part = carried[column]
            if part and part not in parts:
                parts.append(part)
        headers.append(" ".join(parts).strip() or f"column_{column + 1}")
    return headers


def _read_repeating_matrix(
    source: _SourceSpec,
    rows: list[list[Any]],
) -> list[dict[str, Any]]:
    """Read a repeating matrix source into row dictionaries.

    Parameters
    ----------
    source : _SourceSpec
        Source specification.
    rows : list[list[Any]]
        Raw worksheet rows.

    Returns
    -------
    list[dict[str, Any]]
        Matrix values normalized as row dictionaries.
    """

    if not rows:
        return []
    year = _required_int(source.matrix, "year", source.raw_path)
    month = _required_int(source.matrix, "start_month", source.raw_path)
    block_height = _optional_int(
        source.matrix, "block_height", Path(source.raw_path), 0
    )
    value_rows = _optional_string_tuple(
        source.matrix, "value_rows", Path(source.raw_path), 0
    )
    if not value_rows:
        _fail(f"{source.raw_path}: matrix.value_rows deve contenere almeno una riga")
    block_height = block_height or len(value_rows) + 1
    date_column_start = _required_int(
        source.matrix, "date_column_start", source.raw_path
    )
    value_column = _optional_string(source.matrix, "value_column") or "value"
    date_column = _optional_string(source.matrix, "date_column") or "Data"
    label_column = _optional_string(source.matrix, "label_column") or "label"
    normalized: list[dict[str, Any]] = []
    previous_day: int | None = None
    for block_start in range(0, len(rows), block_height):
        header = rows[block_start] if block_start < len(rows) else []
        block_days: list[tuple[int, int, date]] = []
        for column in range(date_column_start - 1, len(header)):
            day = _day_from_text(header[column])
            if day is None:
                continue
            if previous_day is not None and day < previous_day:
                month += 1
            previous_day = day
            block_days.append((column, day, date(year, month, day)))
        for offset, label in enumerate(value_rows, start=1):
            row_index = block_start + offset
            row = rows[row_index] if row_index < len(rows) else []
            for column, _day, observation_date in block_days:
                normalized.append(
                    {
                        date_column: observation_date,
                        label_column: label,
                        value_column: row[column] if column < len(row) else None,
                    }
                )
    return normalized


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

    Raises
    ------
    ConfigError
        If a row value cannot be normalized.
    """

    points: list[dict[str, Any]] = []
    previous_values: dict[tuple[int, str], Any] = {}
    for row_index, row in enumerate(rows, start=2):
        for extract_index, extract in enumerate(source.extracts):
            state = _ExtractState(
                previous_values=previous_values,
                extract_index=extract_index,
            )
            try:
                observation_date, date_note = _date_with_policy(
                    _mapped_value(source, extract, row, "date", state),
                    extract.date_policy,
                )
            except ConfigError:
                if extract.skip_invalid_dates:
                    continue
                raise
            if observation_date is None:
                continue
            point: dict[str, Any] = {
                "id": (
                    f"{_slug(extract.series_id)}-{observation_date}-"
                    f"{source_index + 1}-{extract_index + 1}-{row_index}"
                ),
                "series_id": extract.series_id,
                "observation_date": observation_date,
                "source_type": "spreadsheet",
                "source_reference": extract.source_reference,
            }
            compound = _compound_values(source, extract, row)
            for field in ("numeric_value", "systolic", "diastolic", "pulse"):
                raw_value = _mapped_value(source, extract, row, field, state)
                value = _number_value(
                    raw_value if raw_value is not None else compound.get(field)
                )
                if value is not None:
                    point[field] = value
            text_value = _text_value(
                _mapped_value(source, extract, row, "text_value", state)
                or _mapped_value(source, extract, row, "value", state)
                or compound.get("text_value")
                or compound.get("value")
            )
            if text_value is not None:
                point["text_value"] = text_value
            if not any(
                field in point
                for field in ("numeric_value", "systolic", "diastolic", "text_value")
            ):
                continue
            note = _point_note(source, extract, row, date_note)
            if note is not None:
                point["note"] = note
            points.append(point)
    return points


def _mapped_value(
    source: _SourceSpec,
    extract: _ExtractSpec,
    row: dict[str, Any],
    field: str,
    state: _ExtractState | None = None,
) -> Any:
    """Return a mapped row value.

    Parameters
    ----------
    source : _SourceSpec
        Source specification.
    extract : _ExtractSpec
        Extraction specification.
    row : dict[str, Any]
        Source row.
    field : str
        Logical field name.
    state : _ExtractState | None
        Optional per-extract state used for fill-down fields.

    Returns
    -------
    Any
        Mapped value or ``None``.
    """

    column = extract.columns.get(field)
    if column is None:
        return None
    value = row.get(column)
    if state is None:
        return value
    key = (state.extract_index, field)
    if value in (None, "") and field in source.fill_down:
        return state.previous_values.get(key)
    if value not in (None, ""):
        state.previous_values[key] = value
    return value


def _compound_values(
    source: _SourceSpec,
    extract: _ExtractSpec,
    row: dict[str, Any],
) -> dict[str, str]:
    """Return values parsed from a compound source column.

    Parameters
    ----------
    source : _SourceSpec
        Source specification.
    extract : _ExtractSpec
        Extraction specification.
    row : dict[str, Any]
        Source row.

    Returns
    -------
    dict[str, str]
        Named regex groups parsed from the compound value.
    """

    if extract.compound_column is None or extract.compound_pattern is None:
        return {}
    raw_value = _text_value(row.get(extract.compound_column))
    if raw_value is None:
        return {}
    match = re.search(extract.compound_pattern, raw_value)
    if match is None:
        _fail(
            f"{source.raw_path}: valore composto non valido per "
            f"{extract.compound_column}: {raw_value}"
        )
    return {key: value for key, value in match.groupdict().items() if value is not None}


def _point_note(
    source: _SourceSpec,
    extract: _ExtractSpec,
    row: dict[str, Any],
    date_note: str | None,
) -> str | None:
    """Compose the note for one imported point.

    Parameters
    ----------
    source : _SourceSpec
        Source specification.
    extract : _ExtractSpec
        Extraction specification.
    row : dict[str, Any]
        Source row.
    date_note : str | None
        Optional date normalization note.

    Returns
    -------
    str | None
        Composed note.
    """

    fragments: list[str] = []
    for value in (
        _text_value(row.get(column))
        for column in extract.note_columns
        if row.get(column) not in (None, "")
    ):
        if value is not None:
            fragments.append(value)
    mapped_note = _text_value(row.get(extract.columns.get("note", "")))
    if mapped_note is not None:
        fragments.append(mapped_note)
    if extract.static_note is not None:
        fragments.append(extract.static_note)
    if date_note is not None:
        fragments.append(date_note)
    if not fragments:
        return None
    return extract.note_join.join(fragments)


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


def _optional_int(
    item: dict[str, Any],
    field: str,
    path: Path,
    index: int,
) -> int | None:
    """Return an optional positive integer.

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
    int | None
        Parsed integer.
    """

    value = item.get(field)
    if value is None:
        return None
    return _positive_int(value, path, field, index)


def _required_int(item: dict[str, Any], field: str, source: str) -> int:
    """Return a required positive integer.

    Parameters
    ----------
    item : dict[str, Any]
        TOML table.
    field : str
        Field name.
    source : str
        Source label for diagnostics.

    Returns
    -------
    int
        Parsed integer.
    """

    value = item.get(field)
    if value is None:
        _fail(f"{source}: campo {field} obbligatorio")
    return _positive_int(value, Path(source), field, 0)


def _positive_int(value: Any, path: Path, field: str, index: int) -> int:
    """Return a positive integer value.

    Parameters
    ----------
    value : Any
        Raw value.
    path : pathlib.Path
        Source path.
    field : str
        Field name.
    index : int
        Table index.

    Returns
    -------
    int
        Parsed positive integer.
    """

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        _fail(f"{path}: elemento {index} campo {field} deve essere intero positivo")
    return value


def _optional_table(
    item: dict[str, Any],
    field: str,
    path: Path,
    index: int,
) -> dict[str, Any]:
    """Return an optional nested table.

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
    dict[str, Any]
        Parsed table or an empty mapping.
    """

    value = item.get(field, {})
    if not isinstance(value, dict):
        _fail(f"{path}: elemento {index} campo {field} deve essere tabella")
    return cast("dict[str, Any]", value)


def _optional_string_tuple(
    item: dict[str, Any],
    field: str,
    path: Path,
    index: int,
) -> tuple[str, ...]:
    """Return an optional list of strings as a tuple.

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
    tuple[str, ...]
        Parsed strings.
    """

    value = item.get(field, [])
    if value is None:
        return ()
    if not isinstance(value, list):
        _fail(f"{path}: elemento {index} campo {field} deve essere lista")
    result: list[str] = []
    for offset, item_value in enumerate(value):
        if not isinstance(item_value, str) or not item_value.strip():
            _fail(
                f"{path}: elemento {index} campo {field}[{offset}] deve essere stringa"
            )
        result.append(item_value.strip())
    return tuple(result)


def _date_with_policy(value: Any, policy: str) -> tuple[str | None, str | None]:
    """Return an ISO date and optional normalization note.

    Parameters
    ----------
    value : Any
        Raw cell value.
    policy : str
        Date normalization policy.

    Returns
    -------
    tuple[str | None, str | None]
        ISO date and optional note.
    """

    if policy == "exact":
        return _date_value(value), None
    text = _text_value(value)
    if text is None:
        return None, None
    if policy == "year_start":
        year = _year_from_text(text)
        if year is None:
            _fail(f"anno osservazione non valido: {text}")
        return f"{year:04d}-01-01", f"data approssimata: solo anno nel foglio ({text})"
    if policy == "period_start":
        year = _year_from_text(text)
        if year is None:
            _fail(f"periodo osservazione non valido: {text}")
        return (
            f"{year:04d}-01-01",
            f"data approssimata: inizio periodo nel foglio ({text})",
        )
    _fail(f"politica data osservazione non supportata: {policy}")
    return None, None


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


def _year_from_text(value: str) -> int | None:
    """Return the first four-digit year in text.

    Parameters
    ----------
    value : str
        Raw text value.

    Returns
    -------
    int | None
        Parsed year.
    """

    match = re.search(r"\b(19\d{2}|20\d{2})\b", value)
    if match is None:
        return None
    return int(match.group(1))


def _day_from_text(value: Any) -> int | None:
    """Return the first day-of-month number in text.

    Parameters
    ----------
    value : Any
        Raw cell value.

    Returns
    -------
    int | None
        Parsed day.
    """

    text = _text_value(value)
    if text is None:
        return None
    match = re.search(r"\b(\d{1,2})\b", text)
    if match is None:
        return None
    day = int(match.group(1))
    if not 1 <= day <= 31:
        return None
    return day


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
