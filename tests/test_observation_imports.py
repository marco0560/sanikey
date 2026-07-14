"""Observation import tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sanikey.config import PersonConfig
from sanikey.errors import ConfigError
from sanikey.metadata import load_curated_metadata
from sanikey.observation_imports import (
    ensure_observation_imports_current,
    import_observations,
)

if TYPE_CHECKING:
    from pathlib import Path


def _person(tmp_path: Path) -> PersonConfig:
    """Build a synthetic patient config.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary test directory.

    Returns
    -------
    PersonConfig
        Patient configuration.
    """

    return PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=tmp_path / "documents",
        metadata_directory=tmp_path / "metadata",
        local_build=tmp_path / "generated",
        usb_uuid="1A2B-3C4D",
    )


def test_import_observations_writes_normalized_points(tmp_path: Path) -> None:
    """Verify manifest-driven observation import writes normalized metadata.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    person.metadata_directory.mkdir(parents=True)
    (person.source_documents / "peso.csv").write_text(
        "Data,Peso,Note\n2026-01-02,70.5,prima misura\n",
        encoding="utf-8",
    )
    (person.metadata_directory / "observation_imports.toml").write_text(
        """
[[series]]
id = "peso"
name = "Peso"
value_type = "numeric"
unit = "kg"

[[source]]
path = "peso.csv"
series_id = "peso"

[source.columns]
date = "Data"
numeric_value = "Peso"
note = "Note"
""".strip(),
        encoding="utf-8",
    )

    result = import_observations(person)
    metadata = load_curated_metadata(person.metadata_directory)

    assert result.series == 1
    assert result.points == 1
    assert metadata.observation_series[0].name == "Peso"
    assert metadata.observation_points[0].numeric_value == 70.5
    assert metadata.observation_points[0].note == "prima misura"
    ensure_observation_imports_current(person)


def test_import_observations_duplicate_warning_is_configurable(
    tmp_path: Path,
) -> None:
    """Verify same-day duplicate warnings can be disabled.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    person.metadata_directory.mkdir(parents=True)
    (person.source_documents / "pressione.csv").write_text(
        "Data,Sistolica,Diastolica\n2026-01-02,120,80\n2026-01-02,125,82\n",
        encoding="utf-8",
    )
    manifest = """
[[series]]
id = "pressione"
name = "Pressione"
value_type = "blood_pressure"
warn_duplicate_same_day = {warning}

[[source]]
path = "pressione.csv"
series_id = "pressione"

[source.columns]
date = "Data"
systolic = "Sistolica"
diastolic = "Diastolica"
"""
    (person.metadata_directory / "observation_imports.toml").write_text(
        manifest.format(warning="true"),
        encoding="utf-8",
    )

    result = import_observations(person)

    assert result.warnings == (
        "serie pressione: 2 misurazioni nella stessa data 2026-01-02",
    )

    (person.metadata_directory / "observation_imports.toml").write_text(
        manifest.format(warning="false"),
        encoding="utf-8",
    )
    result = import_observations(person)

    assert result.warnings == ()


def test_observation_import_stale_check_detects_source_changes(
    tmp_path: Path,
) -> None:
    """Verify build stale checks detect changed observation sources.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    person.metadata_directory.mkdir(parents=True)
    source = person.source_documents / "inr.csv"
    source.write_text("Data,INR\n2026-01-02,2.1\n", encoding="utf-8")
    (person.metadata_directory / "observation_imports.toml").write_text(
        """
[[series]]
id = "inr"
name = "INR"
value_type = "numeric"

[[source]]
path = "inr.csv"
series_id = "inr"

[source.columns]
date = "Data"
numeric_value = "INR"
""".strip(),
        encoding="utf-8",
    )
    import_observations(person)

    source.write_text("Data,INR\n2026-01-02,2.4\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="import-observations"):
        ensure_observation_imports_current(person)


def test_import_observations_supports_dirty_headers_fill_down_and_notes(
    tmp_path: Path,
) -> None:
    """Verify dirty real-world sheets can be imported declaratively.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    person.metadata_directory.mkdir(parents=True)
    (person.source_documents / "pressione.csv").write_text(
        "Titolo diario,,,,\n"
        "Data,Ora,Sistolica,Diastolica,Frequenza\n"
        "2026-01-02,08:00,120,80,60\n"
        ",21:00,125,82,64\n",
        encoding="utf-8",
    )
    (person.metadata_directory / "observation_imports.toml").write_text(
        """
[[series]]
id = "pressione"
name = "Pressione"
value_type = "blood_pressure"
warn_duplicate_same_day = false

[[source]]
path = "pressione.csv"
series_id = "pressione"
header_row = 2
fill_down = ["date"]

[source.columns]
date = "Data"
systolic = "Sistolica"
diastolic = "Diastolica"
pulse = "Frequenza"
note = "Ora"
""".strip(),
        encoding="utf-8",
    )

    result = import_observations(person)
    metadata = load_curated_metadata(person.metadata_directory)

    assert result.points == 2
    assert [point.observation_date for point in metadata.observation_points] == [
        "2026-01-02",
        "2026-01-02",
    ]
    assert metadata.observation_points[1].note == "21:00"


def test_import_observations_supports_multiple_extracts_and_approximate_dates(
    tmp_path: Path,
) -> None:
    """Verify one source row can produce multiple series.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    person.metadata_directory.mkdir(parents=True)
    (person.source_documents / "peso.csv").write_text(
        "Anno,Peso,BMI,Evento,Farmaci\n2025,141.2,46.58,dimissione,terapia invariata\n",
        encoding="utf-8",
    )
    (person.metadata_directory / "observation_imports.toml").write_text(
        """
[[series]]
id = "peso"
name = "Peso"
value_type = "numeric"
unit = "kg"

[[series]]
id = "bmi"
name = "BMI"
value_type = "numeric"
unit = "kg/m2"

[[source]]
path = "peso.csv"

[[source.extract]]
series_id = "peso"
date_policy = "year_start"
note_columns = ["Evento", "Farmaci"]

[source.extract.columns]
date = "Anno"
numeric_value = "Peso"

[[source.extract]]
series_id = "bmi"
date_policy = "year_start"
static_note = "BMI da foglio peso"

[source.extract.columns]
date = "Anno"
numeric_value = "BMI"
""".strip(),
        encoding="utf-8",
    )

    result = import_observations(person)
    metadata = load_curated_metadata(person.metadata_directory)

    assert result.series == 2
    assert result.points == 2
    assert [point.series_id for point in metadata.observation_points] == ["bmi", "peso"]
    assert {point.observation_date for point in metadata.observation_points} == {
        "2025-01-01"
    }
    assert "data approssimata" in (metadata.observation_points[0].note or "")
    assert "data approssimata" in (metadata.observation_points[1].note or "")


def test_import_observations_supports_compound_pressure_values(
    tmp_path: Path,
) -> None:
    """Verify compound pressure cells can be parsed with a named regex.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    person.metadata_directory.mkdir(parents=True)
    (person.source_documents / "pressione.csv").write_text(
        "Data,Misura\n2026-01-02,113/65 54\n",
        encoding="utf-8",
    )
    (person.metadata_directory / "observation_imports.toml").write_text(
        r"""
[[series]]
id = "pressione"
name = "Pressione"
value_type = "blood_pressure"

[[source]]
path = "pressione.csv"
series_id = "pressione"

[source.columns]
date = "Data"

[source.compound_value]
column = "Misura"
pattern = '^(?P<systolic>\d+)/(?P<diastolic>\d+)\s+(?P<pulse>\d+)$'
""".strip(),
        encoding="utf-8",
    )

    import_observations(person)
    point = load_curated_metadata(person.metadata_directory).observation_points[0]

    assert point.systolic == 113
    assert point.diastolic == 65
    assert point.pulse == 54


def test_import_observations_supports_repeating_matrix_layout(
    tmp_path: Path,
) -> None:
    """Verify repeated matrix pressure logs can be normalized.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    person = _person(tmp_path)
    person.source_documents.mkdir(parents=True)
    person.metadata_directory.mkdir(parents=True)
    (person.source_documents / "matrix.csv").write_text(
        ",Domenica 28,lunedi 29,martedi 30,mercoledi 1\n"
        "mattino,124/84 67,135/82 67,114/68 60,115/73 75\n"
        "pomeriggio,106/61 67,104/60 57,108/63 62,111/75 93\n",
        encoding="utf-8",
    )
    (person.metadata_directory / "observation_imports.toml").write_text(
        r"""
[[series]]
id = "pressione"
name = "Pressione"
value_type = "blood_pressure"
warn_duplicate_same_day = false

[[source]]
path = "matrix.csv"
layout = "repeating_matrix"

[source.matrix]
year = 2008
start_month = 9
block_height = 3
date_column_start = 2
value_rows = ["mattino", "pomeriggio"]
date_column = "Data"
value_column = "Misura"
label_column = "Fascia"

[[source.extract]]
series_id = "pressione"
note_columns = ["Fascia"]

[source.extract.columns]
date = "Data"

[source.extract.compound_value]
column = "Misura"
pattern = '^(?P<systolic>\d+)/(?P<diastolic>\d+)\s+(?P<pulse>\d+)$'
""".strip(),
        encoding="utf-8",
    )

    result = import_observations(person)
    metadata = load_curated_metadata(person.metadata_directory)

    assert result.points == 8
    assert metadata.observation_points[0].observation_date == "2008-09-28"
    assert metadata.observation_points[-1].observation_date == "2008-10-01"
    assert metadata.observation_points[-1].note == "pomeriggio"
