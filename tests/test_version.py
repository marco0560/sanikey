"""Version metadata tests."""

from __future__ import annotations

from sanikey import __version__


def test_version_is_defined() -> None:
    """Verify the package exposes a non-empty version string.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    assert __version__


def test_version_is_not_static_template_literal() -> None:
    """Verify the generated package does not expose a hard-coded template version.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    assert __version__ != "0.1.0"
