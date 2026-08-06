"""Deterministic generated artefacts for longitudinal parameter slices."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from .parameter_rules import ParameterBuildResult, ParameterRules
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
    export, script = write_parameter_extraction_reports(build_root, result)
    return candidates, None, export, script


def write_parameter_extraction_reports(
    build_root: Path,
    result: ParameterBuildResult,
) -> tuple[Path, Path]:
    """Write only the reports and exports from configured parameter rules.

    Parameters
    ----------
    build_root : pathlib.Path
        Patient generated-artifact root.
    result : sanikey.parameter_rules.ParameterBuildResult
        Curated rule result to export.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path, pathlib.Path]
        JSON export and JavaScript export.
    """

    reports = build_root / "reports"
    exports = build_root / "exports"
    data = build_root / "web" / "data"
    reports.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    export = exports / "parameter-slices.json"
    script = data / "parameter-slices.js"
    payload = {
        "schema_version": "1.0",
        "series": result.series,
        "points": result.points,
        "decisions": result.decisions,
    }
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
    return export, script


def write_parameter_rejections(
    build_root: Path,
    discovery: DiscoveryResult,
    result: ParameterBuildResult,
    extra: tuple[dict[str, object], ...] = (),
) -> tuple[Path, Path]:
    """Write local machine- and human-readable rejected-parameter diagnostics.

    Parameters
    ----------
    build_root : pathlib.Path
        Patient generated-artifact root.
    discovery : sanikey.parameter_slices.DiscoveryResult
        Candidates with document provenance.
    result : sanikey.parameter_rules.ParameterBuildResult
        Rule decisions to filter for rejected candidates.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path]
        JSON and tabular text reports, both local-only build artefacts.
    """

    reports = build_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    candidates = {item.stable_id: item for item in discovery.candidates}
    rows: list[dict[str, object]] = [
        {
            "candidate_id": decision.candidate_id,
            "parameter": decision.rule_id,
            "document": candidate.document_name,
            "line": candidate.line_number,
            "page": candidate.page_number,
            "page_label": candidate.page_label,
            "context": candidate.context,
            "value": candidate.raw_value,
            "reason_code": decision.reason_code,
        }
        for decision in result.decisions
        if (candidate := candidates.get(decision.candidate_id))
    ]
    rows.extend(
        {
            "page": None,
            "page_label": "non disponibile",
            "context": "",
            **row,
        }
        for row in extra
    )
    accepted = [row for row in rows if str(row["reason_code"]).startswith("ACCEPTED_")]
    rejected = [
        row for row in rows if not str(row["reason_code"]).startswith("ACCEPTED_")
    ]
    accepted_json, accepted_text = _write_parameter_decision_report(
        reports, "accepted", accepted
    )
    rejected_json, rejected_text = _write_parameter_decision_report(
        reports, "rejected", rejected
    )
    return rejected_json, rejected_text


def write_parameter_reconciliation(
    build_root: Path,
    discovery: DiscoveryResult,
    result: ParameterBuildResult,
    rules: ParameterRules,
) -> tuple[Path, Path]:
    """Write per-parameter coverage reconciliation diagnostics.

    Parameters
    ----------
    build_root : pathlib.Path
        Patient generated-artifact root.
    discovery : sanikey.parameter_slices.DiscoveryResult
        Configured-label mentions and syntactic candidates.
    result : sanikey.parameter_rules.ParameterBuildResult
        Curated rule decisions.
    rules : sanikey.parameter_rules.ParameterRules
        Enabled rules used for candidate evaluation.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path]
        JSON and tabular text reconciliation report paths.
    """

    reports = build_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    occurrences = dict(discovery.recognized_label_occurrences)
    rows: list[dict[str, object]] = []
    for rule in rules.rules:
        if not rule.enabled:
            continue
        candidates = [
            item
            for item in discovery.candidates
            if item.normalized_label in rule.synonyms
        ]
        decisions = [item for item in result.decisions if item.rule_id == rule.id]
        accepted = [item for item in decisions if item.accepted]
        substantive_rejections = [
            item
            for item in decisions
            if not item.accepted and item.reason_code != "REJECTED_LABEL"
        ]
        label_mentions = sum(occurrences.get(label, 0) for label in rule.synonyms)
        rows.append(
            {
                "parameter": rule.id,
                "raw_label_mentions": label_mentions,
                "structured_candidates": len(candidates),
                "unmatched_label_mentions": max(label_mentions - len(candidates), 0),
                "accepted": len(accepted),
                "substantive_rejected": len(substantive_rejections),
                "label_rejections": len(decisions)
                - len(accepted)
                - len(substantive_rejections),
            }
        )
    rows.sort(key=lambda item: str(item["parameter"]))
    json_path = reports / "parameter-reconciliation.json"
    text_path = reports / "parameter-reconciliation.txt"
    _write_json(json_path, {"schema_version": "1.0", "parameters": rows})
    headings = (
        "Parametro",
        "Etichette grezze",
        "Candidati",
        "Etichette senza candidato",
        "Accettati",
        "Rifiuti sostanziali",
        "Rifiuti etichetta",
    )
    values = [
        headings,
        *[
            (
                row["parameter"],
                row["raw_label_mentions"],
                row["structured_candidates"],
                row["unmatched_label_mentions"],
                row["accepted"],
                row["substantive_rejected"],
                row["label_rejections"],
            )
            for row in rows
        ],
    ]
    widths = [
        max(len(str(row[index])) for row in values) for index in range(len(headings))
    ]
    text_path.write_text(
        "\n".join(
            " | ".join(str(cell).ljust(widths[index]) for index, cell in enumerate(row))
            for row in values
        )
        + "\n",
        encoding="utf-8",
    )
    return json_path, text_path


def _write_parameter_decision_report(
    reports: Path, status: str, rows: list[dict[str, object]]
) -> tuple[Path, Path]:
    """Write one machine- and human-readable parameter decision report.

    Parameters
    ----------
    reports : pathlib.Path
        Local reports directory.
    status : str
        Decision status, either ``accepted`` or ``rejected``.
    rows : list[dict[str, object]]
        Render-ready decision rows.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path]
        JSON and text report paths.
    """

    json_path = reports / f"parameter-{status}.json"
    text_path = reports / f"parameter-{status}.txt"
    _write_json(json_path, {"schema_version": "1.0", status: rows})
    headings = (
        "Parametro",
        "Documento",
        "Pagina",
        "Riga",
        "Valore",
        "Contesto",
        "Ragione",
    )
    values = [
        headings,
        *[
            (
                row["parameter"],
                row["document"],
                row["page_label"],
                str(row["line"]),
                row["value"],
                row["context"],
                row["reason_code"],
            )
            for row in rows
        ],
    ]
    widths = [
        max(len(str(row[index])) for row in values) for index in range(len(headings))
    ]
    text_path.write_text(
        "\n".join(
            " | ".join(str(cell).ljust(widths[index]) for index, cell in enumerate(row))
            for row in values
        )
        + "\n",
        encoding="utf-8",
    )
    return json_path, text_path


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
        f'generated_at = "{datetime.now().astimezone().isoformat(timespec="seconds")}"',
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
