"""Version metadata tests."""

from __future__ import annotations

from sanikey import __version__
from sanikey.version import source_checkout_version


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


def test_version_matches_current_checkout_when_scm_metadata_is_available() -> None:
    """Ensure editable development runs do not expose stale package metadata.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    source_version = source_checkout_version()
    if source_version is not None:
        assert __version__ == source_version
