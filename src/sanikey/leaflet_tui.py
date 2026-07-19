"""ncurses interface for resolving ambiguous AIFA medication candidates."""

from __future__ import annotations

import curses
import textwrap
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .leaflets import AifaCandidate
    from .models import Medication, TherapyEpisode


@dataclass(frozen=True)
class LeafletReviewDecision:
    """Represent an operator action in the AIFA candidate review.

    Parameters
    ----------
    candidate_index : int | None, optional
        One-based approved candidate index, when the operator approves one.
    exit_requested : bool, optional
        Whether the operator requested immediate command exit without saving.
    manual_query : str | None, optional
        A new AIFA query requested by the operator.
    mark_non_aifa : bool, optional
        Whether the medication should be persisted as not applicable to AIFA.
    """

    candidate_index: int | None = None
    exit_requested: bool = False
    manual_query: str | None = None
    mark_non_aifa: bool = False


def choose_aifa_candidate(
    medication: Medication,
    therapies: tuple[TherapyEpisode, ...],
    candidates: tuple[AifaCandidate, ...],
) -> LeafletReviewDecision:
    """Show a two-pane ncurses review screen for one ambiguous medication.

    Parameters
    ----------
    medication : sanikey.models.Medication
        Curated medication identity shown in the right pane.
    therapies : tuple[sanikey.models.TherapyEpisode, ...]
        Curated therapy episodes linked to the medication.
    candidates : tuple[sanikey.leaflets.AifaCandidate, ...]
        AIFA candidates displayed in the left pane.

    Returns
    -------
    LeafletReviewDecision
        Operator decision, including a request to exit without saving.
    """

    return curses.wrapper(_review_screen, medication, therapies, candidates)


def _review_screen(
    screen: curses.window,
    medication: Medication,
    therapies: tuple[TherapyEpisode, ...],
    candidates: tuple[AifaCandidate, ...],
) -> LeafletReviewDecision:
    """Run the ncurses event loop for one medication review.

    Parameters
    ----------
    screen : curses.window
        Root ncurses screen.
    medication : sanikey.models.Medication
        Curated medication identity.
    therapies : tuple[sanikey.models.TherapyEpisode, ...]
        Linked curated therapy episodes.
    candidates : tuple[sanikey.leaflets.AifaCandidate, ...]
        AIFA candidates.

    Returns
    -------
    LeafletReviewDecision
        Operator decision, including a request to exit without saving.
    """

    selected = 0
    curses.start_color()
    curses.use_default_colors()
    screen.bkgd(" ", curses.color_pair(0))
    curses.curs_set(0)
    screen.keypad(True)
    while True:
        _draw_review(screen, medication, therapies, candidates, selected)
        key = screen.getch()
        if key in (curses.KEY_UP, ord("k")) and candidates:
            selected = max(0, selected - 1)
        elif key in (curses.KEY_DOWN, ord("j")) and candidates:
            selected = min(len(candidates) - 1, selected + 1)
        elif key in (curses.KEY_ENTER, ord("\n"), ord("a")) and candidates:
            return LeafletReviewDecision(selected + 1)
        elif key == ord("r"):
            return LeafletReviewDecision()
        elif key == ord("n"):
            return LeafletReviewDecision(mark_non_aifa=True)
        elif key == ord("s"):
            manual_query = _prompt_manual_query(screen)
            if manual_query:
                return LeafletReviewDecision(manual_query=manual_query)
        elif key in (ord("q"), ord("x"), 27):
            return LeafletReviewDecision(exit_requested=True)


def _draw_review(
    screen: curses.window,
    medication: Medication,
    therapies: tuple[TherapyEpisode, ...],
    candidates: tuple[AifaCandidate, ...],
    selected: int,
) -> None:
    """Draw candidate and curated-therapy panels.

    Parameters
    ----------
    screen : curses.window
        Root ncurses screen.
    medication : sanikey.models.Medication
        Curated medication identity.
    therapies : tuple[sanikey.models.TherapyEpisode, ...]
        Linked curated therapy episodes.
    candidates : tuple[sanikey.leaflets.AifaCandidate, ...]
        AIFA candidates.
    selected : int
        Zero-based selected candidate index.

    Returns
    -------
    None
    """

    screen.erase()
    height, width = screen.getmaxyx()
    split = max(40, width // 2)
    _safe_add(screen, 0, 0, "Candidati AIFA")
    _safe_add(screen, 0, split, "Terapia curata")
    for row in range(1, height - 2):
        _safe_add(screen, row, split - 1, "|")
    for index, candidate in enumerate(candidates):
        marker = ">" if index == selected else " "
        summary = " - ".join(
            item
            for item in (candidate.title, candidate.strength, candidate.form)
            if item
        )
        _safe_add(
            screen,
            2 + index,
            0,
            f"{marker} {summary}"[: split - 2],
        )
    candidate_top = min(4 + len(candidates), max(5, height // 3))
    if candidates:
        _draw_lines(
            screen, candidate_top, 0, split - 2, _candidate_card(candidates[selected])
        )
    else:
        _safe_add(screen, 2, 0, "Nessun candidato automatico rilevato.")
    _draw_lines(
        screen, 2, split, width - split - 1, _curated_card(medication, therapies)
    )
    _safe_add(
        screen,
        height - 1,
        0,
        "Frecce/j/k: seleziona  Invio/a: approva  s: cerca  n: non AIFA  r: rifiuta  q/Esc/x: esci",
    )
    screen.refresh()


def _prompt_manual_query(screen: curses.window) -> str | None:
    """Prompt for a manual AIFA search without changing terminal colours.

    Parameters
    ----------
    screen : curses.window
        Root ncurses screen.

    Returns
    -------
    str | None
        Trimmed search text, or ``None`` when the operator leaves it empty.
    """

    height, width = screen.getmaxyx()
    prompt = "Ricerca manuale AIFA: "
    _safe_add(screen, height - 1, 0, " " * max(0, width - 1))
    _safe_add(screen, height - 1, 0, prompt)
    with suppress(curses.error):
        curses.curs_set(1)
        curses.echo()
        raw = screen.getstr(
            height - 1, min(len(prompt), width - 1), max(1, width - len(prompt) - 1)
        )
        curses.noecho()
        curses.curs_set(0)
        return raw.decode("utf-8", errors="replace").strip() or None
    return None


def _candidate_card(candidate: AifaCandidate) -> tuple[str, ...]:
    """Build visible details for a selected AIFA candidate.

    Parameters
    ----------
    candidate : sanikey.leaflets.AifaCandidate
        Selected AIFA candidate.

    Returns
    -------
    tuple[str, ...]
        Candidate detail lines.
    """

    return _detail_lines(
        "Scheda candidato",
        (
            ("Nome", candidate.title),
            (
                "Forma/dosaggio",
                " - ".join(
                    item for item in (candidate.form, candidate.strength) if item
                ),
            ),
            ("Principi attivi", ", ".join(candidate.active_ingredients)),
            ("ATC", ", ".join(candidate.atc)),
            ("Via", ", ".join(candidate.routes)),
            ("Titolare", candidate.company or ""),
            ("Confezioni", "; ".join(candidate.packages[:3])),
            ("AIFA", f"{candidate.codice_sis}/{candidate.aic6}"),
            (
                "Da verificare",
                ", ".join(candidate.mismatches),
            ),
        ),
    )


def _curated_card(
    medication: Medication,
    therapies: tuple[TherapyEpisode, ...],
) -> tuple[str, ...]:
    """Build visible details for the curated medication and linked therapies.

    Parameters
    ----------
    medication : sanikey.models.Medication
        Curated medication identity.
    therapies : tuple[sanikey.models.TherapyEpisode, ...]
        Linked curated therapy episodes.

    Returns
    -------
    tuple[str, ...]
        Curated medication and therapy detail lines.
    """

    fields: list[tuple[str, str]] = [
        ("Farmaco", medication.name),
        ("Principio attivo", medication.active_ingredient or ""),
        ("Forma", medication.form or ""),
        ("Dosaggio", medication.strength_per_unit or ""),
    ]
    for therapy in therapies:
        fields.extend(
            (
                ("Terapia", therapy.id),
                ("Dose", therapy.dosage or ""),
                ("Schema", ", ".join(therapy.schedule)),
                ("Istruzioni", therapy.instructions or ""),
                (
                    "Periodo",
                    " - ".join(
                        item for item in (therapy.start_date, therapy.end_date) if item
                    ),
                ),
                ("Ruolo", therapy.role or ""),
            )
        )
    return _detail_lines("Dati da TOML curato", tuple(fields))


def _detail_lines(title: str, fields: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
    """Format non-empty labeled fields for a terminal card.

    Parameters
    ----------
    title : str
        Card title.
    fields : tuple[tuple[str, str], ...]
        Labeled values.

    Returns
    -------
    tuple[str, ...]
        Card lines before terminal-width wrapping.
    """

    return (title, *(f"{label}: {value}" for label, value in fields if value))


def _draw_lines(
    screen: curses.window,
    top: int,
    left: int,
    width: int,
    lines: tuple[str, ...],
) -> None:
    """Draw wrapped card lines inside a screen column.

    Parameters
    ----------
    screen : curses.window
        Root ncurses screen.
    top : int
        Starting row.
    left : int
        Starting column.
    width : int
        Available line width.
    lines : tuple[str, ...]
        Unwrapped card lines.

    Returns
    -------
    None
    """

    height, _ = screen.getmaxyx()
    row = top
    for line in lines:
        for wrapped in textwrap.wrap(line, width=max(10, width)) or [""]:
            if row >= height - 2:
                return
            _safe_add(screen, row, left, wrapped)
            row += 1


def _safe_add(
    screen: curses.window,
    row: int,
    column: int,
    text: str,
    attributes: int = 0,
) -> None:
    """Write a clipped terminal line without propagating resize errors.

    Parameters
    ----------
    screen : curses.window
        Root ncurses screen.
    row : int
        Target row.
    column : int
        Target column.
    text : str
        Text to draw.
    attributes : int, optional
        ncurses attribute mask.

    Returns
    -------
    None
    """

    with suppress(curses.error):
        screen.addstr(row, column, text, attributes)
