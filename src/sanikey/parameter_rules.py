"""Curated rules for deterministic longitudinal parameter slices."""

# ruff: noqa: EM102, TRY003

from __future__ import annotations

import hashlib
import json
import tomllib
import unicodedata
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from .errors import ConfigError
from .models import CuratedMetadata, ObservationPoint, ObservationSeries
from .parameter_slices import DiscoverySettings, ParameterCandidate, normalize_label

if TYPE_CHECKING:
    from pathlib import Path

    from .config import SearchDictionary


_FORMATS = {
    "integer",
    "decimal-comma",
    "decimal-point",
    "grouped-comma-decimal-point",
    "grouped-point-decimal-comma",
}
_POLICIES = {"required", "allowed-but-unknown", "assume-configured-unit"}
_TYPES = {"scalar", "qualified-scalar"}
_SCALAR_VALUE_TYPES = frozenset({"numeric", "scalar", "qualified-scalar"})


@dataclass(frozen=True)
class UnitConversion:
    """Represent an explicit affine unit conversion.

    Parameters
    ----------
    from_unit : str
        Source unit.
    to_unit : str
        Normalized output unit.
    multiplier : Decimal
        Multiplication factor.
    offset : Decimal
        Additive factor.
    version : int
        Curator-declared conversion version.
    """

    from_unit: str
    to_unit: str
    multiplier: Decimal
    offset: Decimal
    version: int


@dataclass(frozen=True)
class ParameterRule:
    """Represent one resolved curator-approved recognition rule.

    Parameters
    ----------
    id : str
        Stable parameter identifier.
    display_name : str
        User-facing parameter name.
    synonyms : tuple[str, ...]
        Exact normalized labels accepted by this rule.
    version : int
        Curator-declared rule version.
    value_type : str
        Supported point type.
    number_formats : tuple[str, ...]
        Accepted numeric formats.
    unit_policy : str
        Missing-unit policy.
    enabled : bool
        Whether the rule can create points.
    series_id : str
        Canonical observation-series id.
    units : tuple[str, ...]
        Accepted units.
    canonical_unit : str | None
        Target unit after conversion.
    assumed_unit : str | None
        Explicit unit for missing-unit assumption.
    minimum : Decimal | None
        Inclusive plausible minimum.
    maximum : Decimal | None
        Inclusive plausible maximum.
    document_categories : tuple[str, ...]
        Accepted normalized categories.
    required_context : tuple[str, ...]
        Required normalized same-line text.
    excluded_context : tuple[str, ...]
        Rejected normalized same-line text.
    conversions : tuple[UnitConversion, ...]
        Explicit allowed conversions.
    specimen : str | None
        Required biological specimen when configured.
    default_specimen_labels : tuple[str, ...]
        Labels allowed to use the configured specimen without explicit evidence.
    digest : str
        Resolved rule contract digest.
    """

    id: str
    display_name: str
    synonyms: tuple[str, ...]
    version: int
    value_type: str
    number_formats: tuple[str, ...]
    unit_policy: str
    enabled: bool
    series_id: str
    units: tuple[str, ...]
    canonical_unit: str | None
    assumed_unit: str | None
    minimum: Decimal | None
    maximum: Decimal | None
    document_categories: tuple[str, ...]
    required_context: tuple[str, ...]
    excluded_context: tuple[str, ...]
    conversions: tuple[UnitConversion, ...]
    specimen: str | None
    default_specimen_labels: tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class ParameterRules:
    """Contain discovery configuration and deterministic parameter rules.

    Parameters
    ----------
    discovery : DiscoverySettings
        Generic candidate-discovery configuration.
    rules : tuple[ParameterRule, ...]
        Curator-approved rules in identifier order.
    """

    discovery: DiscoverySettings
    rules: tuple[ParameterRule, ...]


@dataclass(frozen=True)
class RuleDecision:
    """Explain a rule evaluation.

    Parameters
    ----------
    candidate_id : str
        Candidate identity.
    rule_id : str
        Evaluated rule id.
    accepted : bool
        Whether the rule accepted the candidate.
    reason_code : str
        Stable decision reason.
    """

    candidate_id: str
    rule_id: str
    accepted: bool
    reason_code: str


@dataclass(frozen=True)
class ParameterBuildResult:
    """Contain derived series, points, and rule decisions.

    Parameters
    ----------
    series : tuple[ObservationSeries, ...]
        Derived series.
    points : tuple[ObservationPoint, ...]
        Derived document-extraction points.
    decisions : tuple[RuleDecision, ...]
        Explainable rule decisions.
    """

    series: tuple[ObservationSeries, ...]
    points: tuple[ObservationPoint, ...]
    decisions: tuple[RuleDecision, ...]


def load_parameter_rules(path: Path, dictionary: SearchDictionary) -> ParameterRules:
    """Load parameters TOML using the configured search dictionary.

    Parameters
    ----------
    path : pathlib.Path
        Curated parameter-rule path.
    dictionary : sanikey.config.SearchDictionary
        Resolved search dictionary.

    Returns
    -------
    ParameterRules
        Validated settings and resolved rules.

    Raises
    ------
    ConfigError
        If the configuration is malformed.
    """

    if not path.exists():
        return ParameterRules(DiscoverySettings(), ())
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        message = f"TOML non valido in {path}: {exc}"
        raise ConfigError(message) from exc
    if not isinstance(data, dict) or set(data) - {"discovery", "parameters"}:
        raise ConfigError(f"file parametri non valido: {path}")
    discovery = _discovery(data.get("discovery", {}), path)
    raw_rules = data.get("parameters", {})
    if not isinstance(raw_rules, dict):
        raise ConfigError(f"{path} parameters deve essere una tabella")
    return ParameterRules(
        discovery,
        tuple(
            _rule(rule_id, raw, dictionary, path)
            for rule_id, raw in sorted(raw_rules.items())
        ),
    )


def load_patient_parameter_rules(
    common_path: Path,
    patient_path: Path,
    dictionary: SearchDictionary,
) -> ParameterRules:
    """Load mandatory common rules and complete or replace them per patient.

    Parameters
    ----------
    common_path : pathlib.Path
        Mandatory common ``parameters.toml`` path.
    patient_path : pathlib.Path
        Optional patient-specific complement and override path.
    dictionary : sanikey.config.SearchDictionary
        Resolved search dictionary.

    Returns
    -------
    ParameterRules
        Common rules with same-id patient rules fully replaced.

    Raises
    ------
    ConfigError
        If the common rule file is absent.
    """

    if not common_path.is_file():
        raise ConfigError(f"regole parametri comuni assenti: {common_path}")
    common = load_parameter_rules(common_path, dictionary)
    patient = load_parameter_rules(patient_path, dictionary)
    merged = {rule.id: rule for rule in common.rules}
    merged.update({rule.id: rule for rule in patient.rules})
    return ParameterRules(
        patient.discovery if _has_discovery(patient_path) else common.discovery,
        tuple(merged[key] for key in sorted(merged)),
    )


def _has_discovery(path: Path) -> bool:
    """Return whether a parameter TOML explicitly declares discovery settings.

    Parameters
    ----------
    path : pathlib.Path
        Parameter TOML file to inspect.

    Returns
    -------
    bool
        Whether the top-level ``discovery`` table is present.
    """

    if not path.is_file():
        return False
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return False
    return isinstance(data, dict) and "discovery" in data


def build_parameter_slices(
    candidates: tuple[ParameterCandidate, ...],
    rules: ParameterRules,
) -> ParameterBuildResult:
    """Apply enabled rules without silently resolving ambiguous matches.

    Parameters
    ----------
    candidates : tuple[ParameterCandidate, ...]
        Deterministic discovery candidates.
    rules : ParameterRules
        Curated parameter rules.

    Returns
    -------
    ParameterBuildResult
        Derived points, series, and diagnostics.
    """

    decisions: list[RuleDecision] = []
    accepted: list[
        tuple[ParameterCandidate, ParameterRule, Decimal, str | None, str]
    ] = []
    for candidate in candidates:
        matches: list[tuple[ParameterRule, Decimal, str | None, str]] = []
        for rule in rules.rules:
            if rule.enabled:
                evaluation = _evaluate(candidate, rule)
                if isinstance(evaluation, RuleDecision):
                    decisions.append(evaluation)
                else:
                    matches.append((rule, *evaluation))
        if len(matches) == 1:
            rule, value, unit, reason = matches[0]
            decisions.append(RuleDecision(candidate.stable_id, rule.id, True, reason))
            accepted.append((candidate, rule, value, unit, reason))
        elif len(matches) > 1:
            decisions.extend(
                RuleDecision(
                    candidate.stable_id,
                    item[0].id,
                    False,
                    "REJECTED_MULTIPLE_RULE_MATCHES",
                )
                for item in matches
            )
    points = tuple(
        _point(candidate, rule, value, unit, reason)
        for candidate, rule, value, unit, reason in accepted
    )
    by_rule = {rule.id: rule for rule in rules.rules}
    series = _series(points, by_rule)
    return ParameterBuildResult(
        series=series,
        points=tuple(
            sorted(
                points,
                key=lambda item: (item.series_id, item.observation_date, item.id),
            )
        ),
        decisions=tuple(
            sorted(
                decisions,
                key=lambda item: (item.candidate_id, item.rule_id, item.reason_code),
            )
        ),
    )


def merge_parameter_observations(
    metadata: CuratedMetadata,
    result: ParameterBuildResult,
) -> CuratedMetadata:
    """Integrate compatible derived parameters into imported named series.

    Parameters
    ----------
    metadata : CuratedMetadata
        Existing curated metadata.
    result : ParameterBuildResult
        Derived parameter output.

    Returns
    -------
    CuratedMetadata
        Metadata including derived observations.

    Raises
    ------
    ConfigError
        If a series id conflicts with incompatible curated fields or a
        same-name integration has more than one compatible target.
    """

    existing = {item.id: item for item in metadata.observation_series}
    additions: list[ObservationSeries] = []
    replacements: dict[str, str] = {}
    for series in result.series:
        old = existing.get(series.id)
        if old is None:
            targets = _same_name_series(metadata.observation_series, series)
            if len(targets) == 1:
                replacements[series.id] = targets[0].id
            elif len(targets) > 1:
                raise ConfigError(
                    f"serie osservazioni ambigua per parametro: {series.name}"
                )
            else:
                additions.append(series)
        elif not _series_compatible(old, series):
            raise ConfigError(
                f"serie osservazioni incompatibile per parametro: {series.id}"
            )
    return replace(
        metadata,
        observation_series=tuple((*metadata.observation_series, *additions)),
        observation_points=tuple(
            (
                *metadata.observation_points,
                *(
                    replace(
                        point,
                        series_id=replacements.get(point.series_id, point.series_id),
                    )
                    for point in result.points
                ),
            )
        ),
    )


def _same_name_series(
    existing: tuple[ObservationSeries, ...],
    derived: ObservationSeries,
) -> tuple[ObservationSeries, ...]:
    """Return existing series compatible with a derived series name.

    Parameters
    ----------
    existing : tuple[sanikey.models.ObservationSeries, ...]
        Existing imported or curated observation series.
    derived : sanikey.models.ObservationSeries
        Derived parameter series seeking an integration target.

    Returns
    -------
    tuple[sanikey.models.ObservationSeries, ...]
        Compatible existing series with the same normalized display name.
    """

    normalized_name = normalize_label(derived.name)
    return tuple(
        item
        for item in existing
        if normalize_label(item.name) == normalized_name
        and _series_compatible(item, derived)
    )


def _series_compatible(
    left: ObservationSeries,
    right: ObservationSeries,
) -> bool:
    """Check whether two observation series can share one point collection.

    Parameters
    ----------
    left : sanikey.models.ObservationSeries
        First series.
    right : sanikey.models.ObservationSeries
        Second series.

    Returns
    -------
    bool
        Whether value type and normalized units are compatible.

    Notes
    -----
    Derived points are already converted by their parameter rule before this
    comparison.  This function therefore accepts typography-only unit variants
    but does not infer a clinical conversion.
    """

    return _value_types_compatible(
        left.value_type, right.value_type
    ) and _units_compatible(left.unit, right.unit)


def _value_types_compatible(left: str, right: str) -> bool:
    """Check whether two observation value types have the same chart semantics.

    Parameters
    ----------
    left : str
        First observation value type.
    right : str
        Second observation value type.

    Returns
    -------
    bool
        Whether both types are scalar numeric variants or are exactly equal.

    Notes
    -----
    ``numeric``, ``scalar``, and ``qualified-scalar`` all use the numeric
    point representation.  Blood pressure remains distinct because it stores
    separate systolic and diastolic components.
    """

    return left == right or {left, right}.issubset(_SCALAR_VALUE_TYPES)


def _units_compatible(left: str | None, right: str | None) -> bool:
    """Compare optional measurement units without case sensitivity.

    Parameters
    ----------
    left : str | None
        First optional unit.
    right : str | None
        Second optional unit.

    Returns
    -------
    bool
        Whether both units are absent or have the same normalized key.
    """

    if left is None or right is None:
        return left is right
    return _unit_key(left) == _unit_key(right)


def _discovery(value: Any, path: Path) -> DiscoverySettings:
    """Parse optional discovery limits.

    Parameters
    ----------
    value : Any
        Raw TOML discovery table.
    path : pathlib.Path
        Source path for diagnostics.

    Returns
    -------
    DiscoverySettings
        Validated settings.

    Raises
    ------
    ConfigError
        If the discovery configuration is malformed.
    """

    if not isinstance(value, dict):
        raise ConfigError(f"{path} discovery deve essere una tabella")
    allowed = {
        "min_label_length",
        "max_label_length",
        "max_label_words",
        "min_occurrences",
        "min_distinct_documents",
        "min_distinct_dates",
        "excluded_labels",
    }
    if set(value) - allowed:
        raise ConfigError(f"{path} discovery contiene campi sconosciuti")
    try:
        return DiscoverySettings(
            min_label_length=_positive(value, "min_label_length", 2, path),
            max_label_length=_positive(value, "max_label_length", 80, path),
            max_label_words=_positive(value, "max_label_words", 8, path),
            min_occurrences=_positive(value, "min_occurrences", 2, path),
            min_distinct_documents=_positive(value, "min_distinct_documents", 2, path),
            min_distinct_dates=_positive(value, "min_distinct_dates", 1, path),
            excluded_labels=_strings(
                value.get("excluded_labels", []), path, "excluded_labels"
            ),
        )
    except ValueError as exc:
        raise ConfigError(f"{path} discovery non valida: {exc}") from exc


def _rule(
    rule_id: str, value: Any, dictionary: SearchDictionary, path: Path
) -> ParameterRule:
    """Parse and resolve a single rule.

    Parameters
    ----------
    rule_id : str
        Canonical rule identifier.
    value : Any
        Raw TOML table.
    dictionary : sanikey.config.SearchDictionary
        Search dictionary with accepted synonyms.
    path : pathlib.Path
        Source path.

    Returns
    -------
    ParameterRule
        Resolved rule.

    Raises
    ------
    ConfigError
        If the rule is malformed.
    """

    if not isinstance(value, dict):
        raise ConfigError(f"{path} parameters.{rule_id} deve essere una tabella")
    required = {
        "display_name",
        "term",
        "version",
        "value_type",
        "number_formats",
        "unit_policy",
        "enabled",
    }
    optional = {
        "series_id",
        "units",
        "canonical_unit",
        "assumed_unit",
        "minimum",
        "maximum",
        "document_categories",
        "required_context",
        "excluded_context",
        "conversions",
        "specimen",
        "default_specimen_labels",
    }
    if set(value) - required - optional or not required.issubset(value):
        raise ConfigError(f"{path} parameters.{rule_id} campi non validi")
    term = _string(value["term"], path, "term")
    synonyms = dictionary.terms.get(term)
    if synonyms is None:
        raise ConfigError(f"{path} parameters.{rule_id} term non presente: {term}")
    formats = _strings(value["number_formats"], path, "number_formats")
    if not formats or set(formats) - _FORMATS:
        raise ConfigError(f"{path} parameters.{rule_id} number_formats non validi")
    policy = _string(value["unit_policy"], path, "unit_policy")
    if policy not in _POLICIES:
        raise ConfigError(f"{path} parameters.{rule_id} unit_policy non supportata")
    value_type = _string(value["value_type"], path, "value_type")
    if value_type not in _TYPES:
        raise ConfigError(f"{path} parameters.{rule_id} value_type non supportato")
    enabled = value["enabled"]
    if not isinstance(enabled, bool):
        raise ConfigError(f"{path} parameters.{rule_id} enabled deve essere booleano")
    assumed = _optional_string(value.get("assumed_unit"), path, "assumed_unit")
    if policy == "assume-configured-unit" and assumed is None:
        raise ConfigError(f"{path} parameters.{rule_id} richiede assumed_unit")
    minimum = _decimal(value.get("minimum"), path, "minimum")
    maximum = _decimal(value.get("maximum"), path, "maximum")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ConfigError(f"{path} parameters.{rule_id} minimum supera maximum")
    raw: dict[str, Any] = {
        "id": rule_id,
        "display_name": _string(value["display_name"], path, "display_name"),
        "synonyms": tuple(
            sorted(
                {normalize_label(term), *(normalize_label(item) for item in synonyms)}
            )
        ),
        "version": _positive(value, "version", None, path),
        "value_type": value_type,
        "number_formats": tuple(sorted(formats)),
        "unit_policy": policy,
        "enabled": enabled,
        "series_id": _optional_string(value.get("series_id"), path, "series_id")
        or rule_id,
        "units": tuple(
            sorted(
                _unit(item) for item in _strings(value.get("units", []), path, "units")
            )
        ),
        "canonical_unit": _optional_unit(
            value.get("canonical_unit"), path, "canonical_unit"
        ),
        "assumed_unit": _unit(assumed) if assumed else None,
        "minimum": minimum,
        "maximum": maximum,
        "document_categories": tuple(
            sorted(
                normalize_label(item)
                for item in _strings(
                    value.get("document_categories", []), path, "document_categories"
                )
            )
        ),
        "required_context": tuple(
            sorted(
                normalize_label(item)
                for item in _strings(
                    value.get("required_context", []), path, "required_context"
                )
            )
        ),
        "excluded_context": tuple(
            sorted(
                normalize_label(item)
                for item in _strings(
                    value.get("excluded_context", []), path, "excluded_context"
                )
            )
        ),
        "conversions": _conversions(value.get("conversions", []), path, rule_id),
        "specimen": _optional_string(value.get("specimen"), path, "specimen"),
        "default_specimen_labels": tuple(
            sorted(
                normalize_label(item)
                for item in _strings(
                    value.get("default_specimen_labels", []),
                    path,
                    "default_specimen_labels",
                )
            )
        ),
    }
    digest = hashlib.sha256(_canonical(raw).encode("utf-8")).hexdigest()
    return ParameterRule(**raw, digest=digest)


def _evaluate(
    candidate: ParameterCandidate, rule: ParameterRule
) -> RuleDecision | tuple[Decimal, str | None, str]:
    """Evaluate one candidate against one rule.

    Parameters
    ----------
    candidate : ParameterCandidate
        Candidate to evaluate.
    rule : ParameterRule
        Curated rule.

    Returns
    -------
    RuleDecision | tuple[Decimal, str | None, str]
        Rejection or normalized accepted data.
    """

    if candidate.normalized_label not in rule.synonyms:
        return _reject(candidate, rule, "REJECTED_LABEL")
    acceptance_reason = "ACCEPTED_CONFIGURED_SYNONYM"
    if rule.specimen:
        explicit = (
            "serum"
            if candidate.normalized_label.startswith("s-")
            else "urine"
            if candidate.normalized_label.startswith("u-")
            else None
        )
        observed = explicit or candidate.section_specimen
        if observed and observed != rule.specimen:
            return _reject(candidate, rule, "REJECTED_SPECIMEN_MISMATCH")
        if observed is None:
            if candidate.normalized_label not in rule.default_specimen_labels:
                return _reject(candidate, rule, "REJECTED_SPECIMEN_AMBIGUOUS")
            acceptance_reason = "ACCEPTED_DEFAULT_SPECIMEN"
    if (
        candidate.parsed_value is None
        or candidate.number_format not in rule.number_formats
    ):
        return _reject(
            candidate, rule, candidate.reason_code or "REJECTED_NUMBER_FORMAT"
        )
    if candidate.qualifier and rule.value_type != "qualified-scalar":
        return _reject(candidate, rule, "REJECTED_QUALIFIER_UNSUPPORTED")
    if candidate.document_date is None:
        return _reject(candidate, rule, "REJECTED_DOCUMENT_DATE_MISSING")
    if (
        rule.document_categories
        and normalize_label(candidate.document_category) not in rule.document_categories
    ):
        return _reject(candidate, rule, "REJECTED_DOCUMENT_CATEGORY")
    line = normalize_label(candidate.original_line)
    if any(item not in line for item in rule.required_context):
        return _reject(candidate, rule, "REJECTED_REQUIRED_CONTEXT_MISSING")
    if any(item in line for item in rule.excluded_context):
        return _reject(candidate, rule, "REJECTED_EXCLUDED_CONTEXT")
    unit, value, reason = _value_and_unit(candidate, rule)
    if reason:
        return _reject(candidate, rule, reason)
    if (rule.minimum is not None and value < rule.minimum) or (
        rule.maximum is not None and value > rule.maximum
    ):
        return _reject(candidate, rule, "REJECTED_OUT_OF_RANGE")
    return value, unit, acceptance_reason


def _value_and_unit(
    candidate: ParameterCandidate, rule: ParameterRule
) -> tuple[str | None, Decimal, str | None]:
    """Apply an explicit unit policy and conversion.

    Parameters
    ----------
    candidate : ParameterCandidate
        Accepted numeric candidate.
    rule : ParameterRule
        Rule unit contract.

    Returns
    -------
    tuple[str | None, Decimal, str | None]
        Output unit, value, and optional rejection code.
    """

    assert candidate.parsed_value is not None
    unit = _unit(candidate.raw_unit) if candidate.raw_unit else None
    if unit is None:
        if rule.unit_policy == "required":
            return None, candidate.parsed_value, "REJECTED_MISSING_UNIT"
        return rule.assumed_unit, candidate.parsed_value, None
    configured_units = {_unit_key(item): item for item in rule.units}
    configured_unit = configured_units.get(_unit_key(unit))
    if rule.units and configured_unit is None:
        return None, candidate.parsed_value, "REJECTED_UNKNOWN_UNIT"
    for conversion in rule.conversions:
        if _unit_key(unit) == _unit_key(conversion.from_unit):
            return (
                conversion.to_unit,
                candidate.parsed_value * conversion.multiplier + conversion.offset,
                None,
            )
    output_unit = configured_unit or unit
    if rule.canonical_unit and _unit_key(output_unit) != _unit_key(rule.canonical_unit):
        return None, candidate.parsed_value, "REJECTED_UNKNOWN_UNIT"
    return output_unit, candidate.parsed_value, None


def _point(
    candidate: ParameterCandidate,
    rule: ParameterRule,
    value: Decimal,
    unit: str | None,
    reason: str,
) -> ObservationPoint:
    """Build one provenance-rich derived observation point.

    Parameters
    ----------
    candidate : ParameterCandidate
        Accepted candidate.
    rule : ParameterRule
        Accepting rule.
    value : Decimal
        Normalized value.
    unit : str | None
        Normalized unit.
    reason : str
        Acceptance reason.

    Returns
    -------
    ObservationPoint
        Derived point.
    """

    assert candidate.parsed_value is not None and candidate.document_date is not None
    series_id = (
        rule.series_id
        if unit is None or unit == rule.canonical_unit
        else f"{rule.series_id}--{_slug(unit)}"
    )
    point_id = hashlib.sha256(
        f"{rule.id}\x1f{candidate.stable_id}".encode()
    ).hexdigest()
    return ObservationPoint(
        id=point_id,
        series_id=series_id,
        observation_date=candidate.document_date,
        source_type="document-extraction",
        source_reference=candidate.document_href or candidate.document_title,
        numeric_value=float(value),
        source_kind="document-extraction",
        document_id=candidate.document_id,
        document_href=candidate.document_href,
        document_title=candidate.document_title,
        document_category=candidate.document_category,
        source_text_digest=candidate.source_text_digest,
        original_line=candidate.original_line,
        line_number=candidate.line_number,
        character_start=candidate.character_start,
        character_end=candidate.character_end,
        matched_label=candidate.normalized_label,
        raw_value=candidate.raw_value,
        parsed_value=float(candidate.parsed_value),
        raw_unit=candidate.raw_unit,
        normalized_unit=unit,
        qualifier=candidate.qualifier,
        rule_id=rule.id,
        rule_version=rule.version,
        rule_digest=rule.digest,
        reason_code=reason,
    )


def _series(
    points: tuple[ObservationPoint, ...], rules: dict[str, ParameterRule]
) -> tuple[ObservationSeries, ...]:
    """Build one derived series per rule and normalized unit.

    Parameters
    ----------
    points : tuple[ObservationPoint, ...]
        Derived points.
    rules : dict[str, ParameterRule]
        Rules keyed by identifier.

    Returns
    -------
    tuple[ObservationSeries, ...]
        Deterministically ordered series.
    """

    result: dict[str, ObservationSeries] = {}
    for point in points:
        assert point.rule_id is not None
        rule = rules[point.rule_id]
        result.setdefault(
            point.series_id,
            ObservationSeries(
                id=point.series_id,
                name=rule.display_name,
                value_type=rule.value_type,
                unit=point.normalized_unit,
                synonyms=rule.synonyms,
                parameter_rule_id=rule.id,
                parameter_rule_version=rule.version,
                parameter_rule_digest=rule.digest,
                unit_variant=point.normalized_unit
                if point.normalized_unit != rule.canonical_unit
                else None,
            ),
        )
    return tuple(result[key] for key in sorted(result))


def _reject(
    candidate: ParameterCandidate, rule: ParameterRule, reason: str
) -> RuleDecision:
    """Build a rejected decision.

    Parameters
    ----------
    candidate : ParameterCandidate
        Rejected candidate.
    rule : ParameterRule
        Evaluated rule.
    reason : str
        Rejection reason.

    Returns
    -------
    RuleDecision
        Rejected decision.
    """

    return RuleDecision(candidate.stable_id, rule.id, False, reason)


def _conversions(value: Any, path: Path, rule_id: str) -> tuple[UnitConversion, ...]:
    """Parse explicit affine conversions.

    Parameters
    ----------
    value : Any
        Raw conversion list.
    path : pathlib.Path
        Source path.
    rule_id : str
        Rule identifier.

    Returns
    -------
    tuple[UnitConversion, ...]
        Ordered conversions.

    Raises
    ------
    ConfigError
        If a conversion is malformed.
    """

    if not isinstance(value, list):
        raise ConfigError(
            f"{path} parameters.{rule_id} conversions deve essere un array"
        )
    result: list[UnitConversion] = []
    for item in value:
        if not isinstance(item, dict) or set(item) - {
            "from_unit",
            "to_unit",
            "multiplier",
            "offset",
            "version",
        }:
            raise ConfigError(f"{path} parameters.{rule_id} conversione non valida")
        result.append(
            UnitConversion(
                _unit(_string(item.get("from_unit"), path, "from_unit")),
                _unit(_string(item.get("to_unit"), path, "to_unit")),
                _decimal(item.get("multiplier"), path, "multiplier") or Decimal(0),
                _decimal(item.get("offset"), path, "offset") or Decimal(0),
                _positive(item, "version", None, path),
            )
        )
    return tuple(
        sorted(result, key=lambda item: (item.from_unit, item.to_unit, item.version))
    )


def _canonical(value: dict[str, Any]) -> str:
    """Serialize resolved fields for a rule digest.

    Parameters
    ----------
    value : dict[str, Any]
        Rule fields.

    Returns
    -------
    str
        Canonical JSON.
    """

    def render(item: Any) -> Any:
        """Render nested values as JSON primitives.

        Parameters
        ----------
        item : Any
            Value to render.

        Returns
        -------
        Any
            JSON-compatible value.
        """

        if isinstance(item, Decimal):
            return str(item)
        if isinstance(item, UnitConversion):
            return (
                item.from_unit,
                item.to_unit,
                str(item.multiplier),
                str(item.offset),
                item.version,
            )
        if isinstance(item, tuple):
            return [render(part) for part in item]
        return item

    return json.dumps(
        {key: render(item) for key, item in sorted(value.items())},
        sort_keys=True,
        separators=(",", ":"),
    )


def _positive(value: dict[str, Any], key: str, default: int | None, path: Path) -> int:
    """Read a positive TOML integer.

    Parameters
    ----------
    value : dict[str, Any]
        Raw mapping.
    key : str
        Field name.
    default : int | None
        Optional default.
    path : pathlib.Path
        Source path.

    Returns
    -------
    int
        Positive integer.

    Raises
    ------
    ConfigError
        If the field is absent or not positive.
    """

    result = value.get(key, default)
    if not isinstance(result, int) or isinstance(result, bool) or result <= 0:
        raise ConfigError(f"{path} campo {key} deve essere un intero positivo")
    return result


def _string(value: Any, path: Path, key: str) -> str:
    """Read a non-empty TOML string.

    Parameters
    ----------
    value : Any
        Raw value.
    path : pathlib.Path
        Source path.
    key : str
        Field name.

    Returns
    -------
    str
        Trimmed string.

    Raises
    ------
    ConfigError
        If the field is not a non-empty string.
    """

    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{path} campo {key} deve essere una stringa non vuota")
    return value.strip()


def _optional_string(value: Any, path: Path, key: str) -> str | None:
    """Read an optional TOML string.

    Parameters
    ----------
    value : Any
        Raw value.
    path : pathlib.Path
        Source path.
    key : str
        Field name.

    Returns
    -------
    str | None
        Trimmed string or none.
    """

    return None if value is None else _string(value, path, key)


def _strings(value: Any, path: Path, key: str) -> tuple[str, ...]:
    """Read an array of non-empty strings.

    Parameters
    ----------
    value : Any
        Raw array.
    path : pathlib.Path
        Source path.
    key : str
        Field name.

    Returns
    -------
    tuple[str, ...]
        Trimmed strings.

    Raises
    ------
    ConfigError
        If the field is not an array of strings.
    """

    if not isinstance(value, list):
        raise ConfigError(f"{path} campo {key} deve essere un array di stringhe")
    return tuple(_string(item, path, key) for item in value)


def _decimal(value: Any, path: Path, key: str) -> Decimal | None:
    """Read an optional finite TOML number.

    Parameters
    ----------
    value : Any
        Raw value.
    path : pathlib.Path
        Source path.
    key : str
        Field name.

    Returns
    -------
    Decimal | None
        Decimal value or none.

    Raises
    ------
    ConfigError
        If a present value is not finite and numeric.
    """

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigError(f"{path} campo {key} deve essere numerico")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ConfigError(f"{path} campo {key} deve essere finito")
    return result


def _unit(value: str) -> str:
    """Normalize unit typography without clinical inference.

    Parameters
    ----------
    value : str
        Raw unit.

    Returns
    -------
    str
        Normalized unit.
    """

    return " ".join(unicodedata.normalize("NFKC", value).split())


def _unit_key(value: str) -> str:
    """Build a case-insensitive comparison key for a measurement unit.

    Parameters
    ----------
    value : str
        Unit value whose typography has already been normalized or is raw.

    Returns
    -------
    str
        Unicode-normalized, case-insensitive unit comparison key.
    """

    return _unit(value).casefold()


def _optional_unit(value: Any, path: Path, key: str) -> str | None:
    """Read and normalize an optional unit.

    Parameters
    ----------
    value : Any
        Raw optional value.
    path : pathlib.Path
        Source path.
    key : str
        Field name.

    Returns
    -------
    str | None
        Normalized unit or none.
    """

    rendered = _optional_string(value, path, key)
    return _unit(rendered) if rendered else None


def _slug(value: str) -> str:
    """Build a safe deterministic series-id unit suffix.

    Parameters
    ----------
    value : str
        Unit value.

    Returns
    -------
    str
        Identifier-safe suffix.
    """

    return (
        "".join(
            character if character.isalnum() else "-" for character in value.casefold()
        ).strip("-")
        or "unknown"
    )
