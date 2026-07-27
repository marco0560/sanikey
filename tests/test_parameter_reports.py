"""Tests for deterministic parameter discovery artefacts."""

from __future__ import annotations

import tomllib
from pathlib import Path

from sanikey.documents import ExtractedText
from sanikey.models import DocumentRecord
from sanikey.parameter_reports import write_parameter_reports
from sanikey.parameter_slices import DiscoverySettings, discover_candidates


def _document(document_id: str, date: str) -> DocumentRecord:
    """Build one synthetic parameter source document.

    Parameters
    ----------
    document_id : str
        Stable document identifier.
    date : str
        Authoritative document date.

    Returns
    -------
    DocumentRecord
        Synthetic document record.
    """

    return DocumentRecord(
        document_id=document_id,
        patient_id="patient-a",
        path=Path(f"/{document_id}.txt"),
        title="Referto sintetico",
        category="Laboratorio",
        kind="text",
        sha256=document_id * 8,
        date=date,
    )


def test_reports_write_disabled_deterministic_parameter_rule_scaffold(
    tmp_path: Path,
) -> None:
    """Verify discovery emits a stable review-only TOML scaffold.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    discovery = discover_candidates(
        (_document("doc-a", "2026-01-02"), _document("doc-b", "2026-02-03")),
        (
            ExtractedText(document_id="doc-a", text="Hb: 13.7 g/dL\n"),
            ExtractedText(document_id="doc-b", text="Hb: <14.1 g/dL\n"),
        ),
        settings=DiscoverySettings(),
    )

    write_parameter_reports(tmp_path, discovery)
    proposal = tmp_path / "reports" / "parameter-rules.proposed.toml"
    first = proposal.read_bytes()
    write_parameter_reports(tmp_path, discovery)

    parsed = tomllib.loads(proposal.read_text(encoding="utf-8"))
    rule = parsed["parameters"]["hb"]
    assert proposal.read_bytes() == first
    assert rule["enabled"] is False
    assert rule["value_type"] == "qualified-scalar"
    assert rule["number_formats"] == ["decimal-point"]
    assert rule["units"] == ["g/dL"]
