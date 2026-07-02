"""Curated metadata loading for SaniKey."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING, Any, cast

from .errors import ConfigError
from .models import (
    ClinicalProblem,
    CuratedMetadata,
    Medication,
    Observation,
    Procedure,
    TherapyEpisode,
    TimelineEvent,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def load_curated_metadata(metadata_dir: Path) -> CuratedMetadata:
    """Load curated metadata files from a patient metadata directory.

    Parameters
    ----------
    metadata_dir : pathlib.Path
        Directory containing curated TOML files.

    Returns
    -------
    CuratedMetadata
        Parsed metadata. Missing optional files produce empty collections.

    Raises
    ------
    ConfigError
        If a present metadata file is malformed.
    """

    if not metadata_dir.exists():
        return CuratedMetadata()
    if not metadata_dir.is_dir():
        _fail(f"metadata path is not a directory: {metadata_dir}")

    return CuratedMetadata(
        problems=_load_items(
            metadata_dir / "problems.toml",
            "problem",
            _problem_from_table,
        ),
        medications=_load_items(
            metadata_dir / "medications.toml",
            "medication",
            _medication_from_table,
        ),
        therapies=_load_items(
            metadata_dir / "therapies.toml",
            "therapy",
            _therapy_from_table,
        ),
        procedures=_load_items(
            metadata_dir / "procedures.toml",
            "procedure",
            _procedure_from_table,
        ),
        observations=_load_items(
            metadata_dir / "observations.toml",
            "observation",
            _observation_from_table,
        ),
        timeline_events=_load_items(
            metadata_dir / "timeline_events.toml",
            "event",
            _timeline_event_from_table,
        ),
        document_tags=_load_document_tags(metadata_dir / "document_tags.toml"),
        clinical_summary=_load_summary(metadata_dir / "clinical_summary.toml"),
    )


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file or return an empty mapping when absent.

    Parameters
    ----------
    path : pathlib.Path
        File to load.

    Returns
    -------
    dict[str, Any]
        Parsed TOML mapping.

    Raises
    ------
    ConfigError
        If the file is present but invalid.
    """

    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        message = f"invalid TOML in {path}: {exc}"
        raise ConfigError(message) from exc
    if not isinstance(data, dict):
        _fail(f"metadata file must contain a table: {path}")
    return data


def _load_items[T](
    path: Path,
    key: str,
    factory: Callable[[dict[str, Any], Path, int], T],
) -> tuple[T, ...]:
    """Load an array-of-tables metadata collection.

    Parameters
    ----------
    path : pathlib.Path
        Metadata file path.
    key : str
        TOML array key.
    factory : callable[[dict[str, Any], pathlib.Path, int], T]
        Parser for each item table.

    Returns
    -------
    tuple[T, ...]
        Parsed items.
    """

    data = _load_toml(path)
    raw_items = data.get(key, [])
    if not isinstance(raw_items, list):
        _fail(f"{path}: {key} must be an array of tables")
    return tuple(
        factory(_require_table(item, path, index), path, index)
        for index, item in enumerate(raw_items)
    )


def _problem_from_table(
    item: dict[str, Any], path: Path, index: int
) -> ClinicalProblem:
    """Parse one clinical problem.

    Parameters
    ----------
    item : dict[str, Any]
        Raw item table.
    path : pathlib.Path
        Source file path.
    index : int
        Item index.

    Returns
    -------
    ClinicalProblem
        Parsed problem.
    """

    return ClinicalProblem(
        id=_required_string(item, "id", path, index),
        title=_required_string(item, "title", path, index),
        status=_optional_string(item, "status") or "unknown",
    )


def _medication_from_table(item: dict[str, Any], path: Path, index: int) -> Medication:
    """Parse one medication.

    Parameters
    ----------
    item : dict[str, Any]
        Raw item table.
    path : pathlib.Path
        Source file path.
    index : int
        Item index.

    Returns
    -------
    Medication
        Parsed medication.
    """

    return Medication(
        id=_required_string(item, "id", path, index),
        name=_required_string(item, "name", path, index),
        active_ingredient=_optional_string(item, "active_ingredient"),
        form=_optional_string(item, "form"),
        strength_per_unit=_optional_string(item, "strength_per_unit"),
    )


def _therapy_from_table(item: dict[str, Any], path: Path, index: int) -> TherapyEpisode:
    """Parse one therapy episode.

    Parameters
    ----------
    item : dict[str, Any]
        Raw item table.
    path : pathlib.Path
        Source file path.
    index : int
        Item index.

    Returns
    -------
    TherapyEpisode
        Parsed therapy episode.
    """

    return TherapyEpisode(
        id=_required_string(item, "id", path, index),
        medication_id=_required_string(item, "medication_id", path, index),
        start_date=_optional_string(item, "start_date"),
        end_date=_optional_string(item, "end_date"),
        dosage=_optional_string(item, "dosage"),
        schedule=_string_tuple(item.get("schedule", ()), path, "schedule", index),
        instructions=_optional_string(item, "instructions"),
    )


def _procedure_from_table(item: dict[str, Any], path: Path, index: int) -> Procedure:
    """Parse one procedure.

    Parameters
    ----------
    item : dict[str, Any]
        Raw item table.
    path : pathlib.Path
        Source file path.
    index : int
        Item index.

    Returns
    -------
    Procedure
        Parsed procedure.
    """

    return Procedure(
        id=_required_string(item, "id", path, index),
        title=_required_string(item, "title", path, index),
        date=_optional_string(item, "date"),
        status=_optional_string(item, "status") or "unknown",
    )


def _observation_from_table(
    item: dict[str, Any], path: Path, index: int
) -> Observation:
    """Parse one observation.

    Parameters
    ----------
    item : dict[str, Any]
        Raw item table.
    path : pathlib.Path
        Source file path.
    index : int
        Item index.

    Returns
    -------
    Observation
        Parsed observation.
    """

    return Observation(
        id=_required_string(item, "id", path, index),
        kind=_required_string(item, "kind", path, index),
        value=_required_string(item, "value", path, index),
        date=_optional_string(item, "date"),
    )


def _timeline_event_from_table(
    item: dict[str, Any], path: Path, index: int
) -> TimelineEvent:
    """Parse one manual timeline event.

    Parameters
    ----------
    item : dict[str, Any]
        Raw item table.
    path : pathlib.Path
        Source file path.
    index : int
        Item index.

    Returns
    -------
    TimelineEvent
        Parsed timeline event.
    """

    return TimelineEvent(
        id=_required_string(item, "id", path, index),
        title=_required_string(item, "title", path, index),
        start_date=_optional_string(item, "start_date"),
        end_date=_optional_string(item, "end_date"),
        source=_optional_string(item, "source") or "manual",
        links=_string_tuple(item.get("links", ()), path, "links", index),
    )


def _load_document_tags(path: Path) -> dict[str, tuple[str, ...]]:
    """Load document tags mapping.

    Parameters
    ----------
    path : pathlib.Path
        Tags TOML file.

    Returns
    -------
    dict[str, tuple[str, ...]]
        Tags keyed by document reference.
    """

    data = _load_toml(path)
    tags = data.get("tags", {})
    if not isinstance(tags, dict):
        _fail(f"{path}: tags must be a table")
    return {
        str(document): _string_tuple(value, path, f"tags.{document}", 0)
        for document, value in tags.items()
    }


def _load_summary(path: Path) -> str | None:
    """Load curated clinical summary text.

    Parameters
    ----------
    path : pathlib.Path
        Summary TOML file.

    Returns
    -------
    str | None
        Summary text when present.
    """

    data = _load_toml(path)
    if not data:
        return None
    summary = data.get("summary")
    if summary is None:
        return None
    if not isinstance(summary, str):
        _fail(f"{path}: summary must be a string")
    return cast("str", summary)


def _require_table(item: Any, path: Path, index: int) -> dict[str, Any]:
    """Return an item table or fail.

    Parameters
    ----------
    item : Any
        Raw TOML value.
    path : pathlib.Path
        Source file.
    index : int
        Item index.

    Returns
    -------
    dict[str, Any]
        Item table.
    """

    if not isinstance(item, dict):
        _fail(f"{path}: item {index} must be a table")
    return cast("dict[str, Any]", item)


def _required_string(item: dict[str, Any], field: str, path: Path, index: int) -> str:
    """Return a required non-empty string field.

    Parameters
    ----------
    item : dict[str, Any]
        Item table.
    field : str
        Field name.
    path : pathlib.Path
        Source file.
    index : int
        Item index.

    Returns
    -------
    str
        Non-empty field value.
    """

    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        _fail(f"{path}: item {index} field {field} must be a non-empty string")
    return cast("str", value).strip()


def _optional_string(item: dict[str, Any], field: str) -> str | None:
    """Return an optional string field.

    Parameters
    ----------
    item : dict[str, Any]
        Item table.
    field : str
        Field name.

    Returns
    -------
    str | None
        Stripped field value when present.
    """

    value = item.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        _fail(f"field {field} must be a string")
    return cast("str", value).strip()


def _string_tuple(value: Any, path: Path, field: str, index: int) -> tuple[str, ...]:
    """Return a tuple of strings.

    Parameters
    ----------
    value : Any
        Raw TOML value.
    path : pathlib.Path
        Source file.
    field : str
        Field name for diagnostics.
    index : int
        Item index.

    Returns
    -------
    tuple[str, ...]
        Parsed strings.
    """

    if not isinstance(value, list | tuple):
        _fail(f"{path}: item {index} field {field} must be a string array")
    if not all(isinstance(item, str) for item in value):
        _fail(f"{path}: item {index} field {field} must contain only strings")
    return tuple(item.strip() for item in value if item.strip())


def _fail(message: str) -> None:
    """Raise a metadata configuration error.

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
