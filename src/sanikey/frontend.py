"""Static frontend generation for SaniKey."""

from __future__ import annotations

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
    <div>
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
    <label for="search">Cerca nell'archivio</label>
    <input id="search" type="search" placeholder="Cerca documenti, categorie o tag">
    <details class="search-help">
      <summary>Aiuto ricerca</summary>
      <p>Scrivi una o piu' parole presenti in titolo, categoria, tag, tipo,
      percorso o data. Esempi: <code>cardiologo 2024</code>,
      <code>analisi pdf</code>, <code>risonanza</code>.</p>
    </details>
  </header>
  <nav class="tabs" aria-label="Sezioni archivio">
    <button type="button" data-tab-button="documents">Documenti</button>
    <button type="button" data-tab-button="timeline">Timeline</button>
    <button type="button" data-tab-button="summary">Riepilogo</button>
  </nav>
  <main data-default-tab="{default_tab}">
    <section id="documents" class="primary-pane" data-tab-panel="documents" aria-label="Documenti"></section>
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

    return r"""function text(value) {
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
  document.body.dataset.density = text(ui.density || "comfortable");
  document.querySelector("main").dataset.defaultTab = text(ui.default_tab || "documents");
}

function renderSummary(summary) {
  const target = document.querySelector("#summary");
  target.innerHTML = `<h2>Riepilogo</h2>
    <p>Documenti: ${escapeHtml(summary.document_count)}</p>
    <p>Problemi: ${escapeHtml(summary.problem_count)}</p>
    <p>Procedure: ${escapeHtml(summary.procedure_count)}</p>
    <div class="markdown">${html(summary.clinical_summary_html) || `<p>${escapeHtml(summary.clinical_summary)}</p>`}</div>`;
}

function renderTimeline(timeline) {
  const target = document.querySelector("#timeline");
  target.innerHTML = "<h2>Timeline</h2>" + timeline.map((item) =>
    `<article><strong>${escapeHtml(formatDateRange(item.start_date, item.end_date))}</strong> ${escapeHtml(item.title)}</article>`
  ).join("");
}

function renderDocuments(documents, query = "") {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const selected = documents.filter((item) =>
    terms.every((term) => documentSearchText(item).includes(term))
  );
  const target = document.querySelector("#documents");
  const count = query ? `<p class="result-count">${selected.length} risultati</p>` : "";
  target.innerHTML = "<h2>Documenti</h2>" + count + selected.map((item) =>
    `<article><h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(formatDate(item.date))} ${escapeHtml(item.category)} ${escapeHtml(item.kind)}</p>
      <p>${item.tags.map(escapeHtml).join(", ")}</p>
      ${item.markdown_html ? `<div class="markdown">${html(item.markdown_html)}</div>` : ""}
      ${item.href ? `<a href="${attr(item.href)}">Apri originale</a>` : `<span class="muted">Origine nel contenitore</span>`}</article>`
  ).join("");
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

function main() {
  const data = window.SANIKEY_DATA;
  if (!data) {
    throw new Error("Dati archivio non disponibili. Rigenerare l'export USB.");
  }
  const summary = data.summary || {};
  const timeline = data.timeline || [];
  const documents = data.documents || [];
  applyUi(summary);
  renderSummary(summary);
  renderTimeline(timeline);
  renderDocuments(documents);
  window.SaniKeyUi.setupTabs({
    defaultTab: document.querySelector("main").dataset.defaultTab || "documents",
  });
  document.querySelector("#search").addEventListener("input", (event) => {
    renderDocuments(documents, event.target.value);
    window.SaniKeyUi.showTab("documents");
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
}

header {
  align-items: end;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: grid;
  gap: 0.75rem;
  grid-template-columns: 1fr minmax(16rem, 28rem);
  padding: 1rem;
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

label {
  font-weight: 600;
}

.tabs {
  background: white;
  border-bottom: 1px solid var(--border);
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  position: sticky;
  top: 0;
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

article {
  border-bottom: 1px solid var(--border);
  padding: 0.75rem 0;
}

article h3 {
  margin: 0 0 0.25rem;
}

.result-count,
.muted {
  color: var(--muted);
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
  .tabs {
    display: none;
  }

  main {
    grid-template-columns: minmax(0, 1.35fr) minmax(20rem, 0.65fr);
  }

  .secondary-pane {
    border-left: 1px solid var(--border);
    padding-left: 1rem;
  }

  [data-tab-panel],
  [data-tab-panel].is-active {
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
