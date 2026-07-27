"""Deterministic generated artefacts for longitudinal parameter slices."""

from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from .parameter_rules import ParameterBuildResult
    from .parameter_slices import CandidateGroup, DiscoveryResult


def write_parameter_reports(
    build_root: Path,
    discovery: DiscoveryResult,
    result: ParameterBuildResult | None = None,
) -> tuple[Path, Path | None, Path | None, Path | None]:
    """Write deterministic parameter reports and static slice exports.

    Parameters
    ----------
    build_root : pathlib.Path
        Patient generated-artifact root.
    discovery : sanikey.parameter_slices.DiscoveryResult
        Deterministic discovery result.
    result : sanikey.parameter_rules.ParameterBuildResult | None, optional
        Curated rule result when rules have been applied.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path | None, pathlib.Path | None, pathlib.Path | None]
        Candidate report, extraction report, JSON export, and JavaScript export.
    """

    reports = build_root / "reports"
    exports = build_root / "exports"
    data = build_root / "web" / "data"
    reports.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    candidates = reports / "parameter-candidates.json"
    _write_json(
        candidates,
        {
            "schema_version": "1.0",
            "analyzed_lines": discovery.analyzed_lines,
            "candidates": discovery.candidates,
            "groups": discovery.proposed_groups,
        },
    )
    proposal = reports / "parameter-rules.proposed.toml"
    proposal.write_text(
        _render_proposed_rules(discovery.proposed_groups),
        encoding="utf-8",
    )
    if result is None:
        return candidates, None, None, None
    extraction = reports / "parameter-extraction.json"
    export = exports / "parameter-slices.json"
    script = data / "parameter-slices.js"
    payload = {
        "schema_version": "1.0",
        "series": result.series,
        "points": result.points,
        "decisions": result.decisions,
    }
    _write_json(extraction, {"schema_version": "1.0", "decisions": result.decisions})
    _write_json(export, payload)
    script.write_text(
        "window.SANIKEY_PARAMETER_SLICES = "
        + json.dumps(
            _json_value(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + ";\n",
        encoding="utf-8",
    )
    return candidates, extraction, export, script


def _render_proposed_rules(groups: tuple[CandidateGroup, ...]) -> str:
    """Render disabled curator-review rule templates in deterministic TOML.

    Parameters
    ----------
    groups : tuple[sanikey.parameter_slices.CandidateGroup, ...]
        Exact-label candidate groups that passed the discovery thresholds.

    Returns
    -------
    str
        TOML proposal content that never enables or applies a rule.
    """

    lines = [
        "# Proposte determinate: revisionare prima di copiare in parameters.toml.",
        "# Nessuna regola qui generata e' abilitata automaticamente.",
    ]
    for group in groups:
        candidates = group.candidates
        formats = sorted(
            {
                candidate.number_format
                for candidate in candidates
                if candidate.number_format
            }
        )
        units = sorted(
            {candidate.raw_unit for candidate in candidates if candidate.raw_unit}
        )
        value_type = (
            "qualified-scalar"
            if any(candidate.qualifier for candidate in candidates)
            else "scalar"
        )
        label = json.dumps(group.normalized_label, ensure_ascii=False)
        display_name = json.dumps(group.normalized_label.title(), ensure_ascii=False)
        lines.extend(
            (
                "",
                f"# occorrenze={len(candidates)} documenti={group.distinct_documents} "
                f"date={group.distinct_dates}",
                f"[parameters.{label}]",
                f"display_name = {display_name}",
                f"term = {label}",
                "version = 1",
                f'value_type = "{value_type}"',
                "number_formats = " + _toml_strings(formats),
                'unit_policy = "required"',
                "enabled = false",
            )
        )
        if units:
            lines.append("units = " + _toml_strings(units))
    return "\n".join(lines) + "\n"


def _toml_strings(values: list[str]) -> str:
    """Render a TOML string array without relying on an output timestamp.

    Parameters
    ----------
    values : list[str]
        Already deterministically sorted string values.

    Returns
    -------
    str
        TOML-compatible basic-string array.
    """

    return (
        "[" + ", ".join(json.dumps(value, ensure_ascii=False) for value in values) + "]"
    )


def _write_json(path: Path, value: Any) -> None:
    """Write one canonical JSON artefact.

    Parameters
    ----------
    path : pathlib.Path
        Output file path.
    value : Any
        JSON-compatible or dataclass-backed value.

    Returns
    -------
    None
    """

    path.write_text(
        json.dumps(_json_value(value), ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _json_value(value: Any) -> Any:
    """Convert dataclasses and decimals to canonical JSON values.

    Parameters
    ----------
    value : Any
        Value to serialize.

    Returns
    -------
    Any
        JSON-compatible deterministic representation.
    """

    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value
