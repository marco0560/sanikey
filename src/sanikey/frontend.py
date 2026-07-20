"""Static frontend generation for SaniKey."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .config import PersonConfig


@dataclass(frozen=True)
class FrontendResult:
    """Result of frontend generation.

    Parameters
    ----------
    web_dir : pathlib.Path
        Generated frontend directory.
    index : pathlib.Path
        Generated index HTML.
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
    """

    web_dir: Path
    index: Path
    script: Path
    stylesheet: Path
    helper: Path
    material_script: Path
    material_stylesheet: Path


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
    script = web_dir / "app.js"
    stylesheet = web_dir / "style.css"
    helper = assets_dir / "ui-helper.js"
    material_script = assets_dir / "material-web.js"
    material_stylesheet = assets_dir / "material-web.css"
    index.write_text(_index_html(person), encoding="utf-8")
    script.write_text(_app_js(), encoding="utf-8")
    stylesheet.write_text(_style_css(), encoding="utf-8")
    helper.write_text(_ui_helper_js(), encoding="utf-8")
    material_script.write_text(_material_web_js(), encoding="utf-8")
    material_stylesheet.write_text(_material_web_css(), encoding="utf-8")
    if person.ui.background_image is not None:
        shutil.copy2(
            person.ui.background_image,
            assets_dir / f"background{person.ui.background_image.suffix.lower()}",
        )
    return FrontendResult(
        web_dir=web_dir,
        index=index,
        script=script,
        stylesheet=stylesheet,
        helper=helper,
        material_script=material_script,
        material_stylesheet=material_stylesheet,
    )


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
        <p>{subtitle}</p>
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
        <span class="nav-control" data-observation-control="weight" hidden>
          <md-text-button type="button" data-section-button="weight" data-pane-target="left">Peso</md-text-button>
          <md-icon-button type="button" data-section-button="weight" data-pane-target="right" aria-label="Apri Peso a destra">&gt;</md-icon-button>
        </span>
        <span class="nav-control" data-observation-control="pressure" hidden>
          <md-text-button type="button" data-section-button="pressure" data-pane-target="left">Pressione</md-text-button>
          <md-icon-button type="button" data-section-button="pressure" data-pane-target="right" aria-label="Apri Pressione a destra">&gt;</md-icon-button>
        </span>
        <span class="nav-control" data-observation-control="glucose" hidden>
          <md-text-button type="button" data-section-button="glucose" data-pane-target="left">Glicemia</md-text-button>
          <md-icon-button type="button" data-section-button="glucose" data-pane-target="right" aria-label="Apri Glicemia a destra">&gt;</md-icon-button>
        </span>
        <span class="nav-control" data-observation-control="inr" hidden>
          <md-text-button type="button" data-section-button="inr" data-pane-target="left">INR</md-text-button>
          <md-icon-button type="button" data-section-button="inr" data-pane-target="right" aria-label="Apri INR a destra">&gt;</md-icon-button>
        </span>
        <span class="nav-control" data-observation-control="parameters" hidden>
          <md-text-button type="button" data-section-button="parameters" data-pane-target="left">Parametri</md-text-button>
          <md-icon-button type="button" data-section-button="parameters" data-pane-target="right" aria-label="Apri Parametri a destra">&gt;</md-icon-button>
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
    <section id="weight" data-section-panel="weight" aria-label="Peso" hidden></section>
    <section id="pressure" data-section-panel="pressure" aria-label="Pressione" hidden></section>
    <section id="glucose" data-section-panel="glucose" aria-label="Glicemia" hidden></section>
    <section id="inr" data-section-panel="inr" aria-label="INR" hidden></section>
    <section id="parameters" data-section-panel="parameters" aria-label="Parametri" hidden></section>
    <section id="dicom" data-section-panel="dicom" aria-label="Studi DICOM"></section>
  </main>
  <footer class="app-footer"><a href="https://github.com/marco0560/sanikey" target="_blank" rel="noopener">SaniKey su GitHub</a></footer>
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
  <script src="data.js"></script>
  <script src="assets/ui-helper.js"></script>
  <script src="app.js"></script>
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
  weight: "Peso",
  pressure: "Pressione",
  glucose: "Glicemia",
  inr: "INR",
  parameters: "Parametri",
  dicom: "Studi DICOM",
  timeline: "Timeline",
  summary: "Sintesi Clinica",
};

const OBSERVATION_SECTION_BY_ID = {
  peso: "weight",
  weight: "weight",
  pressione: "pressure",
  pressure: "pressure",
  glicemia: "glucose",
  glucose: "glucose",
  inr: "inr",
};

const SECTION_ORDER = ["documents", "therapies", "medications", "problems", "procedures", "observations", "weight", "pressure", "glucose", "inr", "parameters", "dicom", "timeline"];
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

function renderTimeline(timeline) {
  const target = document.querySelector("#timeline");
  target.innerHTML = "<h2>Timeline</h2>" + timeline.map((item) =>
    `<article id="entity-${attr(item.id)}"><strong>${escapeHtml(formatDateRange(item.start_date, item.end_date))}</strong> ${escapeHtml(item.title)}
      ${renderTimelineLinks(item)}</article>`
  ).join("");
}

function renderTimelineLinks(item) {
  const links = item.links || [];
  if (!links.length) {
    return "";
  }
  return `<p>${links.map((link) => `<a href="#entity-${attr(link)}" data-detail-link="${attr(link)}">Dettaglio</a>`).join(" ")}</p>`;
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
  const selected = documents.filter((item) => !isDicomTechnicalDocument(item)).filter((item) =>
    terms.every((term) => documentSearchText(item).includes(term))
  );
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
  return OBSERVATION_SECTION_BY_ID[text(series.id).toLowerCase()] || "parameters";
}

function renderObservationSections(clinical) {
  const series = clinical.observation_series || [];
  const points = clinical.observation_points || [];
  const bySeries = new Map(series.map((item) => [item.id, item]));
  const grouped = {
    weight: [],
    pressure: [],
    glucose: [],
    inr: [],
    parameters: [],
  };
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
  target.innerHTML = `<h2>${escapeHtml(SECTION_LABELS[section])}</h2>` + (
    sorted.length
      ? `<table class="observation-table"><thead><tr><th>Data</th><th>Serie</th><th>Valore</th><th>Fonte</th></tr></thead><tbody>${sorted.map(({series, point}) =>
          `<tr id="entity-${attr(point.id)}"><td>${escapeHtml(formatDate(point.date))}</td><td>${escapeHtml(series.name || series.id)}</td><td>${escapeHtml(point.value)}</td><td>${escapeHtml(point.source_reference)}</td></tr>`
        ).join("")}</tbody></table>`
      : '<p class="muted">Nessuna misurazione disponibile.</p>'
  );
}

function configureObservationNavigation(grouped) {
  Object.entries(grouped).forEach(([section, items]) => {
    document.querySelectorAll(`[data-observation-control="${section}"]`).forEach((control) => {
      control.hidden = !items.length;
    });
    document.querySelector(`#${section}`).hidden = !items.length;
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
  renderSearchResults(
    document.querySelector("#documents"),
    selected,
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
  renderSummary(summary, data.clinical || {});
  renderTimeline(timeline);
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
    return ["documents", "timeline", "summary", "therapies", "weight", "pressure", "glucose", "inr", "parameters", "dicom", "advanced"]
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
        ? dual && state.right === selected
        : state.left === selected;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", active ? "true" : "false");
    });
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
  z-index: 2;
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
  body[data-layout="dual"] main {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
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
    height: calc(100vh - 8rem);
    min-height: 0;
    overflow: auto;
  }
}

@media (max-width: 44rem) {
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
