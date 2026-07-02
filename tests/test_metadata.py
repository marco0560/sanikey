"""Curated metadata loader tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sanikey.errors import ConfigError
from sanikey.metadata import load_curated_metadata

if TYPE_CHECKING:
    from pathlib import Path


def test_load_curated_metadata_reads_supported_files(tmp_path: Path) -> None:
    """Verify curated metadata files are aggregated.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    (tmp_path / "problems.toml").write_text(
        """
[[problem]]
id = "hypertension"
title = "Hypertension"
status = "active"
""",
        encoding="utf-8",
    )
    (tmp_path / "medications.toml").write_text(
        """
[[medication]]
id = "drug-a"
name = "Drug A"
active_ingredient = "Ingredient A"
form = "compresse"
strength_per_unit = "100 mg"
""",
        encoding="utf-8",
    )
    (tmp_path / "therapies.toml").write_text(
        """
[[therapy]]
id = "therapy-a"
medication_id = "drug-a"
start_date = "2026-01-01"
dosage = "1 tablet"
schedule = ["risveglio", "cena"]
instructions = "dopo il pasto"
""",
        encoding="utf-8",
    )
    (tmp_path / "procedures.toml").write_text(
        """
[[procedure]]
id = "procedure-a"
title = "Procedure A"
date = "2026-01-02"
status = "completed"
""",
        encoding="utf-8",
    )
    (tmp_path / "observations.toml").write_text(
        """
[[observation]]
id = "observation-a"
kind = "weight"
value = "70 kg"
date = "2026-01-03"
""",
        encoding="utf-8",
    )
    (tmp_path / "timeline_events.toml").write_text(
        """
[[event]]
id = "event-a"
title = "Event A"
start_date = "2026-01-04"
links = ["procedure-a"]
""",
        encoding="utf-8",
    )
    (tmp_path / "document_tags.toml").write_text(
        """
[tags]
"20260101 Report.pdf" = ["report", "test"]
""",
        encoding="utf-8",
    )
    (tmp_path / "clinical_summary.toml").write_text(
        'summary = """Synthetic summary.\nSecond line."""\n',
        encoding="utf-8",
    )

    metadata = load_curated_metadata(tmp_path)

    assert metadata.problems[0].id == "hypertension"
    assert metadata.medications[0].name == "Drug A"
    assert metadata.medications[0].form == "compresse"
    assert metadata.medications[0].strength_per_unit == "100 mg"
    assert metadata.therapies[0].medication_id == "drug-a"
    assert metadata.therapies[0].schedule == ("risveglio", "cena")
    assert metadata.therapies[0].instructions == "dopo il pasto"
    assert metadata.procedures[0].status == "completed"
    assert metadata.observations[0].value == "70 kg"
    assert metadata.timeline_events[0].links == ("procedure-a",)
    assert metadata.document_tags["20260101 Report.pdf"] == ("report", "test")
    assert metadata.clinical_summary == "Synthetic summary.\nSecond line."


def test_load_curated_metadata_allows_missing_directory(tmp_path: Path) -> None:
    """Verify missing metadata directories produce empty metadata.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    metadata = load_curated_metadata(tmp_path / "missing")

    assert metadata.problems == ()
    assert metadata.clinical_summary is None


def test_load_curated_metadata_rejects_malformed_items(tmp_path: Path) -> None:
    """Verify present malformed metadata files fail deterministically.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    (tmp_path / "problems.toml").write_text(
        """
[[problem]]
id = "missing-title"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="title"):
        load_curated_metadata(tmp_path)


def test_load_curated_metadata_rejects_invalid_toml(tmp_path: Path) -> None:
    """Verify syntactically invalid curated metadata fails.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    (tmp_path / "therapies.toml").write_text(
        "[[therapy]\nid = 'broken'\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="invalid TOML"):
        load_curated_metadata(tmp_path)
