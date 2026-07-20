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
    assert 'data-section-button="documents"' in result.index.read_text(encoding="utf-8")
    assert 'data-section-button="summary"' in result.index.read_text(encoding="utf-8")
    assert 'data-section-button="therapies"' in result.index.read_text(encoding="utf-8")
    assert 'data-section-button="dicom"' in result.index.read_text(encoding="utf-8")
    assert 'data-pane-target="right"' in result.index.read_text(encoding="utf-8")
    assert "data-therapy-control hidden" in result.index.read_text(encoding="utf-8")
    assert "data-dicom-control hidden" in result.index.read_text(encoding="utf-8")
    assert "Aiuto ricerca base" in result.index.read_text(encoding="utf-8")
    assert "Ricerca avanzata" in result.index.read_text(encoding="utf-8")
    assert "search-mode-control" in result.index.read_text(encoding="utf-8")
    assert "data-close-dialog" in result.index.read_text(encoding="utf-8")
    script = result.script.read_text(encoding="utf-8").lower()
    helper = result.helper.read_text(encoding="utf-8").lower()
    material = result.material_script.read_text(encoding="utf-8").lower()
    index = result.index.read_text(encoding="utf-8").lower()
    stylesheet = result.stylesheet.read_text(encoding="utf-8").lower()
    material_stylesheet = result.material_stylesheet.read_text(encoding="utf-8").lower()
    generated = "\n".join(
        (index, script, helper, stylesheet, material, material_stylesheet)
    ).replace("https://github.com/marco0560/sanikey", "")
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
    assert "setupsections" in helper
    assert "showsection" in helper
    assert "matchmedia" in helper
    assert "data-detail-link" in script
    assert "setuptimelinedetaillinks" in script
    assert "setupresultdetaillinks" in script
    assert "data-result-detail-link" in script
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
    assert script.count('target="_blank" rel="noopener">apri documento') == 2
    assert 'target="_blank" rel="noopener">scarica originale' in script
    assert "scarica supporto originale" not in script
    assert "renderdicomstudies" in script
    assert "configuredicomnavigation" in script
    assert "https://github.com/marco0560/sanikey" in index
    assert "rendertherapies" in script
    assert "configuretherapynavigation" in script
    assert "sortdicomstudies" in script
    assert "renderdicomstudycard" in script
    assert "isdicomtechnicaldocument" in script
    assert "anomalia: nessun viewer, anteprima o dicomdir disponibile" in script
    assert "supporto originale per verifica tecnica" in script
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
    assert "overflow-wrap: anywhere" in stylesheet
    assert "grid-row: 1" in stylesheet
    assert ".search-panel" in stylesheet
    assert ".help-dialog" in stylesheet
    assert ".dialog-close" in stylesheet
    assert ".warning" in stylesheet
    assert "--search-basic-accent" in stylesheet
    assert "--search-advanced-accent" in stylesheet
    assert ".badge" in stylesheet
    assert "has-background-image" in stylesheet
    assert "sintesi clinica" in index
    assert "section-jumps" not in index
    assert "function updatesectionjumps(sections)" not in script
    assert ".section-jumps" not in stylesheet
    assert "@media (min-width: 72rem)" in stylesheet
    desktop_css = stylesheet.split("@media (min-width: 72rem)", 1)[1].split(
        "@media (max-width: 44rem)",
        1,
    )[0]
    assert ".tabs" not in desktop_css
    assert "[data-section-panel].is-active" in stylesheet
    assert '[data-pane-role="left"]' in desktop_css
    assert '[data-pane-role="right"]' in desktop_css
    assert "height: calc(100vh - 8rem)" in desktop_css
    assert "min-height: 0" in desktop_css
    mobile_css = stylesheet.split("@media (max-width: 44rem)", 1)[1].split(
        "@media print", 1
    )[0]
    assert ".nav-control md-icon-button" in mobile_css
    assert "display: none" in mobile_css


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
