"""Tests for curated longitudinal parameter rules."""

from __future__ import annotations

from pathlib import Path

from sanikey.config import SearchDictionary
from sanikey.documents import ExtractedText
from sanikey.models import (
    CuratedMetadata,
    DocumentRecord,
    ObservationPoint,
    ObservationSeries,
)
from sanikey.parameter_rules import (
    _series_compatible,
    build_parameter_slices,
    load_parameter_rules,
    merge_parameter_observations,
)
from sanikey.parameter_slices import DiscoverySettings, discover_candidates


def _document(
    document_id: str, document_date: str | None = "2026-01-02"
) -> DocumentRecord:
    """Build one synthetic parameter source document.

    Parameters
    ----------
    document_id : str
        Stable test document id.
    document_date : str | None, optional
        Authoritative document date.

    Returns
    -------
    DocumentRecord
        Synthetic document.
    """

    return DocumentRecord(
        document_id=document_id,
        patient_id="patient-a",
        path=Path(f"/{document_id}.txt"),
        title="Referto sintetico",
        category="Laboratorio",
        kind="text",
        sha256="a" * 64,
        date=document_date,
    )


def _rules(path: Path) -> None:
    """Write a synthetic curator-approved parameter rule.

    Parameters
    ----------
    path : pathlib.Path
        Parameters TOML target.

    Returns
    -------
    None
    """

    path.write_text(
        """
[parameters.emoglobina]
display_name = "Emoglobina"
term = "emoglobina"
version = 1
value_type = "qualified-scalar"
number_formats = ["integer", "decimal-point", "decimal-comma"]
unit_policy = "required"
enabled = true
units = ["g/dL", "g/l"]
canonical_unit = "g/dL"
minimum = 1
maximum = 30
document_categories = ["Laboratorio"]

[[parameters.emoglobina.conversions]]
from_unit = "g/l"
to_unit = "g/dL"
multiplier = 0.1
offset = 0
version = 1
""".strip(),
        encoding="utf-8",
    )


def test_rules_create_provenance_rich_point_with_explicit_conversion(
    tmp_path: Path,
) -> None:
    """Verify configured synonym and conversion create one derived point.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    None
    """

    path = tmp_path / "parameters.toml"
    _rules(path)
    rules = load_parameter_rules(
        path,
        SearchDictionary(terms={"emoglobina": ("Hb", "HGB", "emoglobina")}),
    )
    candidates = discover_candidates(
        (_document("doc-a"),),
        (ExtractedText(document_id="doc-a", text="Hb: 137 g/l\n"),),
        document_hrefs={"doc-a": "../documents/report.txt"},
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    ).candidates

    result = build_parameter_slices(candidates, rules)

    assert len(result.series) == 1
    assert result.series[0].id == "emoglobina"
    point = result.points[0]
    assert point.numeric_value == 13.7
    assert point.raw_value == "137"
    assert point.raw_unit == "g/l"
    assert point.normalized_unit == "g/dL"
    assert point.source_kind == "document-extraction"
    assert point.source_reference == "../documents/report.txt"
    assert point.document_href == "../documents/report.txt"
    assert point.rule_id == "emoglobina"
    assert result.decisions[-1].reason_code == "ACCEPTED_CONFIGURED_SYNONYM"


def test_merge_integrates_same_name_series_after_rule_conversion(
    tmp_path: Path,
) -> None:
    """Verify an imported series and a converted parameter share one target.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    path = tmp_path / "parameters.toml"
    _rules(path)
    rules = load_parameter_rules(
        path,
        SearchDictionary(terms={"emoglobina": ("Hb",)}),
    )
    candidates = discover_candidates(
        (_document("doc-a"),),
        (ExtractedText(document_id="doc-a", text="Hb: 137 g/l\n"),),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    ).candidates
    result = build_parameter_slices(candidates, rules)
    imported = ObservationPoint(
        id="excel-hb",
        series_id="diario-emoglobina",
        observation_date="2026-01-02",
        source_type="spreadsheet",
        source_reference="diario.xlsx",
        numeric_value=13.7,
    )
    metadata = CuratedMetadata(
        observation_series=(
            ObservationSeries(
                id="diario-emoglobina",
                name="Emoglobina",
                value_type="numeric",
                unit="g/dL",
            ),
        ),
        observation_points=(imported,),
    )

    merged = merge_parameter_observations(metadata, result)

    assert merged.observation_series == metadata.observation_series
    assert [point.series_id for point in merged.observation_points] == [
        "diario-emoglobina",
        "diario-emoglobina",
    ]
    assert merged.observation_points[1].numeric_value == 13.7
    assert merged.observation_points[1].source_kind == "document-extraction"


def test_series_compatibility_groups_numeric_scalar_variants() -> None:
    """Verify scalar observation representations share one series semantics.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    numeric = ObservationSeries("numeric", "Parametro", "numeric", "mg/dl")
    scalar = ObservationSeries("scalar", "Parametro", "scalar", "mg/dl")
    qualified = ObservationSeries("qualified", "Parametro", "qualified-scalar", "mg/dl")
    pressure = ObservationSeries("pressure", "Parametro", "blood_pressure", "mg/dl")

    assert _series_compatible(numeric, scalar)
    assert _series_compatible(numeric, qualified)
    assert _series_compatible(scalar, qualified)
    assert not _series_compatible(numeric, pressure)


def test_rules_match_units_case_insensitively_and_keep_configured_typography(
    tmp_path: Path,
) -> None:
    """Verify unit matching ignores capitalization while preserving rule output.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    path = tmp_path / "parameters.toml"
    path.write_text(
        """
[parameters.glicemia]
display_name = "Glicemia"
term = "glicemia"
version = 1
value_type = "scalar"
number_formats = ["integer"]
unit_policy = "required"
enabled = true
units = ["mg/dl"]
canonical_unit = "mg/dl"
document_categories = ["Laboratorio"]
""".strip(),
        encoding="utf-8",
    )
    rules = load_parameter_rules(
        path,
        SearchDictionary(terms={"glicemia": ("GLUCOSIO",)}),
    )
    candidates = discover_candidates(
        (_document("doc-a"),),
        (ExtractedText(document_id="doc-a", text="GLUCOSIO 94 mg/dL\n"),),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    ).candidates

    result = build_parameter_slices(candidates, rules)

    assert result.points[0].numeric_value == 94
    assert result.points[0].raw_unit == "mg/dL"
    assert result.points[0].normalized_unit == "mg/dl"


def test_rules_reject_missing_document_date_and_keep_metadata_separate(
    tmp_path: Path,
) -> None:
    """Verify undated documents cannot create timeline points.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    None
    """

    path = tmp_path / "parameters.toml"
    _rules(path)
    rules = load_parameter_rules(
        path,
        SearchDictionary(terms={"emoglobina": ("Hb",)}),
    )
    candidates = discover_candidates(
        (_document("doc-a", None),),
        (ExtractedText(document_id="doc-a", text="Hb 13.7 g/dL\n"),),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    ).candidates

    result = build_parameter_slices(candidates, rules)

    assert result.points == ()
    assert result.decisions[0].reason_code == "REJECTED_DOCUMENT_DATE_MISSING"
    merged = merge_parameter_observations(CuratedMetadata(), result)
    assert merged.observation_series == ()
    assert merged.observation_points == ()


def test_rules_convert_stacked_piastrine_unit_to_canonical_series(
    tmp_path: Path,
) -> None:
    """Verify an explicit conversion keeps stacked platelet values in one series.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    path = tmp_path / "parameters.toml"
    path.write_text(
        """
[parameters.piastrine]
display_name = "Piastrine"
term = "piastrine"
version = 1
value_type = "scalar"
number_formats = ["integer"]
unit_policy = "required"
enabled = true
series_id = "analisi-piastrine"
units = ["x10", "x10^3/mmc"]
canonical_unit = "x10"
document_categories = ["Laboratorio"]

[[parameters.piastrine.conversions]]
from_unit = "x10^3/mmc"
to_unit = "x10"
multiplier = 1
offset = 0
version = 1
""".strip(),
        encoding="utf-8",
    )
    rules = load_parameter_rules(
        path,
        SearchDictionary(terms={"piastrine": ("PLT (Piastrine)",)}),
    )
    candidates = discover_candidates(
        (_document("doc-a"),),
        (
            ExtractedText(
                document_id="doc-a",
                text="PLT (Piastrine)\n159\nx10^3/mmc\n",
            ),
        ),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    ).candidates

    result = build_parameter_slices(candidates, rules)

    assert result.points[0].series_id == "analisi-piastrine"
    assert result.points[0].normalized_unit == "x10"
    assert result.points[0].numeric_value == 159


def test_rules_accept_column_ordered_hba1c_table_cells(tmp_path: Path) -> None:
    """Verify HbA1c table cells use the label's configured synonym and unit.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    path = tmp_path / "parameters.toml"
    path.write_text(
        """
[parameters.emoglobina_glicata]
display_name = "Emoglobina glicata"
term = "emoglobina_glicata"
version = 2
value_type = "scalar"
number_formats = ["integer", "decimal-comma"]
unit_policy = "required"
enabled = true
units = ["%", "mmol/mol"]
canonical_unit = "%"
document_categories = ["Laboratorio"]

[[parameters.emoglobina_glicata.conversions]]
from_unit = "mmol/mol"
to_unit = "%"
multiplier = 0.0915
offset = 2.15
version = 1
""".strip(),
        encoding="utf-8",
    )
    rules = load_parameter_rules(
        path,
        SearchDictionary(terms={"emoglobina_glicata": ("emoglobina glicosilata",)}),
    )
    candidates = discover_candidates(
        (_document("doc-a"),),
        (
            ExtractedText(
                document_id="doc-a",
                text=(
                    "EMOGLOBINA GLICOSILATA\n%\n<6\n7,0\n"
                    "EMOGLOBINA GLICOSILATA\nmmol/mol\n<42\n53,0\n"
                    "EMOGLOBINA GLICOSILATA\nmmol/mol\n<42\n32\n"
                ),
            ),
        ),
        settings=DiscoverySettings(
            min_occurrences=1,
            min_distinct_documents=1,
            min_distinct_dates=1,
        ),
    ).candidates

    result = build_parameter_slices(candidates, rules)

    assert sorted(
        (point.raw_value, point.raw_unit, point.numeric_value)
        for point in result.points
    ) == [
        ("32", "mmol/mol", 5.078),
        ("53,0", "mmol/mol", 6.9995),
        ("7,0", "%", 7.0),
    ]
