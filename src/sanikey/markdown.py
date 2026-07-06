"""Markdown rendering helpers for SaniKey exports."""

from __future__ import annotations

from functools import lru_cache
from typing import cast

from markdown_it import MarkdownIt


def render_markdown(value: str | None) -> str | None:
    """Render Markdown as safe static HTML.

    Parameters
    ----------
    value : str | None
        Markdown source text.

    Returns
    -------
    str | None
        Rendered HTML, or ``None`` when no source text is present.
    """

    if value is None:
        return None
    return cast("str", _renderer().render(value))


@lru_cache(maxsize=1)
def _renderer() -> MarkdownIt:
    """Return the configured Markdown renderer.

    Parameters
    ----------
    None

    Returns
    -------
    markdown_it.MarkdownIt
        CommonMark renderer with raw HTML disabled.
    """

    return MarkdownIt("commonmark", {"html": False})
