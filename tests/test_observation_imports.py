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
