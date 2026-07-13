"""Static frontend generation tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sanikey.config import PersonConfig, UiConfig
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
    assert result.helper.is_file()
    assert result.material_script.is_file()
    assert result.material_stylesheet.is_file()
    assert "Patient A" in result.index.read_text(encoding="utf-8")
    assert 'data-tab-button="documents"' in result.index.read_text(encoding="utf-8")
    assert 'data-tab-button="summary"' in result.index.read_text(encoding="utf-8")
    assert "Aiuto ricerca base" in result.index.read_text(encoding="utf-8")
    assert "Ricerca avanzata" in result.index.read_text(encoding="utf-8")
    script = result.script.read_text(encoding="utf-8").lower()
    helper = result.helper.read_text(encoding="utf-8").lower()
    material = result.material_script.read_text(encoding="utf-8").lower()
    index = result.index.read_text(encoding="utf-8").lower()
    stylesheet = result.stylesheet.read_text(encoding="utf-8").lower()
    material_stylesheet = result.material_stylesheet.read_text(encoding="utf-8").lower()
    generated = "\n".join(
        (index, script, helper, stylesheet, material, material_stylesheet)
    )
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
    assert 'script src="assets/ui-helper.js"' in index
    assert 'script type="module" src="assets/material-web.js"' in index
    assert 'href="assets/material-web.css"' in index
    assert "fetch(" not in script
    assert "window.sanikey_data" in script
    assert "window.sanikey_content_search" in script
    assert "function parseadvancedquery(query)" in script
    assert 'script.src = "content-search.js"' in script
    assert "and" in script
    assert "or" in script
    assert "not" in script
    assert "window.sanikeyui" in helper
    assert "setuptabs" in helper
    assert "custom-elements" not in material
    assert "customElements.define".lower() in material
    assert "function formatdate(value)" in script
    assert "${match[3]}/${match[2]}/${match[1]}" in script
    assert "formatdaterange(item.start_date, item.end_date)" in script
    assert "formatdate(item.date)" in script
    assert "clinical_summary_html" in script
    assert "markdown_html" in script
    assert "item.href" in script
    assert "item.viewer_href" in script
    assert "apri studio dicom" in script
    assert "renderclinicaldashboard" in script
    assert "renderquicksearch" in script
    assert "rendersearchresults" in script
    assert "section_links" not in script
    assert "section-links" in stylesheet
    assert "data.clinical" in script
    assert "clinicalrecords" in script
    assert "function documentsearchtext(item)" in script
    assert "terms.every" in script
    assert "item.path" in script
    assert ".markdown" in stylesheet
    assert ".search-panel" in stylesheet
    assert ".help-dialog" in stylesheet
    assert ".badge" in stylesheet
    assert "has-background-image" in stylesheet
    assert "sintesi clinica" in index
    assert "@media (min-width: 56rem)" in stylesheet
    assert "section-jumps" in index
    assert "function updatesectionjumps(sections)" in script
    assert ".section-jumps" in stylesheet
    desktop_css = stylesheet.split("@media (min-width: 56rem)", 1)[1].split(
        "@media (max-width: 44rem)",
        1,
    )[0]
    assert ".tabs" not in desktop_css
    assert "[data-tab-panel].is-active" in stylesheet


def test_build_frontend_copies_configured_background_image(tmp_path: Path) -> None:
    """Verify configured background images are copied into frontend assets.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    background = tmp_path / "background.png"
    background.write_bytes(b"synthetic image")
    person = PersonConfig(
        id="patient-a",
        display_name="Patient A",
        source_documents=tmp_path / "documents",
        metadata_directory=tmp_path / "metadata",
        local_build=tmp_path / "generated",
        usb_uuid="1A2B-3C4D",
        ui=UiConfig(background_image=background),
    )

    result = build_frontend(person)

    assert (result.web_dir / "assets" / "background.png").read_bytes() == (
        b"synthetic image"
    )
