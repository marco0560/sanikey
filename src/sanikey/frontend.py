"""Static frontend generation for SaniKey."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import PersonConfig

from . import __version__


@dataclass(frozen=True)
class FrontendResult:
    """Result of frontend generation.

    Parameters
    ----------
    web_dir : pathlib.Path
        Generated frontend directory.
    index : pathlib.Path
        Generated index HTML.
    extended_chart : pathlib.Path
        Generated extended parameter-chart HTML.
    script : pathlib.Path
        Generated JavaScript.
    stylesheet : pathlib.Path
        Generated stylesheet.
    helper : pathlib.Path
        Vendored UI helper JavaScript.
    material_script : pathlib.Path
        Vendored Material Web compatibility JavaScript.
    material_stylesheet : pathlib.Path
        Vendored Material Web compatibility stylesheet.
    chart_script : pathlib.Path
        Vendored Chart.js runtime.
    """

    web_dir: Path
    index: Path
    extended_chart: Path
    script: Path
    stylesheet: Path
    helper: Path
    material_script: Path
    material_stylesheet: Path
    chart_script: Path


def build_frontend(person: PersonConfig) -> FrontendResult:
    """Generate the static frontend shell for one patient.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    FrontendResult
        Generated frontend paths.
    """

    web_dir = person.local_build / "web"
    web_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = web_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    index = web_dir / "index.html"
    extended_chart = web_dir / "parameter-chart.html"
    script = web_dir / "app.js"
    stylesheet = web_dir / "style.css"
    helper = assets_dir / "ui-helper.js"
    material_script = assets_dir / "material-web.js"
    material_stylesheet = assets_dir / "material-web.css"
    chart_script = assets_dir / "chart.umd.min.js"
    index.write_text(_index_html(person), encoding="utf-8")
    extended_chart.write_text(_extended_chart_html(person), encoding="utf-8")
    script.write_text(_app_js(), encoding="utf-8")
    (web_dir / "parameter-chart.js").write_text(_extended_chart_js(), encoding="utf-8")
    stylesheet.write_text(_style_css(), encoding="utf-8")
    (web_dir / "usb-info.js").write_text(_usb_info_js(person), encoding="utf-8")
    helper.write_text(_ui_helper_js(), encoding="utf-8")
    material_script.write_text(_material_web_js(), encoding="utf-8")
    material_stylesheet.write_text(_material_web_css(), encoding="utf-8")
    shutil.copy2(
        Path(__file__).resolve().parent
        / "assets"
        / "vendor"
        / "chartjs"
        / "chart.umd.min.js",
        chart_script,
    )
    shutil.copy2(
        Path(__file__).resolve().parents[2]
        / "immagini"
        / "SaniKey-logo-horizontal-transparent.svg",
        assets_dir / "sanikey-logo-horizontal-transparent.svg",
    )
    if person.ui.background_image is not None:
        shutil.copy2(
            person.ui.background_image,
            assets_dir / f"background{person.ui.background_image.suffix.lower()}",
        )
    return FrontendResult(
        web_dir=web_dir,
        index=index,
        extended_chart=extended_chart,
        script=script,
        stylesheet=stylesheet,
        helper=helper,
        material_script=material_script,
        material_stylesheet=material_stylesheet,
        chart_script=chart_script,
    )


def _usb_info_js(person: PersonConfig) -> str:
    """Render fallback technical information for a local frontend preview.

    Parameters
    ----------
    person : sanikey.config.PersonConfig
        Patient configuration supplying the expected USB UUID.

    Returns
    -------
    str
        Static JavaScript assigning the offline technical-information payload.
    """

    payload = {
        "schema_version": 1,
        "usb_uuid": person.usb_uuid,
        "exported_at": None,
        "sanikey_version": __version__,
        "copy_strategy": None,
    }
    return "window.SANIKEY_USB_INFO = " + json.dumps(payload, sort_keys=True) + ";\n"


def _index_html(person: PersonConfig) -> str:
    """Render index HTML.

    Parameters
    ----------
    person : PersonConfig
        Patient configuration.

    Returns
    -------
    str
        HTML document.
    """

    title = _escape_html(person.display_name)
    subtitle = _escape_html(person.ui.subtitle)
    default_tab = _escape_html(person.ui.default_tab)
    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SaniKey - {title}</title>
  <link rel="stylesheet" href="assets/material-web.css">
  <link rel="stylesheet" href="style.css">
  <script type="module" src="assets/material-web.js"></script>
</head>
<body>
  <header>
    <div class="header-primary">
      <div class="header-title">
        <h1>{title}</h1>
        <div class="header-branding">
          <button class="header-logo-button" type="button" id="usb-info-button" aria-label="Apri informazioni tecniche della chiavetta"><img class="header-logo" src="assets/sanikey-logo-horizontal-transparent.svg" alt="SaniKey"></button>
          <p>{subtitle}</p>
        </div>
      </div>
      <nav class="header-actions" aria-label="Sezioni archivio">
        <span class="nav-control">
          <md-text-button type="button" data-section-button="documents" data-pane-target="left">Documenti</md-text-button>
          <md-icon-button type="button" data-section-button="documents" data-pane-target="right" aria-label="Apri Documenti a destra">&gt;</md-icon-button>
        </span>
        <span class="nav-control">
          <md-text-button type="button" data-section-button="timeline" data-pane-target="left">Timeline</md-text-button>
          <md-icon-button type="button" data-section-button="timeline" data-pane-target="right" aria-label="Apri Timeline a destra">&gt;</md-icon-button>
        </span>
        <span class="nav-control">
          <md-text-button type="button" data-section-button="summary" data-pane-target="left">Sintesi Clinica</md-text-button>
          <md-icon-button type="button" data-section-button="summary" data-pane-target="right" aria-label="Apri Sintesi Clinica a destra">&gt;</md-icon-button>
        </span>
        <span class="nav-control" data-therapy-control hidden>
          <md-text-button type="button" data-section-button="therapies" data-pane-target="left">Terapia</md-text-button>
          <md-icon-button type="button" data-section-button="therapies" data-pane-target="right" aria-label="Apri Terapia a destra">&gt;</md-icon-button>
        </span>
        <span class="nav-control" data-observation-control="parameters" hidden>
          <md-text-button type="button" data-section-button="parameters" data-pane-target="left">Parametri</md-text-button>
        </span>
        <span class="nav-control" data-dicom-control hidden>
          <md-text-button type="button" data-section-button="dicom" data-pane-target="left">Studi DICOM</md-text-button>
          <md-icon-button type="button" data-section-button="dicom" data-pane-target="right" aria-label="Apri Studi DICOM a destra">&gt;</md-icon-button>
        </span>
      </nav>
    </div>
    <div class="search-panel" data-search-mode="basic">
      <div class="search-toolbar" role="group" aria-label="Modalita' ricerca">
        <span class="search-mode-control">
          <md-filled-tonal-button type="button" id="basic-toggle">Ricerca base</md-filled-tonal-button>
          <md-icon-button type="button" id="basic-help-button" aria-label="Aiuto ricerca base">?</md-icon-button>
        </span>
        <span class="search-mode-control">
          <md-outlined-button type="button" id="advanced-toggle">Ricerca avanzata</md-outlined-button>
          <md-icon-button type="button" id="advanced-help-button" aria-label="Aiuto ricerca avanzata">?</md-icon-button>
        </span>
      </div>
      <div class="search-control" data-search-panel="basic">
        <label for="search">Cerca nell'archivio</label>
        <input id="search" type="search" placeholder="Cerca documenti, categorie o tag">
      </div>
      <div class="search-control" data-search-panel="advanced">
        <label for="advanced-search">Cerca nel testo OCR e contenuto estratto</label>
        <input id="advanced-search" type="search" placeholder='Esempio: creatinina AND (2024 OR 2025) NOT "urine"'>
      </div>
    </div>
  </header>
  <main data-default-section="{default_tab}">
    <section id="documents" data-section-panel="documents" aria-label="Documenti"></section>
    <section id="advanced" data-section-panel="advanced" aria-label="Ricerca avanzata">
      <div id="advanced-results" class="advanced-results"></div>
    </section>
    <section id="timeline" data-section-panel="timeline" aria-label="Timeline"></section>
    <section id="summary" data-section-panel="summary" aria-label="Sintesi Clinica"></section>
    <section id="therapies" data-section-panel="therapies" aria-label="Terapia"></section>
    <section id="parameters" data-section-panel="parameters" aria-label="Parametri" hidden></section>
    <section id="parameter-detail" data-section-panel="parameter-detail" aria-label="Dettaglio parametro" hidden></section>
    <section id="dicom" data-section-panel="dicom" aria-label="Studi DICOM"></section>
  </main>
  <footer class="app-footer"><a class="footer-repository" href="https://github.com/marco0560/sanikey" target="_blank" rel="noopener"><img class="footer-logo" src="assets/sanikey-logo-horizontal-transparent.svg" alt="Apri il repository SaniKey su GitHub"></a></footer>
  <dialog id="basic-help-dialog" class="help-dialog">
    <article>
      <h2>Aiuto ricerca base</h2>
      <p>Scrivi una o piu' parole presenti in titolo, categoria, tag, tipo,
      percorso o data. Esempi: <code>cardiologo 2024</code>,
      <code>analisi pdf</code>, <code>risonanza</code>.</p>
      <button type="button" class="dialog-close" data-close-dialog="basic-help-dialog">Chiudi</button>
    </article>
  </dialog>
  <dialog id="advanced-help-dialog" class="help-dialog">
    <article>
      <h2>Aiuto ricerca avanzata</h2>
      <p>Usa parole, frasi tra virgolette, <code>AND</code>, <code>OR</code>,
      <code>NOT</code> e parentesi. Le parole adiacenti valgono come
      <code>AND</code>. La ricerca non distingue maiuscole, minuscole o
      accenti e applica sinonimi configurati.</p>
      <button type="button" class="dialog-close" data-close-dialog="advanced-help-dialog">Chiudi</button>
    </article>
  </dialog>
  <dialog id="usb-info-dialog" class="help-dialog">
    <article>
      <h2>Informazioni tecniche della chiavetta</h2>
      <dl id="usb-info-details"></dl>
      <button type="button" class="dialog-close" data-close-dialog="usb-info-dialog">Chiudi</button>
    </article>
  </dialog>
  <script src="data.js"></script>
  <script src="usb-info.js"></script>
  <script src="assets/ui-helper.js"></script>
  <script src="assets/chart.umd.min.js"></script>
  <script src="app.js"></script>
</body>
</html>
"""


def _extended_chart_html(person: PersonConfig) -> str:
    """Render the standalone extended parameter-chart page.

    Parameters
    ----------
    person : sanikey.config.PersonConfig
        Patient configuration supplying the display name.

    Returns
    -------
    str
        Offline HTML document for extended parameter charts.
    """

    title = _escape_html(person.display_name)
    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Grafici parametri - {title}</title>
  <link rel="stylesheet" href="assets/material-web.css">
  <link rel="stylesheet" href="style.css">
  <script type="module" src="assets/material-web.js"></script>
</head>
<body class="extended-chart-page">
  <main class="extended-chart-main">
    <p><a href="index.html">Torna all'archivio</a></p>
    <h1>Grafici parametri: {title}</h1>
    <p class="muted">Seleziona una o piu' serie. Due unita' condividono un grafico con doppia scala; ulteriori unita' vengono separate.</p>
    <fieldset class="extended-chart-filters">
      <legend>Periodo</legend>
      <label>Da <input type="date" data-extended-filter="from"></label>
      <label>A <input type="date" data-extended-filter="to"></label>
    </fieldset>
    <fieldset class="extended-series-list">
      <legend>Serie</legend>
      <div data-extended-series></div>
    </fieldset>
    <div data-extended-charts></div>
  </main>
  <script src="data.js"></script>
  <script src="assets/chart.umd.min.js"></script>
  <script src="parameter-chart.js"></script>
</body>
</html>
"""


def _app_js() -> str:
    """Render offline JavaScript.

    Parameters
    ----------
    None

    Returns
    -------
    str
        JavaScript source.
    """

    return r"""const SECTION_LABELS = {
  documents: "Documenti",
  therapies: "Terapie",
  medications: "Farmaci",
  problems: "Problemi",
  procedures: "Procedure",
  observations: "Osservazioni",
  parameters: "Parametri",
  dicom: "Studi DICOM",
  timeline: "Timeline",
  summary: "Sintesi Clinica",
};

const SECTION_ORDER = ["documents", "therapies", "medications", "problems", "procedures", "observations", "parameters", "dicom", "timeline"];
function text(value) {
  return value === null || value === undefined ? "" : String(value);
}

function escapeHtml(value) {
  return text(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function attr(value) {
  return escapeHtml(value);
}

function html(value) {
  return value === null || value === undefined ? "" : String(value);
}

function formatDate(value) {
  const rendered = text(value);
  const match = rendered.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : rendered;
}

function formatDateRange(startDate, endDate) {
  const start = formatDate(startDate);
  const end = formatDate(endDate);
  return end ? `${start} - ${end}` : start;
}

function formatTechnicalTimestamp(value) {
  const parsed = new Date(text(value));
  if (Number.isNaN(parsed.getTime())) {
    return "Non disponibile";
  }
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  }).format(parsed);
}

function renderUsbInfo() {
  const info = window.SANIKEY_USB_INFO || {};
  const target = document.querySelector("#usb-info-details");
  const fields = [
    ["UUID USB", text(info.usb_uuid) || "Non disponibile"],
    ["Ultimo export SaniKey", info.exported_at ? formatTechnicalTimestamp(info.exported_at) : "Anteprima locale non esportata"],
    ["Versione SaniKey", text(info.sanikey_version) || "Non disponibile"],
    ["Schema manifest", text(info.schema_version) || "Non disponibile"],
    ["Copia USB", text(info.copy_strategy) || "Non disponibile"],
  ];
  target.innerHTML = fields.map(([label, value]) =>
    `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`
  ).join("");
}

function applyUi(summary) {
  const ui = summary.ui || {};
  document.documentElement.style.setProperty("--accent", text(ui.accent_color || "#2563eb"));
  document.documentElement.style.setProperty("--background-opacity", text(ui.background_opacity || "0.1"));
  if (ui.background_image) {
    document.documentElement.style.setProperty("--background-image", `url("${attr(ui.background_image)}")`);
    document.body.classList.add("has-background-image");
  }
  document.body.dataset.density = text(ui.density || "comfortable");
  document.querySelector("main").dataset.defaultSection = text(ui.default_tab || "documents");
}

function renderSummary(summary, clinical = {}) {
  const target = document.querySelector("#summary");
  target.innerHTML = `<h2>Sintesi Clinica</h2>
    <div class="markdown">${html(summary.clinical_summary_html) || `<p>${escapeHtml(summary.clinical_summary)}</p>`}</div>
    ${renderClinicalDashboard(clinical)}
    <section class="technical-summary" aria-label="Riepilogo tecnico">
      <h3>Riepilogo tecnico</h3>
      <dl>
        <div><dt>Documenti</dt><dd>${escapeHtml(summary.document_count)}</dd></div>
        <div><dt>Problemi</dt><dd>${escapeHtml(summary.problem_count)}</dd></div>
        <div><dt>Procedure</dt><dd>${escapeHtml(summary.procedure_count)}</dd></div>
      </dl>
    </section>`;
}

function renderTimeline(timeline, documents) {
  const target = document.querySelector("#timeline");
  target.innerHTML = "<h2>Timeline</h2>" + timeline.map((item) =>
    `<article id="entity-${attr(item.id)}"><strong>${escapeHtml(formatDateRange(item.start_date, item.end_date))}</strong> ${escapeHtml(item.title)}
      ${renderTimelineLinks(item, documents)}</article>`
  ).join("");
}

function renderTimelineLinks(item, documents) {
  const links = item.links || [];
  if (!links.length) {
    return "";
  }
  const documentsById = new Map((documents || []).map((documentItem) => [documentItem.id, documentItem]));
  return `<p>${links.map((link) => {
    const documentItem = documentsById.get(link);
    if (documentItem && documentItem.href) {
      return `<a class="primary-action" href="${attr(documentItem.href)}" target="_blank" rel="noopener">Apri documento</a>`;
    }
    return `<a href="#entity-${attr(link)}" data-detail-link="${attr(link)}">Dettaglio</a>`;
  }).join(" ")}</p>`;
}

function setupTimelineDetailLinks(documents) {
  const timeline = document.querySelector("#timeline");
  timeline.addEventListener("click", (event) => {
    const link = event.target.closest("[data-detail-link]");
    if (!link) {
      return;
    }
    const detailId = text(link.dataset.detailLink);
    let detail = document.getElementById(`entity-${detailId}`);
    if (!detail) {
      renderDocuments(documents);
      const search = document.querySelector("#search");
      search.value = "";
      detail = document.getElementById(`entity-${detailId}`);
    }
    const panel = detail && detail.closest("[data-section-panel]");
    if (!panel) {
      return;
    }
    event.preventDefault();
    window.SaniKeyUi.showSection(panel.dataset.sectionPanel, "left");
    requestAnimationFrame(() => detail.scrollIntoView({block: "start"}));
  });
}

function setupResultDetailLinks() {
  const results = document.querySelector("#documents");
  results.addEventListener("click", (event) => {
    const link = event.target.closest("[data-result-detail-link]");
    if (!link) {
      return;
    }
    const detail = document.getElementById(`entity-${text(link.dataset.resultDetailLink)}`);
    const panel = detail && detail.closest("[data-section-panel]");
    if (!panel) {
      return;
    }
    event.preventDefault();
    window.SaniKeyUi.showSection(panel.dataset.sectionPanel, "left");
    requestAnimationFrame(() => detail.scrollIntoView({block: "start"}));
  });
}

function renderDocuments(documents, query = "") {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const selected = sortDocumentResults(documents.filter((item) => !isDicomTechnicalDocument(item)).filter((item) =>
    terms.every((term) => documentSearchText(item).includes(term))
  ));
  const target = document.querySelector("#documents");
  const count = query ? `<p class="result-count">${selected.length} risultati</p>` : "";
  target.innerHTML = "<h2>Documenti</h2>" + count + selected.map((item) =>
    `<article id="entity-${attr(item.id)}"><h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(formatDate(item.date))} ${escapeHtml(item.category)} ${escapeHtml(item.kind)}</p>
      <p>${item.tags.map(escapeHtml).join(", ")}</p>
      ${item.markdown_html ? `<div class="markdown">${html(item.markdown_html)}</div>` : ""}
      ${renderDocumentActions(item)}</article>`
  ).join("");
}

function sortDocumentResults(records) {
  return [...records].sort((left, right) =>
    text(right.date).localeCompare(text(left.date))
    || text(left.title).localeCompare(text(right.title), "it")
  );
}

function renderDocumentActions(item) {
  if (item.viewer_href) {
    const label = item.native_viewer_href ? "Apri studio DICOM" : "Apri visualizzatore integrato (non diagnostico)";
    const media = item.dicomdir_href ? ` <a href="${attr(item.dicomdir_href)}">DICOMDIR per viewer professionale</a>` : "";
    return `<p class="actions"><a class="primary-action" href="${attr(item.viewer_href)}" target="_blank" rel="noopener">${label}</a>${media}</p>`;
  }
  if (item.href) {
    const original = item.source_href && item.source_href !== item.href
      ? ` <a href="${attr(item.source_href)}" target="_blank" rel="noopener">Scarica originale</a>`
      : "";
    return `<p class="actions"><a class="primary-action" href="${attr(item.href)}" target="_blank" rel="noopener">Apri documento</a>${original}</p>`;
  }
  return `<span class="muted">Origine nel contenitore</span>`;
}

function renderClinicalDashboard(clinical) {
  const sections = [
    ["problems", clinical.problems || []],
    ["therapies", clinical.therapies || []],
    ["medications", clinical.medications || []],
    ["observations", clinical.observations || []],
    ["procedures", clinical.procedures || []],
  ].filter(([, items]) => items.length);
  if (!sections.length) {
    return "";
  }
  return `<nav class="section-links" aria-label="Sezioni riepilogo">${sections.map(([section, items]) =>
    `<a href="#summary-${attr(section)}">${escapeHtml(SECTION_LABELS[section])} ${items.length}</a>`
  ).join("")}</nav>` + sections.map(([section, items]) =>
    `<section id="summary-${attr(section)}" class="summary-section"><h3>${escapeHtml(SECTION_LABELS[section])}</h3>
      ${items.map((item) => renderEntityCard(item, section)).join("")}</section>`
  ).join("");
}

function renderDicomStudies(studies) {
  const target = document.querySelector("#dicom");
  const selected = sortDicomStudies(studies);
  target.innerHTML = `<h2>Studi DICOM</h2>` + (
    selected.length
      ? selected.map(renderDicomStudyCard).join("")
      : '<p class="muted">Nessuno studio DICOM disponibile.</p>'
  );
}

function observationSectionForSeries(series) {
  return "parameters";
}

function renderObservationSections(clinical) {
  const series = clinical.observation_series || [];
  const points = clinical.observation_points || [];
  const bySeries = new Map(series.map((item) => [item.id, item]));
  const grouped = {parameters: []};
  points.forEach((point) => {
    const itemSeries = bySeries.get(point.series_id) || {id: point.series_id, name: point.series_id};
    grouped[observationSectionForSeries(itemSeries)].push({series: itemSeries, point});
  });
  Object.entries(grouped).forEach(([section, items]) => renderObservationSection(section, items));
  configureObservationNavigation(grouped);
}

function renderObservationSection(section, items) {
  const target = document.querySelector(`#${section}`);
  const sorted = [...items].sort((left, right) => text(right.point.date).localeCompare(text(left.point.date)));
  if (section === "parameters") {
    renderParameterSection(target, sorted);
    return;
  }
  target.innerHTML = `<h2>${escapeHtml(SECTION_LABELS[section])}</h2>` + (
    sorted.length
      ? `<table class="observation-table"><thead><tr><th>Data</th><th>Serie</th><th>Valore</th><th>Fonte</th></tr></thead><tbody>${sorted.map(({series, point}) =>
          `<tr id="entity-${attr(point.id)}"><td>${escapeHtml(formatDate(point.date))}</td><td>${escapeHtml(series.name || series.id)}</td><td>${escapeHtml(observationDisplayValue(point))}</td><td>${renderObservationSource(point)}</td></tr>`
        ).join("")}</tbody></table>`
      : '<p class="muted">Nessuna misurazione disponibile.</p>'
  );
}

function renderParameterSection(target, items) {
  const series = [...new Map(items.map(({series}) => [series.id, series])).values()]
    .sort((left, right) => text(left.name || left.id).localeCompare(text(right.name || right.id), "it"));
  let selectedSeriesId = series[0] && series[0].id;
  let query = "";
  const filters = {from: "", to: "", unit: "", category: "", qualified: "all", order: "desc"};
  const units = [...new Set(items.map(({point}) => point.normalized_unit || point.raw_unit).filter(Boolean))].sort();
  const categories = [...new Set(items.map(({point}) => point.document_category).filter(Boolean))].sort();
  const detailPanel = document.querySelector("#parameter-detail");
  target.innerHTML = `<h2>Parametri</h2>
    <label class="parameter-search">Cerca parametro o sinonimo
      <input type="search" data-parameter-search autocomplete="off">
    </label>
    <fieldset class="parameter-filters"><legend>Filtri</legend>
      <label>Da <input type="date" data-parameter-filter="from"></label><label>A <input type="date" data-parameter-filter="to"></label>
      <label>Unita' <select data-parameter-filter="unit"><option value="">Tutte</option>${units.map((value) => `<option value="${attr(value)}">${escapeHtml(value)}</option>`).join("")}</select></label>
      <label>Categoria <select data-parameter-filter="category"><option value="">Tutte</option>${categories.map((value) => `<option value="${attr(value)}">${escapeHtml(value)}</option>`).join("")}</select></label>
      <label>Qualificati <select data-parameter-filter="qualified"><option value="all">Tutti</option><option value="hide">Nascondi</option><option value="only">Solo qualificati</option></select></label>
      <label>Ordine <select data-parameter-filter="order"><option value="desc">Piu' recenti</option><option value="asc">Meno recenti</option></select></label>
    </fieldset>
    <div class="parameter-layout"><nav class="parameter-list" aria-label="Serie di parametri"></nav>
      <div class="parameter-content"></div></div>`;
  const search = target.querySelector("[data-parameter-search]");
  const list = target.querySelector(".parameter-list");
  const content = target.querySelector(".parameter-content");
  const layout = target.querySelector(".parameter-layout");
  const detailHeading = document.createElement("h2");
  detailHeading.textContent = "Dettaglio parametro";
  const arrange = () => {
    if (document.body.dataset.layout === "dual") {
      detailPanel.replaceChildren(detailHeading, content);
      return;
    }
    layout.appendChild(content);
    detailPanel.replaceChildren();
  };
  const render = () => {
    const normalized = normalizeSearchText(query);
    const visible = series.filter((item) => parameterSearchText(item).includes(normalized));
    if (!visible.some((item) => item.id === selectedSeriesId)) {
      selectedSeriesId = visible[0] && visible[0].id;
    }
    list.innerHTML = visible.length ? visible.map((item) => {
      const count = items.filter(({series}) => series.id === item.id).length;
      return `<button type="button" data-parameter-series="${attr(item.id)}" aria-pressed="${item.id === selectedSeriesId}">${escapeHtml(item.name || item.id)} <span>${count}</span></button>`;
    }).join("") : '<p class="muted">Nessun parametro corrispondente.</p>';
    renderSelectedParameter(content, items, selectedSeriesId, filters);
    list.querySelectorAll("[data-parameter-series]").forEach((button) => button.addEventListener("click", () => {
      selectedSeriesId = button.dataset.parameterSeries;
      render();
    }));
  };
  search.addEventListener("input", () => {
    query = search.value;
    render();
  });
  target.querySelectorAll("[data-parameter-filter]").forEach((control) => control.addEventListener("input", () => {
    filters[control.dataset.parameterFilter] = control.value;
    render();
  }));
  window.addEventListener("sanikeylayoutchange", arrange);
  render();
  arrange();
}

function parameterSearchText(series) {
  return normalizeSearchText([series.name, series.id, ...(series.synonyms || [])].join(" "));
}

function renderSelectedParameter(target, items, seriesId, filters) {
  const selected = items.filter(({series, point}) => series.id === seriesId
    && (!filters.from || point.date >= filters.from)
    && (!filters.to || point.date <= filters.to)
    && (!filters.unit || (point.normalized_unit || point.raw_unit) === filters.unit)
    && (!filters.category || point.document_category === filters.category)
    && (filters.qualified === "all" || (filters.qualified === "only") === Boolean(point.qualifier)))
    .sort((left, right) => filters.order === "asc"
      ? text(left.point.date).localeCompare(text(right.point.date))
      : text(right.point.date).localeCompare(text(left.point.date)));
  if (!selected.length) {
    target.innerHTML = '<p class="muted">Selezionare un parametro.</p>';
    return;
  }
  const series = selected[0].series;
  target.innerHTML = `<h3>${escapeHtml(series.name || series.id)}</h3>
    ${series.synonyms && series.synonyms.length ? `<p class="muted">Sinonimi: ${escapeHtml(series.synonyms.join(", "))}</p>` : ""}
    <div class="parameter-chart-host"></div><div class="parameter-detail" aria-live="polite"></div>
    <table class="observation-table"><thead><tr><th>Data</th><th>Valore originale</th><th>Unita'</th><th>Documento</th><th>Etichetta trovata</th><th>Provenienza</th></tr></thead><tbody>${selected.map(({point}) =>
      `<tr tabindex="0" data-parameter-point="${attr(point.id)}"><td>${escapeHtml(formatDate(point.date))}</td><td>${escapeHtml((point.qualifier || "") + (point.raw_value || point.value || ""))}</td><td>${escapeHtml(point.raw_unit || point.normalized_unit || "")}</td><td>${point.document_href ? `<a href="${attr(point.document_href)}" target="_blank" rel="noopener">Apri documento</a>` : escapeHtml(point.document_title || "")}</td><td>${escapeHtml(point.matched_label || "")}</td><td>${escapeHtml(point.source_reference || "")}</td></tr>`
    ).join("")}</tbody></table>`;
  const detail = target.querySelector(".parameter-detail");
  const showPoint = (point) => { detail.innerHTML = renderParameterDetail(point, series); };
  target.querySelectorAll("[data-parameter-point]").forEach((row) => {
    const point = selected.find(({point: item}) => item.id === row.dataset.parameterPoint).point;
    row.addEventListener("click", () => showPoint(point));
    row.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); showPoint(point); } });
  });
  showPoint(selected[0].point);
  renderParameterChart(target.querySelector(".parameter-chart-host"), selected, showPoint);
}

function renderParameterDetail(point, series) {
  const source = [pointOrigin(point), point.matched_label && "Etichetta: " + point.matched_label].filter(Boolean).join(" · ");
  const action = point.document_href ? `<p class="actions"><a class="primary-action" href="${attr(point.document_href)}" target="_blank" rel="noopener">Apri documento</a></p>` : "";
  const extended = `<p class="actions"><a class="primary-action" href="parameter-chart.html?series=${encodeURIComponent(series.id)}" target="_blank" rel="noopener">Apri grafico esteso</a></p>`;
  return `<h4>Dettaglio misurazione</h4><p>${escapeHtml(observationDisplayValue(point, series.unit))}</p><p class="muted">${escapeHtml(source)}</p>${extended}${action}`;
}

function observationDisplayValue(point, seriesUnit = "") {
  const raw = point.raw_value || point.value;
  const qualifier = point.qualifier || "";
  const unit = point.raw_value ? "" : (point.raw_unit || point.normalized_unit || seriesUnit);
  return qualifier + raw + (unit ? " " + unit : "");
}

function pointOrigin(point) {
  if (point.document_href) {
    const fileName = decodeURIComponent(text(point.document_href).split("/").pop());
    return "Documento: " + fileName;
  }
  if (point.source_reference) {
    return "Origine: " + point.source_reference;
  }
  if (point.source_kind === "curated-observation") {
    return "Origine: osservazione curata";
  }
  return "Origine: non disponibile";
}

function renderObservationSource(point) {
  const details = [
    point.matched_label ? "Etichetta: " + point.matched_label : "",
    point.rule_id ? "Regola: " + point.rule_id : "",
    point.source_reference || "",
  ].filter(Boolean).join(" · ");
  const detail = escapeHtml(details);
  if (!point.document_href) {
    return detail;
  }
  const link = '<a href="' + attr(point.document_href) + '" target="_blank" rel="noopener">Apri originale</a>';
  return link + (detail ? "<br><small>" + detail + "</small>" : "");
}

function renderParameterChart(target, items, onPointSelected) {
  if (typeof Chart === "undefined") {
    return;
  }
  const bloodPressure = items[0] && items[0].series.value_type === "blood_pressure";
  const numeric = items.filter(({point}) => Number.isFinite(Number(point.numeric_value)));
  if (!bloodPressure && !numeric.length) {
    return;
  }
  const canvas = document.createElement("canvas");
  canvas.className = "parameter-chart";
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", "Grafico temporale dei parametri disponibili");
  target.appendChild(canvas);
  const datasets = bloodPressure ? bloodPressureDatasets(items) : numericDatasets(numeric);
  if (!datasets.length) {
    return;
  }
  new Chart(canvas, {
    type: "line",
    data: {datasets},
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: "linear",
          ticks: {callback: (value) => new Date(Number(value)).toLocaleDateString("it-IT")},
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            title: (contexts) => contexts.length ? formatDate(contexts[0].raw.point.date) : "",
            label: (context) => chartPointLabel(context.raw),
            afterLabel: (context) => pointOrigin(context.raw.point),
          },
        },
      },
      onClick: (_event, elements, chart) => {
        if (!elements.length) { return; }
        const element = elements[0];
        const point = chart.data.datasets[element.datasetIndex].data[element.index].point;
        if (!point) { return; }
        if (point.document_href) {
          window.open(point.document_href, "_blank", "noopener");
          return;
        }
        onPointSelected(point);
      },
    },
  });
}

function numericDatasets(numeric) {
  const grouped = new Map();
  numeric.forEach(({series, point}) => {
    const unit = point.normalized_unit || point.raw_unit || series.unit || "";
    const key = series.id + "|" + unit;
    const name = series.name || series.id;
    const label = unit && unit !== series.unit ? name + " (" + unit + ")" : name;
    const entries = grouped.get(key) || {label, series, points: []};
    entries.points.push(point);
    grouped.set(key, entries);
  });
  const datasets = [];
  grouped.forEach((entry) => {
    const regular = entry.points.filter((point) => !point.qualifier);
    const qualified = entry.points.filter((point) => point.qualifier);
    if (regular.length) {
      datasets.push({
        label: entry.label,
        data: regular.map((point) => ({x: Date.parse(point.date + "T00:00:00"), y: Number(point.numeric_value), point, series: entry.series})),
        borderWidth: 2,
        tension: 0.15,
      });
    }
    if (qualified.length) {
      datasets.push({
        label: entry.label + " (qualificati)",
        data: qualified.map((point) => ({x: Date.parse(point.date + "T00:00:00"), y: Number(point.numeric_value), point, series: entry.series})),
        showLine: false,
        pointStyle: "triangle",
        pointRadius: 6,
      });
    }
  });
  return datasets;
}

function bloodPressureDatasets(items) {
  const components = [
    {field: "systolic", label: "Sistolica", color: "#1d4ed8"},
    {field: "diastolic", label: "Diastolica", color: "#dc2626"},
    {field: "pulse", label: "Polso", color: "#15803d"},
  ];
  return components.map((component) => {
    const data = items.filter(({point}) => Number.isFinite(Number(point[component.field])))
      .map(({series, point}) => ({x: Date.parse(point.date + "T00:00:00"), y: Number(point[component.field]), point, series, component}));
    return data.length ? {
      label: component.label,
      data,
      borderColor: component.color,
      backgroundColor: component.color,
      borderWidth: 2,
      tension: 0.15,
    } : null;
  }).filter(Boolean);
}

function chartPointLabel(raw) {
  if (raw.component) {
    return raw.component.label + ": " + raw.point[raw.component.field] + (raw.series.unit ? " " + raw.series.unit : "");
  }
  return observationDisplayValue(raw.point, raw.series.unit);
}

function configureObservationNavigation(grouped) {
  Object.entries(grouped).forEach(([section, items]) => {
    document.querySelectorAll(`[data-observation-control="${section}"]`).forEach((control) => {
      control.hidden = !items.length;
    });
    document.querySelector(`#${section}`).hidden = !items.length;
    if (section === "parameters") {
      document.querySelector("#parameter-detail").hidden = !items.length;
    }
  });
}

function renderTherapies(therapies) {
  const target = document.querySelector("#therapies");
  const selected = therapies || [];
  target.innerHTML = `<h2>Terapia</h2>` + (
    selected.length
      ? selected.map((item) => renderEntityCard(item, "therapies")).join("")
      : '<p class="muted">Nessuna terapia disponibile.</p>'
  );
}

function configureDicomNavigation(studies) {
  const hasDicom = (studies || []).length > 0;
  document.querySelectorAll("[data-dicom-control]").forEach((control) => {
    control.hidden = !hasDicom;
  });
  document.querySelector("#dicom").hidden = !hasDicom;
}

function configureTherapyNavigation(therapies) {
  const hasTherapy = (therapies || []).length > 0;
  document.querySelectorAll("[data-therapy-control]").forEach((control) => {
    control.hidden = !hasTherapy;
  });
  document.querySelector("#therapies").hidden = !hasTherapy;
}

function sortDicomStudies(studies) {
  return [...(studies || [])].sort((left, right) =>
    Number(!left.viewer_href) - Number(!right.viewer_href)
  );
}

function renderDicomStudyCard(item) {
  const anomaly = item.viewer_href || item.dicomdir_href
    ? ""
    : '<p class="warning">Anomalia: nessun viewer, anteprima o DICOMDIR disponibile per lo studio.</p>';
  return `<article id="entity-${attr(item.id)}"><h4>${escapeHtml(item.title)}</h4>
    ${item.date ? `<p>${escapeHtml(formatDate(item.date))}</p>` : ""}
    <details><summary>Dettagli tecnici</summary>${renderFields(item.fields || [])}</details>
    ${renderEntityActions(item, "dicom")}${anomaly}</article>`;
}

function recordKind(item) {
  if (item.kind) {
    return text(item.kind);
  }
  const typeField = (item.fields || []).find((field) => field.label === "Tipo");
  return typeField ? text(typeField.value) : "";
}

function isDicomTechnicalDocument(item) {
  if (item.type !== "document") {
    return false;
  }
  return recordKind(item).startsWith("dicom_");
}

function renderEntityCard(item, section) {
  return `<article id="entity-${attr(item.id)}"><h4>${escapeHtml(item.title)}</h4>
    ${item.date || item.start_date ? `<p>${escapeHtml(formatDate(item.date || item.start_date))}</p>` : ""}
    ${renderFields(item.fields || [])}
    ${renderEntityActions(item, section)}</article>`;
}

function renderEntityActions(item, section) {
  if (section === "dicom") {
    const viewer = item.viewer_href
      ? `<a class="primary-action" href="${attr(item.viewer_href)}" target="_blank" rel="noopener">${item.native_viewer_href ? "Apri studio DICOM" : "Apri visualizzatore integrato (non diagnostico)"}</a>`
      : "";
    const media = item.dicomdir_href
      ? ` <a href="${attr(item.dicomdir_href)}" target="_blank" rel="noopener">DICOMDIR per viewer professionale</a>`
      : "";
    return viewer || media ? `<p class="actions">${viewer}${media}</p>` : "";
  }
  if (section !== "dicom" && item.href) {
    return `<p class="actions"><a class="primary-action" href="${attr(item.href)}" target="_blank" rel="noopener">Apri originale</a></p>`;
  }
  if (item.href) {
    return `<p class="actions"><a class="primary-action" href="${attr(item.href)}">Supporto originale per verifica tecnica</a></p>`;
  }
  if (section === "therapies" && item.leaflet_href) {
    const downloaded = item.leaflet_downloaded_at ? ` scaricato il ${escapeHtml(formatDate(item.leaflet_downloaded_at))}` : "";
    return `<p class="actions"><a href="${attr(item.leaflet_href)}" target="_blank" rel="noopener">Foglio illustrativo${downloaded}</a>${item.rcp_href ? ` <a href="${attr(item.rcp_href)}" target="_blank" rel="noopener">RCP</a>` : ""} <a href="${attr(item.aifa_fi_url)}" target="_blank" rel="noopener">Verifica su AIFA</a></p>`;
  }
  if (section === "therapies" && item.non_aifa) {
    return '<p class="muted">Nessun foglio illustrativo AIFA applicabile.</p>';
  }
  return "";
}

function renderFields(fields) {
  const selected = (fields || []).filter((field) => field.value !== null && field.value !== undefined && text(field.value) !== "");
  if (!selected.length) {
    return "";
  }
  return `<dl>${selected.map((field) =>
    `<div><dt>${escapeHtml(field.label)}</dt><dd>${escapeHtml(field.value)}</dd></div>`
  ).join("")}</dl>`;
}

function renderSearchResults(target, records, heading, emptyMessage) {
  const grouped = groupBySection(records);
  const sections = SECTION_ORDER
    .filter((section) => grouped[section] && grouped[section].length)
    .map((section) => [section, grouped[section]]);
  if (!sections.length) {
    target.innerHTML = `<h2>${escapeHtml(heading)}</h2><p class="muted">${escapeHtml(emptyMessage)}</p>`;
    return;
  }
  const total = records.length;
  target.innerHTML = `<h2>${escapeHtml(heading)}</h2><p class="result-count">${total} risultati</p>
    <nav class="section-links" aria-label="Sezioni risultati">${sections.map(([section, items]) =>
      `<a href="#results-${attr(section)}">${escapeHtml(SECTION_LABELS[section])} ${items.length}</a>`
    ).join("")}</nav>` + sections.map(([section, items]) =>
    `<section id="results-${attr(section)}"><h3>${escapeHtml(SECTION_LABELS[section])}</h3>
        ${items.map((item) => renderResultCard(item, section)).join("")}</section>`
    ).join("");
}

function renderResultCard(item, section) {
  return `<article><h4>${escapeHtml(item.title)} <span class="badge">${escapeHtml(SECTION_LABELS[section] || item.type)}</span></h4>
    ${item.subtitle ? `<p>${escapeHtml(item.subtitle)}</p>` : ""}
    ${renderFields(item.fields || [])}
    ${renderResultAction(item)}</article>`;
}

function renderResultAction(item) {
  if (item.viewer_href) {
    return `<a class="primary-action" href="${attr(item.viewer_href)}" target="_blank" rel="noopener">${item.native_viewer_href ? "Apri studio DICOM" : "Apri visualizzatore integrato (non diagnostico)"}</a>`;
  }
  if (item.type === "dicom_study" && item.dicomdir_href) {
    return `<a class="primary-action" href="${attr(item.dicomdir_href)}" target="_blank" rel="noopener">DICOMDIR per viewer professionale</a>`;
  }
  if (item.type === "document" && item.href) {
    return `<a class="primary-action" href="${attr(item.href)}" target="_blank" rel="noopener">Apri documento</a>`;
  }
  return `<a href="#entity-${attr(item.id)}" data-result-detail-link="${attr(item.id)}">Vai alla scheda</a>`;
}

function groupBySection(records) {
  return records.reduce((grouped, item) => {
    const section = item.section || "documents";
    grouped[section] = grouped[section] || [];
    grouped[section].push(item);
    return grouped;
  }, {});
}

function quickSearchText(item) {
  return normalizeSearchText([
    item.title,
    item.subtitle,
    item.text,
    item.date,
    ...(item.tags || []),
    ...((item.fields || []).map((field) => field.value)),
  ].join(" "));
}

function renderQuickSearch(records, query) {
  const terms = normalizeSearchText(query).split(/\s+/).filter(Boolean);
  const selected = records.filter((item) =>
    terms.every((term) => quickSearchText(item).includes(term))
  );
  const documents = sortDocumentResults(selected.filter((item) => item.type === "document"));
  const otherRecords = selected.filter((item) => item.type !== "document");
  renderSearchResults(
    document.querySelector("#documents"),
    [...documents, ...otherRecords],
    "Risultati",
    "Nessun risultato nella ricerca rapida.",
  );
}

function documentSearchText(item) {
  return [
    item.title,
    item.category,
    item.kind,
    item.path,
    item.date,
    ...(item.tags || []),
  ].map(text).join(" ").toLowerCase();
}

function normalizeSearchText(value) {
  return text(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function tokenizeAdvancedQuery(query) {
  const tokens = [];
  let index = 0;
  while (index < query.length) {
    const char = query[index];
    if (/\s/.test(char)) {
      index += 1;
      continue;
    }
    if (char === "(" || char === ")") {
      tokens.push({type: char, value: char});
      index += 1;
      continue;
    }
    if (char === '"') {
      let end = index + 1;
      let value = "";
      while (end < query.length && query[end] !== '"') {
        value += query[end];
        end += 1;
      }
      if (end >= query.length) {
        throw new Error("Virgolette non chiuse nella ricerca avanzata.");
      }
      tokens.push({type: "TERM", value});
      index = end + 1;
      continue;
    }
    let end = index;
    let value = "";
    while (end < query.length && !/\s|\(|\)/.test(query[end])) {
      value += query[end];
      end += 1;
    }
    const upper = value.toUpperCase();
    tokens.push(["AND", "OR", "NOT"].includes(upper)
      ? {type: upper, value: upper}
      : {type: "TERM", value});
    index = end;
  }
  return insertImplicitAnd(tokens);
}

function insertImplicitAnd(tokens) {
  const result = [];
  tokens.forEach((token, index) => {
    const previous = tokens[index - 1];
    if (previous && canEndExpression(previous) && canStartExpression(token)) {
      result.push({type: "AND", value: "AND"});
    }
    result.push(token);
  });
  return result;
}

function canEndExpression(token) {
  return token.type === "TERM" || token.type === ")";
}

function canStartExpression(token) {
  return token.type === "TERM" || token.type === "(" || token.type === "NOT";
}

function parseAdvancedQuery(query) {
  const tokens = tokenizeAdvancedQuery(query);
  let position = 0;

  function peek() {
    return tokens[position];
  }

  function consume(type) {
    if (peek() && peek().type === type) {
      position += 1;
      return true;
    }
    return false;
  }

  function parseExpression() {
    return parseOr();
  }

  function parseOr() {
    let node = parseAnd();
    while (consume("OR")) {
      node = {type: "OR", left: node, right: parseAnd()};
    }
    return node;
  }

  function parseAnd() {
    let node = parseNot();
    while (consume("AND")) {
      node = {type: "AND", left: node, right: parseNot()};
    }
    return node;
  }

  function parseNot() {
    if (consume("NOT")) {
      return {type: "NOT", child: parseNot()};
    }
    return parsePrimary();
  }

  function parsePrimary() {
    const token = peek();
    if (!token) {
      throw new Error("Query avanzata incompleta.");
    }
    if (consume("(")) {
      const node = parseExpression();
      if (!consume(")")) {
        throw new Error("Parentesi non chiusa nella ricerca avanzata.");
      }
      return node;
    }
    if (token.type === "TERM") {
      position += 1;
      return {type: "TERM", value: normalizeSearchText(token.value)};
    }
    throw new Error(`Token inatteso nella ricerca avanzata: ${escapeHtml(token.value)}`);
  }

  if (tokens.length === 0) {
    return null;
  }
  const expression = parseExpression();
  if (position !== tokens.length) {
    throw new Error(`Sintassi non valida vicino a ${escapeHtml(tokens[position].value)}.`);
  }
  return expression;
}

function advancedSearchTerms(dictionary) {
  const mappings = new Map();
  const addGroup = (items) => {
    Object.entries(items || {}).forEach(([key, values]) => {
      const group = [key, ...(values || [])].map(normalizeSearchText).filter(Boolean);
      group.forEach((value) => mappings.set(value, group));
    });
  };
  addGroup(defaultMonthDictionary());
  addGroup(dictionary.months || {});
  addGroup(dictionary.terms || {});
  return mappings;
}

function defaultMonthDictionary() {
  return {
    gennaio: ["01", "1"],
    febbraio: ["02", "2"],
    marzo: ["03", "3"],
    aprile: ["04", "4"],
    maggio: ["05", "5"],
    giugno: ["06", "6"],
    luglio: ["07", "7"],
    agosto: ["08", "8"],
    settembre: ["09", "9"],
    ottobre: ["10"],
    novembre: ["11"],
    dicembre: ["12"],
  };
}

function evaluateAdvancedExpression(node, haystack, expansions) {
  if (node === null) {
    return true;
  }
  if (node.type === "TERM") {
    const expanded = expansions.get(node.value) || [node.value];
    return expanded.some((term) => haystack.includes(term));
  }
  if (node.type === "AND") {
    return evaluateAdvancedExpression(node.left, haystack, expansions)
      && evaluateAdvancedExpression(node.right, haystack, expansions);
  }
  if (node.type === "OR") {
    return evaluateAdvancedExpression(node.left, haystack, expansions)
      || evaluateAdvancedExpression(node.right, haystack, expansions);
  }
  if (node.type === "NOT") {
    return !evaluateAdvancedExpression(node.child, haystack, expansions);
  }
  return false;
}

function collectPositiveTerms(node) {
  if (!node) {
    return [];
  }
  if (node.type === "TERM") {
    return [node.value];
  }
  if (node.type === "NOT") {
    return [];
  }
  return [...collectPositiveTerms(node.left), ...collectPositiveTerms(node.right)];
}

function advancedHaystack(item) {
  return normalizeSearchText([
    item.title,
    item.date,
    item.category,
    item.kind,
    item.path,
    item.text,
    ...(item.tags || []),
  ].join(" "));
}

function advancedSnippet(item, terms, expansions) {
  const source = text(item.text).replace(/\s+/g, " ").trim();
  const normalized = normalizeSearchText(source);
  const expandedTerms = terms.flatMap((term) => expansions.get(term) || [term]);
  const matchIndex = expandedTerms
    .map((term) => normalized.indexOf(term))
    .filter((index) => index >= 0)
    .sort((a, b) => a - b)[0];
  const start = Math.max(0, (matchIndex || 0) - 90);
  const excerpt = source.slice(start, start + 240);
  return `${start > 0 ? "... " : ""}${excerpt}${start + 240 < source.length ? " ..." : ""}`;
}

function loadAdvancedSearchData() {
  if (window.SANIKEY_CONTENT_SEARCH) {
    return Promise.resolve(window.SANIKEY_CONTENT_SEARCH);
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "content-search.js";
    script.onload = () => resolve(window.SANIKEY_CONTENT_SEARCH);
    script.onerror = () => reject(new Error("Indice di ricerca avanzata non disponibile."));
    document.body.appendChild(script);
  });
}

function setSearchMode(mode) {
  const panel = document.querySelector(".search-panel");
  panel.dataset.searchMode = mode;
  document.body.dataset.searchMode = mode;
  document.querySelector("#basic-toggle").classList.toggle("is-active", mode === "basic");
  document.querySelector("#advanced-toggle").classList.toggle("is-active", mode === "advanced");
  if (mode === "basic") {
    document.querySelector("#search").focus();
    window.SaniKeyUi.showSection("documents", "left");
  } else {
    document.querySelector("#advanced-search").focus();
    window.SaniKeyUi.showSection("advanced", "left");
  }
}

function openHelpDialog(id) {
  const dialog = document.querySelector(id);
  if (dialog.showModal) {
    dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
}

function closeHelpDialog(id) {
  const dialog = document.querySelector(`#${id}`);
  if (dialog.close) {
    dialog.close();
  } else {
    dialog.removeAttribute("open");
  }
}

function advancedDocumentRecord(item, terms, expansions) {
  return {
    id: item.id,
    type: "document",
    section: item.viewer_href ? "dicom" : "documents",
    title: item.title,
    subtitle: [formatDate(item.date), item.category, item.kind].filter(Boolean).join(" "),
    date: item.date,
    text: item.text,
    href: item.href,
    viewer_href: item.viewer_href,
    support_href: item.support_href,
    primary_href: item.primary_href,
    primary_action: item.primary_action,
    fields: [
      {label: "Categoria", value: item.category},
      {label: "Tipo", value: item.kind},
      {label: "Estratto", value: advancedSnippet(item, terms, expansions)},
    ],
  };
}

function renderAdvancedResults(payload, query, clinicalRecords = []) {
  const target = document.querySelector("#advanced-results");
  if (!query.trim()) {
    target.innerHTML = '<p class="muted">Inserisci una query per cercare nel testo estratto e OCR.</p>';
    return;
  }
  let expression;
  try {
    expression = parseAdvancedQuery(query);
  } catch (error) {
    target.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
    return;
  }
  const expansions = advancedSearchTerms(payload.dictionary || {});
  const terms = collectPositiveTerms(expression);
  const documentMatches = (payload.documents || [])
    .filter((item) => evaluateAdvancedExpression(expression, advancedHaystack(item), expansions))
    .map((item) => advancedDocumentRecord(item, terms, expansions));
  const clinicalMatches = clinicalRecords.filter((item) =>
    evaluateAdvancedExpression(expression, quickSearchText(item), expansions)
  );
  renderSearchResults(
    target,
    [...documentMatches, ...clinicalMatches],
    "Risultati ricerca avanzata",
    "Nessun risultato nella ricerca avanzata.",
  );
}

function main() {
  const data = window.SANIKEY_DATA;
  if (!data) {
    throw new Error("Dati archivio non disponibili. Rigenerare l'export USB.");
  }
  const summary = data.summary || {};
  const timeline = data.timeline || [];
  const documents = data.documents || [];
  const dicomStudies = (data.clinical || {}).dicom_studies || [];
  const therapies = (data.clinical || {}).therapies || [];
  const searchRecords = (data.search || []).filter((item) => !isDicomTechnicalDocument(item));
  const clinicalRecords = searchRecords.filter((item) => item.type !== "document");
  const quickRecords = searchRecords;
  applyUi(summary);
  renderUsbInfo();
  renderSummary(summary, data.clinical || {});
  renderTimeline(timeline, documents);
  renderTherapies(therapies);
  configureTherapyNavigation(therapies);
  renderDicomStudies(dicomStudies);
  configureDicomNavigation(dicomStudies);
  renderObservationSections(data.clinical || {});
  renderDocuments(documents);
  setupTimelineDetailLinks(documents);
  setupResultDetailLinks();
  const advancedInput = document.querySelector("#advanced-search");
  const advancedResults = document.querySelector("#advanced-results");
  advancedResults.innerHTML = '<p class="muted">La ricerca avanzata carica il testo estratto al primo uso.</p>';
  window.SaniKeyUi.setupSections({
    defaultSection: document.querySelector("main").dataset.defaultSection || "documents",
    defaultRight: "timeline",
  });
  setSearchMode("basic");
  document.querySelector("#basic-toggle").addEventListener("click", () => setSearchMode("basic"));
  document.querySelector("#advanced-toggle").addEventListener("click", () => setSearchMode("advanced"));
  document.querySelector("#basic-help-button").addEventListener("click", () => openHelpDialog("#basic-help-dialog"));
  document.querySelector("#advanced-help-button").addEventListener("click", () => openHelpDialog("#advanced-help-dialog"));
  document.querySelector("#usb-info-button").addEventListener("click", () => openHelpDialog("#usb-info-dialog"));
  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => closeHelpDialog(button.dataset.closeDialog));
  });
  document.querySelector("#search").addEventListener("input", (event) => {
    setSearchMode("basic");
    if (event.target.value.trim()) {
      renderQuickSearch(quickRecords, event.target.value);
    } else {
      renderDocuments(documents);
    }
    window.SaniKeyUi.showSection("documents", "left");
  });
  advancedInput.addEventListener("input", (event) => {
    setSearchMode("advanced");
    advancedResults.innerHTML = '<p class="muted">Caricamento indice di ricerca avanzata...</p>';
    loadAdvancedSearchData()
      .then((payload) => renderAdvancedResults(payload, event.target.value, clinicalRecords))
      .catch((error) => {
        advancedResults.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
      });
    window.SaniKeyUi.showSection("advanced", "left");
  });
}

try {
  main();
} catch (error) {
  document.body.insertAdjacentHTML("beforeend", `<pre class="error">${error.message}</pre>`);
}
"""


def _extended_chart_js() -> str:
    """Render JavaScript for the standalone extended parameter charts.

    Parameters
    ----------
    None

    Returns
    -------
    str
        Offline JavaScript source.
    """

    return r"""function extendedText(value) {
  return value === null || value === undefined ? "" : String(value);
}

function extendedEscape(value) {
  return extendedText(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function extendedDate(value) {
  const match = extendedText(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : extendedText(value);
}

function extendedOrigin(point) {
  if (point.document_href) {
    return "Documento: " + decodeURIComponent(extendedText(point.document_href).split("/").pop());
  }
  if (point.source_reference) {
    return "Origine: " + point.source_reference;
  }
  return point.source_kind === "curated-observation" ? "Origine: osservazione curata" : "Origine: non disponibile";
}

function extendedPointLabel(raw) {
  if (raw.component) {
    return raw.component.label + ": " + raw.point[raw.component.field] + (raw.series.unit ? " " + raw.series.unit : "");
  }
  const value = raw.point.raw_value || raw.point.value;
  const unit = raw.point.raw_value ? "" : (raw.point.raw_unit || raw.point.normalized_unit || raw.series.unit || "");
  return value + (unit ? " " + unit : "");
}

function extendedChartOptions(units) {
  const scales = {
    x: {type: "linear", ticks: {callback: (value) => new Date(Number(value)).toLocaleDateString("it-IT")}},
    y: {type: "linear", position: "left", title: {display: Boolean(units[0]), text: units[0] || "Valore"}},
  };
  if (units[1]) {
    scales.y1 = {type: "linear", position: "right", title: {display: true, text: units[1]}, grid: {drawOnChartArea: false}};
  }
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales,
    plugins: {tooltip: {callbacks: {
      title: (contexts) => contexts.length ? extendedDate(contexts[0].raw.point.date) : "",
      label: (context) => extendedPointLabel(context.raw),
      afterLabel: (context) => extendedOrigin(context.raw.point),
    }}},
    onClick: (_event, elements, chart) => {
      if (!elements.length) { return; }
      const point = chart.data.datasets[elements[0].datasetIndex].data[elements[0].index].point;
      if (point && point.document_href) {
        window.open(point.document_href, "_blank", "noopener");
      }
    },
  };
}

function appendExtendedChart(target, title, datasets, units) {
  const card = document.createElement("section");
  card.className = "extended-chart-card";
  card.innerHTML = `<h2>${extendedEscape(title)}</h2>`;
  const canvas = document.createElement("canvas");
  canvas.className = "extended-parameter-chart";
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", title);
  card.appendChild(canvas);
  target.appendChild(card);
  new Chart(canvas, {type: "line", data: {datasets}, options: extendedChartOptions(units)});
}

function renderPressureChart(target, series, points) {
  const components = [
    {field: "systolic", label: "Sistolica", color: "#1d4ed8"},
    {field: "diastolic", label: "Diastolica", color: "#dc2626"},
    {field: "pulse", label: "Polso", color: "#15803d"},
  ];
  const datasets = components.map((component) => {
    const data = points.filter((point) => Number.isFinite(Number(point[component.field])))
      .map((point) => ({x: Date.parse(point.date + "T00:00:00"), y: Number(point[component.field]), point, series, component}));
    return data.length ? {label: component.label, data, borderColor: component.color, backgroundColor: component.color, borderWidth: 2, tension: 0.15} : null;
  }).filter(Boolean);
  if (datasets.length) {
    appendExtendedChart(target, series.name || series.id, datasets, [series.unit || "mmHg"]);
  }
}

function renderNumericCharts(target, entries) {
  const byUnit = new Map();
  entries.forEach((entry) => {
    const unit = entry.series.unit || "Senza unita'";
    const group = byUnit.get(unit) || [];
    group.push(entry);
    byUnit.set(unit, group);
  });
  const unitGroups = [...byUnit.entries()];
  const chartGroups = unitGroups.length <= 2 ? [unitGroups] : unitGroups.map((group) => [group]);
  const colors = ["#7c3aed", "#ea580c", "#0f766e", "#be123c", "#0369a1"];
  chartGroups.forEach((chartGroup) => {
    const units = chartGroup.map(([unit]) => unit);
    const datasets = chartGroup.flatMap(([unit, group], unitIndex) => group.map((entry, index) => ({
      label: entry.series.name || entry.series.id,
      yAxisID: unitIndex ? "y1" : "y",
      data: entry.points.map((point) => ({x: Date.parse(point.date + "T00:00:00"), y: Number(point.numeric_value), point, series: entry.series})),
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length],
      borderWidth: 2,
      tension: 0.15,
    })));
    const title = chartGroup.flatMap(([, group]) => group.map((entry) => entry.series.name || entry.series.id)).join(" · ");
    appendExtendedChart(target, title, datasets, units);
  });
}

function main() {
  const clinical = window.SANIKEY_DATA && window.SANIKEY_DATA.clinical || {};
  const series = (clinical.observation_series || []).slice().sort((left, right) => extendedText(left.name || left.id).localeCompare(extendedText(right.name || right.id), "it"));
  const points = clinical.observation_points || [];
  const requested = new URLSearchParams(window.location.search).get("series");
  const selected = new Set(series.some((item) => item.id === requested) ? [requested] : series.slice(0, 1).map((item) => item.id));
  const seriesTarget = document.querySelector("[data-extended-series]");
  const chartTarget = document.querySelector("[data-extended-charts]");
  const filters = {from: "", to: ""};
  function render() {
    seriesTarget.innerHTML = series.map((item) => `<label><input type="checkbox" value="${extendedEscape(item.id)}" ${selected.has(item.id) ? "checked" : ""}> ${extendedEscape(item.name || item.id)}</label>`).join("");
    seriesTarget.querySelectorAll("input").forEach((input) => input.addEventListener("change", () => {
      input.checked ? selected.add(input.value) : selected.delete(input.value);
      render();
    }));
    chartTarget.replaceChildren();
    const entries = series.filter((item) => selected.has(item.id)).map((item) => ({
      series: item,
      points: points.filter((point) => point.series_id === item.id && (!filters.from || point.date >= filters.from) && (!filters.to || point.date <= filters.to)),
    }));
    entries.filter((entry) => entry.series.value_type === "blood_pressure").forEach((entry) => renderPressureChart(chartTarget, entry.series, entry.points));
    const numeric = entries.map((entry) => ({...entry, points: entry.points.filter((point) => Number.isFinite(Number(point.numeric_value)))})).filter((entry) => entry.series.value_type !== "blood_pressure" && entry.points.length);
    renderNumericCharts(chartTarget, numeric);
    if (!chartTarget.children.length) {
      chartTarget.innerHTML = '<p class="muted">Nessun punto grafico nel periodo selezionato.</p>';
    }
  }
  document.querySelectorAll("[data-extended-filter]").forEach((input) => input.addEventListener("input", () => {
    filters[input.dataset.extendedFilter] = input.value;
    render();
  }));
  render();
}

if (typeof Chart !== "undefined") {
  main();
}
"""


def _ui_helper_js() -> str:
    """Render the vendored tab helper JavaScript.

    Parameters
    ----------
    None

    Returns
    -------
    str
        JavaScript source.
    """

    return r"""window.SaniKeyUi = (() => {
  const wideLayout = window.matchMedia("(min-width: 72rem)");
  const state = {
    left: "documents",
    right: "timeline",
  };

  function isDualLayout() {
    return wideLayout.matches;
  }

  function fallbackSection(excluded) {
    return ["documents", "timeline", "summary", "therapies", "parameters", "dicom", "advanced"]
      .find((section) => section !== excluded && isSectionAvailable(section)) || "documents";
  }

  function isSectionAvailable(name) {
    const panel = document.querySelector(`[data-section-panel="${name}"]`);
    return Boolean(panel && !panel.hidden);
  }

  function normalizeSection(name) {
    return isSectionAvailable(name) ? name : fallbackSection(name);
  }

  function showSection(name, target = "left") {
    const selected = normalizeSection(name);
    if (selected === "parameters" && isDualLayout()) {
      state.left = "parameters";
      state.right = normalizeSection("parameter-detail");
      applyPanes();
      return;
    }
    if (!isDualLayout() || target !== "right") {
      if (state.right === selected) {
        state.right = fallbackSection(selected);
      }
      state.left = selected;
      applyPanes();
      return;
    }
    if (state.left === selected) {
      state.left = fallbackSection(selected);
    }
    state.right = selected;
    applyPanes();
  }

  function applyPanes() {
    const dual = isDualLayout();
    state.left = normalizeSection(state.left);
    state.right = normalizeSection(state.right);
    if (dual && state.left === "parameters") {
      state.right = normalizeSection("parameter-detail");
    }
    if (dual && state.right === "parameter-detail" && state.left !== "parameters") {
      state.right = fallbackSection(state.left);
    }
    if (state.left === state.right) {
      state.right = fallbackSection(state.left);
    }
    document.body.dataset.layout = dual ? "dual" : "single";
    document.body.dataset.leftPane = state.left;
    document.body.dataset.rightPane = dual ? state.right : "";
    document.querySelectorAll("[data-section-panel]").forEach((panel) => {
      let role = "none";
      if (panel.dataset.sectionPanel === state.left) {
        role = "left";
      } else if (dual && panel.dataset.sectionPanel === state.right) {
        role = "right";
      }
      panel.dataset.paneRole = role;
      panel.classList.toggle("is-active", role !== "none");
    });
    document.querySelectorAll("[data-section-button]").forEach((button) => {
      const selected = button.dataset.sectionButton;
      const target = button.dataset.paneTarget || "left";
      const active = target === "right"
        ? dual && (state.right === selected || (selected === "parameters" && state.left === selected && state.right === "parameter-detail"))
        : state.left === selected;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", active ? "true" : "false");
    });
    window.dispatchEvent(new CustomEvent("sanikeylayoutchange", {detail: {dual}}));
  }

  function setupSections({defaultSection = "documents", defaultRight = "timeline"} = {}) {
    state.left = normalizeSection(defaultSection === "timeline" ? "documents" : defaultSection);
    state.right = normalizeSection(defaultRight);
    document.querySelectorAll("[data-section-button]").forEach((button) => {
      button.addEventListener("click", () => {
        showSection(button.dataset.sectionButton, button.dataset.paneTarget || "left");
      });
    });
    if (wideLayout.addEventListener) {
      wideLayout.addEventListener("change", applyPanes);
    } else {
      wideLayout.addListener(applyPanes);
    }
    applyPanes();
  }

  return {setupSections, showSection};
})();
"""


def _material_web_js() -> str:
    """Render local Material Web compatibility elements.

    Parameters
    ----------
    None

    Returns
    -------
    str
        JavaScript source.
    """

    return r"""class SaniKeyMaterialButton extends HTMLElement {
  connectedCallback() {
    if (this.dataset.ready === "true") {
      return;
    }
    this.dataset.ready = "true";
    this.setAttribute("role", "button");
    this.setAttribute("tabindex", this.getAttribute("tabindex") || "0");
    this.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        this.click();
      }
    });
  }
}

["md-filled-button", "md-filled-tonal-button", "md-outlined-button", "md-text-button", "md-icon-button"].forEach((name) => {
  if (!customElements.get(name)) {
    customElements.define(name, class extends SaniKeyMaterialButton {});
  }
});
"""


def _material_web_css() -> str:
    """Render local Material Web compatibility styles.

    Parameters
    ----------
    None

    Returns
    -------
    str
        CSS source.
    """

    return """:root {
  --md-sys-color-primary: #1f5f8b;
  --md-sys-color-on-primary: #ffffff;
  --md-sys-color-secondary-container: #d7e8f4;
  --md-sys-color-on-secondary-container: #12384f;
  --md-sys-color-outline: #b8c7d4;
}

md-filled-button,
md-filled-tonal-button,
md-outlined-button,
md-text-button,
md-icon-button {
  align-items: center;
  border-radius: 999px;
  cursor: pointer;
  display: inline-flex;
  font: inherit;
  font-weight: 700;
  justify-content: center;
  min-height: 2.4rem;
  padding: 0.35rem 0.85rem;
  text-decoration: none;
  user-select: none;
}

md-filled-button {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

md-filled-tonal-button {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

md-outlined-button {
  border: 1px solid var(--md-sys-color-outline);
  color: var(--md-sys-color-primary);
}

md-text-button {
  color: var(--md-sys-color-primary);
}

md-icon-button {
  aspect-ratio: 1;
  border: 1px solid var(--md-sys-color-outline);
  color: var(--md-sys-color-primary);
  padding: 0;
  width: 2.4rem;
}
"""


def _style_css() -> str:
    """Render static CSS.

    Parameters
    ----------
    None

    Returns
    -------
    str
        CSS source.
    """

    return """:root {
  --accent: #2563eb;
  --background-image: none;
  --background-opacity: 0.1;
  --border: #d8e0ea;
  --search-basic-accent: #0f766e;
  --search-advanced-accent: #9a5b00;
  --search-current-accent: var(--search-basic-accent);
  --surface: #f6f8fb;
  --text: #1f2933;
  --muted: #617083;
}

* {
  box-sizing: border-box;
}

[hidden] {
  display: none !important;
}

body {
  color: var(--text);
  font-family: system-ui, sans-serif;
  line-height: 1.5;
  margin: 0;
  position: relative;
}

body.has-background-image::before {
  background-image: var(--background-image);
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
  content: "";
  inset: 0;
  opacity: var(--background-opacity);
  pointer-events: none;
  position: fixed;
  z-index: -1;
}

header {
  align-items: start;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(18rem, 0.9fr) minmax(22rem, 1.1fr);
  padding: 1rem;
  position: sticky;
  top: 0;
  z-index: 10;
}

body.has-background-image header {
  background-color: var(--surface);
  background-image: linear-gradient(rgb(246 248 251 / calc(1 - var(--background-opacity))), rgb(246 248 251 / calc(1 - var(--background-opacity)))), var(--background-image);
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
  background-attachment: fixed;
}

.header-primary {
  display: grid;
  gap: 0.7rem;
}

h1 {
  font-size: 1.6rem;
  line-height: 1.15;
  margin: 0;
}

header p {
  color: var(--muted);
  margin: 0.25rem 0 0;
}

.header-logo {
  display: block;
  height: auto;
  width: 10.125rem;
}

.header-logo-button {
  background: transparent;
  border: 0;
  cursor: pointer;
  padding: 0;
}

.header-logo-button:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 4px;
}

.header-branding {
  align-items: baseline;
  display: flex;
  gap: 0.75rem;
}

.header-branding p {
  flex: 1;
  margin: 0;
  min-width: 0;
  transform: translateY(-1.35rem);
}

.header-actions,
.search-toolbar,
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.nav-control,
.search-mode-control {
  align-items: center;
  display: inline-flex;
  gap: 0.25rem;
}

.nav-control[hidden] {
  display: none;
}

.search-panel {
  border: 2px solid var(--search-current-accent);
  border-radius: 8px;
  display: grid;
  gap: 0.65rem;
  padding: 0.75rem;
}

body[data-search-mode="basic"] .search-panel,
.search-panel[data-search-mode="basic"] {
  --search-current-accent: var(--search-basic-accent);
}

body[data-search-mode="advanced"] .search-panel,
.search-panel[data-search-mode="advanced"] {
  --search-current-accent: var(--search-advanced-accent);
}

.search-control {
  display: grid;
  gap: 0.35rem;
}

[data-search-mode="basic"] [data-search-panel="advanced"],
[data-search-mode="advanced"] [data-search-panel="basic"] {
  display: none;
}

label {
  font-weight: 600;
}

main {
  display: grid;
  gap: 1rem;
  margin: 0 auto;
  max-width: 96rem;
  padding: 1rem;
}

input {
  border: 1px solid var(--border);
  border-radius: 6px;
  font: inherit;
  padding: 0.5rem;
  width: 100%;
}

.section-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0.75rem 0;
}

.section-links a {
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--accent);
  padding: 0.25rem 0.6rem;
  text-decoration: none;
}

.primary-action {
  color: var(--accent);
  font-weight: 800;
}

.is-active {
  outline: 2px solid color-mix(in srgb, var(--accent) 35%, transparent);
}

.technical-summary {
  border-top: 1px solid var(--border);
  margin-top: 1rem;
  padding-top: 0.75rem;
}

.app-footer {
  border-top: 1px solid var(--border);
  font-size: 0.875rem;
  margin-top: 1rem;
  padding: 1rem;
  text-align: center;
}

.footer-repository {
  border-radius: 4px;
  display: inline-block;
  line-height: 0;
  text-decoration: none;
}

.footer-repository:hover,
.footer-repository:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--accent) 45%, transparent);
  outline-offset: 4px;
}

.footer-logo {
  display: block;
  height: auto;
  max-width: 100%;
  width: 19.5rem;
}

.help-dialog {
  border: 1px solid var(--border);
  border-radius: 12px;
  max-width: min(34rem, calc(100vw - 2rem));
  padding: 0;
}

.help-dialog::backdrop {
  background: rgb(31 41 51 / 0.35);
}

.help-dialog article {
  border: 0;
  padding: 1rem;
}

.dialog-close {
  background: var(--accent);
  border: 0;
  border-radius: 999px;
  color: white;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  min-height: 2.4rem;
  padding: 0.35rem 0.85rem;
}

article {
  border-bottom: 1px solid var(--border);
  padding: 0.75rem 0;
}

article h3 {
  margin: 0 0 0.25rem;
}

article h4 {
  margin: 0 0 0.25rem;
}

dl {
  display: grid;
  gap: 0.25rem 0.75rem;
  grid-template-columns: max-content minmax(0, 1fr);
  margin: 0.5rem 0;
}

dl div {
  display: contents;
}

dt {
  color: var(--muted);
  font-weight: 700;
}

dd {
  margin: 0;
}

.result-count,
.muted {
  color: var(--muted);
}

.badge {
  background: color-mix(in srgb, var(--accent) 14%, white);
  border-radius: 999px;
  color: var(--accent);
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.1rem 0.45rem;
  vertical-align: middle;
}

.markdown {
  max-width: 100%;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.markdown img,
.markdown table,
.markdown pre,
.markdown code {
  max-width: 100%;
}

.markdown pre {
  overflow: auto;
  white-space: pre-wrap;
}

.markdown table {
  display: block;
  overflow-x: auto;
}

.observation-table {
  border-collapse: collapse;
  width: 100%;
}

.observation-table th,
.observation-table td {
  border-bottom: 1px solid var(--border);
  padding: 0.45rem 0.35rem;
  text-align: left;
  vertical-align: top;
}

.parameter-chart {
  display: block;
  height: 20rem !important;
  margin: 0.75rem 0 1rem;
  max-width: 100%;
  width: 100% !important;
}

.parameter-layout {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(12rem, 1fr) minmax(0, 3fr);
}

.parameter-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 0.75rem;
  margin: 0.75rem 0;
}

.parameter-filters label {
  display: grid;
  gap: 0.2rem;
}

.parameter-list button {
  display: flex;
  justify-content: space-between;
  margin: 0.2rem 0;
  text-align: left;
  width: 100%;
}

.parameter-list button[aria-pressed="true"] {
  font-weight: 700;
}

.parameter-detail {
  border-left: 3px solid var(--border);
  margin: 0.75rem 0;
  padding-left: 0.75rem;
}

.extended-chart-main {
  margin: 0 auto;
  max-width: 110rem;
  padding: 1rem;
}

.extended-chart-filters,
.extended-series-list {
  border: 1px solid var(--border);
  margin: 1rem 0;
  padding: 0.75rem;
}

.extended-chart-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.extended-chart-filters label,
.extended-series-list label {
  display: inline-flex;
  gap: 0.35rem;
}

[data-extended-series] {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
}

.extended-chart-card {
  border: 1px solid var(--border);
  margin: 1rem 0;
  padding: 1rem;
}

.extended-parameter-chart {
  display: block;
  height: min(68dvh, 44rem) !important;
  max-width: 100%;
  width: 100% !important;
}

.observation-table tr[data-parameter-point] {
  cursor: pointer;
}

.markdown h1,
.markdown h2,
.markdown h3 {
  margin: 0.75rem 0 0.25rem;
}

.markdown p,
.markdown ul,
.markdown ol {
  margin: 0.5rem 0;
}

.error {
  color: #9b1c1c;
  padding: 1rem;
}

.warning {
  background: #fff7ed;
  border-left: 4px solid #c2410c;
  color: #7c2d12;
  padding: 0.65rem 0.75rem;
}

body[data-density="compact"] article,
body[data-density="compact"] md-filled-button,
body[data-density="compact"] md-filled-tonal-button,
body[data-density="compact"] md-outlined-button,
body[data-density="compact"] md-text-button {
  padding-bottom: 0.45rem;
  padding-top: 0.45rem;
}

[data-section-panel] {
  display: none;
}

[data-section-panel].is-active {
  display: block;
}

@media (min-width: 72rem) {
  body[data-layout="dual"] {
    min-height: 100dvh;
  }

  body[data-layout="dual"] main {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    max-width: none;
    min-height: 800dvh;
    width: 90%;
  }

  body[data-layout="dual"] [data-pane-role="left"] {
    grid-column: 1;
    grid-row: 1;
    min-width: 0;
  }

  body[data-layout="dual"] [data-pane-role="right"] {
    border-left: 1px solid var(--border);
    grid-column: 2;
    grid-row: 1;
    min-width: 0;
    padding-left: 1rem;
  }

  body[data-layout="dual"] [data-pane-role="left"],
  body[data-layout="dual"] [data-pane-role="right"] {
    height: 800dvh;
    min-height: 800dvh;
    overflow: auto;
  }

  body[data-layout="dual"] #parameters .parameter-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 44rem) {
  .parameter-layout {
    grid-template-columns: 1fr;
  }

  header {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .search-toolbar,
  .header-actions {
    align-items: stretch;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .nav-control,
  .search-mode-control {
    align-items: stretch;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .nav-control {
    grid-template-columns: minmax(0, 1fr);
  }

  .nav-control md-icon-button {
    display: none;
  }
}

@media print {
  input,
  .header-actions,
  .search-panel {
    display: none;
  }
}
"""


def _escape_html(value: str) -> str:
    """Escape minimal HTML text.

    Parameters
    ----------
    value : str
        Text to escape.

    Returns
    -------
    str
        Escaped text.
    """

    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
