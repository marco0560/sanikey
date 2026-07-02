#!/usr/bin/env python3
"""Regenerate docs/cheatsheet.md from marked documentation fragments."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_NAME = "sanikey"
DOCS_DIR = Path("docs")
OUTPUT = DOCS_DIR / "cheatsheet.md"
PATTERN = re.compile(
    r"<!-- cheatsheet:start -->(.*?)<!-- cheatsheet:end -->",
    re.DOTALL | re.IGNORECASE,
)


def main() -> int:
    """Build the cheatsheet from marked documentation blocks.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Process exit status.
    """
    blocks: list[str] = []
    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        if md_file == OUTPUT:
            continue
        matches = PATTERN.findall(md_file.read_text(encoding="utf-8"))
        blocks.extend(block.strip() for block in matches)

    header = (
        f"# Promemoria {PROJECT_NAME}\n\n"
        "Questo file è generato automaticamente dalla documentazione del progetto.\n\n"
        "Non modificare questo file manualmente.\n"
    )
    content = "\n\n---\n\n".join(blocks)
    OUTPUT.write_text(header + "\n" + content + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT} with {len(blocks)} sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
