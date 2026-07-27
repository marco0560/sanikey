"""Tests for the tracked Tesseract medical glossary."""

from __future__ import annotations

from pathlib import Path


def test_tesseract_medical_glossary_is_a_canonical_word_list() -> None:
    """Verify the glossary stays consumable by Tesseract user-words.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    path = Path("src/sanikey/assets/ocr/tesseract-medical-it.user-words")
    content = path.read_text(encoding="utf-8")

    assert content.endswith("\n")
    assert not content.startswith("\ufeff")
    entries = content.splitlines()
    assert entries
    assert all(entry == entry.strip() and entry for entry in entries)
    assert len(entries) == len(set(entries))
    assert "HbA1c" in entries
    assert "HbAlc" not in entries
