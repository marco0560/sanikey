"""Progress output tests."""

from __future__ import annotations

from io import StringIO

from sanikey.progress import ProgressDots


class TtyStringIO(StringIO):
    """StringIO stream that behaves like an interactive terminal.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    def isatty(self) -> bool:
        """Return terminal status for tests.

        Parameters
        ----------
        None

        Returns
        -------
        bool
            Always ``True``.
        """

        return True


def test_progress_dots_render_on_tty() -> None:
    """Verify progress dots render on interactive streams.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    stream = TtyStringIO()
    progress = ProgressDots(enabled=True, stream=stream, interval=2)

    progress.begin("scan-documents patient-a", total=5)
    for index in range(1, 6):
        progress.advance(index, total=5)
    progress.done("done files=5")

    assert stream.getvalue() == "scan-documents patient-a: 0/5 ... done files=5\n"


def test_progress_dots_are_silent_on_non_tty() -> None:
    """Verify progress dots do not render on non-interactive streams.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    stream = StringIO()
    progress = ProgressDots(enabled=True, stream=stream, interval=1)

    progress.begin("scan-documents patient-a", total=1)
    progress.advance(1, total=1)
    progress.done("done")

    assert stream.getvalue() == ""


def test_progress_dots_render_each_advance_without_total() -> None:
    """Verify open-ended progress lines render one dot per advance.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    stream = TtyStringIO()
    progress = ProgressDots(enabled=True, stream=stream, interval=50)

    progress.begin("stage-containers patient-a")
    for index in range(1, 4):
        progress.advance(index)
    progress.done("done containers=3")

    assert stream.getvalue() == "stage-containers patient-a: ... done containers=3\n"


def test_progress_dots_support_line_interval_override() -> None:
    """Verify progress lines can override the default dot interval.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    stream = TtyStringIO()
    progress = ProgressDots(enabled=True, stream=stream, interval=50)

    progress.begin("scan-documents patient-a", total=40, interval=20)
    for index in range(1, 41):
        progress.advance(index, total=40)
    progress.done("done files=40")

    assert stream.getvalue() == "scan-documents patient-a: 0/40 .. done files=40\n"
