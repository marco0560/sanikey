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
    """

    web_dir: Path
    index: Path
    script: Path
    stylesheet: Path
    helper: Path


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
    index.write_text(_index_html(person), encoding="utf-8")
    script.write_text(_app_js(), encoding="utf-8")
    stylesheet.write_text(_style_css(), encoding="utf-8")
    helper.write_text(_ui_helper_js(), encoding="utf-8")
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
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <div class="header-title">
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
    <div class="search-control">
      <label for="search">Cerca nell'archivio</label>
      <input id="search" type="search" placeholder="Cerca documenti, categorie o tag">
    </div>
    <details class="search-help">
      <summary>Aiuto ricerca</summary>
      <p>Scrivi una o piu' parole presenti in titolo, categoria, tag, tipo,
      percorso o data. Esempi: <code>cardiologo 2024</code>,
      <code>analisi pdf</code>, <code>risonanza</code>.</p>
    </details>
    <nav id="section-jumps" class="section-jumps" aria-label="Vai alla sezione"></nav>
  </header>
  <nav class="tabs" aria-label="Sezioni archivio">
    <button type="button" data-tab-button="documents">Documenti</button>
    <button type="button" data-tab-button="advanced">Ricerca avanzata</button>
    <button type="button" data-tab-button="timeline">Timeline</button>
    <button type="button" data-tab-button="summary">Riepilogo</button>
  </nav>
  <main data-default-tab="{default_tab}">
    <section id="documents" class="primary-pane" data-tab-panel="documents" aria-label="Documenti"></section>
    <section id="advanced" class="primary-pane" data-tab-panel="advanced" aria-label="Ricerca avanzata">
      <h2>Ricerca avanzata</h2>
      <label for="advanced-search">Cerca nel contenuto OCR e testo estratto</label>
      <input id="advanced-search" type="search" placeholder='Esempio: creatinina AND (2024 OR 2025) NOT "urine"'>
      <details class="search-help" open>
        <summary>Sintassi ricerca avanzata</summary>
        <p>Usa parole, frasi tra virgolette, <code>AND</code>, <code>OR</code>,
        <code>NOT</code> e parentesi. Le parole adiacenti valgono come
        <code>AND</code>. La ricerca non distingue maiuscole, minuscole o
        accenti e applica sinonimi configurati.</p>
      </details>
      <div id="advanced-results" class="advanced-results"></div>
    </section>
    <aside class="secondary-pane">
      <section id="timeline" data-tab-panel="timeline" aria-label="Timeline"></section>
      <section id="summary" data-tab-panel="summary" aria-label="Riepilogo"></section>
    </aside>
  </main>
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
  dicom: "Studi DICOM",
  timeline: "Timeline",
  summary: "Riepilogo",
};

const SECTION_ORDER = ["documents", "therapies", "medications", "problems", "procedures", "observations", "dicom", "timeline"];

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
  document.querySelector("main").dataset.defaultTab = text(ui.default_tab || "documents");
}

function renderSummary(summary, clinical = {}) {
  const target = document.querySelector("#summary");
  target.innerHTML = `<h2>Riepilogo</h2>
    <p>Documenti: ${escapeHtml(summary.document_count)}</p>
    <p>Problemi: ${escapeHtml(summary.problem_count)}</p>
    <p>Procedure: ${escapeHtml(summary.procedure_count)}</p>
    <div class="markdown">${html(summary.clinical_summary_html) || `<p>${escapeHtml(summary.clinical_summary)}</p>`}</div>
    ${renderClinicalDashboard(clinical)}`;
}

function renderTimeline(timeline) {
  const target = document.querySelector("#timeline");
  target.innerHTML = "<h2>Timeline</h2>" + timeline.map((item) =>
    `<article id="entity-${attr(item.id)}"><strong>${escapeHtml(formatDateRange(item.start_date, item.end_date))}</strong> ${escapeHtml(item.title)}
      ${renderTimelineLinks(item)}</article>`
  ).join("");
}

function updateSectionJumps(sections) {
  const target = document.querySelector("#section-jumps");
  const selected = sections.filter((section) => section && SECTION_LABELS[section.label]);
  if (!selected.length) {
    target.innerHTML = "";
    return;
  }
  target.innerHTML = selected.map((section) =>
    `<a href="#${attr(section.id)}">${escapeHtml(SECTION_LABELS[section.label])}${section.count === undefined ? "" : ` ${escapeHtml(section.count)}`}</a>`
  ).join("");
}

function renderTimelineLinks(item) {
  const links = item.links || [];
  if (!links.length) {
    return "";
  }
  return `<p>${links.map((link) => `<a href="#entity-${attr(link)}">Dettaglio</a>`).join(" ")}</p>`;
}

function renderDocuments(documents, query = "") {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const selected = documents.filter((item) =>
    terms.every((term) => documentSearchText(item).includes(term))
  );
  const target = document.querySelector("#documents");
  const count = query ? `<p class="result-count">${selected.length} risultati</p>` : "";
  target.innerHTML = "<h2>Documenti</h2>" + count + selected.map((item) =>
    `<article id="entity-${attr(item.id)}"><h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(formatDate(item.date))} ${escapeHtml(item.category)} ${escapeHtml(item.kind)}</p>
      <p>${item.tags.map(escapeHtml).join(", ")}</p>
      ${item.markdown_html ? `<div class="markdown">${html(item.markdown_html)}</div>` : ""}
      ${item.href ? `<a href="${attr(item.href)}">Apri originale</a>` : `<span class="muted">Origine nel contenitore</span>`}</article>`
  ).join("");
  updateSectionJumps([
    {id: "documents", label: "documents", count: selected.length},
    {id: "timeline", label: "timeline"},
    {id: "summary", label: "summary"},
  ]);
}

function renderClinicalDashboard(clinical) {
  const sections = [
    ["problems", clinical.problems || []],
    ["therapies", clinical.therapies || []],
    ["medications", clinical.medications || []],
    ["observations", clinical.observations || []],
    ["procedures", clinical.procedures || []],
    ["dicom", clinical.dicom_studies || []],
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

function renderEntityCard(item, section) {
  return `<article id="entity-${attr(item.id)}"><h4>${escapeHtml(item.title)}</h4>
    ${item.date || item.start_date ? `<p>${escapeHtml(formatDate(item.date || item.start_date))}</p>` : ""}
    ${renderFields(item.fields || [])}
    ${item.href ? `<a href="${attr(item.href)}">${section === "dicom" ? "Apri supporto DICOM" : "Apri originale"}</a>` : ""}
    ${item.viewer_href ? `<a href="${attr(item.viewer_href)}" target="_blank" rel="noopener">Apri viewer HTML</a>` : ""}</article>`;
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
    updateSectionJumps([]);
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
  updateSectionJumps(sections.map(([section, items]) => ({
    id: `results-${section}`,
    label: section,
    count: items.length,
  })));
}

function renderResultCard(item, section) {
  return `<article><h4>${escapeHtml(item.title)} <span class="badge">${escapeHtml(SECTION_LABELS[section] || item.type)}</span></h4>
    ${item.subtitle ? `<p>${escapeHtml(item.subtitle)}</p>` : ""}
    ${renderFields(item.fields || [])}
    ${item.type === "document" && item.href ? `<a href="${attr(item.href)}">Apri originale</a>` : `<a href="#entity-${attr(item.id)}">Vai alla scheda</a>`}</article>`;
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

function advancedDocumentRecord(item, terms, expansions) {
  return {
    id: item.id,
    type: "document",
    section: "documents",
    title: item.title,
    subtitle: [formatDate(item.date), item.category, item.kind].filter(Boolean).join(" "),
    date: item.date,
    text: item.text,
    href: item.href,
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
  const clinicalRecords = (data.search || []).filter((item) => item.type !== "document");
  const quickRecords = data.search || [];
  applyUi(summary);
  renderSummary(summary, data.clinical || {});
  renderTimeline(timeline);
  renderDocuments(documents);
  const advancedInput = document.querySelector("#advanced-search");
  const advancedResults = document.querySelector("#advanced-results");
  advancedResults.innerHTML = '<p class="muted">La ricerca avanzata carica il testo estratto al primo uso.</p>';
  window.SaniKeyUi.setupTabs({
    defaultTab: document.querySelector("main").dataset.defaultTab || "documents",
  });
  document.querySelector("#search").addEventListener("input", (event) => {
    if (event.target.value.trim()) {
      renderQuickSearch(quickRecords, event.target.value);
    } else {
      renderDocuments(documents);
    }
    window.SaniKeyUi.showTab("documents");
  });
  advancedInput.addEventListener("input", (event) => {
    advancedResults.innerHTML = '<p class="muted">Caricamento indice di ricerca avanzata...</p>';
    loadAdvancedSearchData()
      .then((payload) => renderAdvancedResults(payload, event.target.value, clinicalRecords))
      .catch((error) => {
        advancedResults.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
      });
    window.SaniKeyUi.showTab("advanced");
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
  function showTab(name) {
    document.body.dataset.activeTab = name;
    document.querySelectorAll("[data-tab-button]").forEach((button) => {
      const selected = button.dataset.tabButton === name;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-selected", selected ? "true" : "false");
    });
    document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.tabPanel === name);
    });
  }

  function setupTabs({defaultTab = "documents"} = {}) {
    document.querySelectorAll("[data-tab-button]").forEach((button) => {
      button.addEventListener("click", () => showTab(button.dataset.tabButton));
    });
    showTab(defaultTab);
  }

  return {setupTabs, showTab};
})();
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
  --surface: #f6f8fb;
  --text: #1f2933;
  --muted: #617083;
}

* {
  box-sizing: border-box;
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
  align-items: end;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: grid;
  gap: 0.75rem;
  grid-template-columns: 1fr minmax(16rem, 28rem);
  padding: 1rem;
  position: sticky;
  top: 0;
  z-index: 2;
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

.search-control {
  display: grid;
  gap: 0.35rem;
}

label {
  font-weight: 600;
}

.tabs {
  background: white;
  border-bottom: 1px solid var(--border);
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  position: sticky;
  top: 8.25rem;
  z-index: 1;
}

.tabs button {
  background: white;
  border: 0;
  border-bottom: 3px solid transparent;
  color: var(--muted);
  cursor: pointer;
  font: inherit;
  padding: 0.75rem;
}

.tabs button.is-active {
  border-color: var(--accent);
  color: var(--text);
  font-weight: 700;
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

.search-help {
  color: var(--muted);
  font-size: 0.92rem;
  grid-column: 2;
}

.search-help summary {
  color: var(--accent);
  cursor: pointer;
  font-weight: 700;
}

.search-help p {
  margin: 0.35rem 0 0;
}

.section-links,
.section-jumps {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0.75rem 0;
}

.section-links a,
.section-jumps a {
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--accent);
  padding: 0.25rem 0.6rem;
  text-decoration: none;
}

.section-jumps {
  grid-column: 1 / -1;
  margin: 0;
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
  max-width: 64rem;
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

body[data-density="compact"] article,
body[data-density="compact"] .tabs button {
  padding-bottom: 0.45rem;
  padding-top: 0.45rem;
}

[data-tab-panel] {
  display: none;
}

[data-tab-panel].is-active {
  display: block;
}

@media (min-width: 56rem) {
  main {
    grid-template-columns: minmax(0, 1.35fr) minmax(20rem, 0.65fr);
  }

  .secondary-pane {
    border-left: 1px solid var(--border);
    padding-left: 1rem;
  }

  #advanced {
    display: none;
  }

  body[data-active-tab="advanced"] main {
    grid-template-columns: 1fr;
  }

  body[data-active-tab="advanced"] #documents,
  body[data-active-tab="advanced"] .secondary-pane {
    display: none;
  }

  body[data-active-tab="advanced"] #advanced {
    display: block;
  }

  #timeline {
    max-height: calc(100vh - 8rem);
    overflow: auto;
  }
}

@media (max-width: 44rem) {
  header {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .search-help {
    grid-column: 1;
  }
}

@media print {
  input,
  .tabs {
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
