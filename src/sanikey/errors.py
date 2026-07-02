"""Application-specific exceptions for SaniKey."""

from __future__ import annotations


class SaniKeyError(Exception):
    """Base class for deterministic SaniKey failures."""


class ConfigError(SaniKeyError):
    """Raised when configuration is missing or invalid."""


class PrivacyError(SaniKeyError):
    """Raised when real-data paths violate repository privacy rules."""
