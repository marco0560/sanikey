#!/usr/bin/env python3
"""Create a new decision note under docs/decisions/."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import unicodedata
from pathlib import Path

DEFAULT_DECISIONS_DIR = Path("docs/decisions")
INDEX_FILENAME = "index.md"
STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "of",
    "to",
    "for",
    "in",
    "on",
    "with",
    "by",
}


def slugify(text: str) -> str:
    """Convert a one-line description into a filesystem-friendly slug.

    Parameters
    ----------
    text : str
        Description to convert.

    Returns
    -------
    str
        Filesystem-friendly slug.

    Raises
    ------
    ValueError
        If ``text`` does not produce any slug token.
    """
    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized).lower()
    tokens = [token for token in normalized.split() if token not in STOPWORDS]
    if not tokens:
        msg = "Description does not produce a valid slug"
        raise ValueError(msg)
    return "-".join(tokens)


def next_decision_number(decisions_dir: Path) -> int:
    """Return the next numeric decision prefix.

    Parameters
    ----------
    decisions_dir : pathlib.Path
        Directory containing decision Markdown files.

    Returns
    -------
    int
        Next available numeric decision prefix.
    """
    numbers = []
    for path in decisions_dir.glob("*.md"):
        match = re.match(r"(\d+)-", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def fail(message: str) -> None:
    """Print an error and exit.

    Parameters
    ----------
    message : str
        Error message to print.

    Returns
    -------
    None
    """
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    """Create the decision note and append it to the index.

    Parameters
    ----------
    argv : list[str] | None, optional
        Command-line arguments. When omitted, use ``sys.argv``.

    Returns
    -------
    int
        Process exit status.
    """
    parser = argparse.ArgumentParser(description="Create a new decision note.")
    parser.add_argument("--decisions-dir", type=Path, default=DEFAULT_DECISIONS_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    decisions_dir = args.decisions_dir
    index_file = decisions_dir / INDEX_FILENAME
    if not decisions_dir.is_dir():
        fail(f"Decisions directory not found: {decisions_dir}")
    if not index_file.is_file():
        fail(f"Decision index not found: {index_file}")

    description = input("One-line description: ").strip()
    if not description:
        fail("Description cannot be empty")

    decision_number = next_decision_number(decisions_dir)
    filename = f"{decision_number:04d}-{slugify(description)}.md"
    target = decisions_dir / filename
    content = f"""# Decision {decision_number:04d} - {description}

**Date**: {dt.date.today().isoformat()}
**Status**: Accepted

## Context

<Describe the context>

## Decision

<Describe the decision>

## Consequences

<Describe the consequences>
"""
    index_entry = f"- [{decision_number:04d} — {description}]({filename})\n"

    print(f"Decision file: {target}")
    if args.dry_run:
        return 0

    target.write_text(content, encoding="utf-8")
    with index_file.open("a", encoding="utf-8") as handle:
        handle.write(index_entry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
