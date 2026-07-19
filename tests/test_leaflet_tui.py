"""ncurses leaflet review presentation tests."""

from __future__ import annotations

import curses
from typing import TYPE_CHECKING

from sanikey import leaflet_tui
from sanikey.leaflet_tui import (
    _candidate_card,
    _curated_card,
    _review_screen,
)
from sanikey.leaflets import AifaCandidate
from sanikey.models import Medication, TherapyEpisode

if TYPE_CHECKING:
    import pytest


def test_candidate_card_exposes_aifa_details() -> None:
    """Verify the candidate card includes discriminating AIFA attributes.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    card = _candidate_card(
        AifaCandidate(
            "Drug A",
            "123",
            "456",
            ("Ingredient A",),
            "Compressa",
            "20 mg compressa",
            "Example Pharma",
            ("ATC A",),
            ("Orale",),
            ("20 mg - 30 compresse",),
        )
    )

    assert "Forma/dosaggio: Compressa - 20 mg compressa" in card
    assert "Principi attivi: Ingredient A" in card
    assert "Titolare: Example Pharma" in card
    assert "Confezioni: 20 mg - 30 compresse" in card


def test_curated_card_exposes_medication_and_therapy_toml_data() -> None:
    """Verify the curated panel includes the linked therapy record.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    card = _curated_card(
        Medication("drug-a", "Drug A", "Ingredient A", "compresse", "20 mg"),
        (
            TherapyEpisode(
                "therapy-a",
                "drug-a",
                "2025-01-01",
                None,
                "1 compressa",
                "antipertensivo",
                ("mattino",),
                "dopo colazione",
            ),
        ),
    )

    assert "Farmaco: Drug A" in card
    assert "Principio attivo: Ingredient A" in card
    assert "Dose: 1 compressa" in card
    assert "Istruzioni: dopo colazione" in card


class _Screen:
    """Minimal ncurses screen recording a deterministic key sequence."""

    def __init__(self, keys: list[int], query: bytes = b"") -> None:
        """Initialize the screen with pending key codes.

        Parameters
        ----------
        keys : list[int]
            Key codes returned by ``getch`` in order.

        Returns
        -------
        None
        """

        self.keys = keys
        self.query = query
        self.drawn: list[str] = []

    def bkgd(self, _character: str, _attributes: int) -> None:
        """Accept the active terminal default color background.

        Parameters
        ----------
        _character : str
            Background fill character.
        _attributes : int
            ncurses default-color attributes.

        Returns
        -------
        None
        """

    def keypad(self, _enabled: bool) -> None:
        """Accept keypad configuration.

        Parameters
        ----------
        _enabled : bool
            Requested keypad state.

        Returns
        -------
        None
        """

    def erase(self) -> None:
        """Accept screen clearing.

        Returns
        -------
        None
        """

    def getmaxyx(self) -> tuple[int, int]:
        """Return a realistic terminal size.

        Returns
        -------
        tuple[int, int]
            Rows and columns.
        """

        return (32, 120)

    def addstr(self, _row: int, _column: int, text: str, _attributes: int = 0) -> None:
        """Record rendered text.

        Parameters
        ----------
        _row : int
            Target row.
        _column : int
            Target column.
        text : str
            Rendered text.
        _attributes : int, optional
            Requested ncurses attributes.

        Returns
        -------
        None
        """

        self.drawn.append(text)

    def refresh(self) -> None:
        """Accept a screen refresh.

        Returns
        -------
        None
        """

    def getch(self) -> int:
        """Return the next synthetic key.

        Returns
        -------
        int
            ncurses key code.
        """

        return self.keys.pop(0)

    def getstr(self, _row: int, _column: int, _limit: int) -> bytes:
        """Return synthetic text entered at the manual search prompt.

        Parameters
        ----------
        _row : int
            Prompt row.
        _column : int
            Prompt column.
        _limit : int
            Input byte limit.

        Returns
        -------
        bytes
            Pending synthetic operator input.
        """

        return self.query


def _candidates() -> tuple[AifaCandidate, ...]:
    """Build two synthetic candidates for ncurses interaction tests.

    Returns
    -------
    tuple[sanikey.leaflets.AifaCandidate, ...]
        Ordered synthetic candidates.
    """

    return (
        AifaCandidate("Drug A", "123", "456", strength="10 mg"),
        AifaCandidate("Drug B", "123", "457", strength="20 mg"),
    )


def test_review_screen_navigates_and_approves_selected_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify navigation selects the intended candidate before approval.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    screen = _Screen([curses.KEY_DOWN, ord("a")])
    monkeypatch.setattr(leaflet_tui.curses, "start_color", lambda: None)
    monkeypatch.setattr(leaflet_tui.curses, "use_default_colors", lambda: None)
    monkeypatch.setattr(leaflet_tui.curses, "color_pair", lambda _pair: 0)
    monkeypatch.setattr(leaflet_tui.curses, "curs_set", lambda _value: None)

    result = _review_screen(screen, Medication("drug-a", "Drug A"), (), _candidates())

    assert result.candidate_index == 2
    assert not result.exit_requested
    assert "Candidati AIFA" in screen.drawn
    assert "Terapia curata" in screen.drawn
    assert any("Drug B" in text for text in screen.drawn)


def test_review_screen_rejects_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify rejection returns no selection and leaves the TOML untouched.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    monkeypatch.setattr(leaflet_tui.curses, "curs_set", lambda _value: None)
    monkeypatch.setattr(leaflet_tui.curses, "start_color", lambda: None)
    monkeypatch.setattr(leaflet_tui.curses, "use_default_colors", lambda: None)
    monkeypatch.setattr(leaflet_tui.curses, "color_pair", lambda _pair: 0)

    result = _review_screen(
        _Screen([ord("r")]), Medication("drug-a", "Drug A"), (), _candidates()
    )

    assert result.candidate_index is None
    assert not result.exit_requested


def test_review_screen_quits_immediately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify q requests exit rather than rejecting only one candidate.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    monkeypatch.setattr(leaflet_tui.curses, "curs_set", lambda _value: None)
    monkeypatch.setattr(leaflet_tui.curses, "start_color", lambda: None)
    monkeypatch.setattr(leaflet_tui.curses, "use_default_colors", lambda: None)
    monkeypatch.setattr(leaflet_tui.curses, "color_pair", lambda _pair: 0)

    result = _review_screen(
        _Screen([ord("q")]), Medication("drug-a", "Drug A"), (), _candidates()
    )

    assert result.candidate_index is None
    assert result.exit_requested


def test_review_screen_requests_manual_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify s returns the entered manual AIFA query.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    for name in ("curs_set", "start_color", "use_default_colors", "color_pair"):
        monkeypatch.setattr(
            leaflet_tui.curses,
            name,
            (lambda _value=None: 0)
            if name in {"curs_set", "color_pair"}
            else lambda: None,
        )
    monkeypatch.setattr(leaflet_tui.curses, "echo", lambda: None)
    monkeypatch.setattr(leaflet_tui.curses, "noecho", lambda: None)

    result = _review_screen(
        _Screen([ord("s")], b"Zanedip"),
        Medication("zanedip", "Zanedip 10 mg"),
        (),
        (),
    )

    assert result.manual_query == "Zanedip"
    assert not result.exit_requested


def test_review_screen_marks_non_aifa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify n returns an explicit non-AIFA decision.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    monkeypatch.setattr(leaflet_tui.curses, "curs_set", lambda _value: None)
    monkeypatch.setattr(leaflet_tui.curses, "start_color", lambda: None)
    monkeypatch.setattr(leaflet_tui.curses, "use_default_colors", lambda: None)
    monkeypatch.setattr(leaflet_tui.curses, "color_pair", lambda _pair: 0)

    result = _review_screen(
        _Screen([ord("n")]), Medication("supplement", "Supplemento"), (), ()
    )

    assert result.mark_non_aifa
