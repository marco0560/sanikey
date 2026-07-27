"""Deterministic discovery of longitudinal clinical parameter candidates."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .documents import ExtractedText
    from .models import DocumentRecord


_CANDIDATE_RE = re.compile(
    r"^(?P<label>.+?)(?P<separator>\s*(?::|=)\s*|\s+)"
    r"(?P<qualifier><=|>=|<|>)?\s*"
    r"(?P<number>\d{1,3}(?:[.,]\d{3})+[.,]\d+|\d+[.,]\d+|\d+)"
    r"(?:\s*(?P<unit>[A-Za-z%µμ][A-Za-z0-9%µμ/._^*\-]*"
    r"(?:\s*/\s*[A-Za-z%µμ][A-Za-z0-9%µμ._^*\-]*)?))?"
)
_STACKED_VALUE_RE = re.compile(
    r"^\s*(?P<qualifier><=|>=|<|>)?\s*"
    r"(?P<number>\d{1,3}(?:[.,]\d{3})+[.,]\d+|\d+[.,]\d+|\d+)\s*$"
)
_STACKED_UNIT_RE = re.compile(
    r"^\s*(?P<unit>[A-Za-z%µμ][A-Za-z0-9%µμ/._^+*\-\" ]*)\s*$"
)
_REFERENCE_RANGE_SUFFIX_RE = re.compile(
    r"\s+(?:[<>=~]\s*)?\d+(?:[.,]\d+)?\s*(?:-|–|a)\s*\d+(?:[.,]\d+)?\s*$"
)
_REFERENCE_CELL_RE = re.compile(
    r"^\s*(?:\(\s*)?(?:<=|>=|<|>)?\s*\d+(?:[.,]\d+)?"
    r"(?:\s*(?:-|–|a)\s*(?:<=|>=|<|>)?\s*\d+(?:[.,]\d+)?)?\s*\)?\s*$"
)
_VALUE_DESCRIPTION_RE = re.compile(
    r"^\s*valore\s+(?P<kind>in\s+massa|percentuale)\s*$",
    re.IGNORECASE,
)
_GLYCATED_HEMOGLOBIN_LABEL_RE = re.compile(
    r"\b(?:hb\s+glicosilat|hb\s+glicat|emoglobina\s+glicosilat)",
    re.IGNORECASE,
)
_LETTER_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
_SPACE_RE = re.compile(r"\s+")
_TRAILING_SEPARATOR_RE = re.compile(r"\s*[:=]\s*$")
_ERR_MIN_LABEL_LENGTH = "min_label_length deve essere positivo"
_ERR_MAX_LABEL_LENGTH = "max_label_length non puo' essere minore del minimo"
_ERR_MAX_LABEL_WORDS = "max_label_words deve essere positivo"
_ERR_PROPOSAL_THRESHOLDS = "le soglie di proposta devono essere positive"


@dataclass(frozen=True)
class DiscoverySettings:
    """Configure deterministic candidate discovery.

    Parameters
    ----------
    min_label_length : int
        Minimum normalized label length.
    max_label_length : int
        Maximum normalized label length.
    max_label_words : int
        Maximum number of words in a label.
    min_occurrences : int
        Minimum group occurrence count for a proposal.
    min_distinct_documents : int
        Minimum distinct documents for a proposal.
    min_distinct_dates : int
        Minimum distinct dated documents for a proposal.
    excluded_labels : tuple[str, ...]
        Labels excluded after deterministic normalization.
    """

    min_label_length: int = 2
    max_label_length: int = 80
    max_label_words: int = 8
    min_occurrences: int = 2
    min_distinct_documents: int = 2
    min_distinct_dates: int = 1
    excluded_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParameterCandidate:
    """Represent one syntactic name-value candidate with provenance.

    Parameters
    ----------
    stable_id : str
        Deterministic candidate identity.
    document_id : str
        Source document identity.
    document_date : str | None
        Authoritative document date.
    document_href : str | None
        Relative link to the exported original document.
    document_title : str
        Source document title.
    document_category : str
        Source document category.
    source_text_digest : str
        SHA-256 digest of the exact extracted text.
    line_number : int
        One-based source line number.
    character_start : int
        Zero-based inclusive match offset in the extracted text.
    character_end : int
        Zero-based exclusive match offset in the extracted text.
    original_line : str
        Unmodified source line or stacked table-cell fragment.
    normalized_label : str
        Deterministically normalized candidate label.
    raw_value : str
        Numeric token as found in the source text.
    parsed_value : Decimal | None
        Parsed value, absent when its format is ambiguous or invalid.
    number_format : str | None
        Recognized numeric format.
    qualifier : str | None
        Optional comparison qualifier.
    raw_unit : str | None
        Unit token as found in the source text.
    prefix_context : str
        Text before the recognized sequence on the same line.
    suffix_context : str
        Text after the recognized sequence on the same line.
    reason_code : str | None
        Parse rejection reason, when the numeric token is not usable.
    """

    stable_id: str
    document_id: str
    document_date: str | None
    document_href: str | None
    document_title: str
    document_category: str
    source_text_digest: str
    line_number: int
    character_start: int
    character_end: int
    original_line: str
    normalized_label: str
    raw_value: str
    parsed_value: Decimal | None
    number_format: str | None
    qualifier: str | None
    raw_unit: str | None
    prefix_context: str
    suffix_context: str
    reason_code: str | None = None


@dataclass(frozen=True)
class CandidateGroup:
    """Represent an exact-label group proposed for curator review.

    Parameters
    ----------
    normalized_label : str
        Shared normalized label.
    candidates : tuple[ParameterCandidate, ...]
        Deterministically ordered group members.
    """

    normalized_label: str
    candidates: tuple[ParameterCandidate, ...]

    @property
    def distinct_documents(self) -> int:
        """Return the number of distinct documents.

        Parameters
        ----------
        None

        Returns
        -------
        int
            Number of distinct source documents.
        """

        return len({candidate.document_id for candidate in self.candidates})

    @property
    def distinct_dates(self) -> int:
        """Return the number of distinct authoritative dates.

        Parameters
        ----------
        None

        Returns
        -------
        int
            Number of distinct non-empty document dates.
        """

        return len(
            {
                candidate.document_date
                for candidate in self.candidates
                if candidate.document_date is not None
            }
        )


@dataclass(frozen=True)
class DiscoveryResult:
    """Contain candidates and proposal groups from one deterministic scan.

    Parameters
    ----------
    candidates : tuple[ParameterCandidate, ...]
        Every syntactic candidate found in source order.
    proposed_groups : tuple[CandidateGroup, ...]
        Groups meeting the configured proposal thresholds.
    analyzed_lines : int
        Number of extracted-text lines scanned.
    """

    candidates: tuple[ParameterCandidate, ...]
    proposed_groups: tuple[CandidateGroup, ...]
    analyzed_lines: int


@dataclass(frozen=True)
class _LineSource:
    """Hold immutable document-wide provenance for one scanned line.

    Parameters
    ----------
    document : sanikey.models.DocumentRecord
        Document owning the extracted text.
    text_digest : str
        SHA-256 digest of the exact extracted text.
    document_href : str | None
        Optional relative link to the exported original document.
    """

    document: DocumentRecord
    text_digest: str
    document_href: str | None


def discover_candidates(
    documents: tuple[DocumentRecord, ...],
    extracted_text: tuple[ExtractedText, ...],
    *,
    document_hrefs: Mapping[str, str] | None = None,
    settings: DiscoverySettings = DiscoverySettings(),
) -> DiscoveryResult:
    """Discover deterministic parameter candidates from existing extracted text.

    Parameters
    ----------
    documents : tuple[sanikey.models.DocumentRecord, ...]
        Documents associated with the extracted text.
    extracted_text : tuple[sanikey.documents.ExtractedText, ...]
        Text records already produced by the normal extraction pipeline.
    document_hrefs : collections.abc.Mapping[str, str] | None, optional
        Optional relative links keyed by document id.
    settings : DiscoverySettings, optional
        Candidate and proposal thresholds.

    Returns
    -------
    DiscoveryResult
        Candidates, exact-label proposal groups, and line count.
    """

    _validate_settings(settings)
    records_by_id = {document.document_id: document for document in documents}
    hrefs = document_hrefs or {}
    candidates: list[ParameterCandidate] = []
    analyzed_lines = 0
    for extracted in sorted(extracted_text, key=lambda item: item.document_id):
        document = records_by_id.get(extracted.document_id)
        if document is None:
            continue
        text_digest = hashlib.sha256(extracted.text.encode("utf-8")).hexdigest()
        lines = extracted.text.splitlines()
        line_offsets: list[int] = []
        line_offset = 0
        for original_line in lines:
            line_offsets.append(line_offset)
            line_offset += len(original_line) + 1
        for index, original_line in enumerate(lines):
            analyzed_lines += 1
            source = _LineSource(
                document=document,
                text_digest=text_digest,
                document_href=hrefs.get(document.document_id),
            )
            candidate = _candidate_from_line(
                source,
                original_line,
                index + 1,
                line_offsets[index],
                settings,
            )
            if candidate is None:
                candidate = _candidate_from_stacked_cells(
                    source,
                    lines,
                    index,
                    line_offsets,
                    settings,
                )
            if candidate is None:
                candidate = _candidate_from_unit_reference_value_cells(
                    source,
                    lines,
                    index,
                    line_offsets,
                    settings,
                )
            if candidate is None:
                candidate = _candidate_from_described_value_cells(
                    source,
                    lines,
                    index,
                    line_offsets,
                    settings,
                )
            if candidate is not None:
                candidates.append(candidate)
    ordered_candidates = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.normalized_label,
                item.document_date or "",
                item.document_id,
                item.character_start,
                item.stable_id,
            ),
        )
    )
    groups = _proposed_groups(ordered_candidates, settings)
    return DiscoveryResult(
        candidates=ordered_candidates,
        proposed_groups=groups,
        analyzed_lines=analyzed_lines,
    )


def normalize_label(value: str) -> str:
    """Normalize one label without semantic expansion.

    Parameters
    ----------
    value : str
        Raw label text.

    Returns
    -------
    str
        Unicode-normalized, case-folded label suitable for exact comparison.
    """

    normalized = unicodedata.normalize("NFKC", value)
    normalized = _TRAILING_SEPARATOR_RE.sub("", normalized)
    normalized = _SPACE_RE.sub(" ", normalized.strip())
    return normalized.casefold()


def _candidate_from_line(
    source: _LineSource,
    original_line: str,
    line_number: int,
    line_offset: int,
    settings: DiscoverySettings,
) -> ParameterCandidate | None:
    """Build one candidate from a source line when the grammar matches.

    Parameters
    ----------
    source : _LineSource
        Document-wide provenance for the line.
    original_line : str
        Exact extracted source line.
    line_number : int
        One-based source line number.
    line_offset : int
        Zero-based starting offset of the line in the extracted text.
    settings : DiscoverySettings
        Label constraints.

    Returns
    -------
    ParameterCandidate | None
        Candidate when the line passes syntactic checks, otherwise ``None``.
    """

    match = _CANDIDATE_RE.search(original_line)
    if match is None:
        return None
    raw_label = match.group("label")
    normalized_label = normalize_label(raw_label)
    if not _label_is_eligible(normalized_label, settings):
        return None
    raw_value = match.group("number")
    parsed_value, number_format, reason_code = _parse_number(raw_value)
    character_start = line_offset + match.start()
    character_end = line_offset + match.end()
    stable_source = "\x1f".join(
        (
            source.document.document_id,
            source.text_digest,
            str(character_start),
            str(character_end),
            normalized_label,
            raw_value,
            match.group("unit") or "",
        )
    )
    stable_id = hashlib.sha256(stable_source.encode("utf-8")).hexdigest()
    return ParameterCandidate(
        stable_id=stable_id,
        document_id=source.document.document_id,
        document_date=source.document.date,
        document_href=source.document_href,
        document_title=source.document.title,
        document_category=source.document.category,
        source_text_digest=source.text_digest,
        line_number=line_number,
        character_start=character_start,
        character_end=character_end,
        original_line=original_line,
        normalized_label=normalized_label,
        raw_value=raw_value,
        parsed_value=parsed_value,
        number_format=number_format,
        qualifier=match.group("qualifier"),
        raw_unit=match.group("unit"),
        prefix_context=original_line[: match.start()],
        suffix_context=original_line[match.end() :],
        reason_code=reason_code,
    )


def _candidate_from_stacked_cells(
    source: _LineSource,
    lines: list[str],
    label_index: int,
    line_offsets: list[int],
    settings: DiscoverySettings,
) -> ParameterCandidate | None:
    """Build a candidate from a vertically extracted table row.

    Parameters
    ----------
    source : _LineSource
        Document-wide provenance for the row.
    lines : list[str]
        All extracted lines for the source document.
    label_index : int
        Zero-based label-cell index in ``lines``.
    line_offsets : list[int]
        Zero-based offsets corresponding to ``lines``.
    settings : DiscoverySettings
        Label constraints.

    Returns
    -------
    ParameterCandidate | None
        Candidate when three stacked cells form a valid measurement.
    """

    following = [
        (index, item)
        for index, item in enumerate(
            lines[label_index + 1 : label_index + 5], label_index + 1
        )
        if item.strip()
    ]
    if len(following) < 2:
        return None
    _, value_line = following[0]
    unit_index, unit_line = following[1]
    label = lines[label_index]
    line_number = label_index + 1
    line_offset = line_offsets[label_index]
    normalized_label = normalize_label(label)
    value_match = _STACKED_VALUE_RE.fullmatch(value_line)
    unit_match = _STACKED_UNIT_RE.fullmatch(unit_line)
    if (
        not _label_is_eligible(normalized_label, settings)
        or value_match is None
        or unit_match is None
    ):
        return None
    raw_value = value_match.group("number")
    raw_unit = _unit_without_reference_range(unit_match.group("unit"))
    if not raw_unit:
        return None
    parsed_value, number_format, reason_code = _parse_number(raw_value)
    character_start = line_offset
    character_end = line_offsets[unit_index] + unit_line.index(raw_unit) + len(raw_unit)
    original_line = "\n".join(lines[label_index : unit_index + 1])
    stable_source = "\x1f".join(
        (
            source.document.document_id,
            source.text_digest,
            str(character_start),
            str(character_end),
            normalized_label,
            raw_value,
            raw_unit,
        )
    )
    stable_id = hashlib.sha256(stable_source.encode("utf-8")).hexdigest()
    return ParameterCandidate(
        stable_id=stable_id,
        document_id=source.document.document_id,
        document_date=source.document.date,
        document_href=source.document_href,
        document_title=source.document.title,
        document_category=source.document.category,
        source_text_digest=source.text_digest,
        line_number=line_number,
        character_start=character_start,
        character_end=character_end,
        original_line=original_line,
        normalized_label=normalized_label,
        raw_value=raw_value,
        parsed_value=parsed_value,
        number_format=number_format,
        qualifier=value_match.group("qualifier"),
        raw_unit=raw_unit,
        prefix_context="",
        suffix_context="",
        reason_code=reason_code,
    )


def _candidate_from_unit_reference_value_cells(
    source: _LineSource,
    lines: list[str],
    label_index: int,
    line_offsets: list[int],
    settings: DiscoverySettings,
) -> ParameterCandidate | None:
    """Build a candidate from label, unit, reference, and value table cells.

    Parameters
    ----------
    source : _LineSource
        Document-wide provenance for the row.
    lines : list[str]
        All extracted lines for the source document.
    label_index : int
        Zero-based label-cell index in ``lines``.
    line_offsets : list[int]
        Zero-based offsets corresponding to ``lines``.
    settings : DiscoverySettings
        Label constraints.

    Returns
    -------
    ParameterCandidate | None
        Candidate when four stacked cells form a valid measurement.
    """

    following = [
        (index, item)
        for index, item in enumerate(
            lines[label_index + 1 : label_index + 7], label_index + 1
        )
        if item.strip()
    ]
    if len(following) < 3:
        return None
    unit_index, unit_line = following[0]
    _, reference_line = following[1]
    value_index, value_line = following[2]
    label = lines[label_index]
    normalized_label = normalize_label(label)
    unit_match = _STACKED_UNIT_RE.fullmatch(unit_line)
    value_match = _STACKED_VALUE_RE.fullmatch(value_line)
    if (
        not _label_is_eligible(normalized_label, settings)
        or unit_match is None
        or value_match is None
        or _REFERENCE_CELL_RE.fullmatch(reference_line) is None
    ):
        return None
    raw_unit = _unit_without_reference_range(unit_match.group("unit"))
    if not raw_unit:
        return None
    raw_value = value_match.group("number")
    parsed_value, number_format, reason_code = _parse_number(raw_value)
    character_start = line_offsets[label_index]
    character_end = (
        line_offsets[value_index] + value_line.rfind(raw_value) + len(raw_value)
    )
    original_line = "\n".join(lines[label_index : value_index + 1])
    stable_source = "\x1f".join(
        (
            source.document.document_id,
            source.text_digest,
            str(character_start),
            str(character_end),
            normalized_label,
            raw_value,
            raw_unit,
        )
    )
    stable_id = hashlib.sha256(stable_source.encode("utf-8")).hexdigest()
    return ParameterCandidate(
        stable_id=stable_id,
        document_id=source.document.document_id,
        document_date=source.document.date,
        document_href=source.document_href,
        document_title=source.document.title,
        document_category=source.document.category,
        source_text_digest=source.text_digest,
        line_number=label_index + 1,
        character_start=character_start,
        character_end=character_end,
        original_line=original_line,
        normalized_label=normalized_label,
        raw_value=raw_value,
        parsed_value=parsed_value,
        number_format=number_format,
        qualifier=value_match.group("qualifier"),
        raw_unit=raw_unit,
        prefix_context="",
        suffix_context="",
        reason_code=reason_code,
    )


def _candidate_from_described_value_cells(
    source: _LineSource,
    lines: list[str],
    label_index: int,
    line_offsets: list[int],
    settings: DiscoverySettings,
) -> ParameterCandidate | None:
    """Build a candidate from a label followed by an explicit value description.

    Parameters
    ----------
    source : _LineSource
        Document-wide provenance for the row.
    lines : list[str]
        All extracted lines for the source document.
    label_index : int
        Zero-based label-cell index in ``lines``.
    line_offsets : list[int]
        Zero-based offsets corresponding to ``lines``.
    settings : DiscoverySettings
        Label constraints.

    Returns
    -------
    ParameterCandidate | None
        Candidate when a mass or percentage description has a value and unit.

    Notes
    -----
    The mass representation is preferred when both mass and percentage occur in
    one extracted block, because it has an explicit configured conversion to
    the canonical percentage series.
    """

    label = lines[label_index]
    normalized_label = normalize_label(label)
    if (
        not _label_is_eligible(normalized_label, settings)
        or _GLYCATED_HEMOGLOBIN_LABEL_RE.search(label) is None
    ):
        return None
    following = [
        (index, item)
        for index, item in enumerate(
            lines[label_index + 1 : label_index + 15], label_index + 1
        )
        if item.strip()
    ]
    for kind in ("in massa", "percentuale"):
        for position, (_, description_line) in enumerate(following):
            description_match = _VALUE_DESCRIPTION_RE.fullmatch(description_line)
            if (
                description_match is None
                or description_match.group("kind").casefold() != kind
            ):
                continue
            if position + 2 >= len(following):
                continue
            value_index, value_line = following[position + 1]
            unit_index, unit_line = following[position + 2]
            value_match = _STACKED_VALUE_RE.fullmatch(value_line)
            unit_match = _STACKED_UNIT_RE.fullmatch(unit_line)
            if value_match is None or unit_match is None:
                continue
            raw_unit = _unit_without_reference_range(unit_match.group("unit"))
            if not raw_unit:
                continue
            raw_value = value_match.group("number")
            parsed_value, number_format, reason_code = _parse_number(raw_value)
            character_start = line_offsets[label_index]
            character_end = (
                line_offsets[unit_index] + unit_line.rfind(raw_unit) + len(raw_unit)
            )
            original_line = "\n".join(lines[label_index : unit_index + 1])
            stable_source = "\x1f".join(
                (
                    source.document.document_id,
                    source.text_digest,
                    str(character_start),
                    str(character_end),
                    normalized_label,
                    raw_value,
                    raw_unit,
                )
            )
            stable_id = hashlib.sha256(stable_source.encode("utf-8")).hexdigest()
            return ParameterCandidate(
                stable_id=stable_id,
                document_id=source.document.document_id,
                document_date=source.document.date,
                document_href=source.document_href,
                document_title=source.document.title,
                document_category=source.document.category,
                source_text_digest=source.text_digest,
                line_number=label_index + 1,
                character_start=character_start,
                character_end=character_end,
                original_line=original_line,
                normalized_label=normalized_label,
                raw_value=raw_value,
                parsed_value=parsed_value,
                number_format=number_format,
                qualifier=value_match.group("qualifier"),
                raw_unit=raw_unit,
                prefix_context="",
                suffix_context="",
                reason_code=reason_code,
            )
    return None


def _unit_without_reference_range(value: str) -> str:
    """Remove a trailing numeric reference interval from a unit cell.

    Parameters
    ----------
    value : str
        Full vertically extracted unit cell.

    Returns
    -------
    str
        Unit text without a trailing reference range.
    """

    return _REFERENCE_RANGE_SUFFIX_RE.sub("", value).strip()


def _label_is_eligible(label: str, settings: DiscoverySettings) -> bool:
    """Return whether a normalized label passes generic safeguards.

    Parameters
    ----------
    label : str
        Normalized candidate label.
    settings : DiscoverySettings
        Configured label limits.

    Returns
    -------
    bool
        ``True`` when the label can produce a candidate.
    """

    if not settings.min_label_length <= len(label) <= settings.max_label_length:
        return False
    if len(label.split()) > settings.max_label_words:
        return False
    if _LETTER_RE.search(label) is None:
        return False
    excluded = {normalize_label(item) for item in settings.excluded_labels}
    return label not in excluded


def _parse_number(raw_value: str) -> tuple[Decimal | None, str | None, str | None]:
    """Parse one numeric token without silently resolving ambiguity.

    Parameters
    ----------
    raw_value : str
        Numeric token captured by the candidate grammar.

    Returns
    -------
    tuple[Decimal | None, str | None, str | None]
        Parsed value, recognized format, and optional rejection reason.
    """

    if raw_value.isdigit():
        return Decimal(raw_value), "integer", None
    if "." in raw_value and "," in raw_value:
        decimal_separator = "." if raw_value.rfind(".") > raw_value.rfind(",") else ","
        grouping_separator = "," if decimal_separator == "." else "."
        integer_part, fraction_part = raw_value.rsplit(decimal_separator, maxsplit=1)
        groups = integer_part.split(grouping_separator)
        if (
            not fraction_part.isdigit()
            or not all(group.isdigit() for group in groups)
            or not 1 <= len(groups[0]) <= 3
            or any(len(group) != 3 for group in groups[1:])
        ):
            return None, None, "REJECTED_INVALID_NUMBER_FORMAT"
        canonical = "".join(groups) + "." + fraction_part
        number_format = (
            "grouped-comma-decimal-point"
            if decimal_separator == "."
            else "grouped-point-decimal-comma"
        )
        return _decimal_or_rejection(canonical, number_format)
    separator = "." if "." in raw_value else ","
    integer_part, fraction_part = raw_value.split(separator, maxsplit=1)
    if not integer_part.isdigit() or not fraction_part.isdigit():
        return None, None, "REJECTED_INVALID_NUMBER_FORMAT"
    if len(fraction_part) == 3:
        return None, None, "REJECTED_AMBIGUOUS_NUMBER_FORMAT"
    number_format = "decimal-point" if separator == "." else "decimal-comma"
    return _decimal_or_rejection(f"{integer_part}.{fraction_part}", number_format)


def _decimal_or_rejection(
    canonical: str,
    number_format: str,
) -> tuple[Decimal | None, str | None, str | None]:
    """Create a decimal or return a deterministic parse rejection.

    Parameters
    ----------
    canonical : str
        Dot-decimal numeric representation.
    number_format : str
        Recognized input format name.

    Returns
    -------
    tuple[Decimal | None, str | None, str | None]
        Parsed value, format, and optional rejection reason.
    """

    try:
        return Decimal(canonical), number_format, None
    except InvalidOperation:
        return None, None, "REJECTED_INVALID_NUMBER_FORMAT"


def _proposed_groups(
    candidates: tuple[ParameterCandidate, ...],
    settings: DiscoverySettings,
) -> tuple[CandidateGroup, ...]:
    """Return exact-label groups that meet all configured thresholds.

    Parameters
    ----------
    candidates : tuple[ParameterCandidate, ...]
        Deterministically sorted candidates.
    settings : DiscoverySettings
        Proposal thresholds.

    Returns
    -------
    tuple[CandidateGroup, ...]
        Qualifying exact-label groups in deterministic order.
    """

    grouped: dict[str, list[ParameterCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.normalized_label, []).append(candidate)
    proposed: list[CandidateGroup] = []
    for label in sorted(grouped):
        group = CandidateGroup(label, tuple(grouped[label]))
        if (
            len(group.candidates) >= settings.min_occurrences
            and group.distinct_documents >= settings.min_distinct_documents
            and group.distinct_dates >= settings.min_distinct_dates
        ):
            proposed.append(group)
    return tuple(proposed)


def _validate_settings(settings: DiscoverySettings) -> None:
    """Validate discovery limits before scanning source text.

    Parameters
    ----------
    settings : DiscoverySettings
        Settings to validate.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If a configured limit is inconsistent.
    """

    if settings.min_label_length < 1:
        raise ValueError(_ERR_MIN_LABEL_LENGTH)
    if settings.max_label_length < settings.min_label_length:
        raise ValueError(_ERR_MAX_LABEL_LENGTH)
    if settings.max_label_words < 1:
        raise ValueError(_ERR_MAX_LABEL_WORDS)
    if (
        min(
            settings.min_occurrences,
            settings.min_distinct_documents,
            settings.min_distinct_dates,
        )
        < 1
    ):
        raise ValueError(_ERR_PROPOSAL_THRESHOLDS)
