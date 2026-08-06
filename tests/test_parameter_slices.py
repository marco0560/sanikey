"""Tests for deterministic parameter candidate discovery."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sanikey.documents import ExtractedText
from sanikey.models import DocumentRecord
from sanikey.parameter_slices import (
    DiscoverySettings,
    discover_candidates,
    discover_configured_candidates,
)


def _document(
    document_id: str, document_date: str | None = "2026-01-02"
) -> DocumentRecord:
    """Build a synthetic document record.

    Parameters
    ----------
    document_id : str
        Stable synthetic document identifier.
    document_date : str | None, optional
        Authoritative document date.

    Returns
    -------
    DocumentRecord
        Synthetic source document.
    """

    return DocumentRecord(
        document_id=document_id,
        patient_id="patient-a",
        path=Path(f"/{document_id}.txt"),
        title=f"Report {document_id}",
        category="Laboratorio",
        kind="text",
        sha256=document_id * 8,
        date=document_date,
    )


def test_configured_discovery_skips_unconfigured_numeric_lines() -> None:
    """Verify configured extraction ignores a telephone-number suffix.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_configured_candidates(
        (_document("doc-a"),),
        (
            ExtractedText(
                document_id="doc-a",
                text="Telefono segreteria 02 12345627\nHb: 13.7 g/dL\n",
            ),
        ),
        accepted_labels=("Hb", "emoglobina"),
        settings=DiscoverySettings(),
    )

    assert [item.normalized_label for item in result.candidates] == ["hb"]
    assert result.proposed_groups == ()


def test_configured_discovery_tracks_labels_and_section_specimens() -> None:
    """Verify configured label mentions retain chemistry and urine context.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_configured_candidates(
        (_document("doc-a"),),
        (
            ExtractedText(
                document_id="doc-a",
                text=(
                    "CHIMICA CLINICA\n"
                    "Glicemia basale\nmg/dl\n(60-100)\n134\n"
                    "URINE COMPLETE\n"
                    "Glucosio\nmg/dl\n(0-10)\n0\n"
                ),
            ),
        ),
        accepted_labels=("glicemia basale", "glucosio"),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    )

    assert result.recognized_label_occurrences == (
        ("glicemia basale", 1),
        ("glucosio", 1),
    )
    assert [(item.raw_value, item.section_specimen) for item in result.candidates] == [
        ("134", "serum"),
        ("0", "urine"),
    ]


def test_discovery_preserves_provenance_and_parses_supported_numbers() -> None:
    """Verify accepted numeric forms preserve exact source provenance.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    document = _document("doc-a")
    text = "Emoglobina 13,7 g/dL\nTAPSE = 22 mm\nFE: 1.234,56 %\nAzotemia 39 ma /AL\n"

    result = discover_candidates(
        (document,),
        (ExtractedText(document_id="doc-a", text=text),),
        document_hrefs={"doc-a": "../documents/report.txt"},
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    )

    assert result.analyzed_lines == 4
    assert [item.normalized_label for item in result.candidates] == [
        "azotemia",
        "emoglobina",
        "fe",
        "tapse",
    ]
    emoglobina = next(
        item for item in result.candidates if item.normalized_label == "emoglobina"
    )
    assert emoglobina.parsed_value == Decimal("13.7")
    assert emoglobina.raw_unit == "g/dL"
    assert emoglobina.document_href == "../documents/report.txt"
    assert emoglobina.document_name == "doc-a.txt"
    assert emoglobina.line_number == 1
    assert emoglobina.character_start == 0
    assert emoglobina.original_line == "Emoglobina 13,7 g/dL"
    fe = next(item for item in result.candidates if item.normalized_label == "fe")
    assert fe.parsed_value == Decimal("1234.56")
    assert fe.number_format == "grouped-point-decimal-comma"
    azotemia = next(
        item for item in result.candidates if item.normalized_label == "azotemia"
    )
    assert azotemia.raw_unit == "ma /AL"


def test_discovery_recognizes_complete_urine_exam_heading() -> None:
    """Verify complete urine-exam headings classify following values as urine.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_candidates(
        (_document("doc-a"),),
        (
            ExtractedText(
                document_id="doc-a",
                text="ESAME COMPLETO DELLE URINE\nGlucosio 500 mg/dl\n",
            ),
        ),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    )

    assert result.candidates[0].normalized_label == "glucosio"
    assert result.candidates[0].section_specimen == "urine"


def test_discovery_reports_ambiguous_single_separator_numbers() -> None:
    """Verify ambiguous numeric tokens are never interpreted silently.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_candidates(
        (_document("doc-a"),),
        (ExtractedText(document_id="doc-a", text="Creatinina 1,234 mg/dL\n"),),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    )

    candidate = result.candidates[0]
    assert candidate.parsed_value is None
    assert candidate.number_format is None
    assert candidate.reason_code == "REJECTED_AMBIGUOUS_NUMBER_FORMAT"


def test_discovery_recognizes_stacked_table_cells_with_exponent_unit() -> None:
    """Verify vertically extracted laboratory rows preserve the complete unit.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_candidates(
        (_document("doc-a"),),
        (
            ExtractedText(
                document_id="doc-a",
                text="PLT (Piastrine)\n    159\n\nx10^3/mmc 140-440\n",
            ),
        ),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    )

    candidate = next(
        item for item in result.candidates if item.normalized_label == "plt (piastrine)"
    )
    assert candidate.normalized_label == "plt (piastrine)"
    assert candidate.raw_value == "159"
    assert candidate.raw_unit == "x10^3/mmc"
    assert candidate.original_line == "PLT (Piastrine)\n    159\n\nx10^3/mmc 140-440"


def test_discovery_recognizes_asterisked_stacked_value() -> None:
    """Verify anomaly asterisks do not prevent stacked-value recognition.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_candidates(
        (_document("doc-a"),),
        (
            ExtractedText(
                document_id="doc-a",
                text="GLICEMIA\n*   120\nmg/dl\n70 - 100\n",
            ),
        ),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    )

    candidate = result.candidates[0]
    assert candidate.normalized_label == "glicemia"
    assert candidate.raw_value == "120"
    assert candidate.raw_unit == "mg/dl"


def test_discovery_recognizes_label_unit_reference_value_table_cells() -> None:
    """Verify column-ordered laboratory tables retain their correct values.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_candidates(
        (_document("doc-a"),),
        (
            ExtractedText(
                document_id="doc-a",
                text=(
                    "GLICEMIA BASALE\nmg/dl\n(60,0-100,0)\n134\n"
                    "EMOGLOBINA GLICOSILATA\n%\n<6\n7,0\n"
                    "EMOGLOBINA GLICOSILATA\nmmol/mol\n<42\n53,0\n"
                    "CREATININA\nmg/dl\n(0,72-1,25)\n1,06\n"
                ),
            ),
        ),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    )

    observed = [
        (candidate.normalized_label, candidate.raw_value, candidate.raw_unit)
        for candidate in result.candidates
    ]
    assert observed == [
        ("creatinina", "1,06", "mg/dl"),
        ("emoglobina glicosilata", "7,0", "%"),
        ("emoglobina glicosilata", "53,0", "mmol/mol"),
        ("glicemia basale", "134", "mg/dl"),
    ]


def test_discovery_recognizes_described_mass_value_cells() -> None:
    """Verify a described mass value is preferred to its percentage duplicate.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_candidates(
        (_document("doc-a"),),
        (
            ExtractedText(
                document_id="doc-a",
                text=(
                    "Hb GLICATA (HbA1c)\n"
                    "met. Elettrof.capillare\n"
                    "valore in massa\n"
                    "41,0\n"
                    "mmol/mol\n"
                    "standardizzazione IFCC: 20 - 42\n"
                    "valore percentuale\n"
                    "5,9\n"
                    "%\n"
                ),
            ),
        ),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    )

    assert [
        (candidate.normalized_label, candidate.raw_value, candidate.raw_unit)
        for candidate in result.candidates
        if candidate.normalized_label == "hb glicata (hba1c)"
    ] == [("hb glicata (hba1c)", "41,0", "mmol/mol")]


def test_discovery_groups_only_exact_normalized_labels() -> None:
    """Verify proposals require exact normalized labels and configured thresholds.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_candidates(
        (_document("doc-a"), _document("doc-b", "2026-02-03")),
        (
            ExtractedText(document_id="doc-a", text="Hb 13.7 g/dL\n"),
            ExtractedText(document_id="doc-b", text="Hb: 14.1 g/dL\nEmoglobina 14\n"),
        ),
        settings=DiscoverySettings(),
    )

    assert [group.normalized_label for group in result.proposed_groups] == ["hb"]
    assert len(result.proposed_groups[0].candidates) == 2


def test_discovery_excludes_labels_without_letters_or_with_configured_exclusion() -> (
    None
):
    """Verify generic label safeguards reduce proposal noise deterministically.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = discover_candidates(
        (_document("doc-a"),),
        (ExtractedText(document_id="doc-a", text="123 45\nProtocollo 12\n"),),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
            excluded_labels=("Protocollo",),
        ),
    )

    assert result.candidates == ()
