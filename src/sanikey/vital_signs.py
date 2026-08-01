"""Extract strict weight and blood-pressure observations from document text."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .models import CuratedMetadata, DocumentRecord, ObservationPoint, ObservationSeries

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .documents import ExtractedText

_WEIGHT = re.compile(
    r"\b(?:peso|peso\s+corporeo)\s*[:=]?\s*(?P<value>\d{2,3}(?:[.,]\d+)?)\s*(?:kg|chilogrammi?)\b",
    re.IGNORECASE,
)
_PRESSURE = re.compile(
    r"\b(?:pressione(?:\s+arteriosa)?|p\.?a\.?)\s*[:=]?\s*(?P<systolic>\d{2,3})\s*/\s*(?P<diastolic>\d{2,3})\s*(?:mm\s*hg|mmhg)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class VitalSignResult:
    """Contain deterministic vital-sign observations extracted from documents.

    Parameters
    ----------
    series : tuple[sanikey.models.ObservationSeries, ...]
        Series represented by at least one valid extracted point.
    points : tuple[sanikey.models.ObservationPoint, ...]
        Provenance-rich extracted vital-sign points.
    rejections : tuple[dict[str, object], ...]
        Deterministic reasons for recognized but rejected vital-sign values.
    """

    series: tuple[ObservationSeries, ...]
    points: tuple[ObservationPoint, ...]
    rejections: tuple[dict[str, object], ...] = ()


def extract_vital_signs(
    documents: tuple[DocumentRecord, ...],
    extracted_text: tuple[ExtractedText, ...],
    *,
    document_hrefs: Mapping[str, str] | None = None,
) -> VitalSignResult:
    """Extract strict weight and pressure forms from dated document text.

    Parameters
    ----------
    documents : tuple[sanikey.models.DocumentRecord, ...]
        Source documents associated with extracted text.
    extracted_text : tuple[sanikey.documents.ExtractedText, ...]
        Existing extracted document text.
    document_hrefs : collections.abc.Mapping[str, str] | None, optional
        Export-relative original-document links keyed by document id.

    Returns
    -------
    VitalSignResult
        Valid extracted points and their non-empty series.
    """

    records = {document.document_id: document for document in documents}
    hrefs = document_hrefs or {}
    points: list[ObservationPoint] = []
    rejections: list[dict[str, object]] = []
    for text in sorted(extracted_text, key=lambda item: item.document_id):
        document = records.get(text.document_id)
        if document is None or document.date is None:
            continue
        for line_number, line in enumerate(text.text.splitlines(), start=1):
            for match in _WEIGHT.finditer(line):
                value = float(match["value"].replace(",", "."))
                if 20 <= value <= 400:
                    points.append(
                        _point(document, hrefs, line_number, line, match, "peso", value)
                    )
                else:
                    rejections.append(
                        {
                            "candidate_id": "",
                            "parameter": "peso",
                            "document": document.title,
                            "line": line_number,
                            "value": line,
                            "reason_code": "REJECTED_OUT_OF_RANGE",
                        }
                    )
            for match in _PRESSURE.finditer(line):
                systolic = float(match["systolic"])
                diastolic = float(match["diastolic"])
                if (
                    60 <= systolic <= 260
                    and 30 <= diastolic <= 160
                    and systolic > diastolic
                ):
                    points.append(
                        _point(
                            document,
                            hrefs,
                            line_number,
                            line,
                            match,
                            "pressione",
                            systolic,
                            diastolic,
                        )
                    )
                else:
                    rejections.append(
                        {
                            "candidate_id": "",
                            "parameter": "pressione",
                            "document": document.title,
                            "line": line_number,
                            "value": line,
                            "reason_code": "REJECTED_OUT_OF_RANGE",
                        }
                    )
    ordered = tuple(
        sorted(
            points, key=lambda item: (item.series_id, item.observation_date, item.id)
        )
    )
    ids = {point.series_id for point in ordered}
    series = tuple(item for item in _SERIES if item.id in ids)
    return VitalSignResult(series=series, points=ordered, rejections=tuple(rejections))


def merge_vital_signs(
    metadata: CuratedMetadata, result: VitalSignResult
) -> CuratedMetadata:
    """Merge vital signs while giving same-day structured data precedence.

    Parameters
    ----------
    metadata : sanikey.models.CuratedMetadata
        Existing curated and imported observations.
    result : VitalSignResult
        Document-extracted vital signs.

    Returns
    -------
    sanikey.models.CuratedMetadata
        Metadata with compatible series and non-duplicating extracted points.
    """

    existing_series = {item.id: item for item in metadata.observation_series}
    additions = tuple(item for item in result.series if item.id not in existing_series)
    structured_dates = {
        (point.series_id, point.observation_date)
        for point in metadata.observation_points
        if point.source_kind == "curated-observation"
    }
    extracted = tuple(
        point
        for point in result.points
        if (point.series_id, point.observation_date) not in structured_dates
    )
    return replace(
        metadata,
        observation_series=tuple((*metadata.observation_series, *additions)),
        observation_points=tuple((*metadata.observation_points, *extracted)),
    )


_SERIES = (
    ObservationSeries(id="peso", name="Peso", value_type="numeric", unit="kg"),
    ObservationSeries(
        id="pressione", name="Pressione", value_type="blood_pressure", unit="mmHg"
    ),
)


def _point(  # noqa: PLR0913
    document: DocumentRecord,
    hrefs: Mapping[str, str],
    line_number: int,
    line: str,
    match: re.Match[str],
    series_id: str,
    numeric_value: float,
    diastolic: float | None = None,
) -> ObservationPoint:
    """Build one deterministic document-derived vital-sign point.

    Parameters
    ----------
    document : sanikey.models.DocumentRecord
        Dated source document.
    hrefs : collections.abc.Mapping[str, str]
        Export-relative document links.
    line_number : int
        One-based source line number.
    line : str
        Exact source line.
    match : re.Match[str]
        Matched vital-sign expression.
    series_id : str
        Canonical vital-sign series id.
    numeric_value : float
        Weight or systolic value.
    diastolic : float | None, optional
        Diastolic pressure when applicable.

    Returns
    -------
    sanikey.models.ObservationPoint
        Provenance-rich vital-sign point.
    """

    raw = match.group(0)
    digest = hashlib.sha256(
        f"{document.document_id}\x1f{line_number}\x1f{raw}".encode()
    ).hexdigest()
    return ObservationPoint(
        id=f"vital-{digest[:24]}",
        series_id=series_id,
        observation_date=document.date or "",
        source_type="document-text",
        source_reference=f"{document.title}: riga {line_number}",
        numeric_value=numeric_value if diastolic is None else None,
        systolic=numeric_value if diastolic is not None else None,
        diastolic=diastolic,
        source_kind="document-extraction",
        document_id=document.document_id,
        document_href=hrefs.get(document.document_id),
        document_title=document.title,
        document_category=document.category,
        original_line=line,
        line_number=line_number,
        matched_label="Peso" if series_id == "peso" else "Pressione",
        raw_value=raw,
        raw_unit="kg" if series_id == "peso" else "mmHg",
        normalized_unit="kg" if series_id == "peso" else "mmHg",
        reason_code="ACCEPTED_STRICT_VITAL_SIGN",
    )
