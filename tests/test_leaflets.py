"""AIFA medication-leaflet integration tests."""

from __future__ import annotations

import json
from io import BytesIO
from typing import TYPE_CHECKING
from urllib.error import HTTPError

from sanikey.leaflets import (
    download_confirmed_leaflets,
    leaflet_download_dates,
    leaflet_urls,
    lookup_aifa_candidate_search,
    lookup_aifa_candidates,
    medication_fingerprint,
    probe_leaflet_documents,
    write_confirmed_references,
)
from sanikey.models import Medication, MedicationLeaflet, MedicationLeafletExclusion

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


def test_lookup_aifa_candidates_filters_incompatible_formulations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify dosage and form remove unrelated formulations of one medicine.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    monkeypatch.setattr(
        "sanikey.leaflets._aifa_json",
        lambda _path: {
            "data": {
                "content": [
                    {
                        "principiAttiviIt": ["ATENOLOLO"],
                        "formaFarmaceutica": "Compressa",
                        "descrizioneFormaDosaggio": f"{dose} mg COMPRESSA",
                        "medicinale": {
                            "codiceSis": 123,
                            "aic6": 456,
                            "denominazioneMedicinale": "ATENOLOLO",
                        },
                    }
                    for dose in (25, 50, 100)
                ]
            }
        },
    )

    candidates = lookup_aifa_candidates(
        Medication(
            "atenololo",
            "Atenololo 100 mg",
            "Atenololo",
            "compresse",
            "100 mg",
        )
    )

    assert candidates is not None
    assert [candidate.strength for candidate in candidates] == ["100 mg COMPRESSA"]


def test_lookup_aifa_candidates_rejects_unmatched_catalog_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify incomplete or incompatible AIFA data does not become a fallback.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    monkeypatch.setattr(
        "sanikey.leaflets._aifa_json",
        lambda _path: {
            "data": {
                "content": [
                    {
                        "formaFarmaceutica": "Gocce orali",
                        "descrizioneFormaDosaggio": "10 mg GOCCE",
                        "medicinale": {
                            "codiceSis": 123,
                            "aic6": 456,
                            "denominazioneMedicinale": "Medicinale lontano",
                        },
                    }
                ]
            }
        },
    )

    candidates = lookup_aifa_candidates(
        Medication("zanedip", "Zanedip 10 mg", "Lercanidipina", "compresse", "10 mg")
    )

    assert candidates == ()


def test_aifa_search_uses_commercial_and_active_ingredient_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify active-ingredient search supplies plausible review candidates.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    calls: list[str] = []

    def response(path: str) -> dict[str, object]:
        """Return a candidate only for the active-ingredient query.

        Parameters
        ----------
        path : str
            API-relative request path.

        Returns
        -------
        dict[str, object]
            Synthetic AIFA response.
        """

        calls.append(path)
        return {
            "data": {
                "content": [
                    {
                        "principiAttiviIt": ["PARACETAMOLO", "CODEINA FOSFATO"],
                        "formaFarmaceutica": "Compressa",
                        "descrizioneFormaDosaggio": "500 mg + 30 mg COMPRESSA",
                        "medicinale": {
                            "codiceSis": 123,
                            "aic6": 456,
                            "denominazioneMedicinale": "CODAMOL",
                        },
                    }
                ]
            }
        }

    monkeypatch.setattr("sanikey.leaflets._aifa_json", response)

    search = lookup_aifa_candidate_search(
        Medication(
            "codamol",
            "Codamol 500 mg + 30 mg",
            "Paracetamolo e codeina",
            "compresse",
            "500/30",
        )
    )

    assert search is not None
    assert len(calls) == 2
    assert search.exact
    assert search.exact[0].title == "CODAMOL"


def test_aifa_search_keeps_only_plausible_review_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify an incomplete matching candidate is separated for review.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    monkeypatch.setattr(
        "sanikey.leaflets._aifa_json",
        lambda _path: {
            "data": {
                "content": [
                    {
                        "principiAttiviIt": ["LERCANIDIPINA"],
                        "formaFarmaceutica": "Gocce orali",
                        "descrizioneFormaDosaggio": "10 mg GOCCE",
                        "medicinale": {
                            "codiceSis": 123,
                            "aic6": 456,
                            "denominazioneMedicinale": "ZANEDIP",
                        },
                    },
                    {
                        "principiAttiviIt": ["SODIO"],
                        "formaFarmaceutica": "Gocce orali",
                        "descrizioneFormaDosaggio": "10 mg GOCCE",
                        "medicinale": {
                            "codiceSis": 124,
                            "aic6": 457,
                            "denominazioneMedicinale": "DIS 10",
                        },
                    },
                ]
            }
        },
    )

    search = lookup_aifa_candidate_search(
        Medication("zanedip", "Zanedip 10 mg", "Lercanidipina", "compresse", "10 mg")
    )

    assert search is not None
    assert search.exact == ()
    assert [candidate.title for candidate in search.review] == ["ZANEDIP"]
    assert search.review[0].mismatches == ("forma",)


def test_download_confirmed_leaflets_records_complete_pdf_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the displayed date denotes one complete local AIFA update.

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

    result = download_confirmed_leaflets(tmp_path, (reference,))

    assert result.downloaded_at["drug-a"]
    assert result.failures == ()
    assert leaflet_download_dates(tmp_path) == result.downloaded_at
    manifest = json.loads(
        (tmp_path / "manifests" / "medication-leaflets.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["downloaded_at"] == result.downloaded_at


def test_download_confirmed_leaflets_reports_failure_without_partial_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify one failed document retains the previous complete local pair.

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
        """Provide a minimal successful PDF response."""

        def __enter__(self) -> Response:
            """Enter the response context."""

            return self

        def __exit__(self, *_args: object) -> None:
            """Exit the response context."""

        def read(self) -> bytes:
            """Return a synthetic PDF payload."""

            return b"%PDF-new"

    reference = MedicationLeaflet("drug-a", "123", "456")
    target = tmp_path / "medication-leaflets" / "drug-a"
    target.mkdir(parents=True)
    (target / "foglio-illustrativo.pdf").write_bytes(b"%PDF-old-fi")
    (target / "rcp.pdf").write_bytes(b"%PDF-old-rcp")

    def failing_rcp(request: object, **_kwargs: object) -> Response:
        """Return FI and fail RCP with an AIFA JSON diagnostic.

        Parameters
        ----------
        request : object
            AIFA request object.
        _kwargs : object
            Ignored urlopen keyword arguments.

        Returns
        -------
        Response
            Successful FI response.

        Raises
        ------
        urllib.error.HTTPError
            For the RCP request.
        """

        url = request.full_url  # type: ignore[attr-defined]
        if url.endswith("ts=RCP"):
            raise HTTPError(
                url,
                503,
                "Servizio non disponibile",
                None,
                BytesIO(b'{"description":"servizio sospeso"}'),
            )
        return Response()

    monkeypatch.setattr("sanikey.leaflets.urlopen", failing_rcp)

    result = download_confirmed_leaflets(tmp_path, (reference,))

    assert result.downloaded_at == {}
    assert len(result.failures) == 1
    assert result.failures[0].kind == "RCP"
    assert result.failures[0].reason == "HTTP 503: servizio sospeso"
    assert result.failures[0].url.endswith("stampati?ts=RCP")
    assert (target / "foglio-illustrativo.pdf").read_bytes() == b"%PDF-old-fi"
    assert (target / "rcp.pdf").read_bytes() == b"%PDF-old-rcp"


def test_download_confirmed_leaflets_rejects_non_pdf_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify an AIFA error body cannot be stored as a leaflet PDF.

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

    monkeypatch.setattr(
        "sanikey.leaflets.urlopen",
        lambda *_args, **_kwargs: BytesIO(b'{"message":"non disponibile"}'),
    )

    result = download_confirmed_leaflets(
        tmp_path,
        (MedicationLeaflet("drug-a", "123", "456"),),
    )

    assert result.downloaded_at == {}
    assert [failure.kind for failure in result.failures] == ["FI", "RCP"]
    assert all(
        failure.reason == "risposta AIFA non in formato PDF"
        for failure in result.failures
    )
    assert not (tmp_path / "medication-leaflets" / "drug-a").exists()


def test_probe_leaflet_documents_uses_aifa_error_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify AIFA's detailed error list is retained in the failure message.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    def unavailable(request: object, **_kwargs: object) -> BytesIO:
        """Raise an AIFA HTTP error containing an ``errors`` list.

        Parameters
        ----------
        request : object
            AIFA request object.
        _kwargs : object
            Ignored urlopen keyword arguments.

        Returns
        -------
        io.BytesIO
            This function always raises before returning.

        Raises
        ------
        urllib.error.HTTPError
            A synthetic AIFA unavailable-document response.
        """

        url = request.full_url  # type: ignore[attr-defined]
        raise HTTPError(
            url,
            404,
            "Not Found",
            None,
            BytesIO(b'{"errors":["Stampato RCP/FI non disponibile"]}'),
        )

    monkeypatch.setattr("sanikey.leaflets.urlopen", unavailable)

    failures = probe_leaflet_documents(MedicationLeaflet("drug-a", "123", "456"))

    assert [failure.kind for failure in failures] == ["FI", "RCP"]
    assert all(
        failure.reason == "HTTP 404: Stampato RCP/FI non disponibile"
        for failure in failures
    )


def test_leaflet_urls_use_aifa_printed_document_query() -> None:
    """Verify public FI and RCP links use the AIFA document query parameter.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    urls = leaflet_urls(MedicationLeaflet("drug-a", "123", "456"))

    assert urls["aifa_fi_url"].endswith("/123/farmaci/456/stampati?ts=FI")
    assert urls["aifa_rcp_url"].endswith("/123/farmaci/456/stampati?ts=RCP")


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


def test_write_confirmed_references_persists_non_aifa_marker(tmp_path: Path) -> None:
    """Verify non-AIFA medications are persisted with the references.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    target = write_confirmed_references(
        tmp_path,
        (),
        (MedicationLeafletExclusion("supplement"),),
    )

    assert '[[unavailable]]\nmedication_id = "supplement"' in target.read_text(
        encoding="utf-8"
    )
