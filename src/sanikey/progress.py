"""Terminal progress helpers for long-running SaniKey commands."""

from __future__ import annotations

import sys
from typing import Protocol, TextIO


class ProgressReporter(Protocol):
    """Progress reporter protocol.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    def begin(
        self,
        label: str,
        *,
        total: int | None = None,
        interval: int | None = None,
    ) -> None:
        """Begin one progress line.

        Parameters
        ----------
        label : str
            Human-readable operation label.
        total : int | None, optional
            Expected item count when known.
        interval : int | None, optional
            Dot interval override for the progress line.

        Returns
        -------
        None
        """

    def advance(self, completed: int, *, total: int | None = None) -> None:
        """Advance the current progress line.

        Parameters
        ----------
        completed : int
            Completed item count.
        total : int | None, optional
            Expected item count when known.

        Returns
        -------
        None
        """

    def done(self, summary: str = "done") -> None:
        """Finish the current progress line.

        Parameters
        ----------
        summary : str, optional
            Completion summary.

        Returns
        -------
        None
        """


class ProgressDots:
    """Render pytest-style progress dots on an interactive stream.

    Parameters
    ----------
    enabled : bool
        Whether progress output is enabled.
    stream : TextIO, optional
        Output stream. Defaults to ``sys.stderr``.
    interval : int, optional
        Number of completed items per dot.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        stream: TextIO | None = None,
        interval: int = 50,
    ) -> None:
        """Initialize a progress dot renderer.

        Parameters
        ----------
        enabled : bool
            Requested progress state.
        stream : TextIO | None, optional
            Output stream. Defaults to ``sys.stderr``.
        interval : int, optional
            Number of completed items per dot.

        Returns
        -------
        None
        """

        self.stream = stream or sys.stderr
        self.enabled = enabled and self.stream.isatty()
        self.interval = max(1, interval)
        self._current_interval = self.interval
        self._last_dot_at = 0
        self._active = False

    def begin(
        self,
        label: str,
        *,
        total: int | None = None,
        interval: int | None = None,
    ) -> None:
        """Begin one progress line.

        Parameters
        ----------
        label : str
            Human-readable operation label.
        total : int | None, optional
            Expected item count when known.
        interval : int | None, optional
            Dot interval override for the progress line.

        Returns
        -------
        None
        """

        if not self.enabled:
            return
        suffix = "" if total is None else f" 0/{total}"
        print(f"{label}:{suffix} ", end="", file=self.stream, flush=True)
        self._current_interval = self.interval if interval is None else max(1, interval)
        self._last_dot_at = 0
        self._active = True

    def advance(self, completed: int, *, total: int | None = None) -> None:
        """Advance the current progress line.

        Parameters
        ----------
        completed : int
            Completed item count.
        total : int | None, optional
            Expected item count when known.

        Returns
        -------
        None
        """

        if not self.enabled or not self._active:
            return
        interval = self._current_interval
        if total is None or total <= interval:
            interval = 1
        should_dot = completed == total or completed - self._last_dot_at >= interval
        if should_dot:
            print(".", end="", file=self.stream, flush=True)
            self._last_dot_at = completed

    def done(self, summary: str = "done") -> None:
        """Finish the current progress line.

        Parameters
        ----------
        summary : str, optional
            Completion summary.

        Returns
        -------
        None
        """

        if not self.enabled or not self._active:
            return
        print(f" {summary}", file=self.stream, flush=True)
        self._active = False
