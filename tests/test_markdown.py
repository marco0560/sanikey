"""Markdown rendering tests."""

from __future__ import annotations

from sanikey.markdown import render_markdown


def test_render_markdown_converts_commonmark() -> None:
    """Verify CommonMark text renders to HTML.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    html = render_markdown("# Sintesi\n\n- Punto")

    assert html == "<h1>Sintesi</h1>\n<ul>\n<li>Punto</li>\n</ul>\n"


def test_render_markdown_escapes_raw_html() -> None:
    """Verify raw HTML inside Markdown is escaped.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    html = render_markdown("<script>alert(1)</script>")

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
