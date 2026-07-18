"""AIFA medication-leaflet integration tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sanikey.leaflets import (
    download_confirmed_leaflets,
    leaflet_download_dates,
    lookup_aifa_candidates,
    medication_fingerprint,
    write_confirmed_references,
)
from sanikey.models import Medication, MedicationLeaflet

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_lookup_aifa_candidates_distinguishes_unavailable_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify an unavailable AIFA service is not reported as no candidate.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    monkeypatch.setattr("sanikey.leaflets._aifa_json", lambda _path: None)

    assert lookup_aifa_candidates(Medication("drug-a", "Drug A")) is None


def test_download_confirmed_leaflets_records_only_successful_fi_updates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the displayed date denotes a newly downloaded local FI.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    class Response:
        """Provide a minimal byte response context manager."""

        def __enter__(self) -> Response:
            """Enter the response context."""

            return self

        def __exit__(self, *_args: object) -> None:
            """Exit the response context."""

        def read(self) -> bytes:
            """Return synthetic PDF content."""

            return b"%PDF-synthetic"

    monkeypatch.setattr(
        "sanikey.leaflets.urlopen", lambda *_args, **_kwargs: Response()
    )
    reference = MedicationLeaflet("drug-a", "123", "456")

    dates = download_confirmed_leaflets(tmp_path, (reference,))

    assert dates["drug-a"]
    assert leaflet_download_dates(tmp_path) == dates
    manifest = json.loads(
        (tmp_path / "manifests" / "medication-leaflets.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["downloaded_at"] == dates


def test_write_confirmed_references_persists_lookup_fingerprint(tmp_path: Path) -> None:
    """Verify persisted references retain the curated identity fingerprint.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    medication = Medication("drug-a", "Drug A", "Ingredient", "tablet", "10 mg")
    target = write_confirmed_references(
        tmp_path,
        (
            MedicationLeaflet(
                "drug-a",
                "123",
                "456",
                source_fingerprint=medication_fingerprint(medication),
            ),
        ),
    )

    assert 'source_fingerprint = "' in target.read_text(encoding="utf-8")
