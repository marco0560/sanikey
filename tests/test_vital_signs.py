"""Tests for strict document-derived weight and pressure observations."""

from __future__ import annotations

from pathlib import Path

from sanikey.documents import ExtractedText
from sanikey.models import (
    CuratedMetadata,
    DocumentRecord,
    ObservationPoint,
    ObservationSeries,
)
from sanikey.vital_signs import extract_vital_signs, merge_vital_signs


def _document() -> DocumentRecord:
    """Build one dated synthetic source document.

    Parameters
    ----------
    None

    Returns
    -------
    sanikey.models.DocumentRecord
        Synthetic document.
    """

    return DocumentRecord(
        "documento",
        "paziente",
        Path("/referto.txt"),
        "Referto",
        "Visita",
        "text",
        "a" * 64,
        "2026-01-02",
    )


def test_extract_vital_signs_accepts_only_explicit_weight_and_pressure_forms() -> None:
    """Verify strict documented forms create the two dedicated series.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = extract_vital_signs(
        (_document(),),
        (ExtractedText("documento", "Peso: 70,5 kg\nPA: 120/80 mmHg\nPeso 70"),),
    )

    assert [item.id for item in result.series] == ["peso", "pressione"]
    assert result.points[0].numeric_value == 70.5
    assert result.points[1].systolic == 120
    assert result.points[1].diastolic == 80


def test_merge_vital_signs_keeps_same_day_structured_observation() -> None:
    """Verify imported data wins over document extraction on the same day.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = extract_vital_signs(
        (_document(),), (ExtractedText("documento", "Peso: 70 kg"),)
    )
    metadata = CuratedMetadata(
        observation_series=(ObservationSeries("peso", "Peso", "numeric", "kg"),),
        observation_points=(
            ObservationPoint(
                "importato", "peso", "2026-01-02", "csv", "peso.csv:2", numeric_value=71
            ),
        ),
    )

    merged = merge_vital_signs(metadata, result)

    assert merged.observation_points == metadata.observation_points
