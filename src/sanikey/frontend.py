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
    """

    web_dir: Path
    index: Path
    script: Path
    stylesheet: Path


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
    index.write_text(_index_html(person), encoding="utf-8")
    script.write_text(_app_js(), encoding="utf-8")
    stylesheet.write_text(_style_css(), encoding="utf-8")
    return FrontendResult(
        web_dir=web_dir, index=index, script=script, stylesheet=stylesheet
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
    <h1>{title}</h1>
    <input id="search" type="search" placeholder="Cerca nell'archivio">
  </header>
  <main>
    <section id="summary" aria-label="Riepilogo"></section>
    <section id="timeline" aria-label="Timeline"></section>
    <section id="documents" aria-label="Documenti"></section>
  </main>
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

    return r"""async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Cannot load ${path}`);
  return response.json();
}

function text(value) {
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

function renderSummary(summary) {
  const target = document.querySelector("#summary");
  target.innerHTML = `<h2>Riepilogo</h2>
    <p>Documenti: ${summary.document_count}</p>
    <p>Problemi: ${summary.problem_count}</p>
    <p>Procedure: ${summary.procedure_count}</p>
    <p>${text(summary.clinical_summary)}</p>`;
}

function renderTimeline(timeline) {
  const target = document.querySelector("#timeline");
  target.innerHTML = "<h2>Timeline</h2>" + timeline.map((item) =>
    `<article><strong>${formatDateRange(item.start_date, item.end_date)}</strong> ${text(item.title)}</article>`
  ).join("");
}

function renderDocuments(documents, query = "") {
  const normalized = query.toLowerCase();
  const selected = documents.filter((item) =>
    `${item.title} ${item.category} ${item.tags.join(" ")}`.toLowerCase().includes(normalized)
  );
  const target = document.querySelector("#documents");
  target.innerHTML = "<h2>Documenti</h2>" + selected.map((item) =>
    `<article><h3>${text(item.title)}</h3>
      <p>${formatDate(item.date)} ${text(item.category)} ${text(item.kind)}</p>
      <p>${item.tags.map(text).join(", ")}</p>
      <a href="${text(item.path)}">Apri originale</a></article>`
  ).join("");
}

async function main() {
  const [summary, timeline, documents] = await Promise.all([
    loadJson("data/summary.json"),
    loadJson("data/timeline.json"),
    loadJson("data/documents.json"),
  ]);
  renderSummary(summary);
  renderTimeline(timeline);
  renderDocuments(documents);
  document.querySelector("#search").addEventListener("input", (event) => {
    renderDocuments(documents, event.target.value);
  });
}

main().catch((error) => {
  document.body.insertAdjacentHTML("beforeend", `<pre class="error">${error.message}</pre>`);
});
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

    return """body {
  color: #1f2933;
  font-family: system-ui, sans-serif;
  line-height: 1.5;
  margin: 0;
}

header {
  background: #eef2f6;
  border-bottom: 1px solid #cad3df;
  padding: 1rem;
}

main {
  display: grid;
  gap: 1rem;
  margin: 0 auto;
  max-width: 72rem;
  padding: 1rem;
}

input {
  font: inherit;
  max-width: 32rem;
  padding: 0.5rem;
  width: 100%;
}

article {
  border-bottom: 1px solid #d9e2ec;
  padding: 0.75rem 0;
}

.error {
  color: #9b1c1c;
  padding: 1rem;
}

@media print {
  input {
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
