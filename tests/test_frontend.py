"""Static frontend generation tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sanikey.config import PersonConfig
from sanikey.frontend import build_frontend

if TYPE_CHECKING:
    from pathlib import Path


def test_build_frontend_writes_offline_static_files(tmp_path: Path) -> None:
    """Verify frontend generation writes static HTML, CSS, and JS."""

    person = PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=tmp_path / "documents",
        metadata_directory=tmp_path / "metadata",
        local_build=tmp_path / "generated",
        usb_uuid="1A2B-3C4D",
    )

    result = build_frontend(person)

    assert result.index.is_file()
    assert result.script.is_file()
    assert result.stylesheet.is_file()
    assert "Patient A" in result.index.read_text(encoding="utf-8")
    assert "telemetry" not in result.script.read_text(encoding="utf-8").lower()
