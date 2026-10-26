"""Static frontend generation tests."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

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
    assert result.extended_chart.is_file()
    assert result.script.is_file()
    assert result.stylesheet.is_file()
    assert result.helper.is_file()
    assert (result.web_dir / "assets" / "chart-navigation.js").is_file()
    for page in (result.index, result.extended_chart):
        html = page.read_text(encoding="utf-8")
        assert html.index("chart.umd.min.js") < html.index("chart-navigation.js")
    assert result.material_script.is_file()
    assert result.material_stylesheet.is_file()
    assert (
        result.web_dir / "assets" / "sanikey-logo-horizontal-transparent.svg"
    ).is_file()
    assert "Patient A" in result.index.read_text(encoding="utf-8")
    assert (
        "<h1>Patient A</h1>\n"
        '          <button class="header-logo-button"'
        in result.index.read_text(encoding="utf-8")
    )
    assert 'data-section-button="documents"' in result.index.read_text(encoding="utf-8")
    assert 'data-section-button="summary"' in result.index.read_text(encoding="utf-8")
    assert 'data-section-button="therapies"' in result.index.read_text(encoding="utf-8")
    assert 'data-section-button="dicom"' in result.index.read_text(encoding="utf-8")
    assert 'data-pane-target="right"' in result.index.read_text(encoding="utf-8")
    assert "data-therapy-control hidden" in result.index.read_text(encoding="utf-8")
    assert "data-dicom-control hidden" in result.index.read_text(encoding="utf-8")
    assert 'data-section-button="parameters"' in result.index.read_text(
        encoding="utf-8"
    )
    assert 'id="parameter-detail"' in result.index.read_text(encoding="utf-8")
    assert (
        'data-section-button="parameters" data-pane-target="right"'
        not in result.index.read_text(encoding="utf-8")
    )
    for legacy_section in ("weight", "pressure", "glucose", "inr"):
        assert f'data-section-button="{legacy_section}"' not in result.index.read_text(
            encoding="utf-8"
        )
        assert f'id="{legacy_section}"' not in result.index.read_text(encoding="utf-8")
    assert "Aiuto ricerca base" in result.index.read_text(encoding="utf-8")
    assert "Ricerca avanzata" in result.index.read_text(encoding="utf-8")
    assert "search-mode-control" in result.index.read_text(encoding="utf-8")
    assert "data-close-dialog" in result.index.read_text(encoding="utf-8")
    assert 'id="usb-info-button"' in result.index.read_text(encoding="utf-8")
    assert 'id="usb-info-dialog"' in result.index.read_text(encoding="utf-8")
    script = result.script.read_text(encoding="utf-8").lower()
    extended_chart = result.extended_chart.read_text(encoding="utf-8").lower()
    extended_script = (
        (result.web_dir / "parameter-chart.js").read_text(encoding="utf-8").lower()
    )
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
    assert 'script src="usb-info.js"' in index
    assert 'script src="assets/ui-helper.js"' in index
    assert 'script src="assets/material-web.js"' in index
    assert 'type="module"' not in index
    assert 'type="module"' not in extended_chart
    assert 'href="assets/material-web.css"' in index
    logo_path = "assets/sanikey-logo-horizontal-transparent.svg"
    assert f'class="header-logo" src="{logo_path}" alt="sanikey"' in index
    assert (
        f'class="footer-logo" src="{logo_path}" '
        'alt="apri il repository sanikey su github"'
    ) in index
    assert "header-branding" in index
    assert "repository su github" not in index
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
    assert "function rendertimeline(timeline, documents)" in script
    assert "const documentitem = documentsbyid.get(link);" in script
    assert (
        'href="${attr(documentitem.href)}" target="_blank" rel="noopener">apri documento'
        in script
    )
    assert (
        'href="#entity-${attr(link)}" data-detail-link="${attr(link)}">dettaglio'
        in script
    )
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
    assert script.count('target="_blank" rel="noopener">apri documento') >= 2
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
    assert "renderparametersection" in script
    assert 'document.queryselector("#parameter-detail")' in script
    assert "sanikeylayoutchange" in script
    assert "function pointorigin(point)" in script
    assert '"documento: " + filename' in script
    assert '"origine: " + point.source_reference' in script
    assert "point.normalized_unit || point.raw_unit || series.unit" in script
    assert "afterlabel: (context) => pointorigin(context.raw.point)" in script
    assert "function bloodpressuredatasets(items)" in script
    assert 'label: "sistolica"' in script
    assert 'label: "diastolica"' in script
    assert 'label: "polso"' in script
    assert "apri grafico esteso" in script
    assert "parameter-chart.html?series=" in script
    assert 'script src="parameter-chart.js"' in extended_chart
    assert "function rendernumericcharts(target, entries)" in extended_script
    assert "scales.y1" in extended_script
    assert "function renderpressurechart(target, series, points)" in extended_script
    assert "observation_section_by_id" not in script
    assert "parametersearchtext" in script
    assert "data-parameter-series" in script
    assert "data-parameter-point" in script
    assert "data-parameter-filter" in script
    assert "filters.qualified" in script
    assert "filters.order" in script
    assert "onpointselected(point)" in script
    assert "renderquicksearch" in script
    assert "renderusbinfo" in script
    assert "sanikey_usb_info" in script
    assert 'timezoneName: "short"'.lower() in script
    assert "datestyle:" not in script
    assert "timestyle:" not in script
    assert "sortdocumentresults" in script
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
    assert ".header-logo" in stylesheet
    assert ".header-logo-button" in stylesheet
    assert ".header-branding" in stylesheet
    assert ".nav-control md-text-button" in stylesheet
    assert "min-height: 2rem;" in stylesheet
    assert "width: 2rem;" in stylesheet
    assert ".header-branding {\n  align-items: center;" in stylesheet
    assert "width: 8.1rem;" in stylesheet
    assert "@media (max-width: 64rem)" in stylesheet
    assert (
        "grid-template-columns: minmax(15rem, 0.85fr) minmax(19rem, 1.15fr);"
        in stylesheet
    )
    assert "width: 6.8rem;" in stylesheet
    assert "width: 6rem;" in stylesheet
    assert ".footer-repository" in stylesheet
    assert ".footer-logo" in stylesheet
    assert ".dialog-close" in stylesheet
    assert ".warning" in stylesheet
    assert "--search-basic-accent" in stylesheet
    assert "--search-advanced-accent" in stylesheet
    assert ".badge" in stylesheet
    assert ".parameter-layout" in stylesheet
    assert ".parameter-filters" in stylesheet
    assert 'input:not([type="checkbox"])' in stylesheet
    assert 'input[type="checkbox"]' in stylesheet
    assert "width: 1.1rem;" in stylesheet
    assert '.extended-chart-filters input[type="date"]' in stylesheet
    assert "width: 10rem;" in stylesheet
    assert "has-background-image" in stylesheet
    header_css = stylesheet.split("header {", 1)[1].split("\n}", 1)[0]
    assert "background: var(--surface)" in header_css
    assert "z-index: 10" in header_css
    header_background_css = stylesheet.split("body.has-background-image header {", 1)[
        1
    ].split("\n}", 1)[0]
    assert "background-image:" in header_background_css
    assert "var(--background-image)" in header_background_css
    assert "var(--background-opacity)" in header_background_css
    assert "background-attachment: fixed" in header_background_css
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
    assert 'body[data-layout="dual"] {' in desktop_css
    assert "min-height: 800dvh" in desktop_css
    assert "height: 800dvh" in desktop_css
    assert "#parameters .parameter-layout" in desktop_css
    assert "max-width: none" in desktop_css
    assert "width: 90%" in desktop_css
    mobile_css = stylesheet.split("@media (max-width: 44rem)", 1)[1].split(
        "@media print", 1
    )[0]
    assert ".nav-control md-icon-button" in mobile_css
    assert "display: none" in mobile_css
    usb_info = (result.web_dir / "usb-info.js").read_text(encoding="utf-8").lower()
    assert "window.sanikey_usb_info" in usb_info
    assert '"usb_uuid": "1a2b-3c4d"' in usb_info


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


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js non disponibile")
def test_extended_chart_series_have_distinct_stable_styles() -> None:
    """Execute chart grouping to verify distinct colors across units and selections.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    from sanikey.frontend import _extended_chart_js

    program = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const context = {};
vm.runInNewContext(fs.readFileSync(0, 'utf8'), context);
let charts = [];
context.appendExtendedChart = (_target, _title, datasets) => charts.push(datasets);
context.renderNumericCharts({}, []);
assert.equal(charts.length, 0);
const first = {series: {id: 'first', name: 'First', unit: 'mg/dL'}, styleIndex: 0,
  points: [{date: '2026-01-02', numeric_value: 1}]};
const second = {series: {id: 'second', name: 'Second', unit: 'kg'}, styleIndex: 1,
  points: [{date: '2026-01-02', numeric_value: 2}]};
context.renderNumericCharts({}, [first, second]);
assert.equal(charts.length, 1);
assert.notEqual(charts[0][0].borderColor, charts[0][1].borderColor);
assert.notEqual(charts[0][0].pointStyle, charts[0][1].pointStyle);
assert.equal(charts[0][0].yAxisID, 'y');
assert.equal(charts[0][1].yAxisID, 'y1');
const color = charts[0][1].borderColor;
charts = [];
context.renderNumericCharts({}, [second]);
assert.equal(charts[0][0].borderColor, color);
for (const value of [null, undefined, '', ' ', 'not-a-number']) {
  assert.equal(context.hasNumericValue(value), false);
}
assert.equal(context.hasNumericValue(0), true);
assert.equal(context.hasNumericValue('1.25'), true);
assert.equal(context.extendedPointLabel({point: {raw_value: '1,2', raw_unit: 'mg/dL'}, series: {unit: 'mg/dL'}}), '1,2 mg/dL');
let pressureUnits;
context.appendExtendedChart = (_target, _title, datasets, units) => {charts = [datasets]; pressureUnits = units;};
context.renderPressureChart({}, {unit: 'mmHg'}, [{date: '2026-01-02', systolic: 120, diastolic: 80, pulse: 70}]);
assert.equal(charts[0][2].yAxisID, 'y1');
assert.equal(pressureUnits[1], 'bpm');
assert.equal(context.extendedPointLabel(charts[0][2].data[0]), 'Polso: 70 bpm');
"""
    result = subprocess.run(
        [shutil.which("node") or "node", "-e", program],
        input=_extended_chart_js(),
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js non disponibile")
def test_parameter_units_and_chart_cleanup_behave_at_runtime() -> None:
    """Keep imported units and destroy replaced charts without plotting nulls.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    from sanikey.frontend import _app_js

    program = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const context = {window: {}, document: {body: {insertAdjacentHTML() {}}}};
vm.runInNewContext(fs.readFileSync(0, 'utf8'), context);
assert.equal(context.parameterUnit({}, {unit: 'kg/m2'}), 'kg/m2');
assert.equal(context.parameterUnit({normalized_unit: 'mg/dL', raw_unit: 'g/L'}, {unit: 'g/L'}), 'mg/dL');
let destroyed = 0;
context.Chart = {getChart: () => ({destroy: () => destroyed++})};
context.destroyParameterCharts({querySelectorAll: () => [{}, {}]});
assert.equal(destroyed, 2);
const points = [{series: {unit: 'mmHg'}, point: {date: '2026-01-02', systolic: 120, diastolic: 80, pulse: null}}];
const datasets = context.bloodPressureDatasets(points);
assert.equal(datasets.length, 2);
assert.equal(datasets.some(dataset => dataset.label === 'Polso'), false);
points[0].point.pulse = 70;
const withPulse = context.bloodPressureDatasets(points);
assert.equal(withPulse[2].yAxisID, 'y1');
assert.equal(context.chartPointLabel(withPulse[2].data[0]), 'Polso: 70 bpm');
assert.equal(context.hasNumericValue(null), false);
assert.equal(context.hasNumericValue(''), false);
assert.equal(context.hasNumericValue(0), true);
assert.equal(context.observationDisplayValue({raw_value: '1,2', raw_unit: 'mg/dL'}), '1,2 mg/dL');
assert.equal(context.observationDisplayValue({raw_value: '80 kg', raw_unit: 'kg'}), '80 kg');
"""
    result = subprocess.run(
        [shutil.which("node") or "node", "-e", program],
        input=_app_js(),
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js non disponibile")
def test_search_navigation_covers_both_search_modes_and_prefers_canonical_cards() -> (
    None
):
    """Delegate search navigation from main and prefer dedicated clinical cards.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    from sanikey.frontend import _app_js

    program = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const context = {window: {}, document: {body: {insertAdjacentHTML() {}}}};
vm.runInNewContext(fs.readFileSync(0, 'utf8'), context);
let listener;
const panel = {dataset: {sectionPanel: 'therapies'}};
let scrolled = false;
const canonical = {closest: () => panel, scrollIntoView: () => scrolled = true};
const summary = {};
context.document.getElementById = id => ({'entity-therapy': canonical, 'summary-entity-therapy': summary, 'summary-entity-problem': summary})[id];
assert.equal(context.findEntityDetail('therapy'), canonical);
assert.equal(context.findEntityDetail('problem'), summary);
context.CustomEvent = class {constructor(_name, options) {this.detail = options.detail;}};
context.document.querySelector = selector => {
  if (selector === 'main') return {addEventListener: (_name, handler) => listener = handler};
  if (selector === '#parameters') return {dispatchEvent: () => true};
  throw new Error('Unexpected delegation target: ' + selector);
};
const opened = [];
context.window.SaniKeyUi = {showSection: (...args) => opened.push(args)};
context.requestAnimationFrame = callback => callback();
context.setupResultDetailLinks();
let prevented = false;
listener({target: {closest: () => ({dataset: {resultDetailLink: 'therapy'}})}, preventDefault: () => prevented = true});
assert.equal(prevented, true);
assert.equal(scrolled, true);
assert.deepEqual(opened, [['therapies', 'left']]);
let selected;
context.document.querySelector = () => ({dispatchEvent: event => {selected = event.detail; return false;}});
assert.equal(context.openParameterDetail('point-a'), true);
assert.equal(selected, 'point-a');
const basicResults = {id: 'documents'};
const advancedResults = {id: 'advanced-results'};
const records = [{id: 'point-a', type: 'observation_point', title: 'Synthetic', section: 'parameters'}];
context.renderSearchResults(basicResults, records, 'Results', 'None');
context.renderSearchResults(advancedResults, records, 'Results', 'None');
assert.equal(basicResults.innerHTML.includes('id="documents-results-parameters"'), true);
assert.equal(advancedResults.innerHTML.includes('id="advanced-results-results-parameters"'), true);
assert.equal(advancedResults.innerHTML.includes('href="#advanced-results-results-parameters"'), true);
"""
    result = subprocess.run(
        [shutil.which("node") or "node", "-e", program],
        input=_app_js(),
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js non disponibile")
def test_chart_navigation_preserves_history_and_disposes_controls() -> None:
    """Check temporal panning, empty periods, selection and lifecycle cleanup.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    import json

    from sanikey.frontend import _chart_navigation_js

    script = (
        r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
function element() {
  return {style: {}, dataset: {}, clientWidth: 400, scrollWidth: 40000, scrollLeft: 0,
    listeners: {}, addEventListener(k, f) { this.listeners[k] = f; },
    removeEventListener(k) { delete this.listeners[k]; }, remove() { this.removed = true; }};
}
const scroll = element(), track = element(), range = element(), empty = element();
const buttons = ['first', 'previous', 'next', 'last'].map(pan => ({...element(), dataset: {pan}}));
const controls = {...element(), querySelector(s) { return s === 'output' ? range : s.endsWith('scroll') ? scroll : s.endsWith('track') ? track : empty; }, querySelectorAll() { return buttons; }};
let disconnected = false;
const context = {window: {}, document: {createElement() {return controls;}},
  ResizeObserver: class {observe() {} disconnect() {disconnected = true;}},
  requestAnimationFrame(f) {f(); return 1;}, cancelAnimationFrame() {},
  Chart: class {constructor(canvas, c) {this.data = c.data; this.options = c.options; this.config = c;} update() {} destroy() {this.config.plugins.forEach(p => p.afterDestroy());}}};
vm.createContext(context);
"""
        + "vm.runInContext("
        + json.dumps(_chart_navigation_js())
        + ", context);"
        + r"""
const api = context.window.SaniKeyCharts;
const date = value => Date.parse(value + 'T00:00:00');
const source = [{x: date('2002-10-10'), y: 120}, {x: date('2026-04-01'), y: 130}, {x: date('2026-06-27'), y: 125}];
const canvas = {parentElement: {after() {}}};
const chart = api.create(canvas, {data: {datasets: [{data: source}]}, options: {scales: {x: {}}}});
assert.equal(chart.data.datasets[0].data.length, 2);
assert.equal(chart.options.scales.x.max - chart.options.scales.x.min, 92 * 86400000);
assert.equal(source.length, 3);
buttons[0].listeners.click();
assert.equal(chart.data.datasets[0].data[0].x, source[0].x);
buttons[2].listeners.click();
assert.equal(chart.data.datasets[0].data.length, 0);
assert.match(empty.textContent, /Nessuna misurazione/);
api.reveal(canvas, source[2].x);
assert.equal(chart.data.datasets[0].data.at(-1).x, source[2].x);
scroll.scrollLeft = 0; scroll.listeners.scroll();
assert.equal(chart.data.datasets[0].data[0].x, source[0].x);
scroll.listeners.keydown({key:'End', preventDefault() {}});
assert.equal(chart.data.datasets[0].data.length, 2);
chart.destroy();
assert.equal(disconnected, true);
assert.equal(controls.removed, true);
assert.equal(Object.keys(scroll.listeners).length, 0);
api.reveal(canvas, source[0].x);
"""
    )
    subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
