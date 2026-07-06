"""Static frontend generation tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sanikey.config import PersonConfig
from sanikey.frontend import build_frontend

if TYPE_CHECKING:
    from pathlib import Path


def test_build_frontend_writes_offline_static_files(tmp_path: Path) -> None:
    """Verify frontend generation writes static HTML, CSS, and JS.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

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
    script = result.script.read_text(encoding="utf-8").lower()
    index = result.index.read_text(encoding="utf-8").lower()
    stylesheet = result.stylesheet.read_text(encoding="utf-8").lower()
    generated = "\n".join((index, script, stylesheet))
    forbidden_fragments = (
        "telemetry",
        "document.cookie",
        "localstorage",
        "sessionstorage",
        "indexeddb",
        "http://",
        "https://",
    )
    assert not any(fragment in generated for fragment in forbidden_fragments)
    assert 'script src="data.js"' in index
    assert "fetch(" not in script
    assert "window.sanikey_data" in script
    assert "function formatdate(value)" in script
    assert "${match[3]}/${match[2]}/${match[1]}" in script
    assert "formatdaterange(item.start_date, item.end_date)" in script
    assert "formatdate(item.date)" in script
