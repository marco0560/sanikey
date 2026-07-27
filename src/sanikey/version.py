"""Resolve SaniKey versions for source checkouts and installed distributions."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as metadata_version
from pathlib import Path


def source_checkout_root() -> Path | None:
    """Return the repository root when this package runs from a checkout.

    Parameters
    ----------
    None

    Returns
    -------
    pathlib.Path | None
        Checkout root containing both ``pyproject.toml`` and ``.git``, or
        ``None`` when the package is installed from a distribution.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / ".git").exists():
            return parent
    return None


def source_checkout_version() -> str | None:
    """Return the current SCM version when executed from a source checkout.

    Parameters
    ----------
    None

    Returns
    -------
    str | None
        Version computed from the checkout's ``setuptools-scm`` configuration,
        or ``None`` when SCM metadata or the optional development dependency is
        unavailable.
    """
    root = source_checkout_root()
    if root is None:
        return None
    try:
        from setuptools_scm import get_version
    except ImportError:
        return None
    try:
        return get_version(
            root=str(root),
            relative_to=__file__,
            tag_regex=r"^v(?P<version>\d+\.\d+\.\d+(?:\.post\d+)?)$",
            version_scheme="post-release",
            local_scheme="no-local-version",
        )
    except LookupError:
        return None


def package_version() -> str:
    """Return the authoritative version for the active SaniKey code.

    Parameters
    ----------
    None

    Returns
    -------
    str
        SCM-derived version for a development checkout, installed distribution
        metadata for a wheel, or ``"development"`` when neither is available.
    """
    source_version = source_checkout_version()
    if source_version is not None:
        return source_version
    try:
        return metadata_version("sanikey")
    except PackageNotFoundError:
        return "development"
