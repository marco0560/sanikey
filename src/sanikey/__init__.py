"""sanikey package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("sanikey")
except PackageNotFoundError:
    __version__ = "development"
