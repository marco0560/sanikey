"""Static JSON export tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sanikey.config import PersonConfig
from sanikey.documents import scan_documents
from sanikey.exports import generate_exports
from sanikey.metadata import load_curated_metadata

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


def test_generate_exports_writes_frontend_data(tmp_path: Path) -> None:
    """Verify static JSON exports include document, search, timeline, and summary data.

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
    (person.source_documents / "20260102 Report.txt").write_text(
        "synthetic",
        encoding="utf-8",
    )
    person.metadata_directory.mkdir()
    (person.metadata_directory / "document_tags.toml").write_text(
        """
[tags]
"20260102 Report.txt" = ["report"]
""",
        encoding="utf-8",
    )
    (person.metadata_directory / "timeline_events.toml").write_text(
        """
[[event]]
id = "therapy-interval"
title = "Therapy interval"
start_date = "2026-01-01"
end_date = "2026-01-31"
source = "manual"
links = ["therapy-a"]
""",
        encoding="utf-8",
    )

    result = generate_exports(
        person,
        scan_documents(person),
        load_curated_metadata(person.metadata_directory),
    )

    documents = json.loads(result.documents.read_text(encoding="utf-8"))
    search = json.loads(result.search.read_text(encoding="utf-8"))
    timeline = json.loads(result.timeline.read_text(encoding="utf-8"))
    summary = json.loads(result.summary.read_text(encoding="utf-8"))
    assert documents[0]["tags"] == ["report"]
    assert search[0]["text"] == "Report uncategorized report"
    assert timeline[0]["id"] == "therapy-interval"
    assert timeline[0]["start_date"] == "2026-01-01"
    assert timeline[0]["end_date"] == "2026-01-31"
    assert timeline[0]["links"] == ["therapy-a"]
    assert timeline[1]["start_date"] == "2026-01-02"
    assert summary["document_count"] == 1
